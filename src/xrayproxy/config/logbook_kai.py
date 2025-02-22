from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class LogbookKaiConfig:
    """
    Configuration for logbook-kai passive server
    """

    enabled: bool
    host: str
    port: int


def create_logbook_kai_config(data: dict[str, Any]) -> LogbookKaiConfig:
    return LogbookKaiConfig(
        enabled=bool(data.get("enabled", False)),
        host=str(data.get("host", "127.0.0.1")),
        port=int(data.get("port", 8888)),
    )
