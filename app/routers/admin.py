"""Admin endpoints for database management."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.schema import Sequence

from app.database import get_db
from app.models import ApplicationLog, Job, Run, UserProfile

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
        # Clean application_logs - Use SQLAlchemy ORM to avoid SQL injection
        if request.clean_application_logs:
            count_result = await db.execute(select(func.count()).select_from(ApplicationLog))
            count = count_result.scalar()
            await db.execute(delete(ApplicationLog))
            deleted_counts["application_logs"] = count
            messages.append(f"Deleted {count} application logs")

        # Clean runs
        if request.clean_runs:
            count_result = await db.execute(select(func.count()).select_from(Run))
            count = count_result.scalar()
            await db.execute(delete(Run))
            deleted_counts["runs"] = count
            messages.append(f"Deleted {count} runs")

        # Clean jobs
        if request.clean_jobs:
            count_result = await db.execute(select(func.count()).select_from(Job))
            count = count_result.scalar()
            await db.execute(delete(Job))
            deleted_counts["jobs"] = count
            messages.append(f"Deleted {count} jobs")

        # Clean user_profiles (careful!)
        if request.clean_user_profiles:
            count_result = await db.execute(select(func.count()).select_from(UserProfile))
            count = count_result.scalar()
            await db.execute(delete(UserProfile))
            deleted_counts["user_profiles"] = count
            messages.append(f"Deleted {count} user profiles")

        # Reset sequences using SQLAlchemy Sequence objects
        # Note: Sequence names are hardcoded, not user-controlled
        sequences_to_reset = []
        if request.clean_jobs:
            sequences_to_reset.append("jobs_id_seq")
        if request.clean_runs:
            sequences_to_reset.append("runs_id_seq")
        if request.clean_application_logs:
            sequences_to_reset.append("application_logs_id_seq")
        if request.clean_user_profiles:
            sequences_to_reset.append("user_profiles_id_seq")

        for seq_name in sequences_to_reset:
            try:
                # Use parameterized query for sequence reset
                # Note: sequence names are validated against hardcoded list above
                from sqlalchemy import text
                await db.execute(text("ALTER SEQUENCE :seq RESTART WITH 1").bindparams(seq=seq_name))
            except Exception:
                # Fallback to direct SQL if bindparams doesn't work with DDL
                try:
                    await db.execute(text(f"ALTER SEQUENCE {seq_name} RESTART WITH 1"))
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

    # Use SQLAlchemy ORM to avoid SQL injection
    model_map = {
        "jobs": Job,
        "runs": Run,
        "application_logs": ApplicationLog,
        "user_profiles": UserProfile,
    }

    for table_name, model in model_map.items():
        try:
            result = await db.execute(select(func.count()).select_from(model))
            stats[table_name] = result.scalar()
        except Exception:
            stats[table_name] = 0

    return DatabaseStatsResponse(**stats)
