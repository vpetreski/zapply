"""Application reporting and notifications."""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, JobStatus
from app.utils import log_to_console


class Reporter:
    """Generate reports and notifications about job matching activity."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize reporter."""
        self.db = db

    async def generate_daily_report(self) -> dict[str, Any]:
        """
        Generate daily summary report.

        Returns:
            Dictionary with report data
        """
        # Get jobs from last 24 hours
        since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)

        # Count by status
        new_query = select(Job).filter(Job.created_at >= since, Job.status == JobStatus.NEW.value)
        new_jobs = (await self.db.execute(new_query)).scalars().all()

        matched_query = select(Job).filter(
            Job.matched_at >= since, Job.status == JobStatus.MATCHED.value
        )
        matched_jobs = (await self.db.execute(matched_query)).scalars().all()

        rejected_query = select(Job).filter(
            Job.matched_at >= since, Job.status == JobStatus.REJECTED.value
        )
        rejected_jobs = (await self.db.execute(rejected_query)).scalars().all()

        return {
            "period": "last_24_hours",
            "summary": {
                "new_jobs": len(new_jobs),
                "matched_jobs": len(matched_jobs),
                "rejected_jobs": len(rejected_jobs),
            },
            "matched": [
                {"id": job.id, "title": job.title, "company": job.company, "url": job.url}
                for job in matched_jobs
            ],
            "generated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        }

    async def send_notification(self, report: dict[str, Any]) -> bool:
        """
        Send notification with report.

        TODO: Implement email/webhook notifications
        """
        # For MVP, just print to console
        log_to_console("\n" + "=" * 80)
        log_to_console("ZAPPLY DAILY REPORT")
        log_to_console("=" * 80)
        log_to_console(f"Period: {report['period']}")
        log_to_console(f"\nSummary:")
        log_to_console(f"  New jobs scraped: {report['summary']['new_jobs']}")
        log_to_console(f"  Jobs matched: {report['summary']['matched_jobs']}")
        log_to_console(f"  Jobs rejected: {report['summary']['rejected_jobs']}")

        if report["matched"]:
            log_to_console(f"\nMatched jobs ready for review:")
            for job in report["matched"]:
                log_to_console(f"  - {job['title']} at {job['company']}")
                log_to_console(f"    {job['url']}")

        log_to_console("=" * 80 + "\n")

        return True
