"""Health check endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.database import get_db
from app.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Check application health status."""
    # Check database connection
    db_status = "healthy"
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar_one()
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # TODO: Check scheduler status
    scheduler_status = "not_implemented"

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        version=__version__,
        database=db_status,
        scheduler=scheduler_status,
    )
