"""
SQLiteに保存されているAPIログ情報を削除するコマンド
"""

import argparse
import datetime
import sys

import sqlalchemy

from xrayproxy.config import load_config_toml
from xrayproxy.generated.sqlc.api_log import Querier


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="log_truncate",
        description="SQLiteに保存されているAPIログ情報を削除するコマンド",
    )
    parser.add_argument(
        "-c",
        "--config",
        default="config/xrayproxy.toml",
        help="X-Ray Proxy設定ファイルのパス",
    )
    parser.add_argument(
        "-d",
        "--days-before",
        type=int,
        default=30,
        help="現在の日時から起算して指定日数以上古いレコードを削除。デフォルトは30日",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="削除せずに削除対象件数のみ表示する",
    )
    args = parser.parse_args()

    config = load_config_toml(args.config)

    days_before = max(args.days_before, 0)
    created_at_before = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_before)
    created_at_before_str = created_at_before.strftime("%Y-%m-%d %H:%M:%S")

    engine = sqlalchemy.create_engine(f"sqlite:///{config.database_path}")

    try:
        conn = engine.connect()
        querier = Querier(conn)

        count_to_delete = querier.count_api_log_before(created_at_before=created_at_before_str)
        if args.dry_run:
            print(f"Would delete {count_to_delete} records.")
        else:
            print(f"Deleting {count_to_delete} records...")
            querier.delete_old_api_log(created_at_before=created_at_before_str)
            remaining_count = querier.count_all_api_log()
            print(f"Done. Remaining records: {remaining_count}.")
    finally:
        engine.dispose()

    return 0


if __name__ == "__main__":
    sys.exit(main())
