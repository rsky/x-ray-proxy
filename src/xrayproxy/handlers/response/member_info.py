import asyncio
from collections.abc import Mapping
from logging import getLogger
from typing import Any, Optional

from xrayproxy.config import Config
from xrayproxy.lib.decorators import error_logging
from xrayproxy.lib.xray import Context

from ..base import BaseResponseHandler
from ..mixin import (
    DEFAULT_COMPRESSION_METHOD,
    CompressionMethodChoices,
    DatabaseMixin,
    JsonMixin,
    ObjectStorageMixin,
    XRayWebhookClientMixin,
)

logger = getLogger(__name__)

# 母港データ。母港表示の度に取得する
PORT_API_PATH = "/kcsapi/api_port/port"

# 起動時に必要尾な情報を取得するAPI
REQUIRE_INFO_API_PATH = "/kcsapi/api_get_member/require_info"

# スキンIDとボリューム設定を取得するAPI
# このAPIは起動時真っ先に読み込まれ、レスポンスにapi_member_idを含まないのでmember_idの特定ができない
OPTION_SETTING_API_PATH = "/kcsapi/api_start2/get_option_setting"

BASIC_MEMBER_INFO_API_PATHS = (
    "/kcsapi/api_get_member/basic",
    "/kcsapi/api_get_member/mapinfo",
    "/kcsapi/api_get_member/questlist",
    "/kcsapi/api_get_member/slot_item",
    "/kcsapi/api_get_member/useitem",
)

API_PATHS_TO_HANDLE = frozenset((PORT_API_PATH, REQUIRE_INFO_API_PATH) + BASIC_MEMBER_INFO_API_PATHS)


class MemberInfoResponseHandler(
    BaseResponseHandler, DatabaseMixin, JsonMixin, ObjectStorageMixin, XRayWebhookClientMixin
):
    """
    母港APIレスポンスとメンバー基本情報の取得APIレスポンスを処理する
    """

    # キャッシュ: member_id -> "nickname@host"
    # 1人〜ごく小数の人間が使うことを想定しているので、
    # DBを使ったりLRUキャッシュにしたりせず、全件を辞書で保持する
    _member_info_cache: dict[int, str] = {}

    def __init__(self) -> None:
        super().__init__(logger)

    def configure(self, config: Config) -> None:
        super().configure(config)
        self.configure_object_storage(config, config.storage.data_bucket)
        self.configure_json_response_handler(config.api_log)
        self.configure_webhook_client(config)

    def accept(self, context: Context) -> bool:
        return context.request.path in API_PATHS_TO_HANDLE

    async def response(self, context: Context) -> None:
        data = self.decode_json(context)
        if not data:
            return

        api_token = self.get_api_token(context.request)
        path = context.request.path
        member_id, contains_member_id = self.detect_member_id(path, api_token, data)
        if member_id is None:
            return

        api_name = path.split("/")[-1]
        object_key = f"member/{member_id}/{api_name}.json"
        if api_token is not None and contains_member_id:
            self.set_member_id(api_token, member_id)

        json_str = self.encode_json(data)
        await self.upload_data(object_key, json_str, context.request.url, context.respond_at_millis)

        if path == REQUIRE_INFO_API_PATH:
            # マスターデータをユーザーごとのパスにコピーする特殊処理
            # /kcsapi/api_start2/getData の段階ではAPIトークンから
            # ユーザーIDを取得できないため、このタイミングでコピーする
            master_data_src_key = f"master_data/{context.request.host}/api_start2.json"
            master_data_dst_key = f"member/{member_id}/api_start2.json"
            await self.copy_master_data(master_data_src_key, master_data_dst_key, context.respond_at_millis)

        if path == PORT_API_PATH:
            # 母港APIレスポンスからニックネームを取得して提督ID、鎮守府サーバーのホスト名とともにWebhookに送信する
            nickname = data["api_data"]["api_basic"]["api_nickname"]
            host = context.request.host
            await self._send_member_info_to_webhook(member_id, nickname, host)

    def detect_member_id(
        self, path: str, api_token: Optional[str], data: Mapping[str, Any]
    ) -> tuple[Optional[int], bool]:
        try:
            if path == PORT_API_PATH or path == "/kcsapi/api_get_member/require_info":
                member_id = int(data["api_data"]["api_basic"]["api_member_id"])
                return member_id, True
            elif path == "/kcsapi/api_get_member/basic":
                member_id = int(data["api_data"]["api_member_id"])
                return member_id, True
            elif api_token:
                return self.get_member_id(api_token), False
            else:
                return None, False
        except (AttributeError, KeyError, ValueError) as err:
            logger.error(f"{path}: api_data.api_basic.api_member_id not found: {err}")
            return None, False

    @error_logging(logger)
    async def upload_data(
        self,
        object_key: str,
        json_str: str,
        url: str,
        timestamp_in_millis: int,
        compression: CompressionMethodChoices = DEFAULT_COMPRESSION_METHOD,
    ) -> None:
        updated_resource_keys = []

        async with self.create_s3_client() as s3:
            (key, body, s3_system_metadata) = self.make_upload_data(object_key, json_str, compression=compression)
            if self._s3_allow_public_access:
                s3_system_metadata["ACL"] = "public-read"

            await self.put_object(s3, key, body, url, purge_cache=True, **s3_system_metadata)
            updated_resource_keys.append(key)

        for key in updated_resource_keys:
            await self.notify_resource_update(key, timestamp_in_millis)

    @error_logging(logger)
    async def copy_master_data(
        self,
        src_key: str,
        dst_key: str,
        timestamp_in_millis: int,
        compression: CompressionMethodChoices = DEFAULT_COMPRESSION_METHOD,
    ) -> None:
        async with self.create_s3_client() as s3:
            compressed_src_key = self.compressed_json_object_key(src_key, compression)
            compressed_dst_key = self.compressed_json_object_key(dst_key, compression)

            s3_system_metadata = {}
            if self._s3_allow_public_access:
                s3_system_metadata["ACL"] = "public-read"

            if await self.copy_object_if_none_match(
                s3,
                src_key=compressed_src_key,
                dst_key=compressed_dst_key,
                original_url=None,
                extra_metadata=None,
                purge_cache=True,
                **s3_system_metadata,
            ):
                await self.notify_resource_update(compressed_dst_key, timestamp_in_millis)

    @error_logging(logger)
    async def _send_member_info_to_webhook(self, member_id: int, nickname: str, host: str) -> None:
        # キャッシュと同じ内容なら送信しない
        cache_value = f"{nickname}@{host}"
        if self._member_info_cache.get(member_id) == cache_value:
            return

        if self._webhook_clients:
            await asyncio.gather(
                *[client.send_member_info(member_id, nickname, host) for client in self._webhook_clients]
            )

        self._member_info_cache[member_id] = cache_value
