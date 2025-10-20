"""
オブジェクトストレージに保存されているAPIログ情報を取得するコマンド
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

import aioboto3
from botocore.exceptions import ClientError

from xrayproxy.config import load_config_toml


async def main() -> None:
    parser = argparse.ArgumentParser(
        prog="log_get",
        description="オブジェクトストレージに保存されているAPIログ情報を取得する",
    )
    parser.add_argument("object_key", help="ログデータのキー")
    parser.add_argument("-o", "--output", type=Path, help="出力先ファイルパス。指定しない場合は標準出力")
    parser.add_argument(
        "-m", "--metadata", action="store_true", help="オブジェクト情報とメタデータを標準エラー出力に表示"
    )
    parser.add_argument("-c", "--config", default="config/xrayproxy.toml", help="X-Ray Proxy設定ファイルのパス")
    args = parser.parse_args()

    config = load_config_toml(args.config)

    bucket = config.storage.api_log_bucket
    session = aioboto3.Session()
    async with session.client("s3", **config.storage.to_s3_client_kwargs()) as s3:
        try:
            obj = await s3.get_object(Bucket=bucket, Key=args.object_key)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey":
                print(f"Error: オブジェクトが見つかりません: {args.object_key}", file=sys.stderr)
            elif error_code == "AccessDenied":
                print("Error: アクセスが拒否されました", file=sys.stderr)
            else:
                print(f"Error: S3エラー: {e}", file=sys.stderr)
            return

        if args.metadata:
            print("Object Info:", file=sys.stderr)
            for field in ("ContentType", "LastModified", "ETag"):
                print(f"  {field}: {obj.get(field, 'N/A')}", file=sys.stderr)
            metadata = obj.get("Metadata", {})
            if metadata:
                print("Custom Metadata:", file=sys.stderr)
                for key, value in metadata.items():
                    print(f"  {key}: {value}", file=sys.stderr)

        content = await obj["Body"].read()
        out: Optional[Path] = args.output
        if out is None:
            sys.stdout.buffer.write(content)
        else:
            out.write_bytes(content)


if __name__ == "__main__":
    try:
        asyncio.run(main())
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(-1)
