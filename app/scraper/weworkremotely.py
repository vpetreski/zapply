"""We Work Remotely job scraper.

Uses RSS feeds for fast job listing. No login or browser automation needed.

IMPORTANT: Cross-source deduplication is NOT available for WWR jobs.
- WWR uses Cloudflare protection that blocks headless browsers
- We cannot programmatically access job detail pages to get real Apply URLs
- Jobs are stored with WWR page URL, not the actual company job URL
- If the same job exists on WWR and another source, both will be stored

This is acceptable for MVP - job overlap is low and manual review catches dupes.
"""

import defusedxml.ElementTree as ET
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.scraper.base import BaseScraper
from app.scraper.registry import ScraperRegistry
from app.utils import log_to_console


@ScraperRegistry.register("we_work_remotely")
class WeWorkRemotelyScraper(BaseScraper):
    """Scraper for We Work Remotely job board.

    Uses RSS feeds for job listing - fast and bypasses Cloudflare.
    The real Apply URLs are stored in raw_data for the Applier to resolve
    when actually applying to a job.

    Note: Cloudflare blocks headless browsers on WWR login/job pages,
    so Apply URL resolution must happen at apply-time with user interaction.
    """

    SOURCE_NAME = "we_work_remotely"
    SOURCE_LABEL = "We Work Remotely"
    SOURCE_DESCRIPTION = "Popular remote job board with backend and fullstack positions"
    REQUIRES_LOGIN = False  # RSS scraping doesn't need login
    REQUIRED_CREDENTIALS = []  # No credentials needed

    # RSS feed URLs for different categories
    RSS_FEEDS = {
        "backend": "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
        "fullstack": "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
    }

    # Regions we're interested in
    ALLOWED_REGIONS = {
        "Anywhere in the World",
        "Latin America Only",
    }

    def __init__(
        self,
        credentials: dict[str, str] | None = None,
        settings: dict[str, Any] | None = None
    ) -> None:
        """Initialize We Work Remotely scraper."""
        super().__init__(credentials, settings)
        self.base_url = "https://weworkremotely.com"

    async def login(self) -> bool:
        """
        Login to We Work Remotely.

        Not used for scraping (RSS doesn't require login).
        Login is handled by Applier when applying to jobs.

        Returns:
            Always True since scraping uses RSS.
        """
        return True

    async def _fetch_rss_jobs(self, posted_days: int = 7) -> list[dict[str, Any]]:
        """
        Fetch jobs from RSS feeds.

        Args:
            posted_days: Only include jobs posted within this many days

        Returns:
            List of job data from RSS
        """
        jobs = []
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=posted_days)

        # Get categories from settings (normalize to lowercase for dict lookup)
        categories = [c.lower() for c in self.settings.get("categories", ["backend", "fullstack"])]

        async with httpx.AsyncClient(timeout=30.0) as client:
            for category in categories:
                feed_url = self.RSS_FEEDS.get(category)
                if not feed_url:
                    log_to_console(f"  ⚠️ Unknown category: {category}")
                    continue

                log_to_console(f"  📡 Fetching {category} RSS feed...")

                try:
                    response = await client.get(feed_url)
                    response.raise_for_status()

                    root = ET.fromstring(response.text)
                    channel = root.find("channel")
                    if channel is None:
                        continue

                    items = channel.findall("item")
                    log_to_console(f"    Found {len(items)} items in {category} feed")

                    for item in items:
                        # Parse job data from RSS
                        job_data = self._parse_rss_item(item, category)
                        if not job_data:
                            continue

                        # Check date filter (only skip if we can confirm it's too old)
                        pub_date = job_data.get("pub_date")
                        if pub_date and pub_date < cutoff_date:
                            continue

                        # Check region filter
                        region = job_data.get("region", "")
                        if region not in self.ALLOWED_REGIONS:
                            continue

                        jobs.append(job_data)

                except Exception as e:
                    log_to_console(f"  ❌ Failed to fetch {category} RSS: {e}")

        return jobs

    def _parse_rss_item(self, item: ET.Element, category: str) -> dict[str, Any] | None:
        """Parse a single RSS item into job data."""
        try:
            # Extract data from RSS item
            title_elem = item.find("title")
            link_elem = item.find("link")
            guid_elem = item.find("guid")
            pub_date_elem = item.find("pubDate")
            region_elem = item.find("region")
            full_title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""

            # Parse title to extract company and job title
            # Format: "Company Name: Job Title" (single colon)
            if ": " in full_title:
                parts = full_title.split(": ", 1)
                company = parts[0].strip()
                title = parts[1].strip()
            else:
                company = "Unknown"
                title = full_title or "Unknown"

            # Get job URL and extract slug
            job_url = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
            if not job_url:
                job_url = guid_elem.text.strip() if guid_elem is not None and guid_elem.text else ""

            # Extract slug from URL: /remote-jobs/company-job-title
            slug = ""
            if "/remote-jobs/" in job_url:
                slug = job_url.split("/remote-jobs/")[-1].rstrip("/")

            if not slug:
                return None

            # Parse publication date
            pub_date = None
            if pub_date_elem is not None and pub_date_elem.text:
                try:
                    pub_date = datetime.strptime(
                        pub_date_elem.text.strip(),
                        "%a, %d %b %Y %H:%M:%S %z"
                    )
                except ValueError:
                    pass

            # Get region
            region = region_elem.text.strip() if region_elem is not None and region_elem.text else ""

            # Get description (HTML content)
            desc_elem = item.find("description")
            description = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""

            # Get job type
            type_elem = item.find("type")
            job_type = type_elem.text.strip() if type_elem is not None and type_elem.text else ""

            # Get skills/tags
            skills_elem = item.find("skills")
            skills = []
            if skills_elem is not None and skills_elem.text:
                skills = [s.strip() for s in skills_elem.text.split(",")]

            return {
                "slug": slug,
                "title": title,
                "company": company,
                "url": job_url,
                "pub_date": pub_date,
                "region": region,
                "description": description,
                "job_type": job_type,
                "skills": skills,
                "category": category,
            }

        except Exception as e:
            log_to_console(f"    ⚠️ Failed to parse RSS item: {e}")
            return None

    async def scrape(
        self,
        since_days: int = 7,
        progress_callback: Callable[[str, str], Awaitable[None]] | None = None,
        job_limit: int = 0,
        existing_slugs: set[str] | None = None,
        **kwargs
    ) -> list[dict[str, Any]]:
        """
        Scrape jobs from We Work Remotely using RSS feeds.

        Strategy:
        1. Fetch job listings from RSS feeds (fast, no Cloudflare)
        2. Filter by date and region
        3. Normalize and return

        Note: The real Apply URLs cannot be scraped in headless mode due to
        Cloudflare protection. The WWR job URL is stored, and the Applier
        will resolve the real Apply URL when actually applying to a job.

        Args:
            since_days: Only include jobs posted within this many days
            progress_callback: Async callback for progress updates
            job_limit: Maximum number of jobs to scrape (0 = unlimited)
            existing_slugs: Set of slugs already in database

        Returns:
            List of normalized job dictionaries
        """
        if existing_slugs is None:
            existing_slugs = set()
        jobs = []

        try:
            # Step 1: Fetch jobs from RSS feeds
            log_to_console("📡 Fetching jobs from RSS feeds...")
            if progress_callback:
                await progress_callback("Fetching jobs from RSS feeds...", "info")

            posted_days = self.settings.get("posted_days", 7)
            rss_jobs = await self._fetch_rss_jobs(posted_days=posted_days)

            log_to_console(f"✅ Found {len(rss_jobs)} jobs from RSS (filtered by region and date)")
            if progress_callback:
                await progress_callback(f"Found {len(rss_jobs)} jobs from RSS feeds", "success")

            if not rss_jobs:
                log_to_console("⚠️ No jobs found in RSS feeds")
                return jobs

            # Step 2: Filter out existing jobs
            new_jobs = [j for j in rss_jobs if j.get("slug") not in existing_slugs]
            skipped_count = len(rss_jobs) - len(new_jobs)

            log_to_console(f"\n📊 Job Summary:")
            log_to_console(f"  Total from RSS: {len(rss_jobs)}")
            log_to_console(f"  ✅ New jobs: {len(new_jobs)}")
            log_to_console(f"  ⏭️  Already exist: {skipped_count}")

            if progress_callback:
                await progress_callback(f"Found {len(new_jobs)} new jobs ({skipped_count} already exist)", "success")

            if not new_jobs:
                log_to_console("✅ All jobs already in database, nothing new to scrape")
                return jobs

            # Apply job limit
            if job_limit > 0 and len(new_jobs) > job_limit:
                new_jobs = new_jobs[:job_limit]
                log_to_console(f"  📉 Limited to {job_limit} jobs")

            # Step 3: Normalize jobs from RSS data
            log_to_console(f"\n📝 Processing {len(new_jobs)} jobs...")

            for i, job_data in enumerate(new_jobs, 1):
                slug = job_data.get("slug", "unknown")
                job_url = job_data.get("url", f"{self.base_url}/remote-jobs/{slug}")

                if progress_callback and i % 10 == 0:
                    await progress_callback(f"Processing job {i}/{len(new_jobs)}", "info")

                # Normalize the job from RSS data
                # NOTE: resolved_url is None - WWR jobs cannot participate in
                # cross-source deduplication due to Cloudflare blocking (see module docstring)
                # Extract pub_date once to avoid double .get()
                job_pub_date = job_data.get("pub_date")

                normalized = self.normalize_job({
                    "id": slug,
                    "url": job_url,  # WWR job page URL (not the actual company job URL)
                    "resolved_url": None,  # Cannot resolve due to Cloudflare - no cross-source dedup
                    "title": job_data.get("title", "Unknown"),
                    "company": job_data.get("company", "Unknown"),
                    "description": job_data.get("description", ""),
                    "location": job_data.get("region", "Anywhere"),
                    "tags": job_data.get("skills", []),
                    "raw_data": {
                        "slug": slug,
                        "wwr_url": job_url,
                        "region": job_data.get("region", ""),
                        "job_type": job_data.get("job_type", ""),
                        "category": job_data.get("category", ""),
                        "pub_date": job_pub_date.isoformat() if job_pub_date else None,
                    },
                })
                jobs.append(normalized)

            log_to_console(f"\n✅ Successfully processed {len(jobs)} jobs!")
            if progress_callback:
                await progress_callback(f"Successfully processed {len(jobs)} jobs!", "success")

        except Exception as e:
            log_to_console(f"❌ Scraping failed: {str(e)}")
            import traceback
            traceback.print_exc()
            if progress_callback:
                await progress_callback(f"Scraping failed: {str(e)}", "error")

        return jobs
