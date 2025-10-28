from logging import getLogger

from mitmproxy import ctx

from xrayproxy.addons.logbook_kai import (
    LogbookKaiAddon,
    PassiveServerParams,
    check_path,
    create_headers,
    create_path,
)
from xrayproxy.config import Config
from xrayproxy.handlers.base import BaseResponseHandler
from xrayproxy.lib.xray import Context

logger = getLogger(__name__)


class LogbookKaiConnectHandler(BaseResponseHandler):
    """
    logbook-kai passive serverへのデータ転送を行うResponseHandler
    """

    _enabled: bool
    _addon: LogbookKaiAddon

    def __init__(self) -> None:
        super().__init__(logger)
        self._addon = LogbookKaiAddon()
        self._enabled = False

    def configure(self, config: Config) -> None:
        super().configure(config)

        c = config.logbook_kai
        self._enabled = c.enabled
        if not self._enabled:
            return

        verify_port(c.host, c.port)

        self._addon.configure_connection(c.host, c.port)

    def running(self) -> None:
        self._addon.running()

    async def done(self) -> None:
        await self._addon.done()

    def accept(self, context: Context) -> bool:
        return self._enabled and check_path(context.request.path)

    async def response(self, context: Context) -> None:
        self._addon.enqueue(
            PassiveServerParams(
                path=create_path(context.request.path_with_query),
                headers=create_headers_by_xray(context),
                content=context.response.content,
            )
        )


def verify_port(host: str, port: int) -> None:
    """
    logbook-kaiのポートがmitmproxyやmitmwebと被っていないかチェックする
    """
    listen_port = (
        ctx.options.listen_port if hasattr(ctx.options, "listen_port") else ctx.options.default("listen_port")
    ) or 8080

    try:
        web_port = (
            ctx.options.web_port if hasattr(ctx.options, "web_port") else ctx.options.default("web_port")
        ) or 8081
    except KeyError:
        # mitmwebが起動していない場合はweb_portオプションが存在しない
        web_port = None

    if port == listen_port:
        if "127.0.0.1" == host:
            raise RuntimeError(f"logbook_kai.port {port} is already used by mitmproxy")
        else:
            logger.warning(f"logbook_kai.port {port} seems to be used by mitmproxy")

    if port == web_port:
        if "127.0.0.1" == host:
            raise RuntimeError(f"logbook_kai.port {port} is already used by mitmweb")
        else:
            logger.warning(f"logbook_kai.port {port} seems to be used by mitmweb")


def create_headers_by_xray(context: Context) -> list[tuple[str, str]]:
    return create_headers(
        request_host=context.request.host,
        request_method=context.request.method,
        request_content_type=context.request.content_type,
        request_content=context.request.content,
        response_content_type=context.response.content_type,
        response_content=context.response.content,
    )
