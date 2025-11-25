"""Clean database - delete all jobs and runs."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete, text

from app.database import async_session_maker
from app.models import Job, Run


async def clean_database():
    """Delete all jobs and runs from the database."""
    async with async_session_maker() as db:
        # Delete all runs
        await db.execute(delete(Run))
        await db.commit()
        print("✅ Deleted all runs")

        # Reset runs sequence
        await db.execute(text("ALTER SEQUENCE runs_id_seq RESTART WITH 1"))
        await db.commit()
        print("✅ Reset runs ID sequence to 1")

        # Delete all jobs
        await db.execute(delete(Job))
        await db.commit()
        print("✅ Deleted all jobs")

        # Reset jobs sequence
        await db.execute(text("ALTER SEQUENCE jobs_id_seq RESTART WITH 1"))
        await db.commit()
        print("✅ Reset jobs ID sequence to 1")

        print("\n🎉 Database cleaned successfully!")


if __name__ == "__main__":
    asyncio.run(clean_database())
