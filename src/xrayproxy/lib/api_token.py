from typing import Optional

import sqlalchemy

from xrayproxy.generated.sqlc.api_token import Querier


class ApiTokenManager:
    _member_id_by_token: dict[str, int] = {}
    _token_by_member_id: dict[int, str] = {}

    def __init__(self, conn: sqlalchemy.engine.Connection) -> None:
        self._conn = conn
        querier = Querier(self._conn)
        for token in querier.get_all_api_tokens():
            self._member_id_by_token[token.token] = token.member_id
            self._token_by_member_id[token.member_id] = token.token

    def get_member_id(self, token: str) -> Optional[int]:
        return self._member_id_by_token.get(token)

    def save_token(self, token: str, member_id: int) -> None:
        current_token = self._token_by_member_id.get(member_id)
        if current_token == token:
            return

        querier = Querier(self._conn)
        querier.save_api_token(member_id=member_id, token=token)
        self._conn.commit()

        self._member_id_by_token[token] = member_id
        self._token_by_member_id[member_id] = token
        if current_token is not None:
            self._member_id_by_token.pop(current_token)
