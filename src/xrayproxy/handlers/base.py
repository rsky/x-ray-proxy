import logging
from abc import ABC, abstractmethod
from logging import Logger
from typing import Any, Optional

from mitmproxy.http import Request, Response

from ..config import Config
from ..lib.api_token import ApiTokenManager
from ..lib.xray import Context, RequestData


class BaseHandler(ABC):
    _log_verbosity = logging.DEBUG
    _api_token_manager: ApiTokenManager

    def __init__(self, logger: Logger) -> None:
        self._logger = logger

    def log(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.log(self._log_verbosity, msg, *args, **kwargs)

    def log_error(self, err: Exception, exc_info: bool = False) -> None:
        self._logger.error(err, exc_info=exc_info)

    def set_log_verbosity(self, level: int) -> None:
        self._log_verbosity = level

    def set_api_token_manager(self, manager: ApiTokenManager) -> None:
        self._api_token_manager = manager

    def set_member_id(self, api_token: str, member_id: int) -> None:
        self._api_token_manager.save_token(api_token, member_id)

    def get_member_id(self, api_token: str) -> Optional[int]:
        return self._api_token_manager.get_member_id(api_token)

    def parse_request(self, request: RequestData) -> tuple[Optional[int], Optional[dict[str, str]]]:
        """
        リクエストを解析し、member_idとrequest_bodyを取得する
        """
        if request.content_type == "application/x-www-form-urlencoded":
            return self.parse_form_data(request.form)
        else:
            return None, None

    def parse_form_data(self, form: dict[str, str]) -> tuple[Optional[int], Optional[dict[str, str]]]:
        params = dict(form)
        api_token = params.get("api_token")
        if api_token is None:
            return None, params

        member_id = self.get_member_id(api_token)
        del params["api_token"]

        return member_id, params

    def get_api_token(self, request: RequestData) -> Optional[str]:
        """
        リクエストからapi_tokenを取得する
        """
        api_token = request.query.get("api_token") or request.form.get("api_token")
        if api_token is None:
            self.log("api_token not found")

        return api_token

    def configure(self, config: Config) -> None:
        """
        XRayAddon.configure()から呼ばれる
        See https://docs.mitmproxy.org/stable/api/events.html#LifecycleEvents.configure
        """
        self.set_log_verbosity(config.log_verbosity)

    async def done(self) -> None:
        """
        XRayAddon.done()から呼ばれる
        See https://docs.mitmproxy.org/stable/api/events.html#LifecycleEvents.done
        """
        pass


class RequestContext(ABC):
    """
    RequestHandler.accept()が返してRequestHandler.request()に渡すコンテキストオブジェクト用マーカーインターフェイス
    """

    pass


class BaseRequestHandler(BaseHandler):
    @abstractmethod
    def accept(self, request: Request) -> bool | RequestContext:
        """
        XRayAddon.request()から呼ばれ、このハンドラーが処理するかどうかを判定する
        TrueまたはRequestContextを返したハンドラーが処理する
        """
        pass

    @abstractmethod
    async def request(self, request: Request, ctx: Optional[RequestContext] = None) -> Optional[Response]:
        """
        accept()がTrueを返した場合にXRayAddon.request()から呼ばれる
        Responseを返した場合は上流へのリクエストが行われず、XRayAddon.response()でも処理対象外となる
        See https://docs.mitmproxy.org/stable/api/events.html#HTTPEvents.request
        """
        pass


class BaseResponseHandler(BaseHandler):
    @abstractmethod
    def accept(self, context: Context) -> bool:
        """
        XRayAddon.response()から呼ばれ、このハンドラーが処理するかどうかを判定する
        Trueを返したハンドラーが処理する
        """
        pass

    @abstractmethod
    async def response(self, context: Context) -> None:
        """
        accept()がTrueを返した場合にXRayAddon.response()から呼ばれる
        See https://docs.mitmproxy.org/stable/api/events.html#HTTPEvents.response
        """
        pass
