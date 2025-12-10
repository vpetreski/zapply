"""Scraper service to handle job scraping, matching, and saving to database."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import AppSettings, Job, Run, RunPhase, RunStatus, RunTriggerType, UserProfile
from app.schemas import JobCreate
from app.scraper import WorkingNomadsScraper
from app.services.matching_service import match_jobs
from app.utils import log_to_console

# PostgreSQL advisory lock ID for scraper runs (arbitrary but consistent number)
SCRAPER_LOCK_ID = 12345678

# Maximum time a run can be "running" before it's considered stale (in minutes)
STALE_RUN_TIMEOUT_MINUTES = 30


async def get_setting(db: AsyncSession, key: str, default: str = "") -> str:
    """Get a setting value from database."""
    result = await db.execute(
        select(AppSettings).where(AppSettings.key == key)
    )
    setting = result.scalar_one_or_none()
    return setting.value if setting else default


def add_log(run: Run, message: str, level: str = "info") -> None:
    """Add a log entry to the run."""
    if run.logs is None:
        run.logs = []

    run.logs.append({
        "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        "level": level,
        "message": message
    })

    # Mark the logs field as modified so SQLAlchemy detects the change
    from sqlalchemy.orm import attributes
    attributes.flag_modified(run, "logs")


async def cleanup_stale_runs(db: AsyncSession) -> int:
    """
    Mark runs that have been 'running' for too long as failed.

    Returns:
        Number of stale runs cleaned up
    """
    cutoff_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=STALE_RUN_TIMEOUT_MINUTES)

    # Find and update stale runs
    result = await db.execute(
        update(Run)
        .where(Run.status == RunStatus.RUNNING.value)
        .where(Run.started_at < cutoff_time)
        .values(
            status=RunStatus.FAILED.value,
            completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
            error_message=f"Run exceeded {STALE_RUN_TIMEOUT_MINUTES} minute timeout - marked as failed automatically"
        )
        .returning(Run.id)
    )
    stale_ids = result.scalars().all()

    if stale_ids:
        await db.commit()
        log_to_console(f"🧹 Cleaned up {len(stale_ids)} stale runs: {stale_ids}")

    return len(stale_ids)


async def acquire_scraper_lock(db: AsyncSession) -> bool:
    """
    Try to acquire a session-level advisory lock for running the scraper.

    Uses PostgreSQL's pg_try_advisory_lock which:
    - Returns true if lock acquired, false if already held by another session
    - Must be explicitly released with release_scraper_lock()
    - Is non-blocking (doesn't wait)

    Returns:
        True if lock acquired, False if another scraper is running
    """
    result = await db.execute(
        text(f"SELECT pg_try_advisory_lock({SCRAPER_LOCK_ID})")
    )
    return result.scalar()


async def release_scraper_lock(db: AsyncSession) -> None:
    """Release the session-level advisory lock."""
    await db.execute(text(f"SELECT pg_advisory_unlock({SCRAPER_LOCK_ID})"))
    log_to_console("🔓 Released scraper lock")


async def scrape_and_save_jobs(
    db: AsyncSession, trigger_type: str = RunTriggerType.MANUAL.value
) -> dict[str, int]:
    """
    Scrape jobs from Working Nomads and save to database.

    Args:
        db: Database session
        trigger_type: How the run was triggered (manual/scheduled_daily/scheduled_hourly)

    Returns:
        Dictionary with statistics: {total, new, existing, failed}

    Raises:
        ValueError: If no user profile exists or if a run is already in progress
    """
    # STEP 1: Clean up any stale runs first
    await cleanup_stale_runs(db)

    # STEP 2: Acquire advisory lock (atomic, prevents race conditions)
    lock_acquired = await acquire_scraper_lock(db)
    if not lock_acquired:
        raise ValueError(
            "Another scraper process is currently running (could not acquire lock). "
            "Please wait for it to complete before starting a new run."
        )

    log_to_console("🔒 Acquired scraper lock")

    # Wrap everything in try/finally to ensure lock is ALWAYS released
    run = None  # Initialize run outside try so we can access it in except
    stats = {"total": 0, "new": 0, "existing": 0, "failed": 0}  # Initialize stats too
    try:
        # STEP 3: Double-check for running runs (belt AND suspenders)
        running_result = await db.execute(
            select(Run).where(Run.status == RunStatus.RUNNING.value)
        )
        running_run = running_result.scalar_one_or_none()
        if running_run:
            raise ValueError(
                f"A run is already in progress (Run #{running_run.id}, started at {running_run.started_at}). "
                "Please wait for it to complete before starting a new run."
            )

        # Check if user profile exists - REQUIRED for matching
        result = await db.execute(select(UserProfile).limit(1))
        profile = result.scalar_one_or_none()

        if not profile:
            raise ValueError(
                "No user profile found. Please create a profile before running the scraper. "
                "The profile is required for job matching."
            )

        # Create run record
        run = Run(
            status=RunStatus.RUNNING.value,
            phase=RunPhase.SCRAPING.value,
            trigger_type=trigger_type,
            logs=[],
            started_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)

        log_to_console(f"📋 Created run #{run.id}")

        add_log(run, "Starting job scraping from Working Nomads", "info")
        await db.commit()

        # Initialize scraper
        scraper = WorkingNomadsScraper()
        add_log(run, "Initialized Working Nomads scraper", "info")
        await db.commit()

        # Fetch existing job slugs from database for deduplication
        log_to_console("📥 Fetching existing job slugs from database...")
        add_log(run, "Fetching existing job slugs from database...", "info")
        await db.commit()

        existing_slugs_result = await db.execute(
            select(Job.source_id).filter(Job.source == "working_nomads")
        )
        existing_slugs = set(row[0] for row in existing_slugs_result.fetchall())

        log_to_console(f"✅ Found {len(existing_slugs)} existing job slugs in database")
        add_log(run, f"Found {len(existing_slugs)} existing job slugs in database", "info")
        await db.commit()

        # Scrape jobs
        log_to_console("🎯 Starting job scraping...")
        add_log(run, "Beginning job scraping process", "info")
        await db.commit()

        # Get scrape job limit from database
        job_limit_str = await get_setting(db, "scrape_job_limit", "0")
        job_limit = int(job_limit_str)

        # Pass callback to scraper for progress updates
        async def progress_callback(message: str, level: str = "info"):
            add_log(run, message, level)
            await db.commit()

        jobs_data = await scraper.scrape(
            progress_callback=progress_callback,
            job_limit=job_limit,
            existing_slugs=existing_slugs
        )
        stats["total"] = len(jobs_data)

        add_log(run, f"Scraped {len(jobs_data)} jobs from Working Nomads", "success")
        await db.commit()

        # Save to database
        log_to_console(f"\n💾 Saving {len(jobs_data)} jobs to database...")
        add_log(run, f"Saving {len(jobs_data)} jobs to database", "info")
        await db.commit()

        for i, job_data in enumerate(jobs_data, 1):
            try:
                # Check if job already exists (use in-memory set for O(1) lookup)
                source_id = job_data.get("source_id")

                if source_id in existing_slugs:
                    if i % 10 == 0 or i == 1:
                        log_to_console(f"  [{i}/{len(jobs_data)}] ⏭️  Already exists: {job_data['title']}")
                    stats["existing"] += 1
                    continue

                # Create new job
                job = Job(
                    source=job_data["source"],
                    source_id=job_data["source_id"],
                    url=job_data["url"],
                    title=job_data["title"],
                    company=job_data["company"],
                    description=job_data["description"],
                    requirements=job_data.get("requirements"),
                    location=job_data.get("location"),
                    salary=job_data.get("salary"),
                    tags=job_data.get("tags"),
                    raw_data=job_data.get("raw_data"),
                )

                db.add(job)
                stats["new"] += 1
                log_to_console(f"  [{i}/{len(jobs_data)}] ✅ NEW: {job.title} @ {job.company}")

            except Exception as e:
                stats["failed"] += 1
                log_to_console(f"  [{i}/{len(jobs_data)}] ❌ FAILED to save: {str(e)}")
                if settings.debug:
                    import traceback
                    log_to_console(f"     Traceback:\n{traceback.format_exc()}")

        # Commit all changes
        await db.commit()

        log_to_console(f"\n✅ Scraping phase completed!")
        log_to_console(f"   Total scraped: {stats['total']}")
        log_to_console(f"   ✅ New jobs: {stats['new']}")
        log_to_console(f"   ⏭️  Duplicates: {stats['existing']}")
        log_to_console(f"   ❌ Failed: {stats['failed']}")

        add_log(run, f"Scraping phase completed successfully!", "success")
        add_log(run, f"Total: {stats['total']}, New: {stats['new']}, Duplicates: {stats['existing']}, Failed: {stats['failed']}", "info")
        await db.commit()

        log_to_console(f"\n📊 Scraping Summary:")
        log_to_console(f"  Total scraped: {stats['total']}")
        log_to_console(f"  New jobs saved: {stats['new']}")
        log_to_console(f"  Already existed: {stats['existing']}")
        log_to_console(f"  Failed: {stats['failed']}")

        # Phase 2: Match jobs with AI
        if stats["new"] > 0:
            log_to_console(f"\n🤖 Starting AI matching phase...")
            run.phase = RunPhase.MATCHING.value
            await db.commit()

            matching_stats = await match_jobs(db, run)

            # Update run stats with matching results
            run.stats = {
                "jobs_scraped": stats["total"],
                "new_jobs": stats["new"],
                "duplicate_jobs": stats["existing"],
                "failed_jobs": stats["failed"],
                "jobs_matched": matching_stats["matched"],
                "jobs_rejected": matching_stats["rejected"],
                "matching_errors": matching_stats["errors"],
                "average_match_score": matching_stats["average_score"],
                "source": "working_nomads",
                "filters": {
                    "category": "development",
                    "location": "anywhere,colombia"
                }
            }
            await db.commit()
        else:
            log_to_console(f"\n⏭️  No new jobs to match, skipping matching phase")
            run.stats = {
                "jobs_scraped": stats["total"],
                "new_jobs": stats["new"],
                "duplicate_jobs": stats["existing"],
                "failed_jobs": stats["failed"],
                "source": "working_nomads",
                "filters": {
                    "category": "development",
                    "location": "anywhere,colombia"
                }
            }
            await db.commit()

        # Complete the run
        run.status = RunStatus.COMPLETED.value
        run.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        run.duration_seconds = (run.completed_at - run.started_at).total_seconds()
        add_log(run, f"Run completed successfully!", "success")
        await db.commit()

    except Exception as e:
        # Handle errors - only update run if it was created
        if run is not None:
            run.status = RunStatus.FAILED.value
            run.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            run.duration_seconds = (run.completed_at - run.started_at).total_seconds()
            run.error_message = str(e)
            add_log(run, f"Scraping failed: {str(e)}", "error")
            await db.commit()
        log_to_console(f"\n❌ Error: {str(e)}")
        raise

    finally:
        # ALWAYS release the lock, even on error
        try:
            await release_scraper_lock(db)
        except Exception as unlock_error:
            log_to_console(f"⚠️ Warning: Failed to release scraper lock: {unlock_error}")

    return stats
