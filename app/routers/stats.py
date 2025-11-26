"""Statistics endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Job, JobStatus
from app.routers.auth import User, get_current_user
from app.schemas import StatsResponse

router = APIRouter()


@router.get("/", response_model=StatsResponse)
async def get_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
) -> StatsResponse:
    """Get application statistics."""
    # Count jobs by status
    total_result = await db.execute(select(func.count(Job.id)))
    total = total_result.scalar_one()

    new_result = await db.execute(
        select(func.count(Job.id)).filter(Job.status == JobStatus.NEW.value)
    )
    new = new_result.scalar_one()

    matched_result = await db.execute(
        select(func.count(Job.id)).filter(Job.status == JobStatus.MATCHED.value)
    )
    matched = matched_result.scalar_one()

    rejected_result = await db.execute(
        select(func.count(Job.id)).filter(Job.status == JobStatus.REJECTED.value)
    )
    rejected = rejected_result.scalar_one()

    applied_result = await db.execute(
        select(func.count(Job.id)).filter(Job.status == JobStatus.APPLIED.value)
    )
    applied = applied_result.scalar_one()

    failed_result = await db.execute(
        select(func.count(Job.id)).filter(Job.status == JobStatus.FAILED.value)
    )
    failed = failed_result.scalar_one()

    # Calculate success rate
    total_attempts = applied + failed
    success_rate = (applied / total_attempts * 100) if total_attempts > 0 else 0.0

    return StatsResponse(
        total_jobs=total,
        new_jobs=new,
        matched_jobs=matched,
        rejected_jobs=rejected,
        applied_jobs=applied,
        failed_jobs=failed,
        success_rate=round(success_rate, 2),
    )
