import asyncio
import io
import re
import urllib.parse
from dataclasses import dataclass
from enum import StrEnum
from logging import getLogger
from pathlib import PurePosixPath
from typing import Optional

from PIL import Image

from xrayproxy.config import Config
from xrayproxy.generated.sqlc.master_data import (
    Querier,
    SetShipgraphDamagedSizeParams,
    SetShipgraphSizeParams,
)
from xrayproxy.handlers.base import BaseResponseHandler
from xrayproxy.handlers.mixin import (
    DatabaseMixin,
    ObjectStorageMixin,
    XRayWebhookClientMixin,
)
from xrayproxy.lib.decorators import error_logging
from xrayproxy.lib.sprite import json_to_sprite, sprite_to_css, sprite_to_html
from xrayproxy.lib.utils import filename_with_extension
from xrayproxy.lib.xray import Context

logger = getLogger(__name__)


KCS2_RESOURCE_PREFIXES = (
    "/kcs2/img/",
    "/kcs2/resources/",
)

SHIP_GRAPHIC_PATTERN = "/kcs2/resources/ship/*/*.png"

FULL_SIZE_SHIP_GRAPHIC_PREFIXES = (
    "/kcs2/resources/ship/full/",
    "/kcs2/resources/ship/full_dmg/",
)

LOGBOOK_KAI_RESOURCE_PREFIXES = (
    "/kcs2/img/common/",
    "/kcs2/img/duty/",
    "/kcs2/img/sally/",
)

LEAST_COMMON_RESOURCE_SET = {
    "/kcs2/img/common/common_event.png",
    "/kcs2/img/common/common_event.json",
    "/kcs2/img/common/common_icon_weapon.png",
    "/kcs2/img/common/common_icon_weapon.json",
    "/kcs2/img/common/common_misc.png",
    "/kcs2/img/common/common_misc.json",
}


def is_kcs2_resource(path: str) -> bool:
    """
    艦これのリソースかどうかを判定する
    """
    return any(path.startswith(prefix) for prefix in KCS2_RESOURCE_PREFIXES)


def is_logbook_kai_compatible_resource(path: str) -> bool:
    """
    航海日誌(logbook-kai)で利用しているリソースかどうかを判定する
    """
    return any(path.startswith(prefix) for prefix in LOGBOOK_KAI_RESOURCE_PREFIXES) and (
        path.endswith(".png") or path.endswith(".json")
    )


def is_least_resource(path: str) -> bool:
    """
    必要最小限のリソースかどうかを判定する
    """
    return path in LEAST_COMMON_RESOURCE_SET


def is_ship_graphic(path: str) -> bool:
    """
    艦娘画像かどうかを判定する
    """
    return PurePosixPath(path).match(SHIP_GRAPHIC_PATTERN)


def is_ship_full_graphic(path: str) -> bool:
    """
    フルサイズの艦娘画像かどうかを判定する
    """
    return is_ship_graphic(path) and any(path.startswith(prefix) for prefix in FULL_SIZE_SHIP_GRAPHIC_PREFIXES)


def make_resource_object_key(path: str, content_type: str) -> str:
    return filename_with_extension("assets/" + path.lstrip("/"), content_type)


def make_ship_graphic_object_keys(
    graphic_type: str, padded_ship_id: str, copy_suffix: Optional[str], extension: str
) -> tuple[str, Optional[str]]:
    base_key = f"assets/ships/{padded_ship_id}/{graphic_type}"
    key = f"{base_key}{extension}"

    # フルサイズ画像は期間限定グラフィックを残すためバージョンを含むsuffixつきファイル名でコピーする
    # NOTE: 潜水母艦のspecial, special_dmgも期間限定グラフィックがあるようだが。。。
    if copy_suffix and graphic_type in {"full", "full_dmg"}:
        copy_key = f"{base_key}{copy_suffix}{extension}"
    else:
        copy_key = None

    return key, copy_key


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class StoreContext:
    url: str
    host: str
    path: str
    query: dict[str, str]
    content_type: str
    content: bytes
    timestamp_in_millis: int


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class UploadContext:
    url: Optional[str]
    content_type: str
    body: bytes
    key: str
    timestamp_in_millis: int
    copy_key: Optional[str] = None
    image_size: Optional[tuple[int, int]] = None


class SaveMode(StrEnum):
    # 全てのリソースを保存
    ALL = "all"
    # デフォルトの保存モード
    DEFAULT = "default"
    # 必要最小限のリソースのみ保存
    LEAST = "least"
    # 何も保存しない
    NONE = "none"


class ResourceResponseHandler(BaseResponseHandler, DatabaseMixin, ObjectStorageMixin, XRayWebhookClientMixin):
    """
    画像等のリソースを処理する
    """

    _save_mode: str
    _ship_graphic_versioning: bool
    _is_sprite_url_escaped_full_path: bool

    _store_queue: asyncio.Queue[StoreContext]
    _store_task: asyncio.Task[None]
    _upload_queue: asyncio.Queue[UploadContext]
    _upload_tasks: tuple[asyncio.Task[None], ...]

    def __init__(self) -> None:
        super().__init__(logger)
        self._save_mode = SaveMode.DEFAULT
        self._ship_graphic_versioning = False
        self._is_sprite_url_escaped_full_path = False

        # 保存キューのタスクは1つだけ
        self._store_queue = asyncio.Queue()
        self._store_task = asyncio.create_task(self.store_worker())

        # アップロードは最大4並列にしてurllib3のコネクションプール数を超えないように
        self._upload_queue = asyncio.Queue()
        self._upload_tasks = tuple(asyncio.create_task(self.upload_worker(f"worker-{i}")) for i in range(4))

    def configure(self, config: Config) -> None:
        super().configure(config)
        self.configure_object_storage(config, config.storage.resource_bucket)

        self._save_mode = config.resource.save_mode or SaveMode.DEFAULT
        self._ship_graphic_versioning = config.resource.ship_graphic_versioning

        self.configure_webhook_client(config)

    async def done(self) -> None:
        await self._store_queue.join()
        await self._upload_queue.join()

        self._store_task.cancel()

        for task in self._upload_tasks:
            task.cancel()

        await asyncio.gather(self._store_task, return_exceptions=True)
        await asyncio.gather(*self._upload_tasks, return_exceptions=True)

        await self.done_webhook_client()

    def accept(self, context: Context) -> bool:
        content_type = context.response.content_type
        if content_type is None or content_type not in {"image/png", "application/json"}:
            return False

        path = context.request.path
        match self._save_mode:
            case SaveMode.ALL:
                return is_kcs2_resource(path)
            case SaveMode.DEFAULT:
                return is_ship_graphic(path) or is_least_resource(path) or is_logbook_kai_compatible_resource(path)
            case SaveMode.LEAST:
                return is_ship_graphic(path) or is_least_resource(path)
            case SaveMode.NONE:
                return False
            case _:
                logger.warning(f"Unknown save mode: {self._save_mode}")
                return False

    async def response(self, context: Context) -> None:
        if context.response.content_type is not None and context.response.content is not None:
            store_ctx = StoreContext(
                url=context.request.url,
                host=context.request.host,
                path=context.request.path,
                query=context.request.query,
                content_type=context.response.content_type,
                content=context.response.content,
                timestamp_in_millis=context.respond_at_millis,
            )
            self._store_queue.put_nowait(store_ctx)

    async def store_worker(self) -> None:
        while True:
            store_ctx = await self._store_queue.get()
            await self.store_worker_impl(store_ctx)
            self._store_queue.task_done()

    async def store_worker_impl(self, store_ctx: StoreContext) -> None:
        image = self.try_convert_png_to_webp(store_ctx)
        if image:
            webp_content, width, height = image
            image_size = (width, height)
        else:
            webp_content = None
            width = 0
            height = 0
            image_size = None

        if webp_content:
            content_type = "image/webp"
            content_to_upload = webp_content
            png_as_webp = True
        else:
            content_type = store_ctx.content_type
            content_to_upload = store_ctx.content
            png_as_webp = False

        m = re.match(r"^/kcs2/resources/ship/(\w+)/(\d+)(_\w+)?\.png$", store_ctx.path)
        if m:
            # 艦娘画像の場合
            graphic_type, padded_ship_id, extra = m.groups()
            version = store_ctx.query.get("version")
            extension = ".webp" if png_as_webp else ".png"
            copy_suffix = None
            if version and self._ship_graphic_versioning:
                copy_suffix = f"_v{version}"
            if extra.startswith("_d_"):
                # 弱体化(装甲破砕後)画像のパスは /kcs2/resources/ship/full/{padded_ship_id}_d_{hash}_{filename}.png
                # hash は通常のフルサイズ画像と同じで、filename も api_mst_shipgraph にあるもの
                graphic_type += "_debuff"  # full_d だと full_dmg との区別がつきにくいので full_debuff とする
            (object_key, copy_object_key) = make_ship_graphic_object_keys(
                graphic_type, padded_ship_id, copy_suffix, extension
            )

            # 艦娘フルサイズ画像ならサイズをデータベースに記録する (レコードは既に作成済みの前提)
            if is_ship_full_graphic(store_ctx.path):
                self.update_ship_full_graphic_size(
                    store_ctx.host, padded_ship_id, graphic_type, version, width, height
                )
        else:
            # その他のリソースの場合
            object_key = make_resource_object_key(store_ctx.path, store_ctx.content_type)
            if png_as_webp and object_key.endswith(".png"):
                object_key = object_key[:-4] + ".webp"
            copy_object_key = None

        upload_ctx = UploadContext(
            url=store_ctx.url,
            content_type=content_type,
            body=content_to_upload,
            key=object_key,
            timestamp_in_millis=store_ctx.timestamp_in_millis,
            copy_key=copy_object_key,
            image_size=image_size,
        )
        self._upload_queue.put_nowait(upload_ctx)

        # CSSスプライトのJSONの場合
        if object_key.endswith(".json") and is_least_resource(store_ctx.path):
            self.store_sprite(store_ctx, object_key)

    def update_ship_full_graphic_size(
        self, host: str, padded_ship_id: str, graphic_type: str, version_str: Optional[str], width: int, height: int
    ) -> None:
        if version_str is None or graphic_type not in {"full", "full_dmg"}:
            return None

        try:
            ship_id = int(padded_ship_id.lstrip("0"))
        except ValueError as err:
            self.log_error(err)
            return None

        try:
            version = int(version_str)
        except ValueError as err:
            version = 0
            self.log_error(err)

        querier = Querier(self._db_conn)
        if graphic_type == "full":
            querier.set_shipgraph_size(
                SetShipgraphSizeParams(
                    host=host,
                    ship_id=ship_id,
                    version=version,
                    full_width=width,
                    full_height=height,
                )
            )
        else:
            querier.set_shipgraph_damaged_size(
                SetShipgraphDamagedSizeParams(
                    host=host,
                    ship_id=ship_id,
                    version=version,
                    full_dmg_width=width,
                    full_dmg_height=height,
                )
            )
        self._db_conn.commit()

    def store_sprite(self, store_ctx: StoreContext, object_key: str) -> None:
        """
        spritesmithで生成されたJSONからCSSスプライトと一覧用のHTMLを生成してアップロードする

        Publicなbucketに保存され、直接アクセスされることを想定しているが、
        WorkersでR2から取得してKVにキャッシュすることも考えられる
        """
        object_key_prefix = object_key[:-5]  # .jsonを除いた部分
        css_object_key = object_key_prefix + ".css"
        html_object_key = object_key_prefix + ".html"
        # 画像(sprite.meta.image)はJSONと同じstemで拡張子.webpと決め打ち (常にPNGをWebPに変換するので)
        image_object_key = object_key_prefix + ".webp"

        try:
            sprite = json_to_sprite(store_ctx.content)
            sprite_name = PurePosixPath(store_ctx.path).stem
            if self._is_sprite_url_escaped_full_path:
                image_url = urllib.parse.quote(image_object_key, safe="")
                css_url = urllib.parse.quote(css_object_key, safe="")
            else:
                image_url = image_object_key.rsplit("/", 1)[-1]
                css_url = css_object_key.rsplit("/", 1)[-1]
            css = sprite_to_css(sprite, sprite_name, image_url=image_url)
            html = sprite_to_html(sprite, sprite_name, css_url=css_url)
        except Exception as err:
            logger.error(f"Failed to generate sprite: {err}")
            return

        # CSSとHTMLをアップロードする
        self._upload_queue.put_nowait(
            UploadContext(
                url=None,
                content_type="text/css",
                body=css.encode("utf-8"),
                key=css_object_key,
                timestamp_in_millis=store_ctx.timestamp_in_millis,
            )
        )
        self._upload_queue.put_nowait(
            UploadContext(
                url=None,
                content_type="text/html",
                body=html.encode("utf-8"),
                key=html_object_key,
                timestamp_in_millis=store_ctx.timestamp_in_millis,
            )
        )

    async def upload_worker(self, name: str) -> None:
        while True:
            upload_ctx = await self._upload_queue.get()
            await self.upload_worker_impl(upload_ctx)
            self._upload_queue.task_done()

    async def upload_worker_impl(self, upload_ctx: UploadContext) -> None:
        self.log(f"Saving resource {upload_ctx.key}")
        await self.upload_resource(upload_ctx)

    @error_logging(logger)
    async def upload_resource(self, upload_ctx: UploadContext) -> None:
        """
        リソースをS3にアップロードする
        """
        s3_system_metadata = {
            "ContentType": upload_ctx.content_type,
        }
        if self._s3_allow_public_access:
            s3_system_metadata["ACL"] = "public-read"

        extra_metadata = {}
        if upload_ctx.image_size:
            extra_metadata["x-ray-image-width"] = str(upload_ctx.image_size[0])
            extra_metadata["x-ray-image-height"] = str(upload_ctx.image_size[1])

        async with self.create_s3_client() as s3:
            saved = await self.put_object_if_none_match(
                s3,
                upload_ctx.key,
                upload_ctx.body,
                upload_ctx.url,
                extra_metadata=extra_metadata,
                purge_cache=True,
                **s3_system_metadata,
            )
            if saved:
                self.log(f"Saved resource {upload_ctx.key}")
                await self.notify_resource_update(upload_ctx.key, upload_ctx.timestamp_in_millis)
            else:
                self.log(f"Resource {upload_ctx.key} did not change")
                # 画像が変更されていなくてもコピー先オブジェクトが
                # 存在しない場合があるので、ここでreturnしない

            if upload_ctx.copy_key is not None:
                # コピー先が存在しない場合のみコピーする (上書きはしない)
                # 404でもCloudflareではデフォルトで3分間キャッシュされるのでpurge_cacheを指定する
                # https://developers.cloudflare.com/cache/concepts/default-cache-behavior/#edge-ttl
                copied = await self.copy_object_if_not_exists(
                    s3,
                    upload_ctx.key,
                    upload_ctx.copy_key,
                    upload_ctx.url,
                    extra_metadata=extra_metadata,
                    purge_cache=True,
                    **s3_system_metadata,
                )
                if copied:
                    self.log(f"Copied resource {upload_ctx.key} to {upload_ctx.copy_key}")
                    await self.notify_resource_update(upload_ctx.key, upload_ctx.timestamp_in_millis)
                else:
                    self.log(f"Resource {upload_ctx.copy_key} already exists")

    @staticmethod
    def convert_png_to_webp(content: bytes) -> tuple[bytes, int, int]:
        with io.BytesIO(content) as src, Image.open(src) as img, io.BytesIO() as dst:
            img.save(dst, format="webp", lossless=True)
            return dst.getvalue(), img.width, img.height

    @staticmethod
    def get_image_size(content: bytes) -> tuple[int, int]:
        with io.BytesIO(content) as src, Image.open(src) as img:
            return img.width, img.height

    def try_convert_png_to_webp(self, store_ctx: StoreContext) -> Optional[tuple[Optional[bytes], int, int]]:
        if store_ctx.content_type != "image/png":
            return None

        try:
            return self.convert_png_to_webp(store_ctx.content)
        except Exception as err:
            logger.error(f"Failed to convert image {store_ctx.url} to WebP: {err}")
            return None
