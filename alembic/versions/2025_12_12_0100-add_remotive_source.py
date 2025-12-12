"""add_remotive_source

Revision ID: add_remotive_source
Revises: 877870b5e517
Create Date: 2025-12-12 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_remotive_source'
down_revision: Union[str, None] = '877870b5e517'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Seed Remotive scraper source
    op.execute("""
        INSERT INTO scraper_sources (name, label, description, enabled, priority, credentials_env_prefix, settings)
        VALUES (
            'remotive',
            'Remotive',
            'Premium remote job board with software development positions worldwide',
            true,
            150,
            'REMOTIVE',
            '{"locations": ["Worldwide", "Latin America (LATAM)", "Colombia"], "posted_days": 7}'
        )
        ON CONFLICT (name) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM scraper_sources WHERE name = 'remotive'")
