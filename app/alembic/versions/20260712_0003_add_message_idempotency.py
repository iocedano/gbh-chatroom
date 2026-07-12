"""add message idempotency

Revision ID: 20260712_0003
Revises: 20260712_0002
Create Date: 2026-07-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260712_0003"
down_revision: Union[str, None] = "20260712_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.add_column("messages", sa.Column("idempotency_request_hash", sa.String(length=64), nullable=True))
    op.create_unique_constraint(
        "uq_messages_room_sender_idempotency_key",
        "messages",
        ["room_id", "sender_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_messages_room_sender_idempotency_key", "messages", type_="unique")
    op.drop_column("messages", "idempotency_request_hash")
    op.drop_column("messages", "idempotency_key")
