"""Admin endpoints for database management."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter()


class CleanupRequest(BaseModel):
    """Request body for database cleanup."""

    clean_jobs: bool = False
    clean_runs: bool = False
    clean_application_logs: bool = False
    clean_user_profiles: bool = False


class CleanupResponse(BaseModel):
    """Response from database cleanup operation."""

    success: bool
    message: str
    deleted_counts: dict[str, int]


@router.post("/cleanup", response_model=CleanupResponse)
async def cleanup_database(
    request: CleanupRequest,
    db: AsyncSession = Depends(get_db)
) -> CleanupResponse:
    """
    Clean up database tables based on selected options.

    WARNING: This will permanently delete data!
    """
    deleted_counts = {}
    messages = []

    try:
        # Clean application_logs
        if request.clean_application_logs:
            result = await db.execute(text("SELECT COUNT(*) FROM application_logs"))
            count = result.scalar()
            await db.execute(text("DELETE FROM application_logs"))
            deleted_counts["application_logs"] = count
            messages.append(f"Deleted {count} application logs")

        # Clean runs
        if request.clean_runs:
            result = await db.execute(text("SELECT COUNT(*) FROM runs"))
            count = result.scalar()
            await db.execute(text("DELETE FROM runs"))
            deleted_counts["runs"] = count
            messages.append(f"Deleted {count} runs")

        # Clean jobs
        if request.clean_jobs:
            result = await db.execute(text("SELECT COUNT(*) FROM jobs"))
            count = result.scalar()
            await db.execute(text("DELETE FROM jobs"))
            deleted_counts["jobs"] = count
            messages.append(f"Deleted {count} jobs")

        # Clean user_profiles (careful!)
        if request.clean_user_profiles:
            result = await db.execute(text("SELECT COUNT(*) FROM user_profiles"))
            count = result.scalar()
            await db.execute(text("DELETE FROM user_profiles"))
            deleted_counts["user_profiles"] = count
            messages.append(f"Deleted {count} user profiles")

        # Reset sequences
        sequences_to_reset = []
        if request.clean_jobs:
            sequences_to_reset.append("jobs_id_seq")
        if request.clean_runs:
            sequences_to_reset.append("runs_id_seq")
        if request.clean_application_logs:
            sequences_to_reset.append("application_logs_id_seq")
        if request.clean_user_profiles:
            sequences_to_reset.append("user_profiles_id_seq")

        for seq in sequences_to_reset:
            try:
                await db.execute(text(f"ALTER SEQUENCE {seq} RESTART WITH 1"))
            except Exception:
                pass  # Sequence might not exist

        if sequences_to_reset:
            messages.append(f"Reset {len(sequences_to_reset)} sequences")

        await db.commit()

        return CleanupResponse(
            success=True,
            message="; ".join(messages) if messages else "No data deleted (nothing selected)",
            deleted_counts=deleted_counts
        )

    except Exception as e:
        await db.rollback()
        return CleanupResponse(
            success=False,
            message=f"Cleanup failed: {str(e)}",
            deleted_counts=deleted_counts
        )


class DatabaseStatsResponse(BaseModel):
    """Database table row counts."""

    jobs: int
    runs: int
    application_logs: int
    user_profiles: int


@router.get("/database-stats", response_model=DatabaseStatsResponse)
async def get_database_stats(db: AsyncSession = Depends(get_db)) -> DatabaseStatsResponse:
    """Get current row counts for all tables."""
    stats = {}

    tables = ["jobs", "runs", "application_logs", "user_profiles"]
    for table in tables:
        try:
            result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
            stats[table] = result.scalar()
        except Exception:
            stats[table] = 0

    return DatabaseStatsResponse(**stats)
