from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class ApiLogConfig:
    """
    Configuration for API log
    """

    save_sortie_log: bool
    save_practice_log: bool
    save_other_log: bool
    pretty: bool


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class ResourceConfig:
    """
    Configuration for resource
    """

    save_mode: Optional[str]
    ship_graphic_versioning: bool


def create_api_log_config(data: dict[str, Any]) -> ApiLogConfig:
    return ApiLogConfig(
        save_sortie_log=bool(data.get("save_sortie_log", False)),
        save_practice_log=bool(data.get("save_practice_log", False)),
        save_other_log=bool(data.get("save_other_log", False)),
        pretty=bool(data.get("pretty", False)),
    )


def create_resource_config(data: dict[str, Any]) -> ResourceConfig:
    return ResourceConfig(
        save_mode=str(data["save_mode"]) if "save_mode" in data else None,
        ship_graphic_versioning=bool(data.get("ship_graphic_versioning", False)),
    )
