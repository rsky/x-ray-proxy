from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class CloudflareStorageConfig:
    """
    Cloudflare R2 specific configuration
    """

    api_token: Optional[str]
    zone_id: Optional[str]
    resource_bucket_public_host_name: Optional[str]
    data_bucket_public_host_name: Optional[str]

    def __post_init__(self) -> None:
        if self.api_token is None:
            return

        missing_keys = []
        if not self.zone_id:
            missing_keys.append("zone_id")
        if not self.resource_bucket_public_host_name:
            missing_keys.append("resource_bucket_public_host_name")
        if not self.data_bucket_public_host_name:
            missing_keys.append("data_bucket_public_host_name")

        if missing_keys:
            missing = ", ".join(missing_keys)
            raise ValueError(f"storage.cloudflare.api_token is set, but {missing} is missing.")


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
    resource_bucket: str
    allow_public_access: bool
    cloudflare: CloudflareStorageConfig

    def to_s3_client_kwargs(self) -> dict[str, Any]:
        return {
            "region_name": self.region,
            "aws_access_key_id": self.access_key_id,
            "aws_secret_access_key": self.secret_access_key,
            "endpoint_url": self.endpoint_url,
        }


def create_cloudflare_storage_config(data: dict[str, Any]) -> CloudflareStorageConfig:
    return CloudflareStorageConfig(
        api_token=str(data["api_token"]) if "api_token" in data else None,
        zone_id=str(data["zone_id"]) if "zone_id" in data else None,
        resource_bucket_public_host_name=(
            str(data["resource_bucket_public_host_name"]) if "resource_bucket_public_host_name" in data else None
        ),
        data_bucket_public_host_name=(
            str(data["data_bucket_public_host_name"]) if "data_bucket_public_host_name" in data else None
        ),
    )


def create_storage_config(data: dict[str, Any]) -> StorageConfig:
    resource_bucket = str(data.get("resource_bucket") or data.get("resources_bucket", ""))

    return StorageConfig(
        region=str(data.get("region", "")),
        access_key_id=str(data.get("access_key_id", "")),
        secret_access_key=str(data.get("secret_access_key", "")),
        endpoint_url=str(data["endpoint_url"]) if "endpoint_url" in data else None,
        api_log_bucket=str(data.get("api_log_bucket", "")),
        data_bucket=str(data.get("data_bucket", "")),
        resource_bucket=resource_bucket,
        allow_public_access=bool(data.get("allow_public_access", False)),
        cloudflare=create_cloudflare_storage_config(data.get("cloudflare", {})),
    )
