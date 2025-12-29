"""Database migration utilities."""

import logging
import subprocess
import sys

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    """
    Run Alembic migrations to upgrade the database to the latest version.

    This function runs automatically on app startup to ensure the database
    schema is up to date. It executes `alembic upgrade head` programmatically.
    """
    try:
        logger.info("🔄 Running database migrations...")

        # Run alembic upgrade head
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True
        )

        # Log output if there were any migrations applied
        if result.stdout.strip():
            logger.info(f"✓ Migrations complete:\n{result.stdout}")
        else:
            logger.info("✓ Database schema is up to date")

    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Migration failed: {e.stderr}")
        raise RuntimeError(f"Database migration failed: {e.stderr}") from e
    except Exception as e:
        logger.error(f"❌ Unexpected error during migration: {e}")
        raise
