import os
import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from .cloudflare import create_cloudflare_config
from .logbook_kai import create_logbook_kai_config
from .rewrite import create_rewrite_config
from .save import create_api_log_config, create_resource_config
from .storage import create_storage_config
from .utils import SubConfigLoader, parse_log_verbosity
from .xray import create_x_ray_config

if TYPE_CHECKING:
    from .cloudflare import CloudflareConfig
    from .logbook_kai import LogbookKaiConfig
    from .rewrite import RewriteConfig
    from .save import ApiLogConfig, ResourceConfig
    from .storage import StorageConfig
    from .xray import XRayConfig


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class Config:
    """
    The root configuration
    """

    assets_dir: str
    database_path: str
    log_verbosity: int
    enable_retry: bool
    retry_api_only: bool

    x_ray: "XRayConfig"
    api_log: "ApiLogConfig"
    resource: "ResourceConfig"
    storage: "StorageConfig"
    logbook_kai: "LogbookKaiConfig"
    rewrite: "RewriteConfig"
    cloudflare: Optional["CloudflareConfig"]


def load_config(loader: SubConfigLoader, data: dict[str, Any]) -> Config:
    assets_dir = str(data.get("assets_dir", "assets"))
    if os.path.isdir(assets_dir):
        assets_dir = os.path.abspath(assets_dir)
    else:
        raise ValueError(f'Directory "{assets_dir}" does not exist.')

    database_path = str(data.get("database_path", "data/x_ray_proxy.db"))

    log_verbosity = parse_log_verbosity(data.get("log_verbosity"), "log_verbosity")

    enable_retry = bool(data.get("enable_retry", False))
    retry_api_only = bool(data.get("retry_api_only", False))

    return Config(
        assets_dir=assets_dir,
        database_path=database_path,
        log_verbosity=log_verbosity,
        enable_retry=enable_retry,
        retry_api_only=retry_api_only,
        x_ray=create_x_ray_config(loader.get(data, "x_ray")),
        api_log=create_api_log_config(data.get("api_log", {})),
        resource=create_resource_config(loader.get(data, "resource")),
        storage=create_storage_config(loader.get(data, "storage")),
        logbook_kai=create_logbook_kai_config(loader.get(data, "logbook_kai")),
        rewrite=create_rewrite_config(loader.get(data, "rewrite")),
        cloudflare=create_cloudflare_config(loader.get(data, "cloudflare")) if "cloudflare" in data else None,
    )


def load_config_toml(path: str) -> Config:
    with open(path, "rb") as f:
        loader = SubConfigLoader(os.path.dirname(path))
        return load_config(loader, tomllib.load(f))
