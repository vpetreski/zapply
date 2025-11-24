"""Job management endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Job, JobStatus
from app.schemas import JobListResponse, JobResponse, JobStatusUpdate

router = APIRouter()


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by job status"),
    source: Optional[str] = Query(None, description="Filter by job source"),
    company: Optional[str] = Query(None, description="Filter by company name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    """List jobs with optional filtering and pagination."""
    # Build query
    query = select(Job)

    if status:
        query = query.filter(Job.status == status)
    if source:
        query = query.filter(Job.source == source)
    if company:
        query = query.filter(Job.company.ilike(f"%{company}%"))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Apply pagination
    query = query.order_by(Job.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    # Execute query
    result = await db.execute(query)
    jobs = result.scalars().all()

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
    result = await db.execute(select(Job).filter(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse.model_validate(job)


@router.patch("/{job_id}/status", response_model=JobResponse)
async def update_job_status(
    job_id: int,
    update: JobStatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Update job status and related information."""
    result = await db.execute(select(Job).filter(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
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

    return JobResponse.model_validate(job)


@router.delete("/{job_id}")
async def delete_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Delete a job (for testing/cleanup purposes)."""
    result = await db.execute(select(Job).filter(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    await db.delete(job)
    await db.commit()

    return {"message": f"Job {job_id} deleted successfully"}
