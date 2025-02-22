from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class StorageConfig:
    """
    Configuration for object storage
    """

    region: str
    access_key_id: str
    secret_access_key: str
    endpoint_url: Optional[str]
    api_log_bucket: str
    data_bucket: str
    resources_bucket: str
    allow_public_access: bool

    def to_s3_client_kwargs(self) -> dict[str, Any]:
        return {
            "region_name": self.region,
            "aws_access_key_id": self.access_key_id,
            "aws_secret_access_key": self.secret_access_key,
            "endpoint_url": self.endpoint_url,
        }


def create_storage_config(data: dict[str, Any]) -> StorageConfig:
    return StorageConfig(
        region=str(data.get("region", "")),
        access_key_id=str(data.get("access_key_id", "")),
        secret_access_key=str(data.get("secret_access_key", "")),
        endpoint_url=str(data["endpoint_url"]) if "endpoint_url" in data else None,
        api_log_bucket=str(data.get("api_log_bucket", "")),
        data_bucket=str(data.get("data_bucket", "")),
        resources_bucket=str(data.get("resources_bucket", "")),
        allow_public_access=bool(data.get("allow_public_access", False)),
    )
