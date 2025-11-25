"""Runs API endpoints."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Run, RunPhase, RunStatus

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("/latest")
async def get_latest_run(db: AsyncSession = Depends(get_db)) -> dict[str, Any] | None:
    """
    Get the latest run (active if running, otherwise most recent completed).

    Returns:
        Latest run details or null if no runs exist
    """
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
        return None

    # Return only last 5 log entries for dashboard
    logs = run.logs[-5:] if run.logs else []

    return {
        "id": run.id,
        "status": run.status,
        "phase": run.phase,
        "trigger_type": run.trigger_type,
        "stats": run.stats,
        "logs": logs,  # Only last 5 entries
        "error_message": run.error_message,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "duration_seconds": run.duration_seconds,
    }


@router.get("")
async def list_runs(
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

    # Convert to dict
    runs_data = []
    for run in runs:
        run_dict = {
            "id": run.id,
            "status": run.status,
            "phase": run.phase,
            "trigger_type": run.trigger_type,
            "stats": run.stats,
            "logs": run.logs,
            "error_message": run.error_message,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "duration_seconds": run.duration_seconds,
        }
        runs_data.append(run_dict)

    return {
        "runs": runs_data,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{run_id}")
async def get_run(run_id: int, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Get details for a specific run.

    Args:
        run_id: Run ID
        db: Database session

    Returns:
        Run details

    Raises:
        HTTPException: If run not found
    """
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return {
        "id": run.id,
        "status": run.status,
        "phase": run.phase,
        "trigger_type": run.trigger_type,
        "stats": run.stats,
        "logs": run.logs,
        "error_message": run.error_message,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "duration_seconds": run.duration_seconds,
    }
