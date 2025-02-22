from dataclasses import dataclass
from typing import Any, List, Optional

from .utils import maybe_env_str


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class XRayConfig:
    """
    Configuration for the X-Ray Application
    """

    webhook: List["XRayWebhookConfig"]


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class XRayWebhookConfig:
    """
    Configuration for the X-Ray Webhook
    """

    base_url: str
    client_id: str
    client_secret: str
    local_token: Optional[str] = None


def create_x_ray_config(data: dict[str, Any]) -> XRayConfig:
    webhook = [create_webhook_config(webhook) for webhook in data.get("webhook", [])]

    return XRayConfig(webhook=webhook)


def create_webhook_config(data: dict[str, Any]) -> XRayWebhookConfig:
    base_url = str(data["base_url"])
    client_id = maybe_env_str("client_id", data)
    client_secret = maybe_env_str("client_secret", data)
    local_token = maybe_env_str("local_token", data)

    return XRayWebhookConfig(
        base_url=base_url,
        client_id=client_id or "",
        client_secret=client_secret or "",
        local_token=local_token,
    )
