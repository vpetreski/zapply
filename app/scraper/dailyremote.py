"""DailyRemote job scraper.

Uses Playwright for browser automation to scrape job listings.
Requires premium token for access (no username/password needed).
Uses stealth mode to bypass Cloudflare protection.
"""

import re
from collections.abc import Awaitable, Callable
from typing import Any

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth.stealth import Stealth

from app.scraper.base import BaseScraper
from app.scraper.registry import ScraperRegistry
from app.utils import log_to_console, resolve_redirect_url


@ScraperRegistry.register("dailyremote")
class DailyRemoteScraper(BaseScraper):
    """Scraper for DailyRemote job board."""

    SOURCE_NAME = "dailyremote"
    SOURCE_LABEL = "DailyRemote"
    SOURCE_DESCRIPTION = "Premium remote job board with software development positions"
    REQUIRES_LOGIN = True
    REQUIRED_CREDENTIALS = ["token"]

    # Location URLs to scrape (in order)
    LOCATION_URLS = [
        ("Worldwide", "https://dailyremote.com/remote-software-development-jobs?page=1&sort_by=time&location_region=Worldwide#main"),
        ("South America", "https://dailyremote.com/remote-software-development-jobs?page=1&sort_by=time&location_region=South%20America#main"),
        ("Colombia", "https://dailyremote.com/remote-software-development-jobs?page=1&sort_by=time&location_country=Colombia#main"),
    ]

    def __init__(
        self,
        credentials: dict[str, str] | None = None,
        settings: dict[str, Any] | None = None
    ) -> None:
        """Initialize DailyRemote scraper."""
        super().__init__(credentials, settings)

        # Get token from credentials
        self.token = credentials.get("token", "") if credentials else ""

        self.base_url = "https://dailyremote.com"
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.stealth = Stealth()

    async def login(self) -> bool:
        """
        Activate premium session using token from environment.

        Returns:
            True if activation successful, False otherwise
        """
        if not self.page:
            return False

        if not self.token:
            log_to_console("❌ Missing DailyRemote token (DAILYREMOTE_TOKEN)")
            return False

        try:
            log_to_console("🔐 Activating DailyRemote premium session...")

            # Use token URL to activate premium
            activate_url = f"{self.base_url}/premium/activate?action=reactivate&token={self.token}"
            await self.page.goto(activate_url, wait_until="domcontentloaded", timeout=60000)
            await self.page.wait_for_timeout(3000)

            # Check if activation was successful
            # The page should redirect to homepage after successful activation
            current_url = self.page.url
            page_text = await self.page.inner_text("body")

            # Check for Cloudflare challenge (activation blocked)
            if "verify you are human" in page_text.lower() or "cloudflare" in page_text.lower():
                log_to_console("❌ Cloudflare is blocking the request")
                return False

            # Check for explicit error messages
            if "token expired" in page_text.lower() or "invalid token" in page_text.lower():
                log_to_console("❌ Token activation failed - invalid or expired token")
                return False

            # If we're no longer on the activation URL, activation succeeded
            if "/premium/activate" not in current_url:
                log_to_console("✅ Premium session activated!")
                return True

            # Still on activation page might indicate an issue
            log_to_console(f"⚠️ Still on activation page, continuing anyway... URL: {current_url}")
            return True

        except Exception as e:
            log_to_console(f"❌ Activation failed: {str(e)}")
            return False

    def _get_page_url(self, base_url: str, page_num: int) -> str:
        """Build URL for a specific page number."""
        # Replace page=1 with the current page number
        return re.sub(r'page=\d+', f'page={page_num}', base_url)

    def _parse_date_label(self, label: str) -> int | None:
        """
        Parse a date label and return approximate days ago.

        Args:
            label: Date label like "23 hours ago", "Yesterday", "2 Days Ago", "1 Week Ago"

        Returns:
            Number of days ago, or None if unparseable
        """
        label = label.lower().strip()

        # Handle "just now", "now", etc.
        if "just" in label or label == "now":
            return 0
        # Handle minutes and hours (same day)
        elif "min" in label or "hour" in label or "sec" in label:
            return 0
        elif "yesterday" in label:
            return 1
        elif "day" in label:
            match = re.search(r'(\d+)', label)
            if match:
                return int(match.group(1))
        elif "week" in label:
            match = re.search(r'(\d+)', label)
            if match:
                return int(match.group(1)) * 7
        elif "month" in label:
            match = re.search(r'(\d+)', label)
            if match:
                return int(match.group(1)) * 30

        return None

    async def _scrape_location(
        self,
        location_name: str,
        location_url: str,
        existing_slugs: set[str],
        all_seen_slugs: set[str],
        since_days: int = 7,
        job_limit: int = 0,
        current_job_count: int = 0,
        progress_callback: Callable[[str, str], Awaitable[None]] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Scrape jobs from a single location filter.

        Args:
            location_name: Name of location for logging
            location_url: URL with location filter
            existing_slugs: Slugs already in database
            all_seen_slugs: Slugs seen in this scraping session (for dedup across locations)
            since_days: Number of days to look back
            job_limit: Maximum jobs to collect (0 = unlimited)
            current_job_count: Jobs already collected from previous locations
            progress_callback: Optional progress callback

        Returns:
            List of job data dictionaries
        """
        if not self.page:
            return []

        jobs = []
        page_num = 1
        max_pages = 50  # Safety limit
        cutoff_days = since_days  # Stop when we see jobs older than this

        log_to_console(f"\n🌍 Scraping location: {location_name}")
        if progress_callback:
            await progress_callback(f"Scraping {location_name}...", "info")

        # Phase 1: Collect all job slugs from listing pages
        slugs_to_scrape = []
        found_old_job = False
        remaining_limit = job_limit - current_job_count if job_limit > 0 else 0

        while page_num <= max_pages and not found_old_job:
            # Check if we've hit the job limit
            if job_limit > 0 and len(slugs_to_scrape) >= remaining_limit:
                log_to_console(f"   🛑 Reached job limit ({job_limit}), stopping collection")
                break
            page_url = self._get_page_url(location_url, page_num)
            log_to_console(f"   📄 Page {page_num}")

            try:
                await self.page.goto(page_url, wait_until="domcontentloaded", timeout=60000)
                await self.page.wait_for_timeout(2000)

                # Find job cards - DailyRemote uses article elements for job listings
                job_cards = await self.page.query_selector_all('article')

                if not job_cards:
                    log_to_console(f"   ⚠️  No jobs found on page {page_num}")
                    break

                log_to_console(f"   Found {len(job_cards)} job cards")
                page_has_new_jobs = False

                for card in job_cards:
                    card_text = await card.inner_text()

                    # Check date - match all patterns _parse_date_label handles
                    date_match = re.search(r'(just now|now|\d+\s*(?:sec(?:ond)?|min(?:ute)?|hour|day|week|month)s?\s*ago|yesterday)', card_text, re.IGNORECASE)
                    if date_match:
                        date_label = date_match.group(1)
                        days_ago = self._parse_date_label(date_label)

                        if days_ago is not None and days_ago > cutoff_days:
                            log_to_console(f"   📅 Found job from {days_ago} days ago - stopping collection")
                            found_old_job = True
                            break

                    # Find job link
                    link = await card.query_selector('a[href*="/remote-job/"]')
                    if not link:
                        continue

                    href = await link.get_attribute('href')
                    if not href:
                        continue

                    slug = href.rstrip('/').split('/')[-1]

                    # Skip if already seen (in DB or in this session)
                    if slug in existing_slugs or slug in all_seen_slugs:
                        continue

                    all_seen_slugs.add(slug)
                    slugs_to_scrape.append(slug)
                    page_has_new_jobs = True

                    # Check if we've hit the job limit
                    if job_limit > 0 and len(slugs_to_scrape) >= remaining_limit:
                        log_to_console(f"   🛑 Reached job limit ({job_limit}), stopping collection")
                        found_old_job = True  # Reuse flag to exit outer loop
                        break

                # If no new jobs on this page (all duplicates), stop
                if not page_has_new_jobs and not found_old_job:
                    log_to_console(f"   ⏭️  No new jobs on page {page_num}")
                    break

                # Check for next page / pagination
                next_page_exists = await self.page.query_selector(f'a[href*="page={page_num + 1}"]')
                if not next_page_exists:
                    log_to_console(f"   📄 No more pages after {page_num}")
                    break

                page_num += 1
                await self.page.wait_for_timeout(1000)  # Be polite

            except Exception as e:
                log_to_console(f"   ❌ Error on page {page_num}: {str(e)}")
                break

        # Phase 2: Scrape job details for collected slugs
        # Limit slugs if needed (safety check)
        if job_limit > 0 and len(slugs_to_scrape) > remaining_limit:
            slugs_to_scrape = slugs_to_scrape[:remaining_limit]

        log_to_console(f"   📝 Scraping {len(slugs_to_scrape)} job details...")

        for i, slug in enumerate(slugs_to_scrape, 1):
            job_data = await self._scrape_job_details(slug)
            if job_data:
                jobs.append(job_data)
                log_to_console(f"   [{i}/{len(slugs_to_scrape)}] ✅ {job_data.get('title', slug)[:50]}")
            else:
                log_to_console(f"   [{i}/{len(slugs_to_scrape)}] ❌ Failed: {slug}")

            # Small delay between job detail scrapes
            if i % 10 == 0:
                await self.page.wait_for_timeout(1000)

        log_to_console(f"   📊 Found {len(jobs)} jobs for {location_name}")
        return jobs

    async def _scrape_job_details(self, slug: str) -> dict[str, Any] | None:
        """
        Scrape details for a single job.

        Args:
            slug: Job slug from URL

        Returns:
            Job data dictionary or None if failed
        """
        if not self.page:
            return None

        try:
            job_url = f"{self.base_url}/remote-job/{slug}"
            await self.page.goto(job_url, wait_until="domcontentloaded", timeout=60000)
            await self.page.wait_for_timeout(1500)

            # Title - usually in h1
            title = slug.replace('-', ' ').title()
            title_elem = await self.page.query_selector('h1')
            if title_elem:
                title = (await title_elem.inner_text()).strip()

            # Company - look for company name element
            company = "Unknown"
            company_selectors = [
                '[class*="company"] a',
                '[class*="company"]',
                'a[href*="/company/"]',
                'h2',  # Sometimes company is in h2
            ]
            for selector in company_selectors:
                elem = await self.page.query_selector(selector)
                if elem:
                    text = (await elem.inner_text()).strip()
                    if text and len(text) < 100:
                        company = text
                        break

            # Description - main content area
            description = ""
            desc_selectors = [
                '[class*="job-description"]',
                '[class*="description"]',
                'article',
                '.content',
                'main',
            ]
            for selector in desc_selectors:
                elem = await self.page.query_selector(selector)
                if elem:
                    text = (await elem.inner_text()).strip()
                    if len(text) > 100:
                        description = text
                        break

            # Location
            location = "Remote"
            location_selectors = [
                '[class*="location"]',
                '[data-testid="location"]',
            ]
            for selector in location_selectors:
                elem = await self.page.query_selector(selector)
                if elem:
                    text = (await elem.inner_text()).strip()
                    if text:
                        location = text
                        break

            # Tags/Skills
            tags = []
            tag_selectors = [
                '[class*="tag"]',
                '[class*="skill"]',
                '.badge',
            ]
            for selector in tag_selectors:
                elems = await self.page.query_selector_all(selector)
                for elem in elems[:15]:
                    text = (await elem.inner_text()).strip()
                    if text and len(text) < 50:
                        tags.append(text.lower())

            # Apply button - get the real job URL
            apply_url = None
            resolved_url = None

            apply_selectors = [
                'a:has-text("Apply Now")',
                'a:has-text("Apply")',
                'a[class*="apply"]',
                'button:has-text("Apply")',
            ]

            for selector in apply_selectors:
                btn = await self.page.query_selector(selector)
                if btn:
                    href = await btn.get_attribute('href')
                    if href:
                        # Handle both absolute and relative URLs
                        if href.startswith('http'):
                            apply_url = href
                        elif href.startswith('/'):
                            apply_url = f"{self.base_url}{href}"
                        else:
                            continue  # Skip invalid URLs
                        # Resolve redirect to get actual job URL
                        try:
                            resolved_url = await resolve_redirect_url(apply_url)
                        except Exception as e:
                            log_to_console(f"   ⚠️ Failed to resolve URL for {slug}: {str(e)}")
                            resolved_url = None
                        break

            return {
                "id": slug,
                "url": resolved_url or apply_url or job_url,
                "resolved_url": resolved_url,
                "title": title,
                "company": company,
                "description": description,
                "requirements": None,
                "location": location,
                "salary": None,
                "tags": tags if tags else None,
                "raw_data": {
                    "slug": slug,
                    "dailyremote_url": job_url,
                    "apply_url_raw": apply_url,
                    "apply_url_resolved": resolved_url,
                }
            }

        except Exception as e:
            log_to_console(f"❌ Failed to scrape job {slug}: {str(e)}")
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
        Scrape jobs from DailyRemote.

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

        jobs = []
        all_seen_slugs = set()  # Track slugs across all locations
        playwright = None
        location_stats = {}  # Track jobs per location

        try:
            # Launch browser with stealth mode
            log_to_console("🚀 Launching browser for DailyRemote (with stealth)...")
            if progress_callback:
                await progress_callback("Launching browser...", "info")
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)

            # Create context with realistic user agent
            self.context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            self.page = await self.context.new_page()

            # Apply stealth to bypass Cloudflare
            await self.stealth.apply_stealth_async(self.page)

            # Activate premium session
            if progress_callback:
                await progress_callback("Activating premium session...", "info")
            if not await self.login():
                log_to_console("❌ Premium activation failed, cannot continue")
                return jobs

            # Scrape each location
            for location_name, location_url in self.LOCATION_URLS:
                # Skip if we've already hit the limit
                if job_limit > 0 and len(jobs) >= job_limit:
                    log_to_console(f"🛑 Job limit ({job_limit}) reached, skipping remaining locations")
                    break

                location_jobs = await self._scrape_location(
                    location_name=location_name,
                    location_url=location_url,
                    existing_slugs=existing_slugs,
                    all_seen_slugs=all_seen_slugs,
                    since_days=since_days,
                    job_limit=job_limit,
                    current_job_count=len(jobs),
                    progress_callback=progress_callback,
                )

                location_stats[location_name] = len(location_jobs)

                # Normalize and add jobs
                for job_data in location_jobs:
                    normalized_job = self.normalize_job(job_data)
                    jobs.append(normalized_job)

                # Small delay between locations
                await self.page.wait_for_timeout(2000)

            # Log summary
            log_to_console(f"\n📊 DailyRemote Scraping Summary:")
            for loc, count in location_stats.items():
                log_to_console(f"   {loc}: {count} jobs")
            log_to_console(f"   Total: {len(jobs)} jobs")

            if progress_callback:
                await progress_callback(f"Successfully scraped {len(jobs)} jobs!", "success")

        except Exception as e:
            log_to_console(f"❌ Scraping failed: {str(e)}")
            import traceback
            traceback.print_exc()
            if progress_callback:
                await progress_callback(f"Scraping failed: {str(e)}", "error")

        finally:
            # Close browser and context
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if playwright:
                await playwright.stop()
            log_to_console("🔒 Browser closed")

        return jobs
