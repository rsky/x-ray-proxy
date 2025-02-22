import difflib
import json
import unittest

from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine

from xrayproxy.config import ReplaceShipGraphicEntry
from xrayproxy.generated.sqlc.master_data import Querier, SaveShipgraphParams
from xrayproxy.handlers.response_rewriter import replace_master_ship_graphics_data


class ReplaceMasterShipGraphicsDataTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._data = {
            "api_data": {
                "api_mst_shipgraph": [
                    {
                        "api_id": 433,
                        "api_filename": "qtuuhjmqmvfh",
                        "api_version": ["2", "1", "808"],
                        "api_battle_n": [48, 66],
                        "api_battle_d": [24, 222],
                        "api_sortno": 233,
                        "api_boko_n": [60, 60],
                        "api_boko_d": [90, 252],
                        "api_kaisyu_n": [36, -42],
                        "api_kaisyu_d": [18, -9],
                        "api_kaizo_n": [-18, -24],
                        "api_kaizo_d": [6, 120],
                        "api_map_n": [60, 60],
                        "api_map_d": [42, 222],
                        "api_ensyuf_n": [12, 54],
                        "api_ensyuf_d": [48, 192],
                        "api_ensyue_n": [-30, 0],
                        "api_weda": [354, 150],
                        "api_wedb": [132, 144],
                        "api_pa": [0, 0],
                        "api_pab": [0, 0],
                    },
                    {
                        "api_id": 966,
                        "api_filename": "erhlwuihpcnw",
                        "api_version": ["51", "1", "808"],
                        "api_battle_n": [135, 181],
                        "api_battle_d": [150, 245],
                        "api_sortno": 566,
                        "api_boko_n": [98, 179],
                        "api_boko_d": [10, 242],
                        "api_kaisyu_n": [40, 14],
                        "api_kaisyu_d": [82, 23],
                        "api_kaizo_n": [100, 64],
                        "api_kaizo_d": [29, 61],
                        "api_map_n": [118, 159],
                        "api_map_d": [128, 229],
                        "api_ensyuf_n": [115, 150],
                        "api_ensyuf_d": [128, 177],
                        "api_ensyue_n": [112, 0],
                        "api_weda": [226, -15],
                        "api_wedb": [121, 197],
                        "api_pa": [0, 0],
                        "api_pab": [0, 0],
                    },
                ],
            },
        }

        engine = create_engine("sqlite://")
        metadata = MetaData()
        Table(
            "shipgraph",
            metadata,
            Column("host", String, primary_key=True),
            Column("ship_id", Integer, primary_key=True),
            Column("version", Integer, primary_key=True),
            Column("filename", String),
            Column("full_width", Integer),
            Column("full_height", Integer),
            Column("full_dmg_width", Integer),
            Column("full_dmg_height", Integer),
            Column("points", String),
            Column("created_at", String),
            Column("updated_at", String),
        )
        metadata.create_all(engine)
        self._engine = engine

    def tearDown(self):
        self._engine.dispose()

    @staticmethod
    def _setup_shipgraph(querier: Querier) -> None:
        querier.save_shipgraph(
            SaveShipgraphParams(
                host="localhost",
                ship_id=433,
                version=1,
                filename="qtuuhjmqmvfh",
                points=json.dumps(
                    {
                        "battle_n": [1, 2],
                        "battle_d": [3, 4],
                        "boko_n": [5, 6],
                        "boko_d": [7, 8],
                        "kaisyu_n": [9, 10],
                        "kaisyu_d": [11, 12],
                        "kaizo_n": [13, 14],
                        "kaizo_d": [15, 16],
                        "map_n": [17, 18],
                        "map_d": [19, 20],
                        "ensyuf_n": [21, 22],
                        "ensyuf_d": [23, 24],
                        "ensyue_n": [25, 26],
                        "weda": [27, 28],
                        "wedb": [29, 30],
                        "pa": [31, 32],
                        "pab": [33, 34],
                    },
                    separators=(",", ":"),
                ),
            )
        )

    def test_without_version(self) -> None:
        expected = {
            "api_data": {
                "api_mst_shipgraph": [
                    {
                        "api_id": 433,
                        "api_filename": "qtuuhjmqmvfh",
                        "api_version": ["51", "1", "808"],
                        "api_battle_n": [135, 181],
                        "api_battle_d": [150, 245],
                        "api_sortno": 233,
                        "api_boko_n": [98, 179],
                        "api_boko_d": [10, 242],
                        "api_kaisyu_n": [40, 14],
                        "api_kaisyu_d": [82, 23],
                        "api_kaizo_n": [100, 64],
                        "api_kaizo_d": [29, 61],
                        "api_map_n": [118, 159],
                        "api_map_d": [128, 229],
                        "api_ensyuf_n": [115, 150],
                        "api_ensyuf_d": [128, 177],
                        "api_ensyue_n": [112, 0],
                        "api_weda": [226, -15],
                        "api_wedb": [121, 197],
                        "api_pa": [0, 0],
                        "api_pab": [0, 0],
                    },
                    {
                        "api_id": 966,
                        "api_filename": "erhlwuihpcnw",
                        "api_version": ["51", "1", "808"],
                        "api_battle_n": [135, 181],
                        "api_battle_d": [150, 245],
                        "api_sortno": 566,
                        "api_boko_n": [98, 179],
                        "api_boko_d": [10, 242],
                        "api_kaisyu_n": [40, 14],
                        "api_kaisyu_d": [82, 23],
                        "api_kaizo_n": [100, 64],
                        "api_kaizo_d": [29, 61],
                        "api_map_n": [118, 159],
                        "api_map_d": [128, 229],
                        "api_ensyuf_n": [115, 150],
                        "api_ensyuf_d": [128, 177],
                        "api_ensyue_n": [112, 0],
                        "api_weda": [226, -15],
                        "api_wedb": [121, 197],
                        "api_pa": [0, 0],
                        "api_pab": [0, 0],
                    },
                ],
            },
        }

        mapping = {
            433: ReplaceShipGraphicEntry(from_ship_id=433, to_ship_id=966, to_version=None),
        }

        with self._engine.connect() as conn:
            querier = Querier(conn)
            self._setup_shipgraph(querier)

            result = replace_master_ship_graphics_data("localhost", self._data, mapping, querier)
            msg = "\n".join(
                difflib.unified_diff(
                    json.dumps(expected, indent=2).splitlines(),
                    json.dumps(result, indent=2).splitlines(),
                )
            )
            self.assertDictEqual(result, expected, msg=msg)

    def test_with_version(self) -> None:
        expected = {
            "api_data": {
                "api_mst_shipgraph": [
                    {
                        "api_id": 433,
                        "api_filename": "qtuuhjmqmvfh",
                        "api_version": ["2", "1", "808"],
                        "api_battle_n": [48, 66],
                        "api_battle_d": [24, 222],
                        "api_sortno": 233,
                        "api_boko_n": [60, 60],
                        "api_boko_d": [90, 252],
                        "api_kaisyu_n": [36, -42],
                        "api_kaisyu_d": [18, -9],
                        "api_kaizo_n": [-18, -24],
                        "api_kaizo_d": [6, 120],
                        "api_map_n": [60, 60],
                        "api_map_d": [42, 222],
                        "api_ensyuf_n": [12, 54],
                        "api_ensyuf_d": [48, 192],
                        "api_ensyue_n": [-30, 0],
                        "api_weda": [354, 150],
                        "api_wedb": [132, 144],
                        "api_pa": [0, 0],
                        "api_pab": [0, 0],
                    },
                    {
                        "api_id": 966,
                        "api_filename": "erhlwuihpcnw",
                        "api_version": ["2", "1", "808"],
                        "api_battle_n": [1, 2],
                        "api_battle_d": [3, 4],
                        "api_sortno": 566,
                        "api_boko_n": [5, 6],
                        "api_boko_d": [7, 8],
                        "api_kaisyu_n": [9, 10],
                        "api_kaisyu_d": [11, 12],
                        "api_kaizo_n": [13, 14],
                        "api_kaizo_d": [15, 16],
                        "api_map_n": [17, 18],
                        "api_map_d": [19, 20],
                        "api_ensyuf_n": [21, 22],
                        "api_ensyuf_d": [23, 24],
                        "api_ensyue_n": [25, 26],
                        "api_weda": [27, 28],
                        "api_wedb": [29, 30],
                        "api_pa": [31, 32],
                        "api_pab": [33, 34],
                    },
                ],
            },
        }

        mapping = {
            966: ReplaceShipGraphicEntry(from_ship_id=966, to_ship_id=433, to_version=1),
        }

        with self._engine.connect() as conn:
            querier = Querier(conn)
            self._setup_shipgraph(querier)

            result = replace_master_ship_graphics_data("localhost", self._data, mapping, querier)
            msg = "\n".join(
                difflib.unified_diff(
                    json.dumps(expected, indent=2).splitlines(),
                    json.dumps(result, indent=2).splitlines(),
                )
            )
            self.assertDictEqual(result, expected, msg=msg)

    def test_with_version_same_ship(self) -> None:
        expected = {
            "api_data": {
                "api_mst_shipgraph": [
                    {
                        "api_id": 433,
                        "api_filename": "qtuuhjmqmvfh",
                        "api_version": ["2", "1", "808"],
                        "api_battle_n": [1, 2],
                        "api_battle_d": [3, 4],
                        "api_sortno": 233,
                        "api_boko_n": [5, 6],
                        "api_boko_d": [7, 8],
                        "api_kaisyu_n": [9, 10],
                        "api_kaisyu_d": [11, 12],
                        "api_kaizo_n": [13, 14],
                        "api_kaizo_d": [15, 16],
                        "api_map_n": [17, 18],
                        "api_map_d": [19, 20],
                        "api_ensyuf_n": [21, 22],
                        "api_ensyuf_d": [23, 24],
                        "api_ensyue_n": [25, 26],
                        "api_weda": [27, 28],
                        "api_wedb": [29, 30],
                        "api_pa": [31, 32],
                        "api_pab": [33, 34],
                    },
                    {
                        "api_id": 966,
                        "api_filename": "erhlwuihpcnw",
                        "api_version": ["51", "1", "808"],
                        "api_battle_n": [135, 181],
                        "api_battle_d": [150, 245],
                        "api_sortno": 566,
                        "api_boko_n": [98, 179],
                        "api_boko_d": [10, 242],
                        "api_kaisyu_n": [40, 14],
                        "api_kaisyu_d": [82, 23],
                        "api_kaizo_n": [100, 64],
                        "api_kaizo_d": [29, 61],
                        "api_map_n": [118, 159],
                        "api_map_d": [128, 229],
                        "api_ensyuf_n": [115, 150],
                        "api_ensyuf_d": [128, 177],
                        "api_ensyue_n": [112, 0],
                        "api_weda": [226, -15],
                        "api_wedb": [121, 197],
                        "api_pa": [0, 0],
                        "api_pab": [0, 0],
                    },
                ],
            },
        }

        mapping = {
            433: ReplaceShipGraphicEntry(from_ship_id=433, to_ship_id=433, to_version=1),
        }

        with self._engine.connect() as conn:
            querier = Querier(conn)
            self._setup_shipgraph(querier)

            result = replace_master_ship_graphics_data("localhost", self._data, mapping, querier)
            msg = "\n".join(
                difflib.unified_diff(
                    json.dumps(expected, indent=2).splitlines(),
                    json.dumps(result, indent=2).splitlines(),
                )
            )
            self.assertDictEqual(result, expected, msg=msg)
