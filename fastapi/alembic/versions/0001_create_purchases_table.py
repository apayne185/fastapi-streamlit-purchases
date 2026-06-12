"""create purchases table

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "purchases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_name", sa.String(), nullable=False),
        sa.Column("country", sa.String(), nullable=False),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchases_id", "purchases", ["id"])
    op.create_index("ix_purchases_customer_name", "purchases", ["customer_name"])
    op.create_index("ix_purchases_country", "purchases", ["country"])
    op.create_index("ix_purchases_purchase_date", "purchases", ["purchase_date"])


def downgrade() -> None:
    op.drop_index("ix_purchases_purchase_date", table_name="purchases")
    op.drop_index("ix_purchases_country", table_name="purchases")
    op.drop_index("ix_purchases_customer_name", table_name="purchases")
    op.drop_index("ix_purchases_id", table_name="purchases")
    op.drop_table("purchases")
