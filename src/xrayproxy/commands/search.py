"""
収集したバスターデータを元に艦娘・深海棲艦を検索し、情報を表示するコマンド
"""

import argparse
import dataclasses
import sys
from typing import Optional

import sqlalchemy

from xrayproxy.config import load_config_toml
from xrayproxy.generated.sqlc.master_data import Querier
from xrayproxy.generated.sqlc.models import Ship
from xrayproxy.lib.ship import ship_graphic_url


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class SearchParams:
    ship_id: Optional[int]
    picture_book_no: Optional[int]
    name_prefix: Optional[str]
    banner: bool = False
    card: bool = False
    reward: bool = False
    recursive: bool = False
    no_replace: bool = False

    def to_options(self) -> "ImageOptions":
        return ImageOptions(
            banner=self.banner,
            card=self.card,
            reward=self.reward,
            recursive=self.recursive,
            no_replace=self.no_replace,
        )


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True, eq=False)
class ImageOptions:
    banner: bool = False
    card: bool = False
    reward: bool = False
    recursive: bool = False
    no_replace: bool = False


BIG_SEVEN = {
    541,  # 長門改二
    573,  # 陸奥改二
    571,  # Nelson
    576,  # Nelson改
    572,  # Rodney
    577,  # Rodney改
    601,  # Colorado
    1496,  # Colorado改
    913,  # Maryland
    918,  # Maryland改
}


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="search",
        description="収集したマスターデータを元に艦娘・深海棲艦を検索し、情報を表示する",
    )
    parser.add_argument("name", nargs="?", help="艦名（前方一致）もしくは図鑑ID")
    parser.add_argument("-i", "--ship-id", type=int, help="マスターデータ上の艦船ID")
    parser.add_argument("--banner", action="store_true", help="バナー画像のURLを表示")
    parser.add_argument("--card", action="store_true", help="カード画像のURLを表示")
    parser.add_argument("--reward", action="store_true", help="選択報酬画像のURLを表示")
    parser.add_argument("-r", "--recursive", action="store_true", help="改装後の艦娘も表示")
    parser.add_argument(
        "-x", "--no-replace", action="store_true", help="X-Ray Proxyによる画像URLの置換を無効化するクエリを追加"
    )
    parser.add_argument("-c", "--config", default="config/xrayproxy.toml", help="X-Ray Proxy設定ファイルのパス")
    args = parser.parse_args()

    config = load_config_toml(args.config)

    if args.name is None and args.ship_id is None:
        parser.print_help()
        return 2

    engine = sqlalchemy.create_engine(f"sqlite:///{config.database_path}")

    try:
        conn = engine.connect()
        params = params_from_args(args)
        count = print_ships(Querier(conn), params)
        if count == 0:
            print("No results.")
            return 1
    finally:
        engine.dispose()

    return 0


def params_from_args(args: argparse.Namespace) -> SearchParams:
    ship_id = args.ship_id
    picture_book_no = None
    name_prefix = None
    if ship_id is None and args.name is not None:
        try:
            picture_book_no = int(args.name)
        except ValueError:
            name_prefix = args.name

    return SearchParams(
        ship_id=ship_id,
        picture_book_no=picture_book_no,
        name_prefix=name_prefix,
        banner=args.banner,
        card=args.card,
        reward=args.reward,
        recursive=args.recursive,
        no_replace=args.no_replace,
    )


def print_ships(querier: Querier, params: SearchParams) -> int:
    options = params.to_options()

    def maybe_print_ship(s: Optional[Ship]) -> int:
        if s:
            print_ship(querier, s, options=options)
            return 1
        else:
            return 0

    if params.ship_id is not None:
        ship = querier.get_ship(id=params.ship_id)
        return maybe_print_ship(ship)

    if params.picture_book_no is not None:
        ship = querier.get_ship_by_picture_book_no(picture_book_no=params.picture_book_no)
        return maybe_print_ship(ship)

    count = 0
    memo = set()
    ships = querier.list_ship_by_name(name_prefix=params.name_prefix)

    for ship in ships:
        if options.recursive:
            if ship.id in memo:
                # avoid duplicate output
                continue
            memo.add(ship.id)
        print_ship(querier, ship, options=options, memo=memo)
        count += 1
    return count


def print_ship(
    querier: Querier,
    ship: Ship,
    *,
    options: Optional[ImageOptions] = None,
    depth: int = 0,
    memo: Optional[set[int]] = None,
) -> None:
    indent = "  " * (depth + 1)
    if depth == 0:
        ship_name = make_ship_name_display(ship)
        print(ship_name)

    if options is None:
        options = ImageOptions()

    shipgraph = querier.get_latest_shipgraph(ship_id=ship.id)
    if shipgraph:
        if ship.picture_book_no is not None:
            graphic_types = ["full", "full_dmg"]
            if ship.id in BIG_SEVEN:
                # ビッグ7の特殊砲撃画像
                graphic_types.append("special")
            elif ship.ship_type_id == 20:
                # 潜水母艦の潜水艦隊攻撃画像
                graphic_types.append("special")
                graphic_types.append("special_dmg")
            if options.banner:
                graphic_types.append("banner")
                graphic_types.append("banner_dmg")
            if options.card:
                graphic_types.append("card")
                graphic_types.append("card_dmg")
            if options.reward:
                graphic_types.append("reward_card")
                graphic_types.append("reward_icon")
        else:
            # 深海棲艦は*_dmg画像がない
            graphic_types = ["full"]
            if options.banner:
                graphic_types.append("banner")

        for graphic_type in graphic_types:
            url = ship_graphic_url(shipgraph, graphic_type, no_replace=options.no_replace)
            print(f"{indent}[画像:{graphic_type}] {url}")
            if graphic_type == "full" and (ship.name.endswith("姫-壊") or ship.name.endswith("鬼-壊")):
                # 弱体化(装甲破砕後)画像。"壊"でなくてもあったり、"壊"でもなかったりするが、とりあえず。
                url = ship_graphic_url(shipgraph, "full", debuff=True)
                print(f"{indent}[画像:full(弱体化)] {url}")

    if ship.after_ship_id is None:
        # after ship is not defined
        return

    after_ship_name = find_after_ship(querier, ship.after_ship_id)
    print(f"{indent}[改装:Lv{ship.after_lv}] {after_ship_name}")

    if not options.recursive or (memo is not None and ship.after_ship_id in memo):
        # avoid infinite loop
        return

    memo = memo or set()
    memo.add(ship.after_ship_id)
    after_ship = querier.get_ship(id=ship.after_ship_id)
    if after_ship:
        print_ship(querier, after_ship, options=options, depth=depth + 1, memo=memo)


def find_after_ship(querier: Querier, after_ship_id: int) -> str:
    ship = querier.get_ship(id=after_ship_id)
    if ship and ship.picture_book_no is not None:
        return f"{ship.name} (No.{ship.picture_book_no}, ID:{ship.id})"
    else:
        return f"unknown (ID:{after_ship_id})"


def make_ship_name_display(ship: Ship) -> str:
    # NOTE: 艦種表示したいところだが、ドロップ時に表示される艦種はマスターデータにはなく
    #       マスターデータで取れるのはapi_stype, api_mst_stypeの内部的な艦種のみ
    if ship.picture_book_no is not None:
        # 艦娘
        return f"{ship.name} (No.{ship.picture_book_no}, ID:{ship.id})"
    else:
        # 深海棲艦
        if ship.yomi != "" and ship.yomi != "-":
            # "yomi" could be elite, flagship, etc.
            return f"{ship.name}{ship.yomi} (ID:{ship.id})"
        else:
            # normal
            return f"{ship.name} (ID:{ship.id})"


if __name__ == "__main__":
    sys.exit(main())
