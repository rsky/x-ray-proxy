import dataclasses
import re
from logging import getLogger
from typing import Optional

from mitmproxy.http import Request, Response

from xrayproxy.config import Config, ReplaceShipGraphicEntry
from xrayproxy.generated.sqlc.master_data import Querier
from xrayproxy.generated.sqlc.models import Shipgraph
from xrayproxy.handlers.base import BaseRequestHandler, RequestContext
from xrayproxy.handlers.mixin import DatabaseMixin, ObjectStorageMixin
from xrayproxy.lib.http import QUERY_KEY_NO_REPLACE, QUERY_VALUE_NO_REPLACE
from xrayproxy.lib.ship import ship_graphic_url

logger = getLogger(__name__)


SHIP_GRAPHIC_PATH_PREFIX = "/kcs2/resources/ship/"


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class ShipGraphicReplaceContext(RequestContext):
    graphic_type: str
    padded_ship_id: str
    ship_id_str: str
    extra: Optional[str]
    replace: ReplaceShipGraphicEntry


class ShipGraphicRequestHandler(BaseRequestHandler, DatabaseMixin, ObjectStorageMixin):
    """
    艦娘グラフィックのリクエストをフックして、指定された艦娘の画像で置換するRequestHandler

    画像の差し替えを設定を反映するには、設定を変更した後にx-ray-proxyを再起動、
    ブラウザはキャッシュを削除して艦これをリロードする必要がある。
    """

    _enabled: bool = False
    _cache_max_age: int
    _pattern: re.Pattern[str]
    _ship_graphics_replace_mapping: dict[int, ReplaceShipGraphicEntry]

    def __init__(self) -> None:
        super().__init__(logger)

    def configure(self, config: Config) -> None:
        super().configure(config)
        self.configure_object_storage(
            config,
            config.storage.resource_bucket,
            allow_public_access=config.storage.allow_resource_public_access,
            purge_cache=True,
            cf_public_host_name=config.storage.cloudflare.resource_bucket_public_host_name,
        )

        target_ship_ids = set(config.rewrite.replace_ship_graphics.mapping.keys())
        if len(target_ship_ids) > 0:
            ship_id_pattern = "|".join(str(x) for x in target_ship_ids)
            # .pngの後には "?version=<version>" のようなクエリ文字列があるので "$" で終端しない
            self._pattern = re.compile(f"^/kcs2/resources/ship/(\\w+)/(0*({ship_id_pattern}))(_\\w+)?\\.png")
            self._ship_graphics_replace_mapping = dict(config.rewrite.replace_ship_graphics.mapping)  # copy
            self._enabled = True
        else:
            self._enabled = False

        self._cache_max_age = config.rewrite.cache_max_age

    def accept(self, request: Request) -> bool | ShipGraphicReplaceContext:
        # パターンマッチ前に荒くフィルタリング
        if not (self._enabled and request.path.startswith(SHIP_GRAPHIC_PATH_PREFIX)):
            return False

        m = self._pattern.match(request.path)
        if not m:
            # 対象の艦娘画像でない場合
            return False

        graphic_type, padded_ship_id, ship_id_str, extra = m.groups()
        if graphic_type in {"special", "special_dmg"}:
            # 特殊砲撃グラフィックは置換しない
            return False

        from_ship_id = int(ship_id_str)
        replace = self._ship_graphics_replace_mapping.get(from_ship_id)
        if not replace:
            # 置換先がない場合 (パターンにマッチしているので通常はあり得ないが)
            return False

        if replace.full_only and graphic_type not in {"full", "full_dmg"}:
            # 立ち絵のみを置換する設定で、立ち絵以外の場合
            return False

        return ShipGraphicReplaceContext(
            graphic_type=graphic_type,
            padded_ship_id=padded_ship_id,
            ship_id_str=ship_id_str,
            extra=extra,
            replace=replace,
        )

    async def request(self, request: Request, ctx: Optional[RequestContext] = None) -> Optional[Response]:
        if not isinstance(ctx, ShipGraphicReplaceContext):
            return None

        if request.query.get(QUERY_KEY_NO_REPLACE) == QUERY_VALUE_NO_REPLACE:
            # 置換対象の画像のオリジナルを取得したい場合は特殊なクエリno_replace=1が付与されている
            # それを削除してNoneを返し、リクエストは通常通りに処理する
            request.query.pop(QUERY_KEY_NO_REPLACE)
            return None

        querier = Querier(self._db_conn)

        response = await self._get_versioned_copy_if_requested(request, ctx, querier)
        if response:
            # バージョン指定があり、その画像スナップショットが保存されていた場合
            return response

        shipgraph = querier.get_latest_shipgraph_by_host(host=request.host, ship_id=ctx.replace.to_ship_id)
        if not shipgraph:
            # 艦娘画像データがDBにない場合 (IDが間違っているか、最新のマスターデータがDBに反映されていない)
            ident = f"host={request.host}, ship_id={ctx.replace.to_ship_id}"
            logger.warning(f"{ident} is not found in the database.")
            return None

        # URLを書き換え、条件付きリクエストの If-None-Match/If-Modified-Since ヘッダも削除する
        old_url = request.url
        new_url = ship_graphic_url(shipgraph, ctx.graphic_type)
        self.log(f"Replace ship graphic: {old_url} -> {new_url}")
        request.url = new_url
        request.headers.pop("If-None-Match", None)
        request.headers.pop("If-Modified-Since", None)

        # Noneを返すことで、XRayAddon.request()のperform_request()で処理され、
        # その後responseハンドラで通常通りS3保存やX-Ray送信が行われる
        return None

    async def _get_versioned_copy_if_requested(
        self,
        request: Request,
        ctx: ShipGraphicReplaceContext,
        querier: Querier,
    ) -> Optional[Response]:
        if (
            ctx.replace.to_version is None  # バージョン指定がない
            or ctx.graphic_type not in {"full", "full_dmg"}  # 期間限定画像の置換対象は立ち絵のみ
            or (ctx.extra and ctx.extra.startswith("_d_"))  # 弱体化画像はバージョンがない
        ):
            return None

        shipgraph = querier.get_shipgraph(
            host=request.host,
            ship_id=ctx.replace.to_ship_id,
            version=ctx.replace.to_version,
        )
        if shipgraph is None:
            # 指定されたバージョンの画像情報がDBにない場合
            # マスターデータの位置補正情報は書き換えられていないので、位置ズレは発生しない。
            ident = f"host={request.host}, ship_id={ctx.replace.to_ship_id}, version={ctx.replace.to_version}"
            logger.warning(f"{ident} is not found in the database.")
            return None

        # 指定されたバージョンの画像情報がDBにある場合
        result = await self._get_versioned_copy_from_object_storage(
            shipgraph, ctx.padded_ship_id, ctx.graphic_type, request.headers.get("If-None-Match")
        )
        if result:
            # 指定されたバージョンの画像スナップショットが保存されている場合
            response, key = result
            self.log(f"Replace ship graphic: {request.url} -> {key}")
            return response
        else:
            # 指定されたバージョンの画像スナップショットが保存されていない場合
            # マスターデータの座標情報が書き換えられているので、
            # 位置ズレが発生する可能性がある。(同一艦娘・カラバリ違いなら問題ない)
            ident = f"ship_id={shipgraph.ship_id}, version={shipgraph.version}, graphic_type={ctx.graphic_type}"
            logger.warning(f"{ident} is not found in the object storage.")
            return None

    async def _get_versioned_copy_from_object_storage(
        self,
        sg: Shipgraph,
        padded_ship_id: str,
        graphic_type: str,
        if_none_match: Optional[str] = None,
    ) -> Optional[tuple[Response, str]]:
        key = f"assets/ships/{padded_ship_id}/{graphic_type}_v{sg.version}.webp"
        async with self.create_s3_client() as s3:
            versioned = await self.get_object(s3, key)
            if versioned is None:
                return None

            etag = versioned["ETag"]
            if etag is not None and if_none_match == etag:
                return (
                    Response.make(
                        status_code=304,
                        content=b"",
                    ),
                    key,
                )
            else:
                try:
                    content = await versioned["Body"].read()
                except Exception as e:
                    logger.error(f"Failed to read '{key}': {e}")
                    return None

                headers = {
                    "Content-Type": versioned["ContentType"],
                }
                if etag is not None:
                    headers["ETag"] = etag

                return (
                    Response.make(
                        status_code=200,
                        content=content,
                        headers=headers,
                    ),
                    key,
                )
