"""Scraper endpoints for manual triggering."""

import asyncio
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker, get_db
from app.models import Run, RunPhase, RunStatus, RunTriggerType, UserProfile
from app.routers.auth import User, get_current_user
from app.services.scraper_service import scrape_and_save_jobs_with_run
from app.utils import log_to_console

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


class StartRunResponse(BaseModel):
    """Response from starting a scraping run."""

    message: str
    run_id: int


async def run_scraper_background(run_id: int):
    """Run the scraper in the background with a pre-created run."""
    async with async_session_maker() as db:
        try:
            log_to_console(f"🚀 Starting background scraper task for run #{run_id}...")
            await scrape_and_save_jobs_with_run(db, run_id)
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
    Manually trigger job scraping from all enabled sources.

    This will:
    1. Check if user profile exists (REQUIRED)
    2. Check if there's already a running run
    3. Create the run record immediately
    4. Start the scraping process in the background
    5. Return immediately with the run ID

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
    log_to_console("✅ User profile found")

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

    # Create run record FIRST (before background task)
    new_run = Run(
        status=RunStatus.RUNNING.value,
        phase=RunPhase.SCRAPING.value,
        trigger_type=RunTriggerType.MANUAL.value,
        logs=[{
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "level": "info",
            "message": "Run created, starting scraper..."
        }],
        started_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(new_run)
    await db.commit()
    await db.refresh(new_run)

    log_to_console(f"✅ Run #{new_run.id} created successfully")

    # Start the scraper in the background with the run ID
    log_to_console("🚀 Starting background scraper task...")
    asyncio.create_task(run_scraper_background(new_run.id))

    log_to_console("="*60 + "\n")

    return StartRunResponse(
        message=f"Scraping run #{new_run.id} started successfully!",
        run_id=new_run.id,
    )
