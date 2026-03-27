"""add proposal source and changes json for manual edits

Revision ID: dad427d58527
Revises: 7d23bb5d061d
Create Date: 2026-02-24 18:43:30.998534

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'dad427d58527'
down_revision: Union[str, Sequence[str], None] = '7d23bb5d061d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE proposal_source_enum AS ENUM ('AI', 'MANUAL')")
    op.add_column('ai_proposals', sa.Column('source', sa.Enum('AI', 'MANUAL', name='proposal_source_enum'), nullable=False, server_default='AI'))
    op.add_column('ai_proposals', sa.Column('changes_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.alter_column('ai_proposals', 'ai_output_id',
               existing_type=sa.INTEGER(),
               nullable=True)


def downgrade() -> None:
    op.alter_column('ai_proposals', 'ai_output_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.drop_column('ai_proposals', 'changes_json')
    op.drop_column('ai_proposals', 'source')
    op.execute("DROP TYPE proposal_source_enum")