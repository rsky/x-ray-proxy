import asyncio
from logging import getLogger

from mitmproxy import ctx
from mitmproxy.addonmanager import Loader

from xrayproxy.config import Config
from xrayproxy.handlers.base import BaseResponseHandler
from xrayproxy.lib import logbook_kai
from xrayproxy.lib.decorators import error_logging
from xrayproxy.lib.xray import Context

logger = getLogger(__name__)


class LogbookKaiConnectHandler(BaseResponseHandler):
    """
    logbook-kai passive serverへのデータ転送を行うResponseHandler
    """

    _queue: asyncio.Queue[Context]
    _tasks: list[asyncio.Task[None]]

    _enabled: bool
    _client: logbook_kai.PassiveServerClient

    def __init__(self) -> None:
        super().__init__(logger)

    def load(self, loader: Loader) -> None:
        # プッシュは最大4並列
        self._queue = asyncio.Queue()
        tasks = []
        for _ in range(4):
            tasks.append(asyncio.create_task(self.worker()))
        self._tasks = tasks

    def configure(self, config: Config) -> None:
        super().configure(config)

        c = config.logbook_kai
        self._enabled = c.enabled
        if not self._enabled:
            return

        verify_port(c.host, c.port)

        # _clientはNoneになり得ないが、そのattributeは初回この下で初期化されるまで存在しない
        if hasattr(self, "_client"):
            asyncio.ensure_future(self._client.dispose())
        self._client = logbook_kai.create_client(c)

    async def done(self) -> None:
        await self._queue.join()

        for task in self._tasks:
            task.cancel()

        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self._client.dispose()

    def accept(self, context: Context) -> bool:
        return self._enabled and logbook_kai.check_path(context.request.path)

    async def response(self, context: Context) -> None:
        self._queue.put_nowait(context)

    async def worker(self) -> None:
        while True:
            context = await self._queue.get()
            await self.worker_impl(context)
            self._queue.task_done()

    async def worker_impl(self, context: Context) -> None:
        self.log(f"Sending {context.request.url} to logbook-kai")
        await self.send_to_logbook_kai(context)

    @error_logging(logger)
    async def send_to_logbook_kai(self, context: Context) -> None:
        await self._client.send(context)
        self.log(f"Sent {context.request.url} to logbook-kai")


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
