import json
import re
from logging import getLogger
from typing import Any, List

from sqlalchemy.orm import Session

from xrayproxy.config import Config
from xrayproxy.config.xray import XRayWebhookConfig
from xrayproxy.generated.sqlc.master_data import (
    Querier,
    SaveShipgraphParams,
    SaveShipParams,
)
from xrayproxy.handlers.base import BaseResponseHandler
from xrayproxy.handlers.mixin import (
    DEFAULT_COMPRESSION_METHOD,
    CompressionMethodChoices,
    DatabaseMixin,
    JsonMixin,
    ObjectStorageMixin,
)
from xrayproxy.lib.decorators import error_logging
from xrayproxy.lib.xray import Context, create_webhook_client

logger = getLogger(__name__)

MASTER_DATA_API_PATH = "/kcsapi/api_start2/getData"


class MasterDataResponseHandler(BaseResponseHandler, DatabaseMixin, JsonMixin, ObjectStorageMixin):
    """
    マスターデータを処理する
    """

    _webhook_configs: List[XRayWebhookConfig] = []

    def __init__(self) -> None:
        super().__init__(logger)

    def configure(self, config: Config) -> None:
        super().configure(config)
        self.configure_object_storage(config, config.storage.data_bucket)
        self.configure_json_response_handler(config.api_log)

        if config.x_ray.webhook:
            self._webhook_configs = config.x_ray.webhook
        else:
            self._webhook_configs = []

    def accept(self, context: Context) -> bool:
        return context.request.path == MASTER_DATA_API_PATH

    async def response(self, context: Context) -> None:
        json_str = self.get_json(context)
        if json_str is None:
            return

        data = self.decode_json(context)
        if not data:
            logger.error(f"{MASTER_DATA_API_PATH}: json decode failed")
            return

        host = context.request.host
        self._update_master_data_db(host, data.get("api_data", {}))

        # マスターデータはサーバー毎のものも残しつつ、共通のパスに保存する
        object_key = f"master_data/{host}/api_start2.json"
        copy_object_key = "master_data/api_start2.json"
        await self.upload_data(object_key, copy_object_key, json_str, context.request.url, context.respond_at_millis)

    @error_logging(logger)
    async def upload_data(
        self,
        object_key: str,
        copy_object_key: str,
        json_str: str,
        url: str,
        timestamp_in_millis: int,
        compression: CompressionMethodChoices = DEFAULT_COMPRESSION_METHOD,
    ) -> None:
        updated_resource_keys = []

        async with self.create_s3_client() as s3:
            (key, body, s3_system_metadata) = self.make_upload_data(object_key, json_str, compression=compression)
            copy_key = key.replace(object_key, copy_object_key)
            if self._s3_allow_public_access:
                s3_system_metadata["ACL"] = "public-read"

            if await self.put_object_if_none_match(s3, key, body, url, **s3_system_metadata):
                updated_resource_keys.append(key)

            if await self.put_object_if_none_match(s3, copy_key, body, url, **s3_system_metadata):
                updated_resource_keys.append(copy_key)

        if len(updated_resource_keys) > 0:
            await self._notify_resource_updates(updated_resource_keys, timestamp_in_millis)

    def _update_master_data_db(self, host: str, master_data: dict[str, Any]) -> None:
        try:
            with Session(self._db_conn) as session, session.begin():
                querier = Querier(self._db_conn)
                self._update_ship(querier, master_data.get("api_mst_ship", []))
                self._update_shipgraph(querier, host, master_data.get("api_mst_shipgraph", []))
        except Exception as err:
            logger.exception(f"failed to update master data: {err}")

    def _update_ship(self, querier: Querier, ship_master_data: list[dict[str, Any]]) -> None:
        for ship in ship_master_data:
            querier.save_ship(self._make_ship_params(ship))

    @staticmethod
    def _make_ship_params(ship: dict[str, Any]) -> SaveShipParams:
        ship_id = int(ship["api_id"])
        sort_id = int(ship["api_sort_id"])
        name = str(ship["api_name"])
        yomi = str(ship["api_yomi"])
        ship_type_id = None
        picture_book_no = None
        after_lv = None
        after_ship_id = None

        if "api_stype" in ship:
            try:
                ship_type_id = int(ship["api_stype"])
            except ValueError:
                ship_type_id = None

        if "api_sortno" in ship:
            try:
                picture_book_no = int(ship["api_sortno"])
            except ValueError:
                picture_book_no = None

        if picture_book_no is not None and "api_afterlv" in ship:
            try:
                _after_lv = int(ship["api_afterlv"])
                _after_ship_id = int(ship["api_aftershipid"])
                if _after_lv > 0 and _after_ship_id > 0:
                    after_lv = _after_lv
                    after_ship_id = _after_ship_id
            except ValueError:
                pass

        return SaveShipParams(
            id=ship_id,
            sort_id=sort_id,
            name=name,
            yomi=yomi,
            ship_type_id=ship_type_id,
            picture_book_no=picture_book_no,
            after_lv=after_lv,
            after_ship_id=after_ship_id,
        )

    def _update_shipgraph(self, querier: Querier, host: str, shipgraph_master_data: list[dict[str, Any]]) -> None:
        for shipgraph in shipgraph_master_data:
            try:
                # [graphic_version, voice_version, port_voice_version]
                version = int(shipgraph["api_version"][0])
            except (LookupError, ValueError) as err:
                version = 0
                self.log_error(err)

            querier.save_shipgraph(
                SaveShipgraphParams(
                    host=host,
                    ship_id=int(shipgraph["api_id"]),
                    version=version,
                    filename=str(shipgraph["api_filename"]),
                    points=self._make_shipgraph_points(shipgraph),
                )
            )

    @staticmethod
    def _make_shipgraph_points(shipgraph: dict[str, Any]) -> str:
        points = {}
        for k, v in shipgraph.items():
            if not isinstance(v, list) or len(v) != 2:
                continue
            m = re.fullmatch(r"api_(\w+_[dn]|wed[ab]|pab?)", k)
            if m:
                points[str(m.group(1))] = v

        return json.dumps(points, separators=(",", ":"))

    async def _notify_resource_updates(self, keys: list[str], timestamp_in_millis: int) -> None:
        for config in self._webhook_configs:
            # マスターデータはその性格上、頻繁に更新されるものではないので、都度clientを作成する
            async with create_webhook_client(config) as client:
                for key in keys:
                    await client.update_resource(key, timestamp_in_millis)
