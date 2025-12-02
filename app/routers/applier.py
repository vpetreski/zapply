"""Applier API endpoints for automated job applications."""

from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Job, JobStatus, UserProfile
from app.routers.auth import User, get_current_user
from app.services.applier_service import (
    apply_to_job,
    apply_to_matched_jobs,
    get_matched_jobs,
    get_user_profile,
)

router = APIRouter()


class ApplyResponse(BaseModel):
    """Response for single job application."""
    success: bool
    message: str
    job_id: int
    job_title: str
    company: str


class ApplyAllResponse(BaseModel):
    """Response for applying to all matched jobs."""
    message: str
    total_matched: int
    processing: bool


class ApplyAllResultsResponse(BaseModel):
    """Results from applying to all matched jobs."""
    total_matched: int
    attempted: int
    successful: int
    failed: int
    skipped: int
    results: list[dict[str, Any]]


class MatchedJobsResponse(BaseModel):
    """Response listing matched jobs."""
    count: int
    jobs: list[dict[str, Any]]


@router.get("/matched", response_model=MatchedJobsResponse)
async def list_matched_jobs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
) -> MatchedJobsResponse:
    """
    List all jobs with MATCHED status that are ready for application.
    """
    jobs = await get_matched_jobs(db)

    return MatchedJobsResponse(
        count=len(jobs),
        jobs=[
            {
                "id": job.id,
                "title": job.title,
                "company": job.company,
                "url": job.url,
                "match_score": job.match_score,
                "matched_at": job.matched_at.isoformat() if job.matched_at else None
            }
            for job in jobs
        ]
    )


@router.post("/apply/{job_id}", response_model=ApplyResponse)
async def apply_to_single_job(
    job_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    dry_run: bool = False
) -> ApplyResponse:
    """
    Apply to a single job by ID.

    Args:
        job_id: ID of the job to apply to
        dry_run: If True, fill form but don't submit
    """
    # Get job
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status == JobStatus.APPLIED.value:
        raise HTTPException(status_code=400, detail="Already applied to this job")

    # Get profile
    profile = await get_user_profile(db)
    if not profile:
        raise HTTPException(status_code=400, detail="No user profile found. Please create a profile first.")

    # Apply
    success, message, _ = await apply_to_job(db, job, profile, dry_run=dry_run)

    return ApplyResponse(
        success=success,
        message=message,
        job_id=job.id,
        job_title=job.title,
        company=job.company
    )


# Store for background task results
_apply_all_results: dict[str, Any] = {}


async def _run_apply_all(db_url: str, limit: int, dry_run: bool):
    """Background task to apply to all matched jobs."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        results = await apply_to_matched_jobs(db, limit=limit, dry_run=dry_run)
        _apply_all_results["latest"] = results

    await engine.dispose()


@router.post("/apply-all", response_model=ApplyAllResponse)
async def apply_to_all_matched(
    current_user: Annotated[User, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    limit: int = 0,
    dry_run: bool = False
) -> ApplyAllResponse:
    """
    Start applying to all matched jobs.

    This runs as a background task. Check /applier/results for progress.

    Args:
        limit: Maximum number of jobs to apply to (0 = all)
        dry_run: If True, fill forms but don't submit
    """
    # Check profile exists
    profile = await get_user_profile(db)
    if not profile:
        raise HTTPException(status_code=400, detail="No user profile found. Please create a profile first.")

    # Get count
    jobs = await get_matched_jobs(db)

    if not jobs:
        return ApplyAllResponse(
            message="No matched jobs to apply to",
            total_matched=0,
            processing=False
        )

    # For now, run synchronously (can add background task later)
    results = await apply_to_matched_jobs(db, limit=limit, dry_run=dry_run)
    _apply_all_results["latest"] = results

    return ApplyAllResponse(
        message=f"Completed applying to {results['attempted']} jobs. {results['successful']} successful, {results['failed']} failed.",
        total_matched=results["total_matched"],
        processing=False
    )


@router.get("/results", response_model=ApplyAllResultsResponse)
async def get_apply_results(
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApplyAllResultsResponse:
    """
    Get results from the latest apply-all operation.
    """
    results = _apply_all_results.get("latest", {
        "total_matched": 0,
        "attempted": 0,
        "successful": 0,
        "failed": 0,
        "skipped": 0,
        "results": []
    })

    return ApplyAllResultsResponse(**results)


@router.post("/reset/{job_id}")
async def reset_job_status(
    job_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Reset a job's status back to MATCHED for re-application.

    Useful for retrying failed applications.
    """
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    old_status = job.status
    job.status = JobStatus.MATCHED.value
    job.applied_at = None
    job.application_data = None
    job.application_error = None

    await db.commit()

    return {
        "success": True,
        "job_id": job_id,
        "old_status": old_status,
        "new_status": JobStatus.MATCHED.value
    }
