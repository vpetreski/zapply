"""Scraper endpoints for manual triggering."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker, get_db
from app.models import Run, RunStatus
from app.services.scraper_service import scrape_and_save_jobs

router = APIRouter()


class StartRunResponse(BaseModel):
    """Response from starting a scraping run."""

    message: str
    run_id: int


async def run_scraper_background():
    """Run the scraper in the background."""
    async with async_session_maker() as db:
        try:
            await scrape_and_save_jobs(db)
        except Exception as e:
            print(f"Background scraper error: {e}")


@router.post("/run", response_model=StartRunResponse)
async def run_scraper(db: AsyncSession = Depends(get_db)) -> StartRunResponse:
    """
    Manually trigger job scraping from Working Nomads.

    This will:
    1. Check if there's already a running run
    2. Start the scraping process in the background
    3. Return immediately with the run ID

    The scraping process will:
    - Login to Working Nomads
    - Apply filters (Development + Anywhere,Colombia)
    - Load all jobs
    - Scrape each job's details
    - Save new jobs to database (skip existing ones)

    Returns the run ID for tracking.
    """
    # Check for existing running runs
    result = await db.execute(
        select(Run).where(Run.status == RunStatus.RUNNING.value).limit(1)
    )
    running_run = result.scalar_one_or_none()

    if running_run:
        raise HTTPException(
            status_code=409,
            detail=f"A run is already in progress (Run #{running_run.id}). Please wait for it to complete."
        )

    # Start the scraper in the background
    asyncio.create_task(run_scraper_background())

    # Wait a moment for the run to be created
    await asyncio.sleep(0.5)

    # Get the newly created run
    result = await db.execute(
        select(Run).order_by(Run.id.desc()).limit(1)
    )
    new_run = result.scalar_one_or_none()

    if not new_run:
        raise HTTPException(status_code=500, detail="Failed to create run")

    return StartRunResponse(
        message=f"Scraping run #{new_run.id} started successfully!",
        run_id=new_run.id,
    )
