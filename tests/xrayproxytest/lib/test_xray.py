import datetime
import json
import math
import unittest
from dataclasses import asdict

from xrayproxy.lib.xray import (
    Context,
    JsonHolder,
    RequestData,
    ResponseData,
    create_payload,
    recursive_shorten_keys,
)


class XRayTestCase(unittest.TestCase):
    def test_recursive_shorten_keys(self):
        source = {
            "api_result": 1,
            "api_result_msg": "成功",
            "api_data": {
                "api_member_id": "7777777",
                "api_nickname": "api_名称未設定",
                "api_nickname_id": "88888888",
                "api_active_flag": 1,
                "api_starttime": 1720000000000,
                "api_level": 120,
                "api_rank": 1,
                "api_experience": 200000000,
                "api_fleetname": None,
                "api_comment": "※",
                "api_comment_id": "166666666",
                "api_max_chara": 630,
                "api_max_slotitem": 2750,
                "api_max_kagu": 0,
                "api_playtime": 0,
                "api_tutorial": 0,
                "api_furniture": [1, 2, 3, 4, 5, 6],
                "api_count_deck": 4,
                "api_count_kdock": 4,
                "api_count_ndock": 4,
                "api_fcoin": 350000,
                "api_st_win": 500000,
                "api_st_lose": 1000,
                "api_ms_count": 100000,
                "api_ms_success": 100000,
                "api_pt_win": 40000,
                "api_pt_lose": 100,
                "api_pt_challenged": 0,
                "api_pt_challenged_win": 0,
                "api_firstflag": 1,
                "api_tutorial_progress": 100,
                "api_pvp": [0, 0],
                "api_medals": 30,
                "api_array": [
                    {"api_id": 1, "api_name": "name1", "api_flag": True},
                    {"api_id": 2, "api_name": "name2", "api_flag": False},
                    {"api_id": 3, "api_name": "name3", "api_flag": True},
                ],
            },
        }
        expected = {
            "result": 1,
            "result_msg": "成功",
            "data": {
                "member_id": "7777777",
                "nickname": "api_名称未設定",
                "nickname_id": "88888888",
                "active_flag": 1,
                "starttime": 1720000000000,
                "level": 120,
                "rank": 1,
                "experience": 200000000,
                "fleetname": None,
                "comment": "※",
                "comment_id": "166666666",
                "max_chara": 630,
                "max_slotitem": 2750,
                "max_kagu": 0,
                "playtime": 0,
                "tutorial": 0,
                "furniture": [1, 2, 3, 4, 5, 6],
                "count_deck": 4,
                "count_kdock": 4,
                "count_ndock": 4,
                "fcoin": 350000,
                "st_win": 500000,
                "st_lose": 1000,
                "ms_count": 100000,
                "ms_success": 100000,
                "pt_win": 40000,
                "pt_lose": 100,
                "pt_challenged": 0,
                "pt_challenged_win": 0,
                "firstflag": 1,
                "tutorial_progress": 100,
                "pvp": [0, 0],
                "medals": 30,
                "array": [
                    {"id": 1, "name": "name1", "flag": True},
                    {"id": 2, "name": "name2", "flag": False},
                    {"id": 3, "name": "name3", "flag": True},
                ],
            },
        }
        shorten = recursive_shorten_keys(source, "")
        self.assertDictEqual(shorten, expected)

    def test_create_payload(self):
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        timestamp = math.floor(now.timestamp() * 1000)
        context = Context(
            proxy_auth_username=None,
            request=RequestData(
                url="http://example.com/kcsapi/api_get_member/ship2",
                method="POST",
                host="example.com",
                path="/kcsapi/api_get_member/ship2",
                path_with_query="/kcsapi/api_get_member/ship2",
                query={},
                form={"api_token": "123456", "api_param": "value"},
                content_type_all="application/x-www-form-urlencoded",
                content_type="application/x-www-form-urlencoded",
                content=b"api_token%3D123456%26api_param%3Dvalue",
            ),
            response=ResponseData(
                content_type_all="application/json",
                content_type="application/json",
                content_encoding=None,
                content=(
                    r"{"
                    r'"api_result":1,'
                    r'"api_result_msg":"成功",'
                    r'"api_data":[{"api_id": 1,"api_ship_id":1}],'
                    r'"api_data_deck":[{"api_id": 1,"api_name":"第1艦隊","api_ship":[1,-1,-1,-1,-1,-1]}]'
                    r"}"
                ).encode("utf-8"),
                json_holder=JsonHolder(),
            ),
            respond_at=now,
            respond_at_millis=timestamp,
        )
        response_data = json.loads(context.response.content.decode("utf-8"))
        payload = create_payload(context, 12345678, response_data, log_bucket="test-bucket", log_key="test-key")
        expected = {
            "member_id": 12345678,
            "request": {
                "url": "http://example.com/kcsapi/api_get_member/ship2",
                "parameters": {
                    "param": "value",
                },
            },
            "response": {
                "timestamp": timestamp,
                "data": {
                    "ship_data": [
                        {"id": 1, "ship_id": 1},
                    ],
                    "deck_data": [
                        {"id": 1, "name": "第1艦隊", "ship": [1, -1, -1, -1, -1, -1]},
                    ],
                },
            },
            "log": {
                "bucket": "test-bucket",
                "key": "test-key",
            },
        }
        from x_ray_webhook.models.api_data_post_request import ApiDataPostRequest

        req = ApiDataPostRequest(
            member_id=payload.member_id,
            request=payload.request,
            response=payload.response,
            log=payload.log,
        )
        self.assertDictEqual(req.to_dict(), expected)


if __name__ == "__main__":
    unittest.main()
