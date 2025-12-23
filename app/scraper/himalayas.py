"""Himalayas job scraper.

Uses the public Himalayas API to fetch remote job listings.
Filters for software engineering jobs compatible with Colombia's timezone (UTC-5).
No authentication required.
"""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from app.scraper.base import BaseScraper
from app.scraper.registry import ScraperRegistry
from app.utils import log_to_console


@ScraperRegistry.register("himalayas")
class HimalayasScraper(BaseScraper):
    """Scraper for Himalayas job board API."""

    SOURCE_NAME = "himalayas"
    SOURCE_LABEL = "Himalayas"
    SOURCE_DESCRIPTION = "Curated remote job board with timezone filtering - API based"
    CREDENTIALS_ENV_PREFIX = ""  # No auth needed
    REQUIRES_LOGIN = False
    REQUIRED_CREDENTIALS: list[str] = []

    # API configuration
    API_URL = "https://himalayas.app/jobs/api"
    MAX_PER_PAGE = 20  # API max is 20
    REQUEST_DELAY = 1.5  # Seconds between requests to avoid rate limiting
    MAX_PAGES = 200  # Safety limit (200 * 20 = 4000 jobs max)
    MAX_RETRIES = 3  # Max retries on 429 rate limit
    MAX_CONSECUTIVE_OLD_JOBS = 50  # Stop after this many old jobs in a row
    MAX_LOCATION_DISPLAY = 3  # Max locations to show in location string

    # Categories that indicate software engineering roles
    # Note: "Research & Development" is excluded because it includes non-software roles
    # like Clinical Trial Coordinators. Better to be more specific.
    DEVELOPER_CATEGORIES = {"Developer", "Data Science"}

    # Only Colombia is accepted as a specific country
    # Other LATAM countries (Brazil, Mexico, etc.) are NOT accepted
    # unless the job explicitly says "LATAM" or "South America" region
    ACCEPTED_COUNTRIES = {"Colombia"}

    # Colombia's timezone offset
    COLOMBIA_TZ_OFFSET = -5

    def __init__(
        self,
        credentials: dict[str, str] | None = None,
        settings: dict[str, Any] | None = None
    ) -> None:
        """Initialize Himalayas scraper."""
        super().__init__(credentials, settings)
        self.client: httpx.AsyncClient | None = None

    async def login(self) -> bool:
        """No login required for Himalayas API."""
        return True

    def _extract_slug(self, guid: str) -> str:
        """
        Extract slug from guid URL for deduplication.

        Example guid: https://himalayas.app/companies/acme/jobs/software-engineer-123
        Returns: software-engineer-123
        """
        if not guid:
            return ""
        # Parse URL and get last path component
        path = urlparse(guid).path
        return path.rstrip("/").split("/")[-1]

    def _is_eligible(self, job: dict[str, Any]) -> tuple[bool, str]:
        """
        Check if a job is eligible based on category, timezone, and location.

        Args:
            job: Job data from API

        Returns:
            Tuple of (is_eligible, reason)
        """
        # Check category - must be developer/data science/R&D
        parent_cats = set(job.get("parentCategories", []))
        if not parent_cats.intersection(self.DEVELOPER_CATEGORIES):
            return False, "not_dev_category"

        # Check timezone (Colombia is UTC-5)
        tz_restrictions = job.get("timezoneRestrictions", [])
        if tz_restrictions and self.COLOMBIA_TZ_OFFSET not in tz_restrictions:
            return False, "timezone_mismatch"

        # Check location restrictions
        loc_restrictions = job.get("locationRestrictions", [])

        if not loc_restrictions:
            # Empty = worldwide remote - eligible!
            return True, "worldwide_remote"

        # Check for explicit worldwide/global
        loc_lower = " ".join([loc.lower() for loc in loc_restrictions])
        if "worldwide" in loc_lower or "global" in loc_lower:
            return True, "explicit_worldwide"

        # Check for explicit LATAM/South America region mentions
        if "latin" in loc_lower or "south america" in loc_lower or "latam" in loc_lower:
            return True, "explicit_latam"

        # Check for Colombia specifically (not other LATAM countries)
        if any(country in loc_restrictions for country in self.ACCEPTED_COUNTRIES):
            return True, "colombia"

        # Job is restricted to other specific countries - reject
        return False, "location_restricted"

    async def _fetch_page(self, offset: int, retry_count: int = 0) -> dict[str, Any] | None:
        """
        Fetch a page of jobs from the API.

        Args:
            offset: Pagination offset
            retry_count: Current retry attempt (for rate limit handling)

        Returns:
            API response dict or None on error
        """
        if not self.client:
            return None

        try:
            response = await self.client.get(
                self.API_URL,
                params={"limit": self.MAX_PER_PAGE, "offset": offset},
                timeout=30.0
            )

            if response.status_code == 429:
                if retry_count >= self.MAX_RETRIES:
                    log_to_console(f"   ❌ Rate limited, max retries ({self.MAX_RETRIES}) exceeded")
                    return None
                wait_time = 5 * (retry_count + 1)  # Exponential backoff: 5, 10, 15 seconds
                log_to_console(f"   ⚠️ Rate limited, waiting {wait_time} seconds (retry {retry_count + 1}/{self.MAX_RETRIES})...")
                await asyncio.sleep(wait_time)
                return await self._fetch_page(offset, retry_count + 1)

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            log_to_console(f"   ❌ HTTP error: {e.response.status_code}")
            return None
        except Exception as e:
            log_to_console(f"   ❌ Request error: {str(e)}")
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
        Scrape jobs from Himalayas API.

        Args:
            since_days: Number of days to look back
            progress_callback: Optional async callback for progress updates
            job_limit: Maximum number of jobs (0 = unlimited)
            existing_slugs: Set of job slugs already in database

        Returns:
            List of normalized job dictionaries
        """
        if existing_slugs is None:
            existing_slugs = set()

        jobs: list[dict[str, Any]] = []
        seen_slugs: set[str] = set()
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=since_days)

        # Stats tracking
        stats = {
            "pages_fetched": 0,
            "jobs_scanned": 0,
            "eligible_found": 0,
            "skipped_existing": 0,
            "skipped_old": 0,
            "rejected": {
                "not_dev_category": 0,
                "timezone_mismatch": 0,
                "location_restricted": 0,
            }
        }

        log_to_console("🚀 Starting Himalayas API scraper...")
        if progress_callback:
            await progress_callback("Starting Himalayas API scraper...", "info")

        async with httpx.AsyncClient(
            headers={"User-Agent": "Zapply Job Scraper/1.0"},
            follow_redirects=True
        ) as client:
            self.client = client
            offset = 0
            found_old_job = False

            while offset < self.MAX_PAGES * self.MAX_PER_PAGE and not found_old_job:
                # Check job limit
                if job_limit > 0 and len(jobs) >= job_limit:
                    log_to_console(f"   🛑 Reached job limit ({job_limit})")
                    if progress_callback:
                        await progress_callback(f"Job limit ({job_limit}) reached", "info")
                    break

                # Fetch page
                data = await self._fetch_page(offset)
                if not data:
                    log_to_console(f"   ❌ Failed to fetch page at offset {offset}")
                    break

                page_jobs = data.get("jobs", [])
                if not page_jobs:
                    log_to_console("   📄 No more jobs")
                    break

                stats["pages_fetched"] += 1
                stats["jobs_scanned"] += len(page_jobs)

                # Log progress every 5 pages
                if stats["pages_fetched"] % 5 == 0:
                    log_to_console(f"   📄 Page {stats['pages_fetched']}: scanned {stats['jobs_scanned']} jobs, found {len(jobs)} eligible")
                    if progress_callback:
                        await progress_callback(
                            f"Page {stats['pages_fetched']}: {len(jobs)} eligible jobs found",
                            "info"
                        )

                for job in page_jobs:
                    # Check date
                    pub_timestamp = job.get("pubDate", 0)
                    pub_date = datetime.fromtimestamp(pub_timestamp, tz=timezone.utc)

                    if pub_date < cutoff_date:
                        stats["skipped_old"] += 1
                        # If we see too many old jobs consecutively, stop
                        if stats["skipped_old"] > self.MAX_CONSECUTIVE_OLD_JOBS:
                            log_to_console(f"   📅 Found {stats['skipped_old']} old jobs, stopping")
                            found_old_job = True
                            break
                        continue

                    # Reset old job counter if we find a recent one
                    stats["skipped_old"] = 0

                    # Extract slug for dedup
                    slug = self._extract_slug(job.get("guid", ""))
                    if not slug:
                        continue

                    # Skip if already exists or seen in this batch
                    if slug in existing_slugs or slug in seen_slugs:
                        stats["skipped_existing"] += 1
                        continue

                    # Check eligibility
                    is_eligible, reason = self._is_eligible(job)
                    if not is_eligible:
                        if reason in stats["rejected"]:
                            stats["rejected"][reason] += 1
                        continue

                    # Job is eligible!
                    seen_slugs.add(slug)
                    stats["eligible_found"] += 1

                    # Normalize and add job
                    normalized = self._normalize_job(job, slug)
                    jobs.append(normalized)

                    # Log eligible job
                    title = job.get("title", "Unknown")[:50]
                    company = job.get("companyName", "Unknown")[:25]
                    log_to_console(f"   ✅ {title} @ {company}")

                # Rate limiting delay
                await asyncio.sleep(self.REQUEST_DELAY)
                offset += self.MAX_PER_PAGE

        # Reset client reference after context manager exits
        self.client = None

        # Log summary
        log_to_console(f"\n📊 Himalayas Scraping Summary:")
        log_to_console(f"   Pages fetched: {stats['pages_fetched']}")
        log_to_console(f"   Jobs scanned: {stats['jobs_scanned']}")
        log_to_console(f"   Eligible found: {len(jobs)}")
        log_to_console(f"   Skipped (existing): {stats['skipped_existing']}")
        log_to_console(f"   Rejected breakdown:")
        log_to_console(f"     - Not dev category: {stats['rejected']['not_dev_category']}")
        log_to_console(f"     - Timezone mismatch: {stats['rejected']['timezone_mismatch']}")
        log_to_console(f"     - Location restricted: {stats['rejected']['location_restricted']}")

        if progress_callback:
            await progress_callback(
                f"Completed! Found {len(jobs)} eligible jobs from {stats['jobs_scanned']} scanned",
                "success"
            )

        return jobs

    def _normalize_job(self, job: dict[str, Any], slug: str) -> dict[str, Any]:
        """
        Normalize Himalayas job data to internal format.

        Args:
            job: Raw job data from API
            slug: Extracted slug for dedup

        Returns:
            Normalized job dictionary
        """
        # Build location string from restrictions
        loc_restrictions = job.get("locationRestrictions", [])
        if not loc_restrictions:
            location = "Worldwide Remote"
        else:
            location = ", ".join(loc_restrictions[:self.MAX_LOCATION_DISPLAY])
            if len(loc_restrictions) > self.MAX_LOCATION_DISPLAY:
                location += f" (+{len(loc_restrictions) - self.MAX_LOCATION_DISPLAY} more)"

        # Build salary string if available
        salary = None
        try:
            min_sal = job.get("minSalary")
            max_sal = job.get("maxSalary")
            currency = job.get("currency", "USD")
            if min_sal or max_sal:
                if min_sal and max_sal:
                    salary = f"{currency} {int(min_sal):,} - {int(max_sal):,}"
                elif min_sal:
                    salary = f"{currency} {int(min_sal):,}+"
                else:
                    salary = f"Up to {currency} {int(max_sal):,}"
        except (ValueError, TypeError):
            # If salary values aren't numeric, skip salary formatting
            salary = None

        # Extract tags from categories
        tags = job.get("categories", []) + job.get("parentCategories", [])
        seniority = job.get("seniority", [])
        if seniority:
            tags.extend(seniority)
        employment_type = job.get("employmentType")
        if employment_type:
            tags.append(employment_type)

        # Clean and dedupe tags
        tags = list(set([tag.replace("-", " ").lower() for tag in tags if tag]))[:20]

        return {
            "source": self.SOURCE_NAME,
            "source_id": slug,
            "url": job.get("applicationLink") or job.get("guid", ""),
            "resolved_url": None,  # Himalayas links directly, no redirect resolution needed
            "title": job.get("title", ""),
            "company": job.get("companyName", "Unknown"),
            "description": job.get("description", ""),
            "requirements": job.get("excerpt"),
            "location": location,
            "salary": salary,
            "tags": tags if tags else None,
            "raw_data": {
                "guid": job.get("guid"),
                "pubDate": job.get("pubDate"),
                "expiryDate": job.get("expiryDate"),
                "employmentType": job.get("employmentType"),
                "seniority": job.get("seniority"),
                "locationRestrictions": job.get("locationRestrictions"),
                "timezoneRestrictions": job.get("timezoneRestrictions"),
                "parentCategories": job.get("parentCategories"),
                "categories": job.get("categories"),
            }
        }
