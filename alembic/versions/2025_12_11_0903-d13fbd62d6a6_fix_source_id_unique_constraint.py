"""fix_source_id_unique_constraint

Revision ID: d13fbd62d6a6
Revises: ee39e6cc9d5a
Create Date: 2025-12-11 09:03:01.585751

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd13fbd62d6a6'
down_revision: Union[str, None] = 'ee39e6cc9d5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def constraint_exists(conn, table_name: str, constraint_name: str) -> bool:
    """Check if a constraint exists on a table."""
    result = conn.execute(sa.text("""
        SELECT 1 FROM pg_constraint
        WHERE conname = :constraint_name
        AND conrelid = :table_name::regclass
    """), {"constraint_name": constraint_name, "table_name": table_name})
    return result.fetchone() is not None


def index_exists(conn, index_name: str) -> bool:
    """Check if an index exists."""
    result = conn.execute(sa.text("""
        SELECT 1 FROM pg_indexes WHERE indexname = :index_name
    """), {"index_name": index_name})
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # Fix jobs table: change source_id from unique to composite unique (source, source_id)
    # This is CRITICAL for multi-source architecture - different sources may use same IDs
    if index_exists(conn, 'ix_jobs_source_id'):
        op.drop_index('ix_jobs_source_id', table_name='jobs')
        op.create_index('ix_jobs_source_id', 'jobs', ['source_id'], unique=False)

    if not constraint_exists(conn, 'jobs', 'uq_jobs_source_source_id'):
        op.create_unique_constraint('uq_jobs_source_source_id', 'jobs', ['source', 'source_id'])

    # Fix source_runs table: add missing FK and unique constraint
    if not constraint_exists(conn, 'source_runs', 'uq_source_runs_run_source'):
        op.create_unique_constraint('uq_source_runs_run_source', 'source_runs', ['run_id', 'source_name'])

    if not constraint_exists(conn, 'source_runs', 'fk_source_runs_run_id_runs'):
        op.create_foreign_key('fk_source_runs_run_id_runs', 'source_runs', 'runs', ['run_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    # Reverse source_runs changes
    op.drop_constraint('fk_source_runs_run_id_runs', 'source_runs', type_='foreignkey')
    op.drop_constraint('uq_source_runs_run_source', 'source_runs', type_='unique')

    # Reverse jobs changes
    op.drop_constraint('uq_jobs_source_source_id', 'jobs', type_='unique')
    op.drop_index('ix_jobs_source_id', table_name='jobs')
    op.create_index('ix_jobs_source_id', 'jobs', ['source_id'], unique=True)
