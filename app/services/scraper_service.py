"""Scraper service to handle job scraping, matching, and saving to database."""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import attributes

from app.config import settings
from app.models import (
    AppSettings,
    Job,
    Run,
    RunPhase,
    RunStatus,
    RunTriggerType,
    ScraperSource,
    SourceRun,
    SourceRunStatus,
    UserProfile,
)
from app.scraper import ScraperRegistry
from app.services.matching_service import match_jobs
from app.services.source_service import get_enabled_sources, get_source_credentials
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
    attributes.flag_modified(run, "logs")


def add_source_log(source_run: SourceRun, message: str, level: str = "info") -> None:
    """Add a log entry to a source run."""
    if source_run.logs is None:
        source_run.logs = []

    source_run.logs.append({
        "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        "level": level,
        "message": message
    })

    attributes.flag_modified(source_run, "logs")


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


async def scrape_single_source(
    db: AsyncSession,
    run: Run,
    source: ScraperSource,
    job_limit: int = 0
) -> SourceRun:
    """
    Scrape jobs from a single source.

    Args:
        db: Database session
        run: Parent Run record
        source: ScraperSource to scrape
        job_limit: Max jobs to scrape (0 = unlimited)

    Returns:
        SourceRun record with results
    """
    # Create source run record
    source_run = SourceRun(
        run_id=run.id,
        source_name=source.name,
        status=SourceRunStatus.RUNNING.value,
        logs=[],
        started_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(source_run)
    await db.commit()
    await db.refresh(source_run)

    log_to_console(f"\n{'='*60}")
    log_to_console(f"🔍 Starting scrape: {source.label} (priority: {source.priority})")
    log_to_console(f"{'='*60}")

    add_log(run, f"Starting {source.label} scraper", "info")
    add_source_log(source_run, f"Starting scrape for {source.label}", "info")
    await db.commit()

    try:
        # Check if scraper is registered
        if not ScraperRegistry.is_registered(source.name):
            raise ValueError(f"Scraper '{source.name}' is not registered")

        # Get credentials and create scraper instance
        credentials = get_source_credentials(source)
        scraper = ScraperRegistry.create_instance(
            source.name,
            credentials=credentials,
            settings=source.settings or {}
        )

        if not scraper:
            raise ValueError(f"Failed to create scraper instance for '{source.name}'")

        # Get existing source_ids for this source (for deduplication)
        existing_result = await db.execute(
            select(Job.source_id).filter(Job.source == source.name)
        )
        existing_slugs = set(row[0] for row in existing_result.fetchall())

        log_to_console(f"📥 Found {len(existing_slugs)} existing jobs for {source.name}")
        add_source_log(source_run, f"Found {len(existing_slugs)} existing jobs", "info")
        await db.commit()

        # Progress callback for real-time updates
        async def progress_callback(message: str, level: str = "info"):
            add_source_log(source_run, message, level)
            add_log(run, f"[{source.label}] {message}", level)
            await db.commit()

        # Scrape jobs
        jobs_data = await scraper.scrape(
            progress_callback=progress_callback,
            job_limit=job_limit,
            existing_slugs=existing_slugs
        )

        source_run.jobs_found = len(jobs_data)

        # Save jobs to database
        jobs_new = 0
        jobs_duplicate = 0
        jobs_failed = 0

        for job_data in jobs_data:
            try:
                source_id = job_data.get("source_id")

                # Check same-source deduplication
                if source_id in existing_slugs:
                    jobs_duplicate += 1
                    continue

                # Check cross-source deduplication via resolved_url
                resolved_url = job_data.get("resolved_url")
                if resolved_url:
                    existing_url = await db.execute(
                        select(Job.id).filter(Job.resolved_url == resolved_url)
                    )
                    if existing_url.scalar_one_or_none():
                        log_to_console(f"  ⏭️ Cross-source duplicate: {job_data['title']}")
                        jobs_duplicate += 1
                        continue

                # Create new job
                job = Job(
                    source=job_data["source"],
                    source_id=job_data["source_id"],
                    url=job_data["url"],
                    resolved_url=job_data.get("resolved_url"),
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
                jobs_new += 1
                existing_slugs.add(source_id)  # Update in-memory set

            except Exception as e:
                jobs_failed += 1
                log_to_console(f"  ❌ Failed to save job: {e}")

        await db.commit()

        # Update source run stats
        source_run.jobs_new = jobs_new
        source_run.jobs_duplicate = jobs_duplicate
        source_run.jobs_failed = jobs_failed
        source_run.status = SourceRunStatus.COMPLETED.value
        source_run.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        source_run.duration_seconds = (source_run.completed_at - source_run.started_at).total_seconds()

        add_source_log(
            source_run,
            f"Completed: {jobs_new} new, {jobs_duplicate} duplicates, {jobs_failed} failed",
            "success"
        )
        add_log(
            run,
            f"[{source.label}] Completed: {jobs_new} new, {jobs_duplicate} duplicates, {jobs_failed} failed",
            "success"
        )
        await db.commit()

        log_to_console(f"\n✅ {source.label} completed: {jobs_new} new, {jobs_duplicate} duplicates, {jobs_failed} failed")

    except Exception as e:
        error_msg = str(e)
        source_run.status = SourceRunStatus.FAILED.value
        source_run.error_message = error_msg
        source_run.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        source_run.duration_seconds = (source_run.completed_at - source_run.started_at).total_seconds()

        add_source_log(source_run, f"Failed: {error_msg}", "error")
        add_log(run, f"[{source.label}] Failed: {error_msg}", "error")
        await db.commit()

        log_to_console(f"\n❌ {source.label} failed: {error_msg}")

    return source_run


async def scrape_and_save_jobs(
    db: AsyncSession,
    trigger_type: str = RunTriggerType.MANUAL.value,
    source_names: list[str] | None = None
) -> dict[str, int]:
    """
    Scrape jobs from all enabled sources (or specific sources) and save to database.

    Args:
        db: Database session
        trigger_type: How the run was triggered (manual/scheduled_daily/scheduled_hourly)
        source_names: Optional list of specific sources to run (None = all enabled)

    Returns:
        Dictionary with aggregate statistics

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

    run = None
    stats = {"total": 0, "new": 0, "existing": 0, "failed": 0, "sources_run": 0, "sources_failed": 0}

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

        # Get sources to scrape
        if source_names:
            # Get specific sources
            sources_result = await db.execute(
                select(ScraperSource)
                .where(ScraperSource.name.in_(source_names))
                .where(ScraperSource.enabled == True)  # noqa: E712
                .order_by(ScraperSource.priority)
            )
            sources = list(sources_result.scalars().all())
        else:
            # Get all enabled sources
            sources = await get_enabled_sources(db)

        if not sources:
            raise ValueError("No enabled scraper sources found. Enable at least one source in Admin settings.")

        source_labels = [s.label for s in sources]
        log_to_console(f"\n🎯 Running scrapers: {', '.join(source_labels)}")

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

        add_log(run, f"Starting job scraping from {len(sources)} source(s): {', '.join(source_labels)}", "info")
        await db.commit()

        # Get scrape job limit from database
        job_limit_str = await get_setting(db, "scrape_job_limit", "0")
        job_limit = int(job_limit_str)

        # Scrape each source sequentially (parallel would require separate DB sessions)
        # For parallel execution, we'd need to create separate sessions per task
        source_runs = []
        for source in sources:
            source_run = await scrape_single_source(db, run, source, job_limit)
            source_runs.append(source_run)

        # Aggregate stats from all source runs
        total_new = sum(sr.jobs_new for sr in source_runs)
        total_found = sum(sr.jobs_found for sr in source_runs)
        total_duplicate = sum(sr.jobs_duplicate for sr in source_runs)
        total_failed = sum(sr.jobs_failed for sr in source_runs)
        sources_completed = sum(1 for sr in source_runs if sr.status == SourceRunStatus.COMPLETED.value)
        sources_failed = sum(1 for sr in source_runs if sr.status == SourceRunStatus.FAILED.value)

        stats = {
            "total": total_found,
            "new": total_new,
            "existing": total_duplicate,
            "failed": total_failed,
            "sources_run": sources_completed,
            "sources_failed": sources_failed,
        }

        log_to_console(f"\n📊 Scraping Summary (all sources):")
        log_to_console(f"  Total jobs found: {total_found}")
        log_to_console(f"  New jobs saved: {total_new}")
        log_to_console(f"  Duplicates skipped: {total_duplicate}")
        log_to_console(f"  Failed: {total_failed}")
        log_to_console(f"  Sources completed: {sources_completed}/{len(sources)}")

        add_log(run, f"Scraping completed: {total_new} new jobs from {sources_completed} sources", "success")
        await db.commit()

        # Phase 2: Match jobs with AI
        if total_new > 0:
            log_to_console(f"\n🤖 Starting AI matching phase...")
            run.phase = RunPhase.MATCHING.value
            await db.commit()

            matching_stats = await match_jobs(db, run)

            # Update run stats
            run.stats = {
                "jobs_scraped": total_found,
                "new_jobs": total_new,
                "duplicate_jobs": total_duplicate,
                "failed_jobs": total_failed,
                "jobs_matched": matching_stats["matched"],
                "jobs_rejected": matching_stats["rejected"],
                "matching_errors": matching_stats["errors"],
                "average_match_score": matching_stats["average_score"],
                "sources_run": sources_completed,
                "sources_failed": sources_failed,
                "sources": [s.name for s in sources],
            }
            await db.commit()
        else:
            log_to_console(f"\n⏭️ No new jobs to match, skipping matching phase")
            run.stats = {
                "jobs_scraped": total_found,
                "new_jobs": total_new,
                "duplicate_jobs": total_duplicate,
                "failed_jobs": total_failed,
                "sources_run": sources_completed,
                "sources_failed": sources_failed,
                "sources": [s.name for s in sources],
            }
            await db.commit()

        # Complete the run
        run.status = RunStatus.COMPLETED.value if sources_failed == 0 else RunStatus.PARTIAL.value
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
