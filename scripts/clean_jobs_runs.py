"""Clean jobs and runs from database but keep user profile."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.database import async_session_maker


async def clean_jobs_and_runs():
    """Delete jobs and runs, but keep user profile."""
    async with async_session_maker() as db:
        print("🧹 Cleaning jobs and runs from database...")

        # List of tables to clean (keep user_profiles!)
        tables = [
            "application_logs",
            "runs",
            "jobs",
        ]

        for table in tables:
            try:
                result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                await db.execute(text(f"DELETE FROM {table}"))
                print(f"  ✅ Deleted {count} rows from {table}")
            except Exception as e:
                print(f"  ⚠️  Error cleaning {table}: {e}")

        # Reset sequences (auto-increment counters)
        sequences = [
            "jobs_id_seq",
            "runs_id_seq",
            "application_logs_id_seq",
        ]

        for seq in sequences:
            try:
                await db.execute(text(f"ALTER SEQUENCE {seq} RESTART WITH 1"))
            except Exception:
                pass  # Sequence doesn't exist, ignore

        print("  ✅ Reset all sequences")

        await db.commit()

        print("\n✨ Database cleaned! User profile preserved.")
        print("\nYou can now trigger a new scraping run.")


if __name__ == "__main__":
    asyncio.run(clean_jobs_and_runs())
