"""
SQLiteに保存されているAPIログ情報をJSON Lines形式でリスト表示するコマンド
"""

import argparse
import datetime
import json
import sys
from dataclasses import asdict
from typing import Iterator, Optional

import sqlalchemy

from xrayproxy.config import load_config_toml
from xrayproxy.generated.sqlc.api_log import (
    ListApiLogDescParams,
    ListApiLogParams,
    Querier,
)
from xrayproxy.generated.sqlc.models import ApiLog


def datetime_type(date_str: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(date_str)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="log_list",
        description="SQLiteに保存されているAPIログ情報をJSON Lines形式でリスト表示する",
    )
    parser.add_argument("-p", "--path", type=str, help="APIパス接頭辞で絞り込む")
    parser.add_argument("-m", "--member-id", type=int, help="member_idで絞り込む")
    parser.add_argument("--start", type=datetime_type, help="抽出開始日時。デフォルトは今日の0時")
    parser.add_argument("--end", type=datetime_type, help="抽出終了日時。デフォルトは現在時刻")
    parser.add_argument("-l", "--limit", type=int, default=10, help="表示件数。デフォルトは10件")
    parser.add_argument("-r", "--desc", action="store_true", help="降順で表示。デフォルトは昇順")
    parser.add_argument(
        "--interactive", action="store_true", help="limit件ごとに続行するか確認する対話モードを有効にする"
    )
    parser.add_argument("--all", action="store_true", help="limitを無視して全件取得する。対話モードでは無効")
    parser.add_argument("-c", "--config", default="config/xrayproxy.toml", help="X-Ray Proxy設定ファイルのパス")
    args = parser.parse_args()

    config = load_config_toml(args.config)

    # LIKE演算使用にpathをエスケープして%を追加。`sqlc generate` で `path LIKE :path ESCAPE '\\' がエラーになったので
    # コード生成後に xrayproxy/generated/sqlc/api_log.py を編集して `path LIKE :p1 ESCAPE '\\'` としている。
    path = args.path.replace("_", "\\_").replace("%", "\\%") + "%" if args.path else None
    member_id = args.member_id if args.member_id and args.member_id > 0 else None
    # 引数の日付をUTCに変換する。timezone-naiveな場合はローカルタイムゾーンからUTCに変換される
    start_datetime: datetime.datetime = (
        args.start.astimezone(datetime.timezone.utc)
        if args.start
        else datetime.datetime.today()
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .astimezone(datetime.timezone.utc)
    )
    end_datetime: datetime.datetime = (
        args.end.astimezone(datetime.timezone.utc) if args.end else datetime.datetime.now(datetime.timezone.utc)
    )
    non_interactive = not args.interactive
    if non_interactive and args.all:
        # 非対話モードで全件取得する場合はlimitを事実上無制限にする
        row_limit = sys.maxsize
        read_limit = sys.maxsize
    else:
        row_limit = max(args.limit, 0)
        # 1行多く読み込んで次のページがあるか確認する
        read_limit = row_limit + 1
    descending = args.desc

    engine = sqlalchemy.create_engine(f"sqlite:///{config.database_path}")

    try:
        list_api_log(
            engine=engine,
            path=path,
            member_id=member_id,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            row_limit=row_limit,
            read_limit=read_limit,
            descending=descending,
            non_interactive=non_interactive,
        )
    except KeyboardInterrupt:
        pass
    finally:
        engine.dispose()

    return 0


def list_api_log(
    *,
    engine: sqlalchemy.engine.base.Engine,
    path: Optional[str],
    member_id: Optional[int],
    start_datetime: datetime.datetime,
    end_datetime: datetime.datetime,
    row_limit: int,
    read_limit: int,
    descending: bool,
    non_interactive: bool,
) -> None:
    conn = engine.connect()
    querier = Querier(conn)

    cursor = sys.maxsize if descending else 0
    read_next = True

    while read_next:
        results = query_api_log(
            querier=querier,
            path=path,
            member_id=member_id,
            cursor=cursor,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            limit=read_limit,
            descending=descending,
        )
        num_rows = 0

        for row in results:
            num_rows += 1
            created_at = to_utc_datetime(row.created_at)
            if num_rows <= row_limit:
                data = asdict(row)
                # paramsはJSON文字列なのでデコードして出力する
                if row.params:
                    data["params"] = json.loads(row.params)
                # UTCをローカルタイムゾーンに変換し、ISO 8601形式で出力する
                data["created_at"] = created_at.astimezone().isoformat()
                # data["raw_created_at"] = row.created_at
                # rowidは出力しない
                del data["rowid"]
                print(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
            elif non_interactive:
                # 非対話モードで結果がlimit件を超えた場合は終了
                read_next = False
            else:
                # 対話モードで結果がlimit件を超えた場合は続行するか確認
                read_next = input("Continue? [Y/n]: ").lower() in ("", "y", "yes")
                # 同一created_atのレコードが複数ある場合にも正しくページングするためにrowidをカーソルにする
                cursor = row.rowid
                if descending:
                    end_datetime = created_at
                else:
                    start_datetime = created_at

        if num_rows == 0 or num_rows <= row_limit:
            read_next = False


def to_utc_datetime(source: str | datetime.datetime) -> datetime.datetime:
    dt: datetime.datetime
    # datetime.datetime型でない場合は変換する
    if type(source) is datetime.datetime:
        dt = source
    elif type(source) is str:
        dt = datetime.datetime.fromisoformat(source)
    else:
        raise TypeError(f"Invalid type: {type(source)}")

    # UTCに変換して返す
    if dt.tzinfo is None:
        # timezone-naiveな場合はUTCとして扱う
        return dt.replace(tzinfo=datetime.timezone.utc)
    else:
        # timezone-awareな場合はUTCに変換する
        return dt.astimezone(datetime.timezone.utc)


_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def query_api_log(
    *,
    querier: Querier,
    path: Optional[str],
    member_id: Optional[int],
    cursor: int,
    start_datetime: datetime.datetime,
    end_datetime: datetime.datetime,
    limit: int,
    descending: bool,
) -> Iterator[ApiLog]:
    if descending:
        return querier.list_api_log_desc(
            ListApiLogDescParams(
                path=path,
                member_id=member_id,
                cursor=cursor,
                start_datetime=start_datetime.strftime(_DATETIME_FORMAT),
                end_datetime=end_datetime.strftime(_DATETIME_FORMAT),
                limit=limit,
            )
        )
    return querier.list_api_log(
        ListApiLogParams(
            path=path,
            member_id=member_id,
            cursor=cursor,
            start_datetime=start_datetime.strftime(_DATETIME_FORMAT),
            end_datetime=end_datetime.strftime(_DATETIME_FORMAT),
            limit=limit,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
