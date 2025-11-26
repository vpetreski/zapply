"""Working Nomads job scraper."""

import re
from collections.abc import Awaitable, Callable
from typing import Any

from playwright.async_api import async_playwright, Browser, Page

from app.scraper.base import BaseScraper
from app.utils import log_to_console


class WorkingNomadsScraper(BaseScraper):
    """Scraper for Working Nomads job board."""

    def __init__(self) -> None:
        """Initialize Working Nomads scraper."""
        from app.config import settings
        self.username = settings.working_nomads_username
        self.password = settings.working_nomads_password
        self.base_url = "https://www.workingnomads.com"
        self.login_url = f"{self.base_url}/users/sign_in"
        self.jobs_url = f"{self.base_url}/jobs"

        self.browser: Browser | None = None
        self.page: Page | None = None

    async def login(self) -> bool:
        """
        Login to Working Nomads.

        Returns:
            True if login successful, False otherwise
        """
        if not self.page:
            return False

        try:
            log_to_console(f"🔐 Logging in to Working Nomads as {self.username}...")

            await self.page.goto(self.login_url, wait_until="domcontentloaded")
            await self.page.wait_for_timeout(1000)

            # Fill login form
            await self.page.fill('input[type="email"]', self.username)
            await self.page.fill('input[type="password"]', self.password)

            # Submit
            await self.page.click('input[type="submit"]')
            await self.page.wait_for_load_state("networkidle")

            # Verify we're logged in (should be at /jobs page)
            if self.page.url.startswith(f"{self.base_url}/jobs"):
                log_to_console("✅ Login successful!")
                return True
            else:
                log_to_console(f"❌ Login failed - unexpected URL: {self.page.url}")
                return False

        except Exception as e:
            log_to_console(f"❌ Login failed: {str(e)}")
            return False

    async def _set_filters(self) -> None:
        """Set job filters: Development category + Anywhere,Colombia locations."""
        if not self.page:
            return

        log_to_console("🔍 Setting filters (Development + Anywhere,Colombia)...")

        filter_url = f"{self.jobs_url}?category=development&location=anywhere,colombia"
        await self.page.goto(filter_url, wait_until="networkidle")

        log_to_console("✅ Filters applied!")

    async def _load_all_jobs(self, job_limit: int = 0) -> None:
        """
        Click 'Show more jobs' button until all jobs are loaded or limit is reached.

        Args:
            job_limit: Maximum number of jobs to load (0 = unlimited)
        """
        if not self.page:
            return

        if job_limit > 0:
            log_to_console(f"📥 Loading jobs (limit: {job_limit})...")
        else:
            log_to_console("📥 Loading all jobs...")

        # Button selectors to try
        button_selectors = [
            'button:has-text("Show more jobs")',
            'button:has-text("Show more")',
            'button:has-text("Load more")',
            'a:has-text("Show more jobs")',
            'a:has-text("Show more")',
            '[class*="load-more"]',
            '[class*="show-more"]',
            'button[class*="more"]',
        ]

        # Find initial button
        found_button = None
        for selector in button_selectors:
            button = await self.page.query_selector(selector)
            if button:
                is_visible = await button.is_visible()
                if is_visible:
                    found_button = button
                    log_to_console("   Found 'Show more jobs' button")
                    break

        if not found_button:
            log_to_console("   No 'Show more jobs' button found - all jobs may already be loaded")
            return

        # Click button until it disappears (all jobs loaded) or we reach the limit
        click_count = 0
        unique_jobs = 0
        while click_count < 50:  # Safety limit
            try:
                # Check if button still exists and is visible
                is_visible = await found_button.is_visible()
                if not is_visible:
                    log_to_console(f"   Button disappeared after {click_count} clicks")
                    break

                await found_button.click()
                await self.page.wait_for_timeout(2000)

                click_count += 1

                # Count jobs after click
                jobs_after = await self.page.query_selector_all('a[href^="/jobs/"]')
                unique_jobs = len(set([await j.get_attribute('href') for j in jobs_after]))
                log_to_console(f"   Click {click_count}: Now showing {unique_jobs} jobs")

                # Check if we've reached the limit
                if job_limit > 0 and unique_jobs >= job_limit:
                    log_to_console(f"   Reached job limit of {job_limit}!")
                    break

                # Try to find button again (it might be re-rendered)
                found_button = None
                for sel in button_selectors:
                    btn = await self.page.query_selector(sel)
                    if btn:
                        is_vis = await btn.is_visible()
                        if is_vis:
                            found_button = btn
                            break

                if not found_button:
                    log_to_console(f"   All jobs loaded! (Total clicks: {click_count})")
                    break

            except Exception as e:
                log_to_console(f"   Error clicking button: {e}")
                break

        if job_limit > 0:
            log_to_console(f"✅ Loaded {unique_jobs} jobs (limit: {job_limit})!")
        else:
            log_to_console("✅ All jobs loaded!")

    async def _extract_job_slugs(self) -> list[str]:
        """
        Extract job slugs from the job listing.

        Returns:
            List of job slugs (e.g., ['middle-java-developer-gr8-tech', ...])
        """
        if not self.page:
            return []

        log_to_console("📋 Extracting job slugs...")

        # Find all job links - format: /jobs/middle-java-developer-gr8-tech
        job_links = await self.page.query_selector_all('a[href^="/jobs/"]')

        slugs = []
        for link in job_links:
            href = await link.get_attribute('href')
            if href and href != '/jobs':
                # Extract slug from URL
                slug = href.replace('/jobs/', '')
                if slug and '/' not in slug and slug not in slugs:
                    slugs.append(slug)

        log_to_console(f"✅ Found {len(slugs)} unique jobs!")
        return slugs

    async def _scrape_job_details(self, slug: str) -> dict[str, Any] | None:
        """
        Scrape details for a single job.

        Args:
            slug: Job slug (e.g., 'middle-java-developer-gr8-tech')

        Returns:
            Job data dictionary or None if failed
        """
        if not self.page:
            return None

        try:
            # Navigate to job detail page with filters to maintain context
            job_url = f"{self.jobs_url}?category=development&location=anywhere,colombia&job={slug}"
            await self.page.goto(job_url, wait_until="networkidle")
            await self.page.wait_for_timeout(500)

            # Title (h1 on job detail page)
            title_elem = await self.page.query_selector('h1')
            title = await title_elem.inner_text() if title_elem else slug.replace('-', ' ').title()
            title = title.strip()

            # Company name (near the h1)
            company = "Unknown"
            # Try to find company - it's usually right after the title
            company_candidates = await self.page.query_selector_all('h1 + div, h1 ~ div')
            for candidate in company_candidates[:3]:
                text = await candidate.inner_text()
                text = text.strip()
                # Company names are usually short and don't have newlines
                if text and 3 < len(text) < 50 and '\n' not in text:
                    # Skip common non-company texts
                    if text.lower() not in ['about the job', 'full-time', 'part-time', 'anywhere']:
                        company = text
                        break

            # Description - get all paragraph text from the main content
            paragraphs = await self.page.query_selector_all('main p, article p, [role="main"] p')
            description_parts = []
            for p in paragraphs:
                text = await p.inner_text()
                if text and len(text) > 20:  # Skip very short paragraphs
                    description_parts.append(text.strip())

            description = '\n\n'.join(description_parts) if description_parts else ""

            # Location (look for "Anywhere" or location text)
            location = "Anywhere"  # Default since we filtered for "Anywhere"

            # Tags (look for badge/tag elements)
            tag_elements = await self.page.query_selector_all('span.badge, .tag, [class*="tag"]')
            tags = []
            for tag_elem in tag_elements[:10]:  # Limit to first 10 tags
                tag_text = await tag_elem.inner_text()
                if tag_text and len(tag_text) < 30:  # Reasonable tag length
                    tags.append(tag_text.strip().lower())

            # Apply button URL
            apply_button = await self.page.query_selector('a:has-text("Apply"), button:has-text("Apply")')
            apply_url = None
            if apply_button:
                apply_url = await apply_button.get_attribute('href')
                # Make absolute URL if relative
                if apply_url and not apply_url.startswith('http'):
                    apply_url = f"{self.base_url}{apply_url}"

            # Full job page URL
            full_url = f"{self.base_url}/jobs/{slug}"

            return {
                "id": slug,
                "url": apply_url or full_url,  # Prefer apply URL
                "title": title,
                "company": company,
                "description": description,
                "requirements": None,  # Could parse separately if needed
                "location": location,
                "salary": None,  # Parse if available
                "tags": tags if tags else None,
                "raw_data": {
                    "slug": slug,
                    "job_page_url": full_url,
                    "apply_url": apply_url,
                }
            }

        except Exception as e:
            log_to_console(f"❌ Failed to scrape job {slug}: {str(e)}")
            return None

    async def scrape(
        self,
        since_days: int = 1,
        progress_callback: Callable[[str, str], Awaitable[None]] | None = None,
        job_limit: int = 0,
        existing_slugs: set[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        Scrape jobs from Working Nomads.

        Args:
            since_days: Not used for initial implementation (we scrape all filtered jobs)
            progress_callback: Optional async callback function for progress updates.
                               Signature: async def callback(message: str, level: str) -> None
            job_limit: Maximum number of jobs to load from the listing page (0 = unlimited)
            existing_slugs: Set of job slugs that already exist in the database (for deduplication)

        Returns:
            List of normalized job dictionaries
        """
        if existing_slugs is None:
            existing_slugs = set()
        jobs = []
        playwright = None

        try:
            # Launch browser
            log_to_console("🚀 Launching browser...")
            if progress_callback:
                await progress_callback("Launching browser...", "info")
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
            self.page = await self.browser.new_page()

            # Login
            if progress_callback:
                await progress_callback("Logging in to Working Nomads...", "info")
            if not await self.login():
                return jobs

            # Set filters
            if progress_callback:
                await progress_callback("Applying filters (Development + Anywhere,Colombia)...", "info")
            await self._set_filters()

            # Load jobs (respecting limit from the start)
            if progress_callback:
                if job_limit > 0:
                    await progress_callback(f"Loading jobs (limit: {job_limit}, stopping early)...", "info")
                else:
                    await progress_callback("Loading all jobs (clicking 'Show more' until all loaded)...", "info")
            await self._load_all_jobs(job_limit=job_limit)

            # Extract job slugs
            all_slugs = await self._extract_job_slugs()

            # Apply limit (in case we loaded slightly more than needed)
            if job_limit > 0 and len(all_slugs) > job_limit:
                all_slugs = all_slugs[:job_limit]

            # Filter out existing slugs (optimization)
            new_slugs = [slug for slug in all_slugs if slug not in existing_slugs]
            skipped_count = len(all_slugs) - len(new_slugs)

            log_to_console(f"\n📊 Job Summary:")
            log_to_console(f"  Total jobs found: {len(all_slugs)}")
            log_to_console(f"  ✅ New jobs to scrape: {len(new_slugs)}")
            log_to_console(f"  ⏭️  Already in database: {skipped_count}")

            if progress_callback:
                await progress_callback(f"Found {len(all_slugs)} jobs: {len(new_slugs)} new, {skipped_count} already exist", "success")

            # Scrape only NEW jobs
            log_to_console(f"\n📝 Scraping {len(new_slugs)} new jobs (skipping {skipped_count} existing)...")

            scraped_count = 0
            for i, slug in enumerate(all_slugs, 1):
                # Check if this job already exists
                if slug in existing_slugs:
                    log_to_console(f"  [{i}/{len(all_slugs)}] ⏭️  SKIP: {slug} (already in database)")
                    if progress_callback:
                        await progress_callback(f"Skipping job {i}/{len(all_slugs)}: {slug} (already exists)", "info")
                    continue

                # Scrape new job
                scraped_count += 1
                log_to_console(f"  [{i}/{len(all_slugs)}] 📝 SCRAPING: {slug}")
                if progress_callback:
                    await progress_callback(f"Scraping job {i}/{len(all_slugs)}: {slug} (new)", "info")

                job_data = await self._scrape_job_details(slug)
                if job_data:
                    normalized_job = self.normalize_job(job_data)
                    jobs.append(normalized_job)

                # Small delay to be polite
                if scraped_count % 10 == 0:
                    await self.page.wait_for_timeout(1000)

            log_to_console(f"\n✅ Successfully scraped {len(jobs)} jobs!")
            if progress_callback:
                await progress_callback(f"Successfully scraped {len(jobs)} jobs!", "success")

        except Exception as e:
            log_to_console(f"❌ Scraping failed: {str(e)}")
            import traceback
            traceback.print_exc()

        finally:
            # Close browser
            if self.browser:
                await self.browser.close()
            if playwright:
                await playwright.stop()
            log_to_console("🔒 Browser closed")

        return jobs

    def get_source_name(self) -> str:
        """Get source name."""
        return "working_nomads"
