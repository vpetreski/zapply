"""Runs API endpoints."""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Run, RunPhase, RunStatus, SourceRun
from app.routers.auth import User, get_current_user
from app.utils import log_to_console

router = APIRouter(prefix="/api/runs", tags=["runs"])


def source_run_to_dict(source_run: SourceRun) -> dict[str, Any]:
    """Convert SourceRun to dictionary."""
    return {
        "id": source_run.id,
        "run_id": source_run.run_id,
        "source_name": source_run.source_name,
        "status": source_run.status,
        "jobs_found": source_run.jobs_found,
        "jobs_new": source_run.jobs_new,
        "jobs_duplicate": source_run.jobs_duplicate,
        "jobs_failed": source_run.jobs_failed,
        "error_message": source_run.error_message,
        "logs": source_run.logs,
        "started_at": source_run.started_at.isoformat() if source_run.started_at else None,
        "completed_at": source_run.completed_at.isoformat() if source_run.completed_at else None,
        "duration_seconds": source_run.duration_seconds,
    }


def run_to_dict(run: Run, source_runs: list[SourceRun] | None = None, include_logs: bool = True) -> dict[str, Any]:
    """Convert Run to dictionary with optional source_runs."""
    result = {
        "id": run.id,
        "status": run.status,
        "phase": run.phase,
        "trigger_type": run.trigger_type,
        "stats": run.stats,
        "logs": run.logs if include_logs else None,
        "error_message": run.error_message,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "duration_seconds": run.duration_seconds,
    }

    if source_runs is not None:
        result["source_runs"] = [source_run_to_dict(sr) for sr in source_runs]

    return result


@router.get("/latest")
async def get_latest_run(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any] | None:
    """
    Get the latest run (active if running, otherwise most recent completed).

    Returns:
        Latest run details or null if no runs exist
    """
    log_to_console("📡 API: GET /api/runs/latest - Get latest run")

    # First try to get active (running) run
    result = await db.execute(
        select(Run)
        .where(Run.status == RunStatus.RUNNING.value)
        .order_by(Run.started_at.desc())
        .limit(1)
    )
    run = result.scalar_one_or_none()

    # If no active run, get most recent completed run
    if not run:
        result = await db.execute(
            select(Run)
            .order_by(Run.started_at.desc())
            .limit(1)
        )
        run = result.scalar_one_or_none()

    if not run:
        log_to_console("⚠️  No runs found")
        return None

    # Get source runs for this run
    source_runs_result = await db.execute(
        select(SourceRun)
        .where(SourceRun.run_id == run.id)
        .order_by(SourceRun.started_at)
    )
    source_runs = list(source_runs_result.scalars().all())

    # Return only last 5 log entries for dashboard
    run_dict = run_to_dict(run, source_runs, include_logs=True)
    run_dict["logs"] = run.logs[-5:] if run.logs else []

    log_to_console(f"✅ Returned run #{run.id} (status: {run.status}, phase: {run.phase})")

    return run_dict


@router.get("")
async def list_runs(
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    phase: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    List all runs with pagination and filtering.

    Args:
        page: Page number (1-indexed)
        page_size: Number of runs per page
        status: Filter by status (optional)
        phase: Filter by phase (optional)
        db: Database session

    Returns:
        Dictionary with runs list and pagination info
    """
    # Build query
    query = select(Run)

    # Apply filters
    if status:
        query = query.where(Run.status == status)
    if phase:
        query = query.where(Run.phase == phase)

    # Order by most recent first
    query = query.order_by(Run.started_at.desc())

    # Get total count
    count_query = select(Run.id)
    if status:
        count_query = count_query.where(Run.status == status)
    if phase:
        count_query = count_query.where(Run.phase == phase)

    result = await db.execute(count_query)
    total = len(result.all())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    runs = result.scalars().all()

    # Get source runs for all fetched runs
    run_ids = [run.id for run in runs]
    source_runs_result = await db.execute(
        select(SourceRun)
        .where(SourceRun.run_id.in_(run_ids))
        .order_by(SourceRun.started_at)
    )
    all_source_runs = list(source_runs_result.scalars().all())

    # Group source runs by run_id
    source_runs_by_run: dict[int, list[SourceRun]] = {}
    for sr in all_source_runs:
        if sr.run_id not in source_runs_by_run:
            source_runs_by_run[sr.run_id] = []
        source_runs_by_run[sr.run_id].append(sr)

    # Convert to dict with source_runs
    runs_data = []
    for run in runs:
        run_source_runs = source_runs_by_run.get(run.id, [])
        # Don't include full logs in list view for performance
        run_dict = run_to_dict(run, run_source_runs, include_logs=False)
        runs_data.append(run_dict)

    return {
        "runs": runs_data,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{run_id}")
async def get_run(
    run_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Get details for a specific run.

    Args:
        run_id: Run ID
        db: Database session

    Returns:
        Run details with source_runs

    Raises:
        HTTPException: If run not found
    """
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Get source runs
    source_runs_result = await db.execute(
        select(SourceRun)
        .where(SourceRun.run_id == run_id)
        .order_by(SourceRun.started_at)
    )
    source_runs = list(source_runs_result.scalars().all())

    return run_to_dict(run, source_runs, include_logs=True)


@router.get("/{run_id}/source-runs")
async def get_run_source_runs(
    run_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Get all source runs for a specific run.

    Args:
        run_id: Run ID
        db: Database session

    Returns:
        List of source runs

    Raises:
        HTTPException: If run not found
    """
    # Verify run exists
    result = await db.execute(select(Run.id).where(Run.id == run_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Run not found")

    # Get source runs
    source_runs_result = await db.execute(
        select(SourceRun)
        .where(SourceRun.run_id == run_id)
        .order_by(SourceRun.started_at)
    )
    source_runs = list(source_runs_result.scalars().all())

    return {
        "source_runs": [source_run_to_dict(sr) for sr in source_runs],
        "total": len(source_runs),
    }


@router.get("/{run_id}/source-runs/{source_name}")
async def get_source_run(
    run_id: int,
    source_name: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Get a specific source run by run ID and source name.

    Args:
        run_id: Run ID
        source_name: Source name (e.g., "working_nomads")
        db: Database session

    Returns:
        Source run details

    Raises:
        HTTPException: If source run not found
    """
    result = await db.execute(
        select(SourceRun)
        .where(SourceRun.run_id == run_id)
        .where(SourceRun.source_name == source_name)
    )
    source_run = result.scalar_one_or_none()

    if not source_run:
        raise HTTPException(
            status_code=404,
            detail=f"Source run not found for run {run_id} and source '{source_name}'"
        )

    return source_run_to_dict(source_run)
