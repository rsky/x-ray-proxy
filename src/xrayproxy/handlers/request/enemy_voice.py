import os
from logging import getLogger
from typing import Optional

from mitmproxy.http import Request, Response

from xrayproxy.config import Config
from xrayproxy.handlers.base import BaseRequestHandler
from xrayproxy.handlers.mixin import ResponseFileMixin

logger = getLogger(__name__)


class EnemyVoiceRequestHandler(BaseRequestHandler, ResponseFileMixin):
    """
    うるさい敵を黙らせるRequestHandler
    """

    _enabled: bool = False
    _cache_max_age: int
    _silent_mp3_path: str
    _all_ships: bool
    _target_ship_ids: frozenset[str]
    _all_voice_types: bool
    _target_voice_types: frozenset[str]

    def __init__(self) -> None:
        super().__init__(logger)

    def configure(self, config: Config) -> None:
        super().configure(config)

        self._silent_mp3_path = os.path.join(config.assets_dir, "one_sec.mp3")

        c = config.rewrite.mute_enemy_voice
        self._enabled = c.enabled
        self._target_ship_ids = frozenset(c.ship_ids)
        self._all_ships = not bool(c.ship_ids)
        self._target_voice_types = frozenset(c.voice_types)
        self._all_voice_types = not bool(c.voice_types)
        self._cache_max_age = config.rewrite.cache_max_age

    async def request(self, request: Request) -> Optional[Response]:
        if self._enabled and self._check_path(request.path):
            return self.response_file(self._silent_mp3_path, "audio/mp3", request.headers.get("If-None-Match"))
        else:
            return None

    def _check_path(self, path: str) -> bool:
        # 深海棲艦ボイスのパスでなければ何もしない
        if not path.startswith("/kcs/sound/kc9998/"):
            return False

        filename = path.split("/")[-1]
        if len(filename) < 10:
            return False

        # ファイル名は <prefix> + ship_id + voice_type + ".mp3"
        # prefixの生成ルールは未調査だが、その桁数は可変であることが確認できたので、後ろから数えて分解する
        ship_id = filename[-10:-6]
        voice_type = filename[-6:-4]
        extension = filename[-4:]

        if (
            extension == ".mp3"
            and (self._all_voice_types or voice_type in self._target_voice_types)
            and (self._all_ships or ship_id in self._target_ship_ids)
        ):
            return True
        else:
            return False
