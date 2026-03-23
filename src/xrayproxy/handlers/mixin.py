import asyncio
import hashlib
import json
from logging import getLogger
from typing import TYPE_CHECKING, Any, List, Literal, Optional

import aioboto3
import brotli
import sqlalchemy
from mitmproxy.http import Response
from zstandard import ZstdCompressor

from xrayproxy.config import ApiLogConfig, Config
from xrayproxy.lib.utils import decode_json, encode_json, format_json
from xrayproxy.lib.xray import Context, XRayWebhookClient, create_webhook_client

if TYPE_CHECKING:
    from aiobotocore.session import ClientCreatorContext
    from types_aiobotocore_s3.client import S3Client
    from types_aiobotocore_s3.type_defs import GetObjectOutputTypeDef

logger = getLogger(__name__)


CompressionMethodChoices = Literal["br", "zstd", "none"]
DEFAULT_COMPRESSION_METHOD: CompressionMethodChoices = "zstd"


class DatabaseMixin:
    _db_conn: sqlalchemy.Connection

    def set_database_connection(self, conn: sqlalchemy.Connection) -> None:
        self._db_conn = conn


class JsonMixin:
    _pretty_json: bool = False

    def configure_json_response_handler(self, config: ApiLogConfig) -> None:
        self._pretty_json = config.pretty

    def get_json(self, context: Context) -> Optional[str]:
        if context.response.content is None:
            return None

        try:
            return format_json(context.response.content, self._pretty_json)
        except (UnicodeDecodeError, json.JSONDecodeError) as err:
            logger.error(f"{context.request.url} returned invalid JSON: {err}")
            # logger.debug(f"Response body: {context.response_body}")
            return None

    @staticmethod
    def decode_json(context: Context) -> Optional[dict[str, Any]]:
        if context.response.json is not None:
            return context.response.json

        if context.response.content is None:
            return None

        try:
            data = decode_json(context.response.content)
            if not isinstance(data, dict):
                logger.warning(f"JSON data is not a dict but {type(data)}: url={context.request.url}")
                return None

            if "api_result" not in data:
                logger.warning(f"JSON data does not contain 'api_result': url={context.request.url}")
                return None

            if int(data["api_result"]) != 1:
                logger.warning(f"API result is not 1: url={context.request.url}, data={data}")
                return None

            context.response.set_json(data)

            return data
        except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as err:
            logger.error(f"{context.request.url} returned invalid JSON: {err}")
            # logger.debug(f"Response body: {context.response_body)}")
            return None

    def encode_json(self, data: Any) -> str:
        return encode_json(data, self._pretty_json)

    @classmethod
    def make_upload_data(
        cls, object_key: str, json_str: str, compression: CompressionMethodChoices = DEFAULT_COMPRESSION_METHOD
    ) -> tuple[str, bytes, dict[str, Any]]:
        """
        JSONを圧縮してS3(R2)にアップロードするためのデータを作成する
        """
        # JSONは仕様上UTF-8エンコーディングなので "; charset=utf-8" は不要
        # 圧縮方法は Content-Encoding で指定する
        s3_system_metadata = {"ContentType": "application/json"}
        key = cls.compressed_json_object_key(object_key, compression)
        json_bytes = json_str.encode("utf-8")
        if compression == "br":
            body = brotli.compress(json_bytes, mode=brotli.MODE_TEXT)
            s3_system_metadata["ContentEncoding"] = "br"
        elif compression == "zstd":
            cctx = ZstdCompressor()
            body = cctx.compress(json_bytes)
            s3_system_metadata["ContentEncoding"] = "zstd"
        else:
            body = json_bytes

        return key, body, s3_system_metadata

    @staticmethod
    def compressed_json_object_key(
        object_key: str,
        compression: CompressionMethodChoices = DEFAULT_COMPRESSION_METHOD,
    ) -> str:
        if object_key.endswith(".json"):
            if compression == "br":
                return object_key + ".br"
            elif compression == "zstd":
                return object_key + ".zst"
            else:
                return object_key
        else:
            return object_key


class ObjectStorageMixin:
    _boto_session: aioboto3.Session
    _s3_bucket: str
    _s3_client_kwargs: dict[str, Any]
    _s3_allow_public_access: bool

    def set_boto_session(self, session: aioboto3.Session) -> None:
        self._boto_session = session

    def configure_object_storage(self, config: Config, bucket: str) -> None:
        self._s3_bucket = bucket
        self._s3_client_kwargs = config.storage.to_s3_client_kwargs()
        self._s3_allow_public_access = config.storage.allow_public_access

    def create_s3_client(self) -> "ClientCreatorContext[S3Client]":
        return self._boto_session.client("s3", **self._s3_client_kwargs)

    async def get_object(
        self,
        s3: "S3Client",
        key: str,
    ) -> Optional["GetObjectOutputTypeDef"]:
        try:
            return await s3.get_object(Bucket=self._s3_bucket, Key=key)
        except s3.exceptions.ClientError as err:
            if err.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise

    async def put_object(
        self,
        s3: "S3Client",
        key: str,
        body: bytes,
        original_url: Optional[str],
        extra_metadata: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> None:
        metadata = dict(extra_metadata or {})
        if original_url is not None:
            metadata["x-ray-original-url"] = original_url

        await s3.put_object(
            Bucket=self._s3_bucket,
            Key=key,
            Body=body,
            Metadata=metadata,
            **kwargs,
        )

    async def put_object_if_none_match(
        self,
        s3: "S3Client",
        key: str,
        body: bytes,
        original_url: Optional[str],
        extra_metadata: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> bool:
        """
        Returns:
            True: put_object が成功した
            False: ETagが一致したため、put_object が実行されなかった
        """
        h = hashlib.md5()
        h.update(body)
        md5digest = h.hexdigest()

        try:
            # このメソッドのユースケースではETagが一致する場合が多いことを期待している。
            # ゆえにPutObjectのカスタムヘッダでIf-None-Matchを指定するのでなく、
            # 通信量節約のためHeadObjectでETagを取得して比較する。
            response = await s3.head_object(Bucket=self._s3_bucket, Key=key)
            # Cloudflare R2のETagは16進数形式のMD5ハッシュ値をダブルクォートで囲んだもの
            if response["ETag"].strip('"') == md5digest:
                return False
        except s3.exceptions.ClientError as err:
            # HeadObjectでオブジェクトが存在しない場合のエラーコードは404
            # GetObjectでオブジェクトが存在しない場合のエラーコードNoSuchKeyとは異なる
            if err.response["Error"]["Code"] != "404":
                raise

        # オブジェクトが存在しなかった場合とETagが一致しなかった場合、put_objectを実行する
        await self.put_object(
            s3,
            key,
            body,
            original_url,
            extra_metadata,
            **kwargs,
        )
        return True

    async def copy_object(
        self,
        s3: "S3Client",
        src_key: str,
        dst_key: str,
        original_url: Optional[str],
        extra_metadata: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> None:
        metadata = dict(extra_metadata or {})
        if original_url is not None:
            metadata["x-ray-original-url"] = original_url
        await s3.copy_object(
            Bucket=self._s3_bucket,
            Key=dst_key,
            CopySource={
                "Bucket": self._s3_bucket,
                "Key": src_key,
            },
            Metadata=metadata,
            **kwargs,
        )

    async def copy_object_if_not_exists(
        self,
        s3: "S3Client",
        src_key: str,
        dst_key: str,
        original_url: Optional[str],
        extra_metadata: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> bool:
        """
        Returns:
            True: dst_key が存在しないため、src_key を dst_key にコピーした
            False: dst_key が既に存在しており、コピーしなかった
        """
        if await self.object_exists(s3, dst_key):
            return False

        await self.copy_object(s3, src_key, dst_key, original_url, extra_metadata, **kwargs)
        return True

    async def copy_object_if_none_match(
        self,
        s3: "S3Client",
        src_key: str,
        dst_key: str,
        original_url: Optional[str],
        extra_metadata: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> bool:
        """
        Returns:
            True: dst_key が存在しないか、ETagが一致しなかったため、src_key を dst_key にコピーした
            False: dst_key が既に存在しておりETagもsrc_keyと一致したため、コピーしなかった
        """
        try:
            response1 = await s3.head_object(Bucket=self._s3_bucket, Key=src_key)
            etag = response1["ETag"]
        except s3.exceptions.ClientError as err:
            if err.response["Error"]["Code"] == "404":
                return False
            else:
                raise

        try:
            response2 = await s3.head_object(Bucket=self._s3_bucket, Key=dst_key)
            if response2["ETag"] == etag:
                return False
        except s3.exceptions.ClientError as err:
            if err.response["Error"]["Code"] != "404":
                raise

        await self.copy_object(s3, src_key, dst_key, original_url, extra_metadata, **kwargs)
        return True

    async def object_exists(self, s3: "S3Client", key: str) -> bool:
        try:
            await s3.head_object(Bucket=self._s3_bucket, Key=key)
            return True
        except s3.exceptions.ClientError as err:
            if err.response["Error"]["Code"] == "404":
                return False
            raise


class ResponseFileMixin:
    @staticmethod
    def response_file(file_path: str, content_type: str, if_none_match: Optional[str] = None) -> Response:
        with open(file_path, "rb") as f:
            content = f.read()
            m = hashlib.md5()
            m.update(content)
            md5sum = m.hexdigest()
            etag = f'"{md5sum}"'

            if if_none_match == etag:
                return Response.make(
                    status_code=304,
                    content=b"",
                )
            else:
                return Response.make(
                    status_code=200,
                    content=content,
                    headers={
                        "Content-Type": content_type,
                        "ETag": etag,
                    },
                )


class XRayWebhookClientMixin:
    _webhook_clients: List[XRayWebhookClient] = []

    def configure_webhook_client(self, config: Config) -> None:
        old_clients = self._webhook_clients
        for client in old_clients:
            asyncio.ensure_future(client.dispose())

        self._webhook_clients = [create_webhook_client(webhook) for webhook in config.x_ray.webhook]

    async def done_webhook_client(self) -> None:
        if self._webhook_clients:
            await asyncio.gather(*[client.dispose() for client in self._webhook_clients])
        self._webhook_clients = []

    async def notify_resource_update(self, key: str, timestamp_in_millis: int) -> None:
        if self._webhook_clients:
            await asyncio.gather(
                *[client.update_resource(key, timestamp_in_millis) for client in self._webhook_clients]
            )
