"""Scheduler service for automated pipeline runs."""

import logging
from pathlib import Path
import json
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models import RunTriggerType
from app.services.scraper_service import scrape_and_save_jobs

logger = logging.getLogger(__name__)

# Settings file path
SETTINGS_FILE = Path("data/admin_settings.json")

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None


def _load_settings() -> dict:
    """Load settings from JSON file."""
    if not SETTINGS_FILE.exists():
        return {"run_frequency": "manual"}

    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"run_frequency": "manual"}


async def run_scheduled_pipeline(trigger_type: str) -> None:
    """
    Run the pipeline with the specified trigger type.

    Args:
        trigger_type: The trigger type (scheduled_daily or scheduled_hourly)
    """
    logger.info(f"Starting scheduled pipeline run: {trigger_type}")

    # Get database session
    async for db in get_db_session():
        try:
            await scrape_and_save_jobs(db, trigger_type=trigger_type)
            logger.info(f"Scheduled pipeline run completed: {trigger_type}")
        except Exception as e:
            logger.error(f"Scheduled pipeline run failed: {trigger_type}, error: {e}")
        finally:
            break  # Only use the first yielded session


async def daily_run() -> None:
    """Run the daily scheduled pipeline."""
    await run_scheduled_pipeline(RunTriggerType.SCHEDULED_DAILY.value)


async def hourly_run() -> None:
    """Run the hourly scheduled pipeline."""
    await run_scheduled_pipeline(RunTriggerType.SCHEDULED_HOURLY.value)


def start_scheduler() -> None:
    """
    Start the scheduler and configure jobs based on settings.
    """
    global scheduler

    if scheduler is not None:
        logger.warning("Scheduler already running")
        return

    scheduler = AsyncIOScheduler()

    # Load settings and configure jobs
    settings = _load_settings()
    frequency = settings.get("run_frequency", "manual")

    configure_scheduler_jobs(frequency)

    scheduler.start()
    logger.info(f"Scheduler started with frequency: {frequency}")


def stop_scheduler() -> None:
    """Stop the scheduler."""
    global scheduler

    if scheduler is None:
        logger.warning("Scheduler not running")
        return

    scheduler.shutdown(wait=False)
    scheduler = None
    logger.info("Scheduler stopped")


def configure_scheduler_jobs(frequency: str) -> None:
    """
    Configure scheduler jobs based on frequency setting.

    Args:
        frequency: Run frequency (manual, daily, or hourly)
    """
    global scheduler

    if scheduler is None:
        logger.error("Scheduler not initialized")
        return

    # Remove all existing jobs
    scheduler.remove_all_jobs()

    if frequency == "manual":
        logger.info("Scheduler configured for manual runs only (no automatic jobs)")
        return

    if frequency == "daily":
        # Run at 9pm Colombian time (UTC-5, which is 2am UTC)
        # Note: Colombia doesn't observe DST, so it's always UTC-5
        trigger = CronTrigger(hour=2, minute=0, timezone="UTC")
        scheduler.add_job(
            daily_run,
            trigger=trigger,
            id="daily_run",
            name="Daily Pipeline Run (9pm Colombian time)",
            replace_existing=True,
        )
        logger.info("Scheduler configured for daily runs at 9pm Colombian time (2am UTC)")

    elif frequency == "hourly":
        # Run at the start of every hour
        trigger = CronTrigger(minute=0, timezone="UTC")
        scheduler.add_job(
            hourly_run,
            trigger=trigger,
            id="hourly_run",
            name="Hourly Pipeline Run",
            replace_existing=True,
        )
        logger.info("Scheduler configured for hourly runs at the start of each hour")

    else:
        logger.warning(f"Unknown frequency: {frequency}, defaulting to manual")


def reconfigure_scheduler(frequency: str) -> None:
    """
    Reconfigure the scheduler with a new frequency.

    Args:
        frequency: Run frequency (manual, daily, or hourly)
    """
    global scheduler

    if scheduler is None:
        logger.warning("Scheduler not running, starting it now")
        start_scheduler()
        return

    configure_scheduler_jobs(frequency)
    logger.info(f"Scheduler reconfigured with frequency: {frequency}")


def get_scheduler_status() -> dict:
    """
    Get the current scheduler status.

    Returns:
        Dictionary with scheduler status and configured jobs
    """
    global scheduler

    if scheduler is None:
        return {
            "running": False,
            "jobs": [],
        }

    jobs = []
    for job in scheduler.get_jobs():
        next_run = job.next_run_time.isoformat() if job.next_run_time else None
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": next_run,
        })

    return {
        "running": True,
        "jobs": jobs,
    }
