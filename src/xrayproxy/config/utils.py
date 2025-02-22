import logging
import os
import re
import tomllib
from typing import Any, Optional

logger = logging.getLogger(__name__)


def parse_log_verbosity(level_name: Optional[str], key: str) -> int:
    if level_name is None:
        return logging.DEBUG

    log_level_names_mapping = logging.getLevelNamesMapping()
    if level_name in log_level_names_mapping:
        level = log_level_names_mapping[level_name]
        logger.log(level, f"{key}={level_name}")
        return level
    else:
        logger.warning(f"{key}={level_name} is not valid, fallback to DEBUG.")
        return logging.DEBUG


def maybe_env_str(key: str, data: dict[str, Any]) -> Optional[str]:
    if key in data:
        value = str(data[key])
        if re.fullmatch(r"\$\{\w+}", value):
            return os.getenv(value[2:-1])
        else:
            return value
    else:
        return None


class SubConfigLoader:
    def __init__(self, base_dir: str):
        self._base_dir = base_dir

    def get(self, data: dict[str, Any], config_name: str) -> dict[str, Any]:
        config = data.get(config_name, {})
        if isinstance(config, str):
            m = re.fullmatch(r"include:(\S+\.toml)", config)
            if m:
                with open(os.path.join(self._base_dir, m.group(1)), "rb") as f:
                    return tomllib.load(f)
            raise ValueError(f"Invalid value for {config_name}: {config}")
        elif isinstance(config, dict):
            return config
        else:
            raise ValueError(f"Invalid type for {config_name}: {type(config)}")
