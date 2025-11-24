"""Scraper service to handle job scraping and saving to database."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job
from app.schemas import JobCreate
from app.scraper import WorkingNomadsScraper


async def scrape_and_save_jobs(db: AsyncSession) -> dict[str, int]:
    """
    Scrape jobs from Working Nomads and save to database.

    Args:
        db: Database session

    Returns:
        Dictionary with statistics: {total, new, existing, failed}
    """
    stats = {
        "total": 0,
        "new": 0,
        "existing": 0,
        "failed": 0,
    }

    # Initialize scraper
    scraper = WorkingNomadsScraper()

    # Scrape jobs
    print("🎯 Starting job scraping...")
    jobs_data = await scraper.scrape()
    stats["total"] = len(jobs_data)

    # Save to database
    print(f"\n💾 Saving {len(jobs_data)} jobs to database...")
    for job_data in jobs_data:
        try:
            # Check if job already exists
            source_id = job_data.get("source_id")
            source = job_data.get("source")

            existing_job = await db.execute(
                select(Job).filter(Job.source_id == source_id, Job.source == source)
            )
            existing = existing_job.scalar_one_or_none()

            if existing:
                print(f"  ⏭️  Job already exists: {source_id}")
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
            print(f"  ✅ Saved: {job.title} at {job.company}")

        except Exception as e:
            stats["failed"] += 1
            print(f"  ❌ Failed to save job: {str(e)}")

    # Commit all changes
    await db.commit()

    print(f"\n📊 Summary:")
    print(f"  Total scraped: {stats['total']}")
    print(f"  New jobs saved: {stats['new']}")
    print(f"  Already existed: {stats['existing']}")
    print(f"  Failed: {stats['failed']}")

    return stats
