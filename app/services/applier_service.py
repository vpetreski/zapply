"""Applier service for automated job applications."""

import base64
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.applier.applier import JobApplier
from app.models import ApplicationLog, Job, JobStatus, UserProfile
from app.utils import log_to_console


async def get_matched_jobs(db: AsyncSession) -> list[Job]:
    """Get all jobs with MATCHED status."""
    result = await db.execute(
        select(Job)
        .where(Job.status == JobStatus.MATCHED.value)
        .order_by(Job.matched_at.desc())
    )
    return list(result.scalars().all())


async def get_user_profile(db: AsyncSession) -> Optional[UserProfile]:
    """Get the user profile for applications."""
    result = await db.execute(select(UserProfile).limit(1))
    return result.scalar_one_or_none()


async def apply_to_job(
    db: AsyncSession,
    job: Job,
    profile: UserProfile,
    dry_run: bool = False
) -> tuple[bool, str, dict[str, Any]]:
    """
    Apply to a single job.

    Args:
        db: Database session
        job: Job to apply to
        profile: User profile with application data
        dry_run: If True, don't actually submit (for testing)

    Returns:
        Tuple of (success, message, application_data)
    """
    log_to_console(f"\n{'='*60}")
    log_to_console(f"📝 Applying to: {job.title} @ {job.company}")
    log_to_console(f"   URL: {job.url}")
    log_to_console(f"{'='*60}")

    # Create application log entry
    app_log = ApplicationLog(
        job_id=job.id,
        status="in_progress",
        started_at=datetime.now(timezone.utc).replace(tzinfo=None),
        ai_prompts=[],
        ai_responses=[],
        screenshots=[]
    )
    db.add(app_log)
    await db.commit()
    await db.refresh(app_log)

    application_data: dict[str, Any] = {
        "job_id": job.id,
        "job_title": job.title,
        "company": job.company,
        "url": job.url,
        "steps": [],
        "screenshots": []
    }

    try:
        # Prepare CV file path if we have CV data
        cv_path: Optional[Path] = None
        if profile.cv_data:
            # Save CV to temp file
            temp_dir = Path(tempfile.gettempdir())
            cv_path = temp_dir / (profile.cv_filename or "resume.pdf")
            cv_path.write_bytes(profile.cv_data)
            log_to_console(f"   CV saved to: {cv_path}")

        # Initialize applier
        applier = JobApplier(
            profile=profile,
            cv_path=cv_path,
            dry_run=dry_run
        )

        # Run the application
        success, error_message, result_data = await applier.apply_to_job(job)

        # Merge result data
        if result_data:
            application_data.update(result_data)

        # Update application log
        app_log.status = "success" if success else "failed"
        app_log.error_message = error_message if not success else None
        app_log.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        app_log.duration_seconds = (
            app_log.completed_at - app_log.started_at
        ).total_seconds()
        app_log.screenshots = application_data.get("screenshots", [])
        app_log.ai_prompts = application_data.get("ai_prompts", [])
        app_log.ai_responses = application_data.get("ai_responses", [])

        # Update job status
        if success:
            job.status = JobStatus.APPLIED.value
            job.applied_at = datetime.now(timezone.utc).replace(tzinfo=None)
            job.application_data = application_data
            log_to_console(f"✅ Successfully applied to {job.title}!")
        else:
            # Check if job is expired (various error patterns)
            error_lower = (error_message or "").lower()
            is_expired = any(indicator in error_lower for indicator in [
                "expired", "empty content", "category listing", "job listing",
                "no longer available", "position has been filled",
                # Timeout errors are often from dead links that hang
                "timeout", "timed out"
            ])

            if is_expired:
                job.status = JobStatus.EXPIRED.value
                job.application_error = error_message
                job.application_data = application_data
                log_to_console(f"⏰ Job expired: {error_message}")
            else:
                job.status = JobStatus.FAILED.value
                job.application_error = error_message
                job.application_data = application_data
                log_to_console(f"❌ Failed to apply: {error_message}")

        await db.commit()

        # Cleanup temp CV file
        if cv_path and cv_path.exists():
            cv_path.unlink()

        return success, error_message or "Application submitted", application_data

    except Exception as e:
        error_msg = f"Application error: {str(e)}"
        log_to_console(f"❌ {error_msg}")

        # Update logs
        app_log.status = "failed"
        app_log.error_message = error_msg
        app_log.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        if app_log.started_at:
            app_log.duration_seconds = (
                app_log.completed_at - app_log.started_at
            ).total_seconds()

        job.status = JobStatus.FAILED.value
        job.application_error = error_msg

        await db.commit()

        return False, error_msg, application_data


async def apply_to_matched_jobs(
    db: AsyncSession,
    limit: int = 0,
    dry_run: bool = False
) -> dict[str, Any]:
    """
    Apply to all matched jobs.

    Args:
        db: Database session
        limit: Maximum jobs to apply to (0 = all)
        dry_run: If True, don't actually submit

    Returns:
        Stats dictionary with results
    """
    stats = {
        "total_matched": 0,
        "attempted": 0,
        "successful": 0,
        "failed": 0,
        "expired": 0,
        "skipped": 0,
        "results": []
    }

    # Get user profile
    profile = await get_user_profile(db)
    if not profile:
        log_to_console("❌ No user profile found! Please create a profile first.")
        return stats

    log_to_console(f"\n👤 Using profile: {profile.name} ({profile.email})")

    # Get matched jobs
    matched_jobs = await get_matched_jobs(db)
    stats["total_matched"] = len(matched_jobs)

    if not matched_jobs:
        log_to_console("ℹ️  No matched jobs to apply to.")
        return stats

    log_to_console(f"\n📋 Found {len(matched_jobs)} matched jobs")

    # Apply limit
    jobs_to_process = matched_jobs[:limit] if limit > 0 else matched_jobs

    for i, job in enumerate(jobs_to_process, 1):
        log_to_console(f"\n[{i}/{len(jobs_to_process)}] Processing job...")

        stats["attempted"] += 1

        success, message, data = await apply_to_job(db, job, profile, dry_run)

        result = {
            "job_id": job.id,
            "title": job.title,
            "company": job.company,
            "success": success,
            "message": message
        }
        stats["results"].append(result)

        if success:
            stats["successful"] += 1
        elif "expired" in (message or "").lower() or "empty content" in (message or "").lower():
            stats["expired"] += 1
        else:
            stats["failed"] += 1

    # Summary
    log_to_console(f"\n{'='*60}")
    log_to_console(f"📊 Application Summary")
    log_to_console(f"{'='*60}")
    log_to_console(f"   Total matched: {stats['total_matched']}")
    log_to_console(f"   Attempted: {stats['attempted']}")
    log_to_console(f"   ✅ Successful: {stats['successful']}")
    log_to_console(f"   ⏰ Expired: {stats['expired']}")
    log_to_console(f"   ❌ Failed: {stats['failed']}")

    return stats
