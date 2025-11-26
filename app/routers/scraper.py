"""Scraper endpoints for manual triggering."""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker, get_db
from app.models import Run, RunStatus, UserProfile
from app.routers.auth import User, get_current_user
from app.services.scraper_service import scrape_and_save_jobs
from app.utils import log_to_console

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


class StartRunResponse(BaseModel):
    """Response from starting a scraping run."""

    message: str
    run_id: int


async def run_scraper_background():
    """Run the scraper in the background."""
    async with async_session_maker() as db:
        try:
            log_to_console("🚀 Starting background scraper task...")
            await scrape_and_save_jobs(db)
            log_to_console("✅ Background scraper task completed successfully")
        except Exception as e:
            log_to_console(f"❌ Background scraper error: {e}")
            import traceback
            traceback.print_exc()


@router.post("/run", response_model=StartRunResponse)
@limiter.limit("5/minute")
async def run_scraper(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
) -> StartRunResponse:
    """
    Manually trigger job scraping from Working Nomads.

    This will:
    1. Check if user profile exists (REQUIRED)
    2. Check if there's already a running run
    3. Start the scraping process in the background
    4. Return immediately with the run ID

    The scraping process will:
    - Login to Working Nomads
    - Apply filters (Development + Anywhere,Colombia)
    - Load all jobs
    - Scrape each job's details
    - Save new jobs to database (skip existing ones)
    - Match jobs against user profile

    Returns the run ID for tracking.
    """
    log_to_console("\n" + "="*60)
    log_to_console("📡 API: POST /api/scraper/run - Manual scraper trigger")
    log_to_console("="*60)

    # Check if user profile exists - REQUIRED
    log_to_console("🔍 Checking if user profile exists...")
    result = await db.execute(select(UserProfile).limit(1))
    profile = result.scalar_one_or_none()

    if not profile:
        log_to_console("❌ No user profile found - rejecting run request")
        raise HTTPException(
            status_code=400,
            detail="No user profile found. Please create a profile before running the scraper."
        )
    log_to_console(f"✅ User profile found: {profile.name}")

    # Check for existing running runs
    log_to_console("🔍 Checking for existing running runs...")
    result = await db.execute(
        select(Run).where(Run.status == RunStatus.RUNNING.value).limit(1)
    )
    running_run = result.scalar_one_or_none()

    if running_run:
        log_to_console(f"⚠️  Run already in progress (Run #{running_run.id}) - rejecting request")
        raise HTTPException(
            status_code=409,
            detail=f"A run is already in progress (Run #{running_run.id}). Please wait for it to complete."
        )
    log_to_console("✅ No active runs - proceeding")

    # Start the scraper in the background
    log_to_console("🚀 Starting background scraper task...")
    asyncio.create_task(run_scraper_background())

    # Wait a moment for the run to be created
    await asyncio.sleep(0.5)

    # Get the newly created run
    result = await db.execute(
        select(Run).order_by(Run.id.desc()).limit(1)
    )
    new_run = result.scalar_one_or_none()

    if not new_run:
        log_to_console("❌ Failed to create run record")
        raise HTTPException(status_code=500, detail="Failed to create run")

    log_to_console(f"✅ Run #{new_run.id} created successfully")
    log_to_console("="*60 + "\n")

    return StartRunResponse(
        message=f"Scraping run #{new_run.id} started successfully!",
        run_id=new_run.id,
    )
