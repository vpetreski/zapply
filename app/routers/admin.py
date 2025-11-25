"""Admin endpoints for database management."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ApplicationLog, AppSettings, Job, Run, UserProfile
from app.utils import log_to_console

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
    log_to_console("="*60)
    log_to_console("📡 API: POST /api/admin/cleanup - Database cleanup")
    log_to_console(f"   Jobs: {request.clean_jobs}, Runs: {request.clean_runs}")
    log_to_console(f"   Logs: {request.clean_application_logs}, Profiles: {request.clean_user_profiles}")
    log_to_console("="*60)

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
                # Direct string formatting is safe here because seq_name is validated
                # against the hardcoded list above (jobs_id_seq, runs_id_seq, etc.)
                # PostgreSQL DDL statements don't support bind parameters
                from sqlalchemy import text
                await db.execute(text(f"ALTER SEQUENCE {seq_name} RESTART WITH 1"))
            except Exception:
                # Sequence might not exist, which is fine
                pass

        if sequences_to_reset:
            messages.append(f"Reset {len(sequences_to_reset)} sequences")

        await db.commit()

        log_to_console(f"✅ Cleanup completed: {deleted_counts}")
        log_to_console("="*60 + "\n")

        return CleanupResponse(
            success=True,
            message="; ".join(messages) if messages else "No data deleted (nothing selected)",
            deleted_counts=deleted_counts
        )

    except Exception as e:
        await db.rollback()
        log_to_console(f"❌ Cleanup failed: {str(e)}")
        log_to_console("="*60 + "\n")
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


class RunFrequencyRequest(BaseModel):
    """Request to set run frequency."""

    frequency: str  # "manual", "daily", or "hourly"


class RunFrequencyResponse(BaseModel):
    """Response with current run frequency."""

    frequency: str


@router.get("/settings/run-frequency", response_model=RunFrequencyResponse)
async def get_run_frequency(db: AsyncSession = Depends(get_db)) -> RunFrequencyResponse:
    """Get current run frequency setting."""
    result = await db.execute(
        select(AppSettings).where(AppSettings.key == "run_frequency")
    )
    setting = result.scalar_one_or_none()
    frequency = setting.value if setting else "manual"
    return RunFrequencyResponse(frequency=frequency)


@router.post("/settings/run-frequency", response_model=RunFrequencyResponse)
async def set_run_frequency(
    request: RunFrequencyRequest, db: AsyncSession = Depends(get_db)
) -> RunFrequencyResponse:
    """Set run frequency (manual, daily, or hourly)."""
    log_to_console(f"📡 API: POST /api/admin/settings/run-frequency - Set to '{request.frequency}'")

    # Validate frequency value
    valid_frequencies = ["manual", "daily", "hourly"]
    if request.frequency not in valid_frequencies:
        log_to_console(f"❌ Invalid frequency: {request.frequency}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid frequency. Must be one of: {', '.join(valid_frequencies)}"
        )

    # Update or create setting in database
    result = await db.execute(
        select(AppSettings).where(AppSettings.key == "run_frequency")
    )
    setting = result.scalar_one_or_none()

    if setting:
        log_to_console(f"   Updating existing setting from '{setting.value}' to '{request.frequency}'")
        setting.value = request.frequency
    else:
        log_to_console(f"   Creating new setting: '{request.frequency}'")
        setting = AppSettings(key="run_frequency", value=request.frequency)
        db.add(setting)

    await db.commit()

    # Reconfigure scheduler with new frequency
    try:
        from app.services.scheduler_service import reconfigure_scheduler
        reconfigure_scheduler(request.frequency)
        log_to_console(f"✅ Scheduler reconfigured to '{request.frequency}'")
    except Exception as e:
        log_to_console(f"❌ Failed to reconfigure scheduler: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reconfigure scheduler: {str(e)}"
        )

    return RunFrequencyResponse(frequency=request.frequency)


class ScrapeJobLimitRequest(BaseModel):
    """Request to set scrape job limit."""

    limit: int  # 0 = unlimited, otherwise limit to N jobs


class ScrapeJobLimitResponse(BaseModel):
    """Response with current scrape job limit."""

    limit: int


@router.get("/settings/scrape-job-limit", response_model=ScrapeJobLimitResponse)
async def get_scrape_job_limit(db: AsyncSession = Depends(get_db)) -> ScrapeJobLimitResponse:
    """Get current scrape job limit setting."""
    result = await db.execute(
        select(AppSettings).where(AppSettings.key == "scrape_job_limit")
    )
    setting = result.scalar_one_or_none()
    limit = int(setting.value) if setting else 0
    return ScrapeJobLimitResponse(limit=limit)


@router.post("/settings/scrape-job-limit", response_model=ScrapeJobLimitResponse)
async def set_scrape_job_limit(
    request: ScrapeJobLimitRequest, db: AsyncSession = Depends(get_db)
) -> ScrapeJobLimitResponse:
    """Set scrape job limit (0 = unlimited, otherwise limit to N jobs per run)."""
    log_to_console(f"📡 API: POST /api/admin/settings/scrape-job-limit - Set to {request.limit}")

    # Validate limit value
    if request.limit < 0:
        log_to_console(f"❌ Invalid limit: {request.limit} (must be >= 0)")
        raise HTTPException(
            status_code=400,
            detail="Limit must be 0 (unlimited) or a positive number"
        )

    # Update or create setting in database
    result = await db.execute(
        select(AppSettings).where(AppSettings.key == "scrape_job_limit")
    )
    setting = result.scalar_one_or_none()

    if setting:
        log_to_console(f"   Updating existing setting from {setting.value} to {request.limit}")
        setting.value = str(request.limit)
    else:
        log_to_console(f"   Creating new setting: {request.limit}")
        setting = AppSettings(key="scrape_job_limit", value=str(request.limit))
        db.add(setting)

    await db.commit()

    log_to_console(f"✅ Scrape job limit updated to {request.limit}")
    return ScrapeJobLimitResponse(limit=request.limit)
