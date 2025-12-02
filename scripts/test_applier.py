#!/usr/bin/env python3
"""Test script for the Applier component."""

import asyncio
import sys
sys.path.insert(0, ".")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models import Job, JobStatus, UserProfile
from app.services.applier_service import apply_to_job, get_user_profile


async def main():
    """Test the applier with a matched job."""
    # Parse command line args
    job_id = None
    auto_confirm = False

    for arg in sys.argv[1:]:
        if arg in ["-y", "--yes"]:
            auto_confirm = True
        else:
            try:
                job_id = int(arg)
            except ValueError:
                pass

    # Create database connection
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Get user profile
        profile = await get_user_profile(db)
        if not profile:
            print("❌ No user profile found!")
            return

        print(f"✅ Profile: {profile.name} ({profile.email})")
        print(f"   CV: {profile.cv_filename or 'Not uploaded'}")
        print(f"   LinkedIn: {profile.linkedin or 'Not set'}")
        print(f"   GitHub: {profile.github or 'Not set'}")

        # Get job - either by ID or first matched
        if job_id:
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                print(f"❌ Job {job_id} not found!")
                return
        else:
            # Get matched jobs and show list
            result = await db.execute(
                select(Job)
                .where(Job.status == JobStatus.MATCHED.value)
                .order_by(Job.match_score.desc())
                .limit(10)
            )
            matched_jobs = list(result.scalars().all())

            if not matched_jobs:
                print("❌ No matched jobs found!")
                return

            print(f"\n📋 Top 10 matched jobs:")
            for i, j in enumerate(matched_jobs, 1):
                print(f"   {i}. [{j.id}] {j.title} @ {j.company} (score: {j.match_score})")

            print("\nUsage: python scripts/test_applier.py <job_id> [-y|--yes]")
            print("Example: python scripts/test_applier.py 252")
            print("         python scripts/test_applier.py 252 -y  # Skip confirmation")
            return

        print(f"\n📋 Testing with job:")
        print(f"   ID: {job.id}")
        print(f"   Title: {job.title}")
        print(f"   Company: {job.company}")
        print(f"   URL: {job.url}")
        print(f"   Score: {job.match_score}")
        print(f"   Status: {job.status}")

        # Ask for confirmation
        print("\n⚠️  This will attempt to apply to this job (DRY RUN - no actual submission)")
        if auto_confirm:
            print("Auto-confirmed with -y flag")
        else:
            confirm = input("Continue? (yes/no): ")
            if confirm.lower() != "yes":
                print("Aborted.")
                return

        # Run applier in DRY RUN mode
        print("\n🚀 Starting application (DRY RUN)...")
        success, message, data = await apply_to_job(db, job, profile, dry_run=True)

        print(f"\n{'='*60}")
        print(f"Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
        print(f"Message: {message}")
        if data and data.get("screenshots"):
            print(f"Screenshots: {len(data['screenshots'])}")
            for ss in data["screenshots"]:
                print(f"  - {ss}")
        if data and data.get("steps"):
            print(f"\nSteps:")
            for step in data["steps"]:
                status = "✅" if step.get("success") else "❌"
                print(f"  {status} {step.get('action')}: {step.get('selector', step.get('url', ''))}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
