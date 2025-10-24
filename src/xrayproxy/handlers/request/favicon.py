import os.path
from logging import getLogger
from typing import Optional

from mitmproxy.http import Request, Response

from xrayproxy.config import Config
from xrayproxy.handlers.base import BaseRequestHandler, RequestContext
from xrayproxy.handlers.mixin import ResponseFileMixin

logger = getLogger(__name__)


class FaviconRequestHandler(BaseRequestHandler, ResponseFileMixin):
    """
    配信サーバーの画像を直接ブラウザで表示しようとした時にリクエストされるfavicon.icoを代理で返すRequestHandler
    """

    _asserts_dir: str
    _enabled: bool
    _cache_max_age: int

    def __init__(self) -> None:
        super().__init__(logger)

    def configure(self, config: Config) -> None:
        super().configure(config)
        self._asserts_dir = config.assets_dir
        self._enabled = config.rewrite.dummy_favicon
        self._cache_max_age = config.rewrite.cache_max_age

    def accept(self, request: Request) -> bool:
        return self._enabled and request.path == "/favicon.ico"

    async def request(self, request: Request, ctx: Optional[RequestContext] = None) -> Optional[Response]:
        path = os.path.join(self._asserts_dir, "blank16x16.png")
        return self.response_file(path, "image/png", request.headers.get("If-None-Match"))
