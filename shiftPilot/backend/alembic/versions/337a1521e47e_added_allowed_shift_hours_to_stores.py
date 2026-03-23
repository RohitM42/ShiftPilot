"""added allowed shift hours to stores

Revision ID: 337a1521e47e
Revises: e9921aea2f21
Create Date: 2026-03-23 17:40:31.625334

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text



# revision identifiers, used by Alembic.
revision: str = '337a1521e47e'
down_revision: Union[str, Sequence[str], None] = 'e9921aea2f21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
      op.add_column('stores', sa.Column(
          'allowed_shift_hours',
          postgresql.ARRAY(sa.Integer()),
          nullable=False,
          server_default=text("'{4,5,6,7,8,9,10,11,12}'")
      ))

def downgrade() -> None:
      op.drop_column('stores', 'allowed_shift_hours')
