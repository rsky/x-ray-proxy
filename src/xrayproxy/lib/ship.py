from urllib.parse import urlencode, urlunparse

from xrayproxy.generated.sqlc.models import Shipgraph
from xrayproxy.lib.hash import ship_graphic_hash
from xrayproxy.lib.http import QUERY_KEY_NO_REPLACE, QUERY_VALUE_NO_REPLACE


def ship_graphic_url(sg: Shipgraph, graphic_type: str, debuff: bool = False, no_replace: bool = False) -> str:
    """
    艦娘画像のURLを生成する
    """
    hash_value = ship_graphic_hash(sg.ship_id, graphic_type)

    if graphic_type in {"full", "full_dmg"}:
        if debuff:
            filename = f"{sg.ship_id:04d}_d_{hash_value}_{sg.filename}.png"
        else:
            filename = f"{sg.ship_id:04d}_{hash_value}_{sg.filename}.png"
    else:
        filename = f"{sg.ship_id:04d}_{hash_value}.png"

    query = ""
    if not debuff:
        query_params: tuple[tuple[str, str], ...] = (("version", str(sg.version)),)
        if no_replace:
            query_params += ((QUERY_KEY_NO_REPLACE, QUERY_VALUE_NO_REPLACE),)
        query = urlencode(query_params)

    return urlunparse(
        (
            "https",  # scheme
            sg.host,  # netloc
            f"/kcs2/resources/ship/{graphic_type}/{filename}",  # url
            "",  # params
            query,  # query
            "",  # fragment
        )
    )
