from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class CloudflareConfig:
    """
    Cloudflare specific configuration
    """

    api_token: str
    zone_id: str
    r2_resource_public_host_name: Optional[str]


def create_cloudflare_config(data: dict[str, Any]) -> CloudflareConfig:
    return CloudflareConfig(
        api_token=str(data["api_token"]),
        zone_id=str(data["zone_id"]),
        r2_resource_public_host_name=_read_optional_str(data, "r2_resource_public_host_name"),
    )


def _read_optional_str(data: dict[str, Any], key: str) -> Optional[str]:
    return str(data.get(key, "")) if key in data else None


def get_r2_resource_public_host_name(config: Optional[CloudflareConfig]) -> Optional[str]:
    if config is None:
        return None
    return config.r2_resource_public_host_name
