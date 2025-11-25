"""Clean all data from the database for fresh start."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.database import async_session_maker


async def clean_database():
    """Drop all data from all tables."""
    async with async_session_maker() as db:
        print("🧹 Cleaning database...")

        # List of tables to clean (in order to respect foreign keys)
        tables = [
            "application_logs",
            "runs",  # Runs has embedded logs, no separate table
            "jobs",
            "user_profiles",
        ]

        for table in tables:
            try:
                await db.execute(text(f"DELETE FROM {table}"))
                print(f"  ✅ Deleted {table}")
            except Exception as e:
                print(f"  ⚠️  Skipped {table} (doesn't exist or error)")

        # Reset sequences (auto-increment counters)
        sequences = [
            "jobs_id_seq",
            "runs_id_seq",
            "user_profiles_id_seq",
            "application_logs_id_seq",
        ]

        for seq in sequences:
            try:
                await db.execute(text(f"ALTER SEQUENCE {seq} RESTART WITH 1"))
            except Exception:
                pass  # Sequence doesn't exist, ignore

        print("  ✅ Reset all sequences")

        await db.commit()

        print("\n✨ Database is now clean!")
        print("\nNext steps:")
        print("  1. Run: uv run python scripts/init_user_profile.py")
        print("  2. Start a new scraping run")


if __name__ == "__main__":
    asyncio.run(clean_database())
