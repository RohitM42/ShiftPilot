"""removed redundant enum value

Revision ID: e9921aea2f21
Revises: 5138c453f6c1
Create Date: 2026-03-22 22:07:11.644034

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e9921aea2f21'
down_revision: Union[str, Sequence[str], None] = '5138c453f6c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.execute("ALTER TYPE proposal_type_enum RENAME TO proposal_type_enum_old")
    op.execute("CREATE TYPE proposal_type_enum AS ENUM ('AVAILABILITY', 'COVERAGE', 'ROLE_REQUIREMENT')")
    op.execute("ALTER TABLE ai_proposals ALTER COLUMN type TYPE proposal_type_enum USING type::text::proposal_type_enum")
    op.execute("DROP TYPE proposal_type_enum_old")

def downgrade():
    op.execute("ALTER TYPE proposal_type_enum RENAME TO proposal_type_enum_old")
    op.execute("CREATE TYPE proposal_type_enum AS ENUM ('AVAILABILITY', 'COVERAGE', 'ROLE_REQUIREMENT', 'LABOUR_BUDGET')")
    op.execute("ALTER TABLE ai_proposals ALTER COLUMN type TYPE proposal_type_enum USING type::text::proposal_type_enum")
    op.execute("DROP TYPE proposal_type_enum_old")