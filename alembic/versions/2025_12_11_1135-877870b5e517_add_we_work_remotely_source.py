"""add_we_work_remotely_source

Revision ID: 877870b5e517
Revises: d13fbd62d6a6
Create Date: 2025-12-11 11:35:07.088658

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '877870b5e517'
down_revision: Union[str, None] = 'd13fbd62d6a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Seed We Work Remotely scraper source
    op.execute("""
        INSERT INTO scraper_sources (name, label, description, enabled, priority, credentials_env_prefix, settings)
        VALUES (
            'we_work_remotely',
            'We Work Remotely',
            'Popular remote job board with backend and fullstack programming positions',
            false,
            200,
            'WE_WORK_REMOTELY',
            '{"categories": ["backend", "fullstack"], "posted_days": 7}'
        )
        ON CONFLICT (name) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM scraper_sources WHERE name = 'we_work_remotely'")
