"""Scraper endpoints for manual triggering."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.scraper_service import scrape_and_save_jobs

router = APIRouter()


class ScrapeResponse(BaseModel):
    """Response from scraping operation."""

    message: str
    total: int
    new: int
    existing: int
    failed: int


@router.post("/run", response_model=ScrapeResponse)
async def run_scraper(db: AsyncSession = Depends(get_db)) -> ScrapeResponse:
    """
    Manually trigger job scraping from Working Nomads.

    This will:
    1. Login to Working Nomads
    2. Apply filters (Development + Anywhere,Colombia)
    3. Load all jobs
    4. Scrape each job's details
    5. Save new jobs to database (skip existing ones)

    Returns statistics about the scraping operation.
    """
    stats = await scrape_and_save_jobs(db)

    return ScrapeResponse(
        message=f"Scraping completed! {stats['new']} new jobs saved.",
        total=stats["total"],
        new=stats["new"],
        existing=stats["existing"],
        failed=stats["failed"],
    )
