"""Scraper service to handle job scraping, matching, and saving to database."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import attributes

from app.config import settings
from app.database import async_session_maker
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


@dataclass
class ScrapeResult:
    """Result from scraping a single source."""
    source_name: str
    source_label: str
    source_run_id: int
    jobs_data: list[dict] = field(default_factory=list)
    jobs_found: int = 0
    error: str | None = None
    success: bool = True


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

    If lock acquisition fails, checks for stale locks (lock held but no
    running pipeline in DB) and clears them.

    Returns:
        True if lock acquired, False if another scraper is running
    """
    result = await db.execute(
        text("SELECT pg_try_advisory_lock(:lock_id)"),
        {"lock_id": SCRAPER_LOCK_ID}
    )
    if result.scalar():
        return True

    # Lock not acquired - check if it's stale
    # A stale lock means the advisory lock is held but no run is actually running
    # NOTE: Small race condition window - another run could start between this
    # check and pg_terminate_backend. Acceptable given low frequency (hourly/daily).
    running_run = await db.execute(
        text("SELECT id FROM runs WHERE status = 'running' LIMIT 1")
    )
    if running_run.scalar() is None:
        # No running pipeline but lock is held = stale lock
        log_to_console("⚠️ Detected stale scraper lock - clearing it")

        # Kill the session holding the stale lock
        terminate_result = await db.execute(text("""
            SELECT pg_terminate_backend(pid)
            FROM pg_locks
            WHERE locktype = 'advisory' AND objid = :lock_id
            LIMIT 1
        """), {"lock_id": SCRAPER_LOCK_ID})

        terminated = terminate_result.scalar()
        if not terminated:
            log_to_console("⚠️ Failed to terminate stale lock holder")
            return False

        # Give terminated session time to clean up
        await asyncio.sleep(0.1)

        # Try to acquire again
        result = await db.execute(
            text("SELECT pg_try_advisory_lock(:lock_id)"),
            {"lock_id": SCRAPER_LOCK_ID}
        )
        if result.scalar():
            log_to_console("✅ Successfully acquired lock after clearing stale lock")
            return True

    return False


async def release_scraper_lock(db: AsyncSession) -> None:
    """Release the session-level advisory lock."""
    await db.execute(
        text("SELECT pg_advisory_unlock(:lock_id)"),
        {"lock_id": SCRAPER_LOCK_ID}
    )
    log_to_console("🔓 Released scraper lock")


async def scrape_source_parallel(
    run_id: int,
    source_name: str,
    source_label: str,
    source_settings: dict | None,
    source_credentials_prefix: str | None,
    job_limit: int = 0
) -> ScrapeResult:
    """
    Scrape jobs from a single source (designed for parallel execution).

    Uses its own DB session for status updates.
    Returns scraped job data without saving to DB (dedup happens later).

    Args:
        run_id: Parent Run ID
        source_name: Source name (e.g., "working_nomads")
        source_label: Source display label
        source_settings: Source-specific settings dict
        source_credentials_prefix: Env var prefix for credentials
        job_limit: Max jobs to scrape (0 = unlimited)

    Returns:
        ScrapeResult with jobs_data list and metadata
    """
    result = ScrapeResult(
        source_name=source_name,
        source_label=source_label,
        source_run_id=0,
    )

    async with async_session_maker() as db:
        try:
            # Create source run record
            source_run = SourceRun(
                run_id=run_id,
                source_name=source_name,
                status=SourceRunStatus.RUNNING.value,
                logs=[],
                started_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            db.add(source_run)
            await db.commit()
            await db.refresh(source_run)
            result.source_run_id = source_run.id

            log_to_console(f"\n{'='*60}")
            log_to_console(f"🔍 Starting scrape: {source_label}")
            log_to_console(f"{'='*60}")

            add_source_log(source_run, f"Starting scrape for {source_label}", "info")

            # Also log to parent run
            run_result = await db.execute(select(Run).where(Run.id == run_id))
            run = run_result.scalar_one_or_none()
            if run:
                add_log(run, f"Starting {source_label} scraper", "info")
            await db.commit()

            # Check if scraper is registered
            if not ScraperRegistry.is_registered(source_name):
                raise ValueError(f"Scraper '{source_name}' is not registered")

            # Get credentials and create scraper instance
            credentials = {}
            if source_credentials_prefix:
                import os
                credentials = {
                    "username": os.getenv(f"{source_credentials_prefix}_USERNAME", ""),
                    "password": os.getenv(f"{source_credentials_prefix}_PASSWORD", ""),
                    "api_key": os.getenv(f"{source_credentials_prefix}_API_KEY", ""),
                }

            scraper = ScraperRegistry.create_instance(
                source_name,
                credentials=credentials,
                settings=source_settings or {}
            )

            if not scraper:
                raise ValueError(f"Failed to create scraper instance for '{source_name}'")

            # Get existing source_ids for this source (for same-source dedup during scrape)
            existing_result = await db.execute(
                select(Job.source_id).filter(Job.source == source_name)
            )
            existing_slugs = set(row[0] for row in existing_result.fetchall())

            log_to_console(f"📥 Found {len(existing_slugs)} existing jobs for {source_name}")
            add_source_log(source_run, f"Found {len(existing_slugs)} existing jobs", "info")
            await db.commit()

            # Progress callback for real-time updates
            async def progress_callback(message: str, level: str = "info"):
                add_source_log(source_run, message, level)
                if run:
                    add_log(run, f"[{source_label}] {message}", level)
                await db.commit()

            # Scrape jobs
            jobs_data = await scraper.scrape(
                progress_callback=progress_callback,
                job_limit=job_limit,
                existing_slugs=existing_slugs
            )

            result.jobs_data = jobs_data
            result.jobs_found = len(jobs_data)
            source_run.jobs_found = len(jobs_data)

            # Mark as completed immediately after scraping
            # Stats (jobs_new, jobs_duplicate) will be updated in save phase
            source_run.status = SourceRunStatus.COMPLETED.value
            source_run.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            source_run.duration_seconds = (source_run.completed_at - source_run.started_at).total_seconds()

            add_source_log(source_run, f"Scraping complete: {len(jobs_data)} jobs found", "success")
            if run:
                add_log(run, f"[{source_label}] Scraping complete: {len(jobs_data)} jobs found", "success")
            await db.commit()

            log_to_console(f"\n✅ {source_label} scraping complete: {len(jobs_data)} jobs found")

        except Exception as e:
            error_msg = str(e)
            result.error = error_msg
            result.success = False

            # Update source run with error
            source_run_result = await db.execute(
                select(SourceRun).where(SourceRun.id == result.source_run_id)
            )
            source_run = source_run_result.scalar_one_or_none()
            if source_run:
                source_run.status = SourceRunStatus.FAILED.value
                source_run.error_message = error_msg
                source_run.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                source_run.duration_seconds = (source_run.completed_at - source_run.started_at).total_seconds()
                add_source_log(source_run, f"Failed: {error_msg}", "error")

            run_result = await db.execute(select(Run).where(Run.id == run_id))
            run = run_result.scalar_one_or_none()
            if run:
                add_log(run, f"[{source_label}] Failed: {error_msg}", "error")
            await db.commit()

            log_to_console(f"\n❌ {source_label} failed: {error_msg}")

    return result


async def save_jobs_and_finalize_source_runs(
    db: AsyncSession,
    run: Run,
    scrape_results: list[ScrapeResult]
) -> dict[str, int]:
    """
    Save scraped jobs to database with cross-source deduplication.
    Finalize source run records with final stats.

    Args:
        db: Database session
        run: Parent Run record
        scrape_results: List of ScrapeResult from parallel scraping

    Returns:
        Aggregate stats dict
    """
    total_new = 0
    total_duplicate = 0
    total_failed = 0
    total_found = 0

    # Track resolved URLs we've seen in this batch for cross-source dedup
    seen_resolved_urls: set[str] = set()

    # Get all existing resolved URLs from database
    existing_urls_result = await db.execute(
        select(Job.resolved_url).where(Job.resolved_url.isnot(None))
    )
    existing_resolved_urls = set(row[0] for row in existing_urls_result.fetchall())

    for result in scrape_results:
        if not result.success:
            # Source already marked as failed, skip
            continue

        source_run_result = await db.execute(
            select(SourceRun).where(SourceRun.id == result.source_run_id)
        )
        source_run = source_run_result.scalar_one_or_none()
        if not source_run:
            continue

        # Get existing source_ids for this source
        existing_source_ids_result = await db.execute(
            select(Job.source_id).filter(Job.source == result.source_name)
        )
        existing_source_ids = set(row[0] for row in existing_source_ids_result.fetchall())

        jobs_new = 0
        jobs_duplicate = 0
        jobs_failed = 0

        add_source_log(source_run, f"Saving jobs to database...", "info")
        add_log(run, f"[{result.source_label}] Saving jobs to database...", "info")
        await db.commit()

        for job_data in result.jobs_data:
            try:
                source_id = job_data.get("source_id")

                # Check same-source deduplication
                if source_id in existing_source_ids:
                    jobs_duplicate += 1
                    continue

                # Check cross-source deduplication via resolved_url
                resolved_url = job_data.get("resolved_url")
                if resolved_url:
                    # Check against DB and this batch
                    if resolved_url in existing_resolved_urls or resolved_url in seen_resolved_urls:
                        log_to_console(f"  ⏭️ Cross-source duplicate: {job_data['title']}")
                        jobs_duplicate += 1
                        continue
                    seen_resolved_urls.add(resolved_url)

                # Create new job
                job = Job(
                    source=job_data["source"],
                    source_id=job_data["source_id"],
                    url=job_data["url"],
                    resolved_url=resolved_url,
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
                existing_source_ids.add(source_id)
                if resolved_url:
                    existing_resolved_urls.add(resolved_url)

            except Exception as e:
                jobs_failed += 1
                log_to_console(f"  ❌ Failed to save job: {e}")

        await db.commit()

        # Update source run stats (status already set to completed in scrape phase)
        source_run.jobs_new = jobs_new
        source_run.jobs_duplicate = jobs_duplicate
        source_run.jobs_failed = jobs_failed

        add_source_log(
            source_run,
            f"Saved: {jobs_new} new, {jobs_duplicate} duplicates, {jobs_failed} failed",
            "success"
        )
        add_log(
            run,
            f"[{result.source_label}] Saved: {jobs_new} new, {jobs_duplicate} duplicates, {jobs_failed} failed",
            "success"
        )
        await db.commit()

        log_to_console(f"\n✅ {result.source_label} saved: {jobs_new} new, {jobs_duplicate} duplicates, {jobs_failed} failed")

        total_new += jobs_new
        total_duplicate += jobs_duplicate
        total_failed += jobs_failed
        total_found += result.jobs_found

    return {
        "total": total_found,
        "new": total_new,
        "duplicate": total_duplicate,
        "failed": total_failed,
    }


async def scrape_and_save_jobs_with_run(
    db: AsyncSession,
    run_id: int,
    source_names: list[str] | None = None
) -> dict[str, int]:
    """
    Execute scraping with a pre-created run record.

    This is called from the API when a run has already been created.
    The run_id is guaranteed to exist and be in RUNNING status.

    Args:
        db: Database session
        run_id: ID of the pre-created run record
        source_names: Optional list of specific sources to run (None = all enabled)

    Returns:
        Dictionary with aggregate statistics
    """
    # Get the existing run
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()

    if not run:
        raise ValueError(f"Run #{run_id} not found")

    return await _execute_scraping(db, run, source_names)


async def scrape_and_save_jobs(
    db: AsyncSession,
    trigger_type: str = RunTriggerType.MANUAL.value,
    source_names: list[str] | None = None
) -> dict[str, int]:
    """
    Scrape jobs from all enabled sources (or specific sources) and save to database.

    This is called from the scheduler when no run exists yet.
    Creates a new run record internally.

    Scraping runs in PARALLEL for speed.
    Deduplication and saving runs SEQUENTIALLY for correctness.

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

        return await _execute_scraping(db, run, source_names)

    finally:
        # ALWAYS release the lock, even on error
        try:
            await release_scraper_lock(db)
        except Exception as unlock_error:
            log_to_console(f"⚠️ Warning: Failed to release scraper lock: {unlock_error}")


async def _execute_scraping(
    db: AsyncSession,
    run: Run,
    source_names: list[str] | None = None
) -> dict[str, int]:
    """
    Internal function that executes the actual scraping logic.

    Args:
        db: Database session
        run: The Run record to use (already created and committed)
        source_names: Optional list of specific sources to run (None = all enabled)

    Returns:
        Dictionary with aggregate statistics
    """
    stats = {"total": 0, "new": 0, "existing": 0, "failed": 0, "sources_run": 0, "sources_failed": 0}

    try:
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
        log_to_console(f"\n🎯 Running scrapers in parallel: {', '.join(source_labels)}")

        add_log(run, f"Starting parallel scraping from {len(sources)} source(s): {', '.join(source_labels)}", "info")
        await db.commit()

        # Get scrape job limit from database
        job_limit_str = await get_setting(db, "scrape_job_limit", "0")
        job_limit = int(job_limit_str)

        # PARALLEL SCRAPING - each source runs concurrently
        scrape_tasks = [
            scrape_source_parallel(
                run_id=run.id,
                source_name=source.name,
                source_label=source.label,
                source_settings=source.settings,
                source_credentials_prefix=source.credentials_env_prefix,
                job_limit=job_limit,
            )
            for source in sources
        ]

        log_to_console(f"\n🚀 Launching {len(scrape_tasks)} parallel scrape task(s)...")
        scrape_results = await asyncio.gather(*scrape_tasks, return_exceptions=True)

        # Handle any exceptions from gather
        processed_results: list[ScrapeResult] = []
        for i, result in enumerate(scrape_results):
            if isinstance(result, Exception):
                log_to_console(f"❌ Scrape task {i} raised exception: {result}")
                # Create a failed result
                processed_results.append(ScrapeResult(
                    source_name=sources[i].name,
                    source_label=sources[i].label,
                    source_run_id=0,
                    error=str(result),
                    success=False,
                ))
            else:
                processed_results.append(result)

        log_to_console(f"\n📦 All scraping complete. Saving jobs with deduplication...")
        add_log(run, "All scraping complete. Saving jobs with cross-source deduplication...", "info")
        await db.commit()

        # SEQUENTIAL SAVE with cross-source deduplication
        save_stats = await save_jobs_and_finalize_source_runs(db, run, processed_results)

        # Calculate final stats
        sources_completed = sum(1 for r in processed_results if r.success)
        sources_failed = sum(1 for r in processed_results if not r.success)

        stats = {
            "total": save_stats["total"],
            "new": save_stats["new"],
            "existing": save_stats["duplicate"],
            "failed": save_stats["failed"],
            "sources_run": sources_completed,
            "sources_failed": sources_failed,
        }

        log_to_console(f"\n📊 Scraping Summary (all sources):")
        log_to_console(f"  Total jobs found: {save_stats['total']}")
        log_to_console(f"  New jobs saved: {save_stats['new']}")
        log_to_console(f"  Duplicates skipped: {save_stats['duplicate']}")
        log_to_console(f"  Failed: {save_stats['failed']}")
        log_to_console(f"  Sources completed: {sources_completed}/{len(sources)}")

        add_log(run, f"Scraping completed: {save_stats['new']} new jobs from {sources_completed} sources", "success")
        await db.commit()

        # Phase 2: Match jobs with AI
        total_new = save_stats["new"]
        if total_new > 0:
            log_to_console(f"\n🤖 Starting AI matching phase...")
            run.phase = RunPhase.MATCHING.value
            await db.commit()

            matching_stats = await match_jobs(db, run)

            # Update run stats
            run.stats = {
                "jobs_scraped": save_stats["total"],
                "new_jobs": save_stats["new"],
                "duplicate_jobs": save_stats["duplicate"],
                "failed_jobs": save_stats["failed"],
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
                "jobs_scraped": save_stats["total"],
                "new_jobs": save_stats["new"],
                "duplicate_jobs": save_stats["duplicate"],
                "failed_jobs": save_stats["failed"],
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
        # Handle errors
        run.status = RunStatus.FAILED.value
        run.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        run.duration_seconds = (run.completed_at - run.started_at).total_seconds()
        run.error_message = str(e)
        add_log(run, f"Scraping failed: {str(e)}", "error")
        await db.commit()
        log_to_console(f"\n❌ Error: {str(e)}")
        raise

    return stats
