"""
APIレスポンスをX-Ray serverに送信したり、リソースをオブジェクトストレージに保存するアドオン
"""

import asyncio
import logging
import re
from logging import getLogger
from typing import Any

import aioboto3
import aiobotocore.session
import botocore.client
import httpx
import sqlalchemy
from mitmproxy import ctx
from mitmproxy.addonmanager import Loader
from mitmproxy.http import HTTPFlow

from xrayproxy.config import ReplaceShipGraphicEntry, load_config_toml
from xrayproxy.generated.sqlc.master_data import Querier
from xrayproxy.handlers import mixin, response_rewriter
from xrayproxy.handlers import request as request_handlers
from xrayproxy.handlers import response as response_handlers
from xrayproxy.handlers.base import BaseRequestHandler, BaseResponseHandler
from xrayproxy.handlers.response.master_data import MASTER_DATA_API_PATH
from xrayproxy.handlers.response.member_info import OPTION_SETTING_API_PATH
from xrayproxy.lib.api_token import ApiTokenManager
from xrayproxy.lib.http import check_request, check_response, perform_request
from xrayproxy.lib.xray import create_context

logger = getLogger(__name__)

MOBILE_USER_AGENT_PATTERN = re.compile("iPhone|iPad|Android")


class XRayAddon:
    _log_verbosity: int = logging.DEBUG
    _request_handlers: tuple[BaseRequestHandler, ...]
    _response_handlers: tuple[BaseResponseHandler, ...]
    _boto_session: aioboto3.Session
    _http_session: httpx.AsyncClient
    _db_engine: sqlalchemy.Engine
    _db_conn: sqlalchemy.engine.Connection
    _replace_ship_graphics_mapping: dict[int, ReplaceShipGraphicEntry]
    _mute_mobile: bool = False

    def __init__(self) -> None:
        self._request_handlers = (
            request_handlers.EnemyVoiceRequestHandler(),
            request_handlers.FaviconRequestHandler(),
            request_handlers.ShipGraphicRequestHandler(),
        )
        self._response_handlers = (
            response_handlers.ResourceResponseHandler(),
            response_handlers.ApiResponseHandler(),
            response_handlers.MemberInfoResponseHandler(),
            response_handlers.MasterDataResponseHandler(),
            response_handlers.LogbookKaiConnectHandler(),
        )

    def set_log_verbosity(self, level: int) -> None:
        self._log_verbosity = level

    def log(self, message: str, *args: Any, **kwargs: Any) -> None:
        """
        getLogger().debug()ではmitmproxyが設定するルートロガーのログレベルに依存するので
        x-ray-proxyだけデバッグログを出すために独自のデバッグ用ログレベルを設定し、log()メソッドでログ出力する
        """
        logger.log(self._log_verbosity, message, *args, **kwargs)

    def load(self, loader: Loader) -> None:
        """
        See https://docs.mitmproxy.org/stable/api/events.html#LifecycleEvents.load
        """
        # ここではまだmitmproxyのログレベルに依存する
        self.log("[Lifecycle] xrayproxy.x_ray.XRayAddon.load")

        loader.add_option("x_ray_config", str, "config/xrayproxy.toml", "x-ray-proxy config TOML file path")

        botocore_session = aiobotocore.session.get_session()
        botocore_session.set_default_client_config(
            botocore.client.Config(
                request_checksum_calculation="when_required",  # Avoid appending `aws-chunked`
                response_checksum_validation="when_required",  # to Content-Encoding header.
            )
        )

        self._boto_session = aioboto3.Session(botocore_session=botocore_session)
        # self._boto_session = aioboto3.Session()
        self._http_session = httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(timeout=5.0, connect=10.0))

        for handler in self._request_handlers + self._response_handlers:
            handler.load(loader)
            if isinstance(handler, mixin.ObjectStorageMixin):
                handler.set_boto_session(self._boto_session)

    def configure(self, updated: set[str]) -> None:
        """
        See https://docs.mitmproxy.org/stable/api/events.html#LifecycleEvents.configure
        """
        if "x_ray_config" in updated:
            config = load_config_toml(ctx.options.x_ray_config)

            self.set_log_verbosity(config.log_verbosity)
            self.log("[Lifecycle] xrayproxy.x_ray.XRayAddon.configure")

            # configure the database engine
            # _db_engineはNoneになり得ないが、そのattributeは初回この下で初期化されるまで存在しない
            if hasattr(self, "_db_engine"):
                self._db_engine.dispose()

            self._db_engine = sqlalchemy.create_engine(f"sqlite:///{config.database_path}")
            self._db_conn = self._db_engine.connect()
            api_token_manager = ApiTokenManager(self._db_conn)

            # configure handlers
            for handler in self._request_handlers + self._response_handlers:
                handler.configure(config)
                handler.set_api_token_manager(api_token_manager)
                if isinstance(handler, mixin.DatabaseMixin):
                    handler.set_database_connection(self._db_conn)

            # configure danger features
            self._replace_ship_graphics_mapping = dict(config.rewrite.replace_ship_graphics.mapping)
            self._mute_mobile = config.rewrite.mute_mobile

    async def done(self) -> None:
        """
        See https://docs.mitmproxy.org/stable/api/events.html#LifecycleEvents.done
        """
        await asyncio.gather(*[handler.done() for handler in self._request_handlers], return_exceptions=True)
        await asyncio.gather(*[handler.done() for handler in self._response_handlers], return_exceptions=True)

        await self._http_session.aclose()

        self._db_conn.close()
        self._db_engine.dispose()

        # ここではルートロガーであるmitmproxyのロガーが出力しないのでprintデバッグ
        # print("[Lifecycle] xrayproxy.x_ray.XRayAddon.done")

    async def request(self, flow: HTTPFlow) -> None:
        """
        See https://docs.mitmproxy.org/stable/api/events.html#HTTPEvents.request
        """
        request = flow.request
        if not check_request(request):
            return

        for req_handler in self._request_handlers:
            response = await req_handler.request(request)
            if response is not None:
                flow.response = response
                return

        response = await perform_request(self._http_session, request)
        if response is None:
            return

        flow.response = response
        if not check_response(request, response):
            return

        context = create_context(flow)

        # contextを作成した後、responseを書き換える特殊な処理
        # X-Rayで扱うレスポンスデータはcontext.response.contentに格納済みなので
        # flow.response.contentに値を代入してもhandlerによる後続の処理に影響はない

        # A. マスターデータの艦船グラフィック情報をマッピングに従って置換する
        if flow.request.path == MASTER_DATA_API_PATH:
            querier = Querier(self._db_conn)
            response_rewriter.replace_master_ship_graphics(flow, self._replace_ship_graphics_mapping, querier)

        # B. User-Agentがモバイル端末のそれなら音量を強制的にゼロにする
        if (
            flow.request.path == OPTION_SETTING_API_PATH
            and self._mute_mobile
            and MOBILE_USER_AGENT_PATTERN.search(flow.request.headers.get("user-agent", "")) is not None
        ):
            response_rewriter.force_mute(flow)

        # X. コンテンツをBrotli圧縮する
        # そもそも艦これAPIはHTTPSでないので、ブラウザがAccept-Encoding: brを送信しない
        # そのため、Brotli再圧縮機能は意味をなさないので封印
        # response_rewriter.brotli_compress(flow)

        for res_handler in self._response_handlers:
            if res_handler.accept(context):
                asyncio.ensure_future(res_handler.response(context))
