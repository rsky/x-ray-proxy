import datetime
import math
from dataclasses import asdict, dataclass
from logging import getLogger
from typing import Any, Mapping, Optional

from mitmproxy.http import Headers, HTTPFlow, Request, Response
from x_ray_webhook import NOT_GIVEN, APIConnectionError, AsyncXRayWebhook, NotGiven
from x_ray_webhook.resources import AsyncAPIDataResource, AsyncMemberInfoResource, AsyncResourceResource
from x_ray_webhook.types import api_data_send_params

from xrayproxy.config.xray import XRayWebhookConfig

logger = getLogger(__name__)


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class Context:
    proxy_auth_username: Optional[str]
    request: "RequestData"
    response: "ResponseData"
    respond_at: datetime.datetime  # response.timestamp_start を表すUTCのdatetime
    respond_at_millis: int  # ミリ秒単位のUNIXタイムスタンプ


@dataclass(slots=True, eq=False)
class JsonHolder:
    json: Optional[dict[str, Any]] = None


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class RequestData:
    url: str
    method: str
    host: str
    path: str
    path_with_query: str
    query: dict[str, str]  # not a kind of MultiDict
    form: dict[str, str]  # not a kind of MultiDict
    content_type_all: Optional[str]
    content_type: Optional[str]
    content: Optional[bytes]


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class ResponseData:
    content_type_all: Optional[str]
    content_type: Optional[str]
    content_encoding: Optional[str]
    content: Optional[bytes]
    json_holder: JsonHolder

    @property
    def json(self) -> Optional[dict[str, Any]]:
        return self.json_holder.json

    def set_json(self, value: Optional[dict[str, Any]]) -> None:
        self.json_holder.json = value


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class ApiDataPayload:
    member_id: int
    request: api_data_send_params.Request
    response: api_data_send_params.Response
    log: api_data_send_params.Log | NotGiven = NOT_GIVEN


class XRayWebhookClient:
    def __init__(
        self,
        *,
        base_url: str,
        client_id: str,
        client_secret: str,
        default_headers: Mapping[str, str] | None = None,
    ) -> None:
        self._client = AsyncXRayWebhook(
            base_url=base_url,
            client_id=client_id,
            client_secret=client_secret,
            default_headers=default_headers,
        )
        self._api_data = AsyncAPIDataResource(self._client)
        self._resource = AsyncResourceResource(self._client)
        self._member_info = AsyncMemberInfoResource(self._client)

    async def __aenter__(self) -> "XRayWebhookClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        await self.dispose()

    async def dispose(self) -> None:
        await self._client.close()

    async def send_api_data(self, payload: ApiDataPayload) -> None:
        """
        APIリクエスト/レスポンスの情報を送信する
        """
        try:
            await self._api_data.send(**asdict(payload))
        except APIConnectionError as e:
            logger.error(f"Failed to connect to the X-Ray Webhook endpoint: {e.message}")

    async def send_member_info(self, member_id: int, nickname: str, host: str) -> None:
        """
        提督ID、ニックネーム、ホスト名を送信する
        """
        try:
            await self._member_info.send(
                member_id=member_id,
                nickname=nickname,
                host=host,
            )
        except APIConnectionError as e:
            logger.error(f"Failed to connect to the X-Ray Webhook endpoint: {e.message}")

    async def update_resource(self, key: str, timestamp_in_millis: int) -> None:
        """
        リソースのキャッシュを無効化する
        """
        try:
            await self._resource.update(key=key, timestamp=timestamp_in_millis)
        except APIConnectionError as e:
            logger.error(f"Failed to connect to the X-Ray Webhook endpoint: {e.message}")


def create_webhook_client(config: XRayWebhookConfig) -> XRayWebhookClient:
    default_headers: Mapping[str, str] | None = None
    if config.local_token:
        # Cloudflare Accessを経由せず、ローカルで実行する場合は
        # CF_Authorizationクッキーでローカル開発用のBot認証トークンを送信する。
        default_headers = {
            "Cookie": f"CF_Authorization={config.local_token}",
        }
        # このとき client_id, client_secret は利用されないので値は何でも良いが、
        # 同時に設定されているべきではない。
        if config.client_id != "" or config.client_secret != "":
            logger.warning("[[x_ray.webhook]] client_id and client_secret should not be set when local_token is set.")

    return XRayWebhookClient(
        base_url=config.base_url,
        client_id=config.client_id,
        client_secret=config.client_secret,
        default_headers=default_headers,
    )


def create_context(flow: HTTPFlow) -> Context:
    proxy_auth = flow.metadata.get("proxyauth")
    username = proxy_auth[0] if proxy_auth else None
    response: Response = flow.response  # type: ignore # この関数が呼び出される際はflow.responseは必ず存在する

    return Context(
        proxy_auth_username=username,
        request=create_request_data(flow.request),
        response=create_response_data(response),
        respond_at=datetime.datetime.fromtimestamp(response.timestamp_start, datetime.timezone.utc),
        respond_at_millis=math.floor(response.timestamp_start * 1000),
    )


def create_request_data(request: Request) -> RequestData:
    content_type_all, content_type = extract_content_type(request.headers)

    return RequestData(
        url=request.url,
        method=request.method,
        host=request.host,
        path=get_path_without_query(request),
        path_with_query=request.path,
        query=dict(request.query),
        form=dict(request.urlencoded_form),
        content_type_all=content_type_all,
        content_type=content_type,
        content=request.content,
    )


def create_response_data(response: Response) -> ResponseData:
    content_type_all, content_type = extract_content_type(response.headers)

    return ResponseData(
        content_type_all=content_type_all,
        content_type=content_type,
        content_encoding=response.headers.get("content-encoding"),
        content=response.content,
        json_holder=JsonHolder(),
    )


def create_payload(
    context: Context,
    member_id: Optional[int],
    response_data: dict[str, Any],
    *,
    log_bucket: Optional[str] = None,
    log_key: Optional[str] = None,
) -> ApiDataPayload | None:
    if member_id is None:
        return None

    # 全てのAPIリクエストはPOSTメソッドでapplication/x-www-form-urlencoded形式で送信される前提
    if context.request.method != "POST":
        return None

    safe_request_params = shorten_keys(context.request.form, "form")
    if "token" in safe_request_params:
        del safe_request_params["token"]

    result_code = response_data.get("api_result")
    if result_code != 1 and result_code != "1":
        logger.warning(f"API result code is not 1: {result_code}")
        return None

    data = response_data.get("api_data")
    if data is None:
        # api_req_sortie/goback_port など、api_dataが存在しない場合がある
        pass
    elif context.request.path == "/kcsapi/api_get_member/ship2":
        # api_get_member/ship2 のレスポンスを api_get_member/ship3 と同じ形式に変換する
        ship_data = data
        data = {
            "api_ship_data": ship_data,
            "api_deck_data": response_data.get("api_data_deck", []),
        }

    return ApiDataPayload(
        member_id=member_id,
        request={
            "url": context.request.url,
            "parameters": safe_request_params,
        },
        response={
            "timestamp": context.respond_at_millis,
            "data": recursive_shorten_keys(data, "api_data"),
        },
        log=(
            {
                "bucket": log_bucket,
                "key": log_key,
            }
            if log_bucket and log_key
            else NOT_GIVEN
        ),
    )


def shorten_keys(data: dict[str, Any], current_key_for_message: str) -> dict[str, Any]:
    return {
        (k[4:] if k.startswith("api_") else k): recursive_shorten_keys(v, f"{current_key_for_message}.{k}")
        for k, v in data.items()
    }


def recursive_shorten_keys(data: Any, current_key_for_message: str) -> Any:
    match data:
        case dict():
            return shorten_keys(data, current_key_for_message)
        case list() | tuple() | set():
            return [recursive_shorten_keys(v, f"{current_key_for_message}[{i}]") for i, v in enumerate(data)]
        case str() | int() | float():
            return data
        case None:
            return None
        case _:
            # raise ValueError(f"Unexpected type: {type(data)}")
            logger.warning(f"Unexpected type: {type(data)} for key: {current_key_for_message}")
            return None


def extract_content_type(headers: Headers) -> tuple[str, str] | tuple[None, None]:
    content_type_all = headers.get("content-type")
    if content_type_all is None:
        return None, None

    content_type = content_type_all.split(";", 1)[0]
    return content_type_all, content_type


def get_path_without_query(request: Request) -> str:
    return request.path.split("?", 1)[0]
