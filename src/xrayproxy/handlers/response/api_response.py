import asyncio
import datetime
import json
import urllib.parse
from logging import getLogger
from typing import Any, Optional

from xrayproxy.config import Config
from xrayproxy.generated.sqlc.api_log import Querier, SaveApiLogParams
from xrayproxy.handlers.base import BaseResponseHandler
from xrayproxy.handlers.mixin import (
    DEFAULT_COMPRESSION_METHOD,
    CompressionMethodChoices,
    DatabaseMixin,
    JsonMixin,
    ObjectStorageMixin,
    XRayWebhookClientMixin,
)
from xrayproxy.lib.decorators import error_logging
from xrayproxy.lib.xray import ApiDataPayload, Context, create_payload

from .master_data import MASTER_DATA_API_PATH
from .member_info import API_PATHS_TO_HANDLE as API_PATHS_HANDLED_BY_MEMBER_INFO

logger = getLogger(__name__)

EXCLUDE_API_PATHS = frozenset((MASTER_DATA_API_PATH,)) | API_PATHS_HANDLED_BY_MEMBER_INFO

BATTLE_PATH_PREFIXES = (
    "/kcsapi/api_req_battle_midnight/",  # 夜戦
    "/kcsapi/api_req_combined_battle/",  # 連合艦隊
    "/kcsapi/api_req_sortie/",  # 通常戦闘
)

PRACTICE_PATH_PREFIX = "/kcsapi/api_req_practice/"  # 演習

MAP_PATH_PREFIX = "/kcsapi/api_req_map/"  # 海域

MEMBER_PATH_PREFIX = "/kcsapi/api_get_member/"  # メンバー情報
MEMBER_PATH_SUFFIXES_TO_SEND = (
    "/deck",
    "/kdock",
    "/material",
    "/mission",
    "/ndock",
    "/record",
    "/ship2",
    "/ship3",
    "/ship_deck",
)

PREFIXES_NEED_TO_SEND = (
    "/kcsapi/api_req_mission/",  # 遠征
    MAP_PATH_PREFIX,
    PRACTICE_PATH_PREFIX,
) + BATTLE_PATH_PREFIXES

# その他のx-ray-api webhookに送信するAPI
# 編成・補給・改装・工廠系などのAPIは、実行後にship2,ship3,slotitem等のAPIが叩かれず
# 単独でデータの更新を判定する必要があるものだけを送信する
OTHER_PATHS_TO_SEND = (
    "/kcsapi/api_req_hensei/change",  # 編成変更
    "/kcsapi/api_req_hensei/combined",  # 連合艦隊編成
    "/kcsapi/api_req_hensei/lock",  # ロック
    "/kcsapi/api_req_hensei/preset_select",  # 編成プリセット選択
    "/kcsapi/api_req_hokyu/charge",  # 補給
    "/kcsapi/api_req_kaisou/open_exslot",  # 補強増設開放
    "/kcsapi/api_req_kaisou/slot_deprive",  # 装備剥ぎ取り
    "/kcsapi/api_req_kaisou/slot_exchange_index",  # 装備入れ替え
    "/kcsapi/api_req_kousyou/destroyitem2",  # 装備廃棄
    "/kcsapi/api_req_kousyou/destroyship",  # 艦娘解体
    "/kcsapi/api_req_member/updatedeckname",  # 艦隊名変更
    "/kcsapi/api_req_nyukyo/start",  # 入渠開始
    "/kcsapi/api_req_ranking/mxltvkpyuklh",  # ランキング
)


def need_to_send(path: str) -> bool:
    if path.startswith(MEMBER_PATH_PREFIX):
        return any(path.endswith(suffix) for suffix in MEMBER_PATH_SUFFIXES_TO_SEND)

    if any(path.startswith(prefix) for prefix in PREFIXES_NEED_TO_SEND):
        return True

    return path in OTHER_PATHS_TO_SEND


def is_battle(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in BATTLE_PATH_PREFIXES)


def is_map(path: str) -> bool:
    return path.startswith(MAP_PATH_PREFIX)


def is_practice(path: str) -> bool:
    return path.startswith(PRACTICE_PATH_PREFIX)


def is_sortie(path: str) -> bool:
    return is_battle(path) or is_map(path)


def format_log_json_object_key(prefix: str, path: str, utc_date: datetime.datetime) -> str:
    """
    ログを保存する際のオブジェクトキーを生成する
    API名よりも時系列が先に来る
    """
    jst_date = utc_date.astimezone(datetime.timezone(datetime.timedelta(hours=9)))
    base_name = "_".join(path.split("/")[1:])
    date_str = jst_date.strftime("%Y/%m/%d")
    time_str = jst_date.strftime("%H%M%S_%f")
    return f"{prefix}/{date_str}/{time_str}_{base_name}.json"


class ApiResponseHandler(BaseResponseHandler, DatabaseMixin, JsonMixin, ObjectStorageMixin, XRayWebhookClientMixin):
    """
    APIレスポンスを処理する
    """

    _save_sortie_log: bool = False
    _save_practice_log: bool = False
    _save_other_log: bool = False
    _bucket: str = ""

    def __init__(self) -> None:
        super().__init__(logger)

    def configure(self, config: Config) -> None:
        super().configure(config)
        self._bucket = config.storage.api_log_bucket
        self.configure_object_storage(config, config.storage.api_log_bucket)
        self.configure_json_response_handler(config.api_log)

        self._save_sortie_log = config.api_log.save_sortie_log
        self._save_practice_log = config.api_log.save_practice_log
        self._save_other_log = config.api_log.save_other_log

        self.configure_webhook_client(config)

    def accept(self, context: Context) -> bool:
        path = context.request.path
        return path.startswith("/kcsapi/") and path not in EXCLUDE_API_PATHS

    async def done(self) -> None:
        await self.done_webhook_client()

    async def response(self, context: Context) -> None:
        json_data = self.decode_json(context)
        if json_data is None:
            return

        tasks = []

        member_id, request_params = self.parse_request(context.request)
        object_key = self.make_object_key(context.request.path, context.respond_at)
        log_key = None if object_key is None else self.compressed_json_object_key(object_key)

        payload: Optional[ApiDataPayload] = None
        if need_to_send(context.request.path):
            payload = create_payload(context, member_id, json_data, log_bucket=self._bucket, log_key=log_key)

        if object_key and log_key:
            # APIログをストレージに保存し、データベースにも記録する
            # 通知が必要ならストレージに保存した後にWebhookに送信する
            json_str = self.encode_json(json_data)
            extra_metadata = {}
            if member_id is not None:
                extra_metadata["x-ray-member-id"] = str(member_id)
            if request_params is not None:
                extra_metadata["x-ray-request-body"] = urllib.parse.urlencode(request_params)
            tasks.append(self.upload_data(object_key, json_str, context.request.url, extra_metadata, payload=payload))

            params = None
            if context.request.method == "GET" and context.request.query:
                params = context.request.query
            elif context.request.method == "POST" and request_params:
                params = request_params

            Querier(self._db_conn).save_api_log(
                SaveApiLogParams(
                    bucket=self._bucket,
                    object_key=log_key,
                    member_id=member_id,
                    host=context.request.host,
                    method=context.request.method,
                    path=context.request.path,
                    raw_size=len(json_str),
                    params=json.dumps(params, ensure_ascii=False, separators=(",", ":")) if params else None,
                )
            )
            self._db_conn.commit()
        elif payload:
            # APIログは記録せず、Webhookに送信のみを行う
            tasks.append(self._send_to_webhook(payload))

        await asyncio.gather(*tasks, return_exceptions=True)

    def make_object_key(self, path: str, utc_date: datetime.datetime) -> Optional[str]:
        if is_sortie(path):
            if self._save_sortie_log:
                return format_log_json_object_key("sortie_log", path, utc_date)
        elif is_practice(path):
            if self._save_practice_log:
                return format_log_json_object_key("practice_log", path, utc_date)
        else:
            if self._save_other_log:
                return format_log_json_object_key("other_log", path, utc_date)

        return None

    @error_logging(logger)
    async def upload_data(
        self,
        object_key: str,
        json_str: str,
        url: str,
        extra_metadata: dict[str, Any],
        compression: CompressionMethodChoices = DEFAULT_COMPRESSION_METHOD,
        payload: Optional[ApiDataPayload] = None,
    ) -> None:
        (key, body, s3_system_metadata) = self.make_upload_data(object_key, json_str, compression=compression)
        if self._s3_allow_public_access:
            s3_system_metadata["ACL"] = "public-read"
        async with self.create_s3_client() as s3:
            await self.put_object(s3, key, body, url, extra_metadata, **s3_system_metadata)
        if payload:
            await self._send_to_webhook(payload)

    @error_logging(logger)
    async def _send_to_webhook(self, payload: ApiDataPayload) -> None:
        if self._webhook_clients:
            await asyncio.gather(*[client.send_api_data(payload) for client in self._webhook_clients])
