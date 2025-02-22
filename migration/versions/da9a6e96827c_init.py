"""init

Revision ID: da9a6e96827c
Revises:
Create Date: 2024-02-29 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "da9a6e96827c"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ship
    op.create_table(
        "ship",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sort_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("yomi", sa.Text(), nullable=False),
        sa.Column("ship_type_id", sa.Integer(), nullable=True),
        sa.Column("picture_book_no", sa.Integer(), nullable=True),
        sa.Column("after_lv", sa.Integer(), nullable=True),
        sa.Column("after_ship_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_ship_sort_id", "ship", ["sort_id"], unique=False)
    op.create_index("idx_ship_name", "ship", ["name"], unique=False)
    op.create_index("idx_ship_picture_book_no", "ship", ["picture_book_no"], unique=False)

    # shipgraph
    shipgraph_version = sa.Column("version", sa.Integer(), nullable=False)
    shipgraph_updated_at = sa.Column(
        "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
    )
    op.create_table(
        "shipgraph",
        sa.Column("host", sa.Text(), nullable=False),
        sa.Column("ship_id", sa.Integer(), nullable=False),
        shipgraph_version,
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("full_width", sa.Integer(), nullable=True, default=sa.Null),
        sa.Column("full_height", sa.Integer(), nullable=True, default=sa.Null),
        sa.Column("full_dmg_width", sa.Integer(), nullable=True, default=sa.Null),
        sa.Column("full_dmg_height", sa.Integer(), nullable=True, default=sa.Null),
        sa.Column("points", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        shipgraph_updated_at,
        sa.PrimaryKeyConstraint("host", "ship_id", "version"),
    )
    op.create_index(
        "idx_shipgraph_ship_id_latest",
        "shipgraph",
        ["ship_id", shipgraph_version.desc(), shipgraph_updated_at.desc()],
        unique=False,
    )

    # api_log
    op.create_table(
        "api_log",
        sa.Column("bucket", sa.Text(), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=True, default=sa.Null),
        sa.Column("host", sa.Text(), nullable=False),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("params", sa.JSON(), nullable=True, default=sa.Null),
        sa.Column("raw_size", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_api_log_created_at", "api_log", ["created_at"], unique=False)
    op.create_index("idx_api_log_member_id_created_at", "api_log", ["member_id", "created_at"], unique=False)
    op.create_index(
        "idx_api_log_member_id_path_created_at", "api_log", ["member_id", "path", "created_at"], unique=False
    )
    op.create_index("idx_api_log_path_created_at", "api_log", ["path", "created_at"], unique=False)

    # api_token
    op.create_table(
        "api_token",
        sa.Column("member_id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("token", sa.Text(), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def downgrade() -> None:
    pass
