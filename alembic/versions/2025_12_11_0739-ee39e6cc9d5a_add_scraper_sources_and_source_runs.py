"""Add scraper_sources and source_runs tables for multi-source support

Revision ID: ee39e6cc9d5a
Revises: afeaf2c6ef29
Create Date: 2025-12-11 07:39:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee39e6cc9d5a'
down_revision: Union[str, None] = 'afeaf2c6ef29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(conn, table_name: str) -> bool:
    """Check if a table exists."""
    result = conn.execute(sa.text(f"""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = '{table_name}'
    """))
    return result.fetchone() is not None


def column_exists(conn, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    result = conn.execute(sa.text(f"""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = '{table_name}' AND column_name = '{column_name}'
    """))
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # Create scraper_sources table (if not exists)
    if not table_exists(conn, 'scraper_sources'):
        op.create_table('scraper_sources',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=50), nullable=False),
            sa.Column('label', sa.String(length=100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
            sa.Column('credentials_env_prefix', sa.String(length=100), nullable=True),
            sa.Column('settings', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_scraper_sources'))
        )
        op.create_index(op.f('ix_scraper_sources_name'), 'scraper_sources', ['name'], unique=True)
        op.create_index(op.f('ix_scraper_sources_enabled'), 'scraper_sources', ['enabled'], unique=False)

    # Create source_runs table (if not exists)
    if not table_exists(conn, 'source_runs'):
        op.create_table('source_runs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('run_id', sa.Integer(), nullable=False),
            sa.Column('source_name', sa.String(length=50), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='running'),
            sa.Column('jobs_found', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('jobs_new', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('jobs_duplicate', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('jobs_failed', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('logs', sa.JSON(), nullable=True),
            sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('duration_seconds', sa.Float(), nullable=True),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_source_runs')),
            sa.ForeignKeyConstraint(['run_id'], ['runs.id'], name=op.f('fk_source_runs_run_id_runs'), ondelete='CASCADE'),
            sa.UniqueConstraint('run_id', 'source_name', name=op.f('uq_source_runs_run_source'))
        )
        op.create_index(op.f('ix_source_runs_run_id'), 'source_runs', ['run_id'], unique=False)
        op.create_index(op.f('ix_source_runs_source_name'), 'source_runs', ['source_name'], unique=False)
        op.create_index(op.f('ix_source_runs_status'), 'source_runs', ['status'], unique=False)

    # Add resolved_url column to jobs table for cross-source deduplication (if not exists)
    if not column_exists(conn, 'jobs', 'resolved_url'):
        op.add_column('jobs', sa.Column('resolved_url', sa.String(length=500), nullable=True))
        op.create_index(op.f('ix_jobs_resolved_url'), 'jobs', ['resolved_url'], unique=False)

    # Seed initial scraper source: Working Nomads (if not exists)
    op.execute("""
        INSERT INTO scraper_sources (name, label, description, enabled, priority, credentials_env_prefix, settings)
        VALUES (
            'working_nomads',
            'Working Nomads',
            'Remote job board for digital nomads with development and tech positions',
            true,
            100,
            'WORKING_NOMADS',
            '{"category": "development", "location": "anywhere,colombia", "posted_days": 7}'
        )
        ON CONFLICT (name) DO NOTHING
    """)


def downgrade() -> None:
    # Remove resolved_url from jobs
    op.drop_index(op.f('ix_jobs_resolved_url'), table_name='jobs')
    op.drop_column('jobs', 'resolved_url')

    # Drop source_runs table
    op.drop_index(op.f('ix_source_runs_status'), table_name='source_runs')
    op.drop_index(op.f('ix_source_runs_source_name'), table_name='source_runs')
    op.drop_index(op.f('ix_source_runs_run_id'), table_name='source_runs')
    op.drop_table('source_runs')

    # Drop scraper_sources table
    op.drop_index(op.f('ix_scraper_sources_enabled'), table_name='scraper_sources')
    op.drop_index(op.f('ix_scraper_sources_name'), table_name='scraper_sources')
    op.drop_table('scraper_sources')
