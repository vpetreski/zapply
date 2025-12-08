"""Job management endpoints."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Job, JobStatus, MatchingSource
from app.routers.auth import User, get_current_user
from app.schemas import JobListResponse, JobResponse, JobStatusUpdate
from app.utils import log_to_console

router = APIRouter()


@router.get("", response_model=JobListResponse)
@router.get("/", response_model=JobListResponse)
async def list_jobs(
    current_user: Annotated[User, Depends(get_current_user)],
    status: Optional[str] = Query(None, description="Filter by job status (matched, rejected)"),
    applied: Optional[bool] = Query(None, description="Filter by application status (true=applied, false=not applied)"),
    source: Optional[str] = Query(None, description="Filter by job source"),
    company: Optional[str] = Query(None, description="Filter by company name"),
    matching_source: Optional[str] = Query(None, description="Filter by matching source (auto, manual)"),
    days: Optional[int] = Query(None, description="Filter by days since scraped (7, 15, 30)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    """List jobs with optional filtering and pagination. Always sorted by date desc, then score desc."""
    log_to_console(f"📡 API: GET /api/jobs - List jobs (page={page}, size={page_size}, status={status}, applied={applied}, matching_source={matching_source}, days={days})")

    # Build query
    query = select(Job)

    # Filter by job status (matched, rejected)
    if status:
        query = query.filter(Job.status == status)

    # Filter by application status
    if applied is not None:
        if applied:
            query = query.filter(Job.applied_at.isnot(None))
        else:
            query = query.filter(Job.applied_at.is_(None))
    if source:
        query = query.filter(Job.source == source)
    if company:
        query = query.filter(Job.company.ilike(f"%{company}%"))
    if matching_source:
        query = query.filter(Job.matching_source == matching_source)
    if days is not None:
        if days == 0:
            # "Today" - since midnight UTC
            cutoff_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        else:
            cutoff_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
        query = query.filter(Job.created_at >= cutoff_date)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Always sort by date (day only) desc, then by score desc
    # Using func.date() to group jobs from same day together, then sort by score within each day
    query = query.order_by(
        func.date(Job.created_at).desc(),
        Job.match_score.desc().nullslast()
    )

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)

    # Execute query
    result = await db.execute(query)
    jobs = result.scalars().all()

    log_to_console(f"✅ Returned {len(jobs)} jobs (total: {total})")

    return JobListResponse(
        jobs=[JobResponse.model_validate(job) for job in jobs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Get a specific job by ID."""
    log_to_console(f"📡 API: GET /api/jobs/{job_id} - Get job details")

    result = await db.execute(select(Job).filter(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        log_to_console(f"❌ Job {job_id} not found")
        raise HTTPException(status_code=404, detail="Job not found")

    log_to_console(f"✅ Returned job: {job.title} @ {job.company}")
    return JobResponse.model_validate(job)


@router.patch("/{job_id}/status", response_model=JobResponse)
async def update_job_status(
    job_id: int,
    update: JobStatusUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Update job status and related information."""
    log_to_console(f"📡 API: PATCH /api/jobs/{job_id}/status - Update job status to {update.status}")

    result = await db.execute(select(Job).filter(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        log_to_console(f"❌ Job {job_id} not found")
        raise HTTPException(status_code=404, detail="Job not found")

    # Update status
    job.status = update.status

    # Update optional fields
    if update.matching_source is not None:
        job.matching_source = update.matching_source
    if update.match_reasoning is not None:
        job.match_reasoning = update.match_reasoning
    if update.match_score is not None:
        job.match_score = update.match_score
    if update.application_data is not None:
        job.application_data = update.application_data
        # Set applied_at timestamp when marking as applied
        if not job.applied_at:
            job.applied_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if update.application_error is not None:
        job.application_error = update.application_error

    await db.commit()
    await db.refresh(job)

    log_to_console(f"✅ Job {job_id} status updated to {update.status}")
    return JobResponse.model_validate(job)


@router.delete("/{job_id}")
async def delete_job(
    job_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Delete a job (for testing/cleanup purposes)."""
    log_to_console(f"📡 API: DELETE /api/jobs/{job_id} - Delete job")

    result = await db.execute(select(Job).filter(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        log_to_console(f"❌ Job {job_id} not found")
        raise HTTPException(status_code=404, detail="Job not found")

    await db.delete(job)
    await db.commit()

    log_to_console(f"✅ Job {job_id} deleted successfully")
    return {"message": f"Job {job_id} deleted successfully"}
