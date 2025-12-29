"""Scheduler service for automated pipeline runs."""

import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.database import get_db_session
from app.models import AppSettings, RunTriggerType
from app.services.scraper_service import scrape_and_save_jobs

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None


async def run_scheduled_pipeline(trigger_type: str, retry_count: int = 0) -> None:
    """
    Run the pipeline with the specified trigger type.

    Args:
        trigger_type: The trigger type (scheduled_daily or scheduled_hourly)
        retry_count: Current retry attempt (for connection failure recovery)
    """
    import asyncio

    MAX_RETRIES = 2
    logger.info(f"Starting scheduled pipeline run: {trigger_type}" + (f" (retry {retry_count})" if retry_count > 0 else ""))

    db_generator = None
    try:
        # Get database session using proper async generator pattern
        db_generator = get_db_session()
        db = await db_generator.__anext__()
        await scrape_and_save_jobs(db, trigger_type=trigger_type)
        logger.info(f"Scheduled pipeline run completed: {trigger_type}")
    except ValueError as e:
        # Expected errors (no profile, run already in progress)
        if "already in progress" in str(e):
            logger.warning(f"Scheduled pipeline skipped: {e}")
        else:
            logger.error(f"Scheduled pipeline validation failed: {e}")
    except Exception as e:
        error_str = str(e)
        # Check if this is a connection error that might be recoverable
        is_connection_error = any(msg in error_str for msg in [
            "connection is closed",
            "connection was closed",
            "ConnectionDoesNotExistError",
            "InterfaceError",
        ])

        if is_connection_error and retry_count < MAX_RETRIES:
            logger.warning(f"Database connection error, will retry in 5 seconds: {e}")
            # Close current generator if possible
            if db_generator:
                try:
                    await db_generator.aclose()
                except Exception:
                    pass
            # Wait a bit for connection pool to recover
            await asyncio.sleep(5)
            # Retry with fresh session
            await run_scheduled_pipeline(trigger_type, retry_count + 1)
            return
        else:
            logger.error(f"Scheduled pipeline run failed: {trigger_type}, error: {e}")
    finally:
        # Properly close the generator to trigger cleanup
        if db_generator:
            try:
                await db_generator.aclose()
            except (StopAsyncIteration, Exception):
                pass


async def daily_run() -> None:
    """Run the daily scheduled pipeline."""
    await run_scheduled_pipeline(RunTriggerType.SCHEDULED_DAILY.value)


async def hourly_run() -> None:
    """Run the hourly scheduled pipeline."""
    await run_scheduled_pipeline(RunTriggerType.SCHEDULED_HOURLY.value)


async def load_run_frequency() -> str:
    """Load run_frequency setting from database."""
    try:
        db_generator = get_db_session()
        db = await db_generator.__anext__()
        result = await db.execute(
            select(AppSettings).where(AppSettings.key == "run_frequency")
        )
        setting = result.scalar_one_or_none()
        frequency = setting.value if setting else "manual"
        await db_generator.aclose()
        return frequency
    except Exception as e:
        logger.error(f"Failed to load run_frequency from database: {e}, defaulting to manual")
        return "manual"


async def start_scheduler_async() -> None:
    """
    Start the scheduler and configure jobs based on settings (async version).
    """
    global scheduler

    if scheduler is not None:
        logger.warning("Scheduler already running")
        return

    scheduler = AsyncIOScheduler()

    # Load frequency from database
    try:
        frequency = await load_run_frequency()
    except Exception as e:
        logger.error(f"Failed to load settings: {e}, defaulting to manual")
        frequency = "manual"

    configure_scheduler_jobs(frequency)

    scheduler.start()
    logger.info(f"Scheduler started with frequency: {frequency}")


def start_scheduler() -> None:
    """
    Start the scheduler (sync wrapper for backwards compatibility).
    Note: Prefer start_scheduler_async() when called from async context.
    """
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        # We're in an async context, schedule the async version
        asyncio.create_task(start_scheduler_async())
    except RuntimeError:
        # No event loop running, safe to use asyncio.run
        asyncio.run(start_scheduler_async())


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
        # Run at 6am Colombian time using proper timezone
        # Colombia uses America/Bogota timezone (UTC-5, no DST)
        from zoneinfo import ZoneInfo

        trigger = CronTrigger(hour=6, minute=0, timezone=ZoneInfo("America/Bogota"))
        scheduler.add_job(
            daily_run,
            trigger=trigger,
            id="daily_run",
            name="Daily Pipeline Run (6am Colombian time)",
            replace_existing=True,
            coalesce=True,  # Combine missed runs into one
            max_instances=1,  # Prevent concurrent runs
        )
        logger.info("Scheduler configured for daily runs at 6am America/Bogota time")

    elif frequency == "hourly":
        # Run at the start of every hour
        trigger = CronTrigger(minute=0, timezone="UTC")
        scheduler.add_job(
            hourly_run,
            trigger=trigger,
            id="hourly_run",
            name="Hourly Pipeline Run",
            replace_existing=True,
            coalesce=True,  # Combine missed runs into one
            max_instances=1,  # Prevent concurrent runs
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
        # After starting, configure with the passed frequency parameter
        # (start_scheduler loads from file, but we want to use the passed value)
        configure_scheduler_jobs(frequency)
        logger.info(f"Scheduler started and configured with frequency: {frequency}")
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
