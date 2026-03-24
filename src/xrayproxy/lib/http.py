import re
from dataclasses import dataclass
from logging import getLogger
from typing import Optional

import httpx
import mitmproxy.http
import tenacity
from multidict import CIMultiDict

from xrayproxy.lib.hosts import get_kcs_host_set

logger = getLogger(__name__)

"""
Hop-by-hop headers / Connection-specific headers
プロキシはクライアントが送ってきたこれらのヘッダを上流に転送してはならない
https://datatracker.ietf.org/doc/html/rfc2616#section-8.1.3
https://datatracker.ietf.org/doc/html/rfc2616#section-13.5.1
https://datatracker.ietf.org/doc/html/rfc7540#section-8.1.2.2
"""
HOP_BY_HOP_HEADERS = frozenset(
    (
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "proxy-connection",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    )
)

_KCS_HOST_SET = get_kcs_host_set()
KANCOLLE_SERVER_SUFFIX = ".kancolle-server.com"

QUERY_KEY_NO_REPLACE = "no_replace"
QUERY_VALUE_NO_REPLACE = "1"
QUERY_PATTERN_NO_REPLACE = re.compile(rf"([?&]){QUERY_KEY_NO_REPLACE}={QUERY_VALUE_NO_REPLACE}(&|$)")


def query_strip_no_replace(url: str) -> str:
    def _repl(match: re.Match[str]) -> str:
        symbol = "?" if match.group(1) == "?" else "&"
        return symbol if match.group(2) == "&" else ""

    return QUERY_PATTERN_NO_REPLACE.sub(_repl, url, count=1)


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class RequestInfo:
    method: str
    url: str
    headers: CIMultiDict[str]
    data: Optional[bytes]


def create_request_info(request: mitmproxy.http.Request) -> "RequestInfo":
    method = request.method
    url = query_strip_no_replace(request.url)
    headers: CIMultiDict[str] = CIMultiDict()
    data = request.raw_content

    for header_name, header_value in request.headers.fields:
        key = header_name.decode("utf-8", "surrogateescape")
        if key.lower() not in HOP_BY_HOP_HEADERS:
            headers.add(key, header_value.decode("utf-8", "surrogateescape"))

    return RequestInfo(method=method, url=url, headers=headers, data=data)


async def perform_request(session: httpx.AsyncClient, request: mitmproxy.http.Request) -> mitmproxy.http.Response:
    """
    通信エラー時のリトライ機能を持たないmitmproxyに代わって艦これサーバーへのリクエストを行う。
    Performs an asynchronous request using the provided HTTPX client session and retries
    on specific transport errors with a defined strategy. Converts HTTPX responses to
    mitmproxy responses where applicable.

    Args:
        session: An HTTPX asynchronous client used for making HTTP requests.
        request: A mitmproxy HTTP request object representing the original request.

    Returns:
        A mitmproxy HTTP response object converted from the HTTPX response.
        Returns a 5xx error response if the request fails.
    """
    req = create_request_info(request)
    retry_error_status_code = 503

    try:
        async for attempt in tenacity.AsyncRetrying(
            wait=tenacity.wait_incrementing(start=0, increment=0.5, max=5),
            stop=tenacity.stop_after_attempt(3),
            retry=tenacity.retry_if_exception_type(httpx.TransportError),
        ):
            with attempt:
                try:
                    return _httpx_response_to_mitmproxy_response(
                        await session.request(
                            req.method,
                            req.url,
                            headers=req.headers,
                            content=req.data,
                        )
                    )
                except httpx.TransportError as e:
                    # Typically, RemoteProtocolError:
                    # `Server disconnected without sending a response.` on HTTP/1.1 or
                    # `<ConnectionTerminated error_code:0, last_stream_id:x, additional_data:None>` on HTTP/2
                    err_cls = e.__class__.__name__
                    logger.info(f"{err_cls}: {e} url={req.url}, attempts={attempt.retry_state.attempt_number}")
                    if isinstance(e, httpx.TimeoutException):
                        retry_error_status_code = 504
                    else:
                        retry_error_status_code = 502
                    raise e
    except tenacity.RetryError:
        return mitmproxy.http.Response.make(status_code=retry_error_status_code)
    except httpx.HTTPStatusError as e:
        err_cls = e.__class__.__name__
        logger.debug(f"{err_cls}: {e} status={e.response.status_code}, url={req.url}")
        return _httpx_response_to_mitmproxy_response(e.response)
    except Exception as e:
        err_cls = e.__class__.__name__
        logger.error(f"Unexpected error [{err_cls}]: url={req.url}", exc_info=True)

    # 予期しないエラー時は500 Internal Server Error扱いとする
    return mitmproxy.http.Response.make(status_code=500)


def _httpx_response_to_mitmproxy_response(response: httpx.Response) -> mitmproxy.http.Response:
    headers = tuple((k, v) for k, v in response.headers.raw if k.decode().lower() not in HOP_BY_HOP_HEADERS)
    return mitmproxy.http.Response.make(
        status_code=response.status_code,
        content=response.content,
        headers=headers,
    )


def check_request(request: mitmproxy.http.Request) -> bool:
    # 艦これ以外のリクエストは扱わない
    return request.host.endswith(KANCOLLE_SERVER_SUFFIX) or request.host in _KCS_HOST_SET


def check_response(request: mitmproxy.http.Request, response: mitmproxy.http.Response) -> bool:
    if not check_request(request):
        return False

    if request.method not in {"GET", "POST"}:
        # GET, POST以外のリクエストへのレスポンスは扱わない
        return False

    if response.status_code not in {200, 201}:
        # 200 OK, 201 Created以外のレスポンスは扱わない
        return False

    if response.raw_content is None:
        # レスポンスボディがない場合は扱わない
        return False

    return True
