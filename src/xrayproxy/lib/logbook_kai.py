import base64
from logging import getLogger

import httpx

from ..config import LogbookKaiConfig
from .decorators import error_logging
from .xray import Context

logger = getLogger(__name__)

PATH_PREFIXES_TO_HANDLE = (
    "/kcsapi/",
    "/kcs2/resources/ship/",
    "/kcs2/img/common/",
    "/kcs2/img/duty/",
    "/kcs2/img/sally/",
)


class PassiveServerClient:
    def __init__(self, host: str, port: int) -> None:
        self._base_url = f"http://{host}:{port}"
        self._client = httpx.AsyncClient(base_url=self._base_url, headers={"User-Agent": "x-ray-proxy"})

    async def dispose(self) -> None:
        await self._client.aclose()

    @error_logging(logger)
    async def send(self, ctx: Context) -> None:
        url = "/pasv" + ctx.request.path_with_query
        headers = context_to_headers(ctx)
        content = ctx.response.content
        try:
            await self._client.post(url, headers=headers, content=content)
        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to the logbook-kai passive server {self._base_url}: {e}")


def check_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in PATH_PREFIXES_TO_HANDLE)


def create_client(config: LogbookKaiConfig) -> PassiveServerClient:
    return PassiveServerClient(config.host, config.port)


def context_to_headers(ctx: Context) -> dict[str, str]:
    headers = {
        "X-Pasv-Request-Method": ctx.request.method,
    }
    # logbook-kaiのRequestMetaDataWrapperはHostを使わないので不要
    # headers["X-Pasv-Request-Host"] = context.request.host

    if (
        ctx.request.content is not None
        and ctx.request.content_type is not None
        and (
            ctx.request.content_type.startswith("text/")
            or ctx.request.content_type in {"application/json", "application/x-www-form-urlencoded"}
        )
    ):
        headers["X-Pasv-Request-Content-Type"] = ctx.request.content_type_all  # type: ignore
        header_safe_body = base64.b64encode(ctx.request.content).decode("utf-8")
        headers["X-Pasv-Request-Body"] = header_safe_body

    if ctx.response.content_type is not None:
        headers["Content-Type"] = ctx.response.content_type
        if ctx.response.content_encoding is not None:
            headers["Content-Encoding"] = ctx.response.content_encoding

    return headers
