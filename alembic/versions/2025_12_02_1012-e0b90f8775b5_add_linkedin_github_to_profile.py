"""add_linkedin_github_to_profile

Revision ID: e0b90f8775b5
Revises: 21383ec8a724
Create Date: 2025-12-02 10:12:50.380281

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e0b90f8775b5'
down_revision: Union[str, None] = '21383ec8a724'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user_profiles', sa.Column('linkedin', sa.String(length=500), nullable=True))
    op.add_column('user_profiles', sa.Column('github', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('user_profiles', 'github')
    op.drop_column('user_profiles', 'linkedin')
