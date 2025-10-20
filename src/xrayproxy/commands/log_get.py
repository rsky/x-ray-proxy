"""
SQLiteに保存されているAPIログ情報を取得するコマンド
"""

import argparse
import asyncio
import datetime
import sys

import aioboto3

from xrayproxy.config import load_config_toml


def datetime_type(date_str: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(date_str)


async def main() -> None:
    parser = argparse.ArgumentParser(
        prog="log_get",
        description="SQLiteに保存されているAPIログ情報を取得する",
    )
    parser.add_argument("object_key", help="ログデータのキー")
    parser.add_argument("-o", "--output", help="出力先ファイルパス。指定しない場合は標準出力")
    parser.add_argument("-c", "--config", default="config/xrayproxy.toml", help="X-Ray Proxy設定ファイルのパス")
    args = parser.parse_args()

    config = load_config_toml(args.config)

    bucket = config.storage.api_log_bucket
    session = aioboto3.Session()
    async with session.client("s3", **config.storage.to_s3_client_kwargs()) as s3:
        obj = await s3.get_object(Bucket=bucket, Key=args.object_key)
        content = await obj["Body"].read()
        out = args.output
        if out is None:
            sys.stdout.buffer.write(content)
        else:
            with open(out, "wb") as f:
                f.write(content)


if __name__ == "__main__":
    try:
        asyncio.run(main())
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(1)
