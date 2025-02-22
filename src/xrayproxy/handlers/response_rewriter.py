import json
from typing import Any

from mitmproxy.http import HTTPFlow

from xrayproxy.config import ReplaceShipGraphicEntry
from xrayproxy.generated.sqlc.master_data import Querier
from xrayproxy.handlers.response.master_data import MASTER_DATA_API_PATH
from xrayproxy.handlers.response.member_info import OPTION_SETTING_API_PATH


def replace_master_ship_graphics(
    flow: HTTPFlow, mapping: dict[int, ReplaceShipGraphicEntry], querier: Querier
) -> None:
    """
    api_mst_shipgraphのデータを指定された艦のものと置換する
    """
    if flow.request.path != MASTER_DATA_API_PATH:
        return
    if flow.response is None or flow.response.status_code != 200:
        return
    if flow.response.content is None:
        return
    if len(mapping) == 0:
        return

    content = flow.response.content.decode("utf-8")
    if content.startswith("svdata="):
        prefix = "svdata="
        data = json.loads(content[7:])
    else:
        prefix = ""
        data = json.loads(content)

    if "api_data" not in data:
        return
    if "api_mst_shipgraph" not in data["api_data"]:
        return

    data = replace_master_ship_graphics_data(flow.request.host, data, mapping, querier)

    # phase:3 置換したデータをレスポンスにセット
    flow.response.content = f"{prefix}{json.dumps(data, ensure_ascii=False)}".encode("utf-8")


def replace_master_ship_graphics_data(
    host: str, data: dict[str, Any], mapping: dict[int, ReplaceShipGraphicEntry], querier: Querier
) -> dict[str, Any]:
    target_ship_id_set = set(x.to_ship_id for x in mapping.values())
    replace_data_map: dict[int, dict[str, Any]] = {}

    # phase:1 置換先shipgraphを取得
    params_to_be_kept = frozenset(["api_id", "api_filename", "api_sortno"])
    for shipgraph in data["api_data"]["api_mst_shipgraph"]:
        ship_id = int(shipgraph["api_id"])
        if ship_id in target_ship_id_set:
            replace_data_map[ship_id] = {k: v for k, v in shipgraph.items() if k not in params_to_be_kept}

    # phase:2 shipgraphの中身を置換
    for shipgraph in data["api_data"]["api_mst_shipgraph"]:
        ship_id = int(shipgraph["api_id"])
        replace = mapping.get(ship_id)
        if replace is None:
            continue

        replace_data = replace_data_map.get(replace.to_ship_id)
        if replace_data is None:
            continue

        # 置換データをマージ。idとボイスのバージョン以外を置換
        for k, v in replace_data.items():
            if k == "api_version":
                # api_version[0]が画像のバージョン。ボイスのバージョンはそのままにする
                if "api_version" in shipgraph and len(shipgraph["api_version"]) > 1:
                    shipgraph[k] = [v[0]] + shipgraph["api_version"][1:]
                else:
                    shipgraph[k] = [v[0]]
            else:
                shipgraph[k] = v

        # ここから先はバージョン指定がある場合のみ
        if replace.to_version is None:
            continue

        versioned_shipgraph = querier.get_shipgraph(host=host, ship_id=replace.to_ship_id, version=replace.to_version)
        if versioned_shipgraph is None:
            continue

        # api_versionは置換しない
        # if "api_version" in shipgraph:
        #    shipgraph["api_version"][0] = str(replace.to_version)

        # 指定されたバージョンの座標データで置換
        points = json.loads(versioned_shipgraph.points)
        for k, f in points.items():
            api_key = f"api_{k}"
            if api_key in shipgraph:
                shipgraph[api_key] = f
    return data


def force_mute(flow: HTTPFlow) -> None:
    """
    api_volume_settingの値を全てゼロにする
    """
    if flow.request.path != OPTION_SETTING_API_PATH:
        return
    if flow.response is None or flow.response.status_code != 200:
        return
    if flow.response.content is None:
        return

    content = flow.response.content.decode("utf-8")
    if content.startswith("svdata="):
        prefix = "svdata="
        data = json.loads(content[7:])
    else:
        prefix = ""
        data = json.loads(content)

    if "api_data" not in data:
        return
    if "api_volume_setting" not in data["api_data"]:
        return

    # phase:1 api_volume_settingの既知のキーの値を全てゼロに
    volume_keys = (
        "api_be_left",
        "api_bgm",
        "api_duty",
        "api_se",
        "api_voice",
    )
    for key in volume_keys:
        if key in data["api_data"]["api_volume_setting"]:
            data["api_data"]["api_volume_setting"][key] = 0

    # phase:2 ミュートしたデータをレスポンスにセット
    flow.response.content = f"{prefix}{json.dumps(data, ensure_ascii=False)}".encode("utf-8")


def brotli_compress(flow: HTTPFlow) -> None:
    """
    Brotli圧縮を行う
    """
    if flow.response is None:
        return
    if flow.response.content is None:
        return
    if flow.response.headers.get("content-encoding") == "br":
        return
    if "br" in flow.request.headers.get("accept-encoding", ""):
        content_type = flow.response.headers.get("content-type", "")
        if content_type.startswith("text/") or content_type.startswith("application/json"):
            flow.response.encode("br")
