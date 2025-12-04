from dataclasses import dataclass
from typing import Any, Optional

DEFAULT_SHIP_IDS_TO_MUTE = (
    1898,  # バタビア沖棲姫 (7-3-2ボス)
    1901,  # バタビア沖棲姫-壊 (同上)
    2059,  # ヒ船団棲姫 (7-4ボス)
    2061,  # ヒ船団棲姫-壊 (同上)
)
DEFAULT_VOICE_TYPES_TO_MUTE = (
    # 10,  # 開幕前
    # 20,  # 砲撃
    30,  # 被弾
    40,  # 撃沈
    41,  # 浄化
)


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class RewriteConfig:
    """
    Configuration for rewriting responses
    """

    dummy_favicon: bool
    cache_max_age: int
    mute_mobile: bool
    mute_mobile_options: "MobileUserAgentOptions"
    mute_enemy_voice: "MuteEnemyVoiceConfig"
    replace_ship_graphics: "ReplaceShipGraphicConfig"


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class MuteEnemyVoiceConfig:
    """
    Configuration for mute enemy voice
    """

    enabled: bool
    ship_ids: tuple[str, ...]
    voice_types: tuple[str, ...]


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class MobileUserAgentOptions:
    """
    Optional Configuration of mute for mobile browsers
    """

    safari: bool
    firefox: bool
    user_agent: Optional[str]


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class ReplaceShipGraphicEntry:
    """
    Configuration entry for replacing ship graphic
    """

    from_ship_id: int
    to_ship_id: int
    to_version: Optional[int] = None
    full_only: bool = False


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class ReplaceShipGraphicConfig:
    """
    Configuration for replacing ship graphic
    """

    mapping: dict[int, "ReplaceShipGraphicEntry"]


def create_rewrite_config(data: dict[str, Any]) -> RewriteConfig:
    mute_mobile_user_agent = data.get("mute_mobile_user_agent")
    replace_ship_graphic_entries = tuple(
        create_replace_ship_graphic_entry(raw_entry) for raw_entry in data.get("replace_ship_graphic", [])
    )

    return RewriteConfig(
        dummy_favicon=bool(data.get("dummy_favicon", False)),
        cache_max_age=int(data.get("cache_max_age", 14400)),
        mute_mobile=bool(data.get("mute_mobile", False)),
        mute_mobile_options=MobileUserAgentOptions(
            safari=bool(data.get("mute_mobile_safari", False)),
            firefox=bool(data.get("mute_mobile_firefox", False)),
            user_agent=str(mute_mobile_user_agent) if mute_mobile_user_agent else None,
        ),
        mute_enemy_voice=create_mute_boss_voice_config(data.get("mute_enemy_voice", {})),
        replace_ship_graphics=ReplaceShipGraphicConfig(
            mapping={entry.from_ship_id: entry for entry in replace_ship_graphic_entries}
        ),
    )


def create_mute_boss_voice_config(data: dict[str, Any]) -> MuteEnemyVoiceConfig:
    return MuteEnemyVoiceConfig(
        enabled=bool(data.get("enabled", False)),
        ship_ids=tuple(str(ship_id) for ship_id in data.get("ship_ids", DEFAULT_SHIP_IDS_TO_MUTE)),
        voice_types=tuple(str(voice_type) for voice_type in data.get("voice_types", DEFAULT_VOICE_TYPES_TO_MUTE)),
    )


def create_replace_ship_graphic_entry(data: dict[str, Any]) -> ReplaceShipGraphicEntry:
    from_ship_id = int(data["from_ship_id"])
    to_ship_id = data.get("to_ship_id")
    version = data.get("to_version")

    return ReplaceShipGraphicEntry(
        from_ship_id=from_ship_id,
        to_ship_id=int(to_ship_id) if to_ship_id is not None else from_ship_id,
        to_version=int(version) if version is not None else None,
        full_only=bool(data.get("full_only", False)),
    )
