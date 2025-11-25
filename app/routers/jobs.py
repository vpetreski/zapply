"""Job management endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Job, JobStatus
from app.schemas import JobListResponse, JobResponse, JobStatusUpdate
from app.utils import log_to_console

router = APIRouter()


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by job status"),
    source: Optional[str] = Query(None, description="Filter by job source"),
    company: Optional[str] = Query(None, description="Filter by company name"),
    min_score: Optional[float] = Query(None, ge=0, le=100, description="Minimum match score"),
    sort_by: str = Query("created_at", description="Sort field (created_at, match_score)"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    """List jobs with optional filtering, sorting, and pagination."""
    log_to_console(f"📡 API: GET /api/jobs - List jobs (page={page}, size={page_size}, status={status}, source={source})")

    # Build query
    query = select(Job)

    if status:
        query = query.filter(Job.status == status)
    if source:
        query = query.filter(Job.source == source)
    if company:
        query = query.filter(Job.company.ilike(f"%{company}%"))
    if min_score is not None:
        query = query.filter(Job.match_score >= min_score)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Apply sorting
    if sort_by == "match_score":
        # Sort by match score (nulls last)
        if sort_order == "desc":
            query = query.order_by(Job.match_score.desc().nullslast())
        else:
            query = query.order_by(Job.match_score.asc().nullslast())
    else:
        # Default: sort by created_at
        if sort_order == "desc":
            query = query.order_by(Job.created_at.desc())
        else:
            query = query.order_by(Job.created_at.asc())

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
    if update.match_reasoning is not None:
        job.match_reasoning = update.match_reasoning
    if update.match_score is not None:
        job.match_score = update.match_score
    if update.application_data is not None:
        job.application_data = update.application_data
    if update.application_error is not None:
        job.application_error = update.application_error

    await db.commit()
    await db.refresh(job)

    log_to_console(f"✅ Job {job_id} status updated to {update.status}")
    return JobResponse.model_validate(job)


@router.delete("/{job_id}")
async def delete_job(
    job_id: int,
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
