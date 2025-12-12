"""Remotive job scraper.

Uses Playwright for browser automation to scrape job listings.
Requires premium login for access to all jobs.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from playwright.async_api import async_playwright, Browser, Page

from app.scraper.base import BaseScraper
from app.scraper.registry import ScraperRegistry
from app.utils import log_to_console, resolve_redirect_url


@ScraperRegistry.register("remotive")
class RemotiveScraper(BaseScraper):
    """Scraper for Remotive job board."""

    SOURCE_NAME = "remotive"
    SOURCE_LABEL = "Remotive"
    SOURCE_DESCRIPTION = "Premium remote job board with software development positions"
    REQUIRES_LOGIN = True
    REQUIRED_CREDENTIALS = ["username", "password"]

    def __init__(
        self,
        credentials: dict[str, str] | None = None,
        settings: dict[str, Any] | None = None
    ) -> None:
        """Initialize Remotive scraper."""
        super().__init__(credentials, settings)

        # Get credentials from init params
        if credentials and credentials.get("username") and credentials.get("password"):
            self.username = credentials["username"]
            self.password = credentials["password"]
        else:
            self.username = ""
            self.password = ""

        self.base_url = "https://remotive.com"
        self.login_url = f"{self.base_url}/web/login"
        # Default filter URL - Software Development, Worldwide + LATAM + Colombia
        self.jobs_url = f"{self.base_url}/remote-jobs/software-development"

        self.browser: Browser | None = None
        self.page: Page | None = None

    async def login(self) -> bool:
        """
        Login to Remotive.

        Returns:
            True if login successful, False otherwise
        """
        if not self.page:
            return False

        if not self.username or not self.password:
            log_to_console("❌ Missing Remotive credentials (REMOTIVE_USERNAME/PASSWORD)")
            return False

        try:
            log_to_console(f"🔐 Logging in to Remotive as {self.username}...")

            await self.page.goto(self.login_url, wait_until="domcontentloaded")
            await self.page.wait_for_timeout(1000)

            # Fill login form
            await self.page.fill('input[name="login"]', self.username)
            await self.page.fill('input[name="password"]', self.password)

            # Submit
            await self.page.click('button[type="submit"]')
            await self.page.wait_for_load_state("networkidle")
            await self.page.wait_for_timeout(2000)

            # Check if login was successful by looking for user menu or redirect
            # After login, should redirect to dashboard or jobs page
            current_url = self.page.url
            if "login" not in current_url.lower():
                log_to_console("✅ Login successful!")
                return True
            else:
                log_to_console(f"❌ Login failed - still on login page: {current_url}")
                return False

        except Exception as e:
            log_to_console(f"❌ Login failed: {str(e)}")
            return False

    def _get_filter_url(self) -> str:
        """Build filter URL from settings or use defaults."""
        # Get filter settings
        locations = self.settings.get("locations", ["Worldwide", "Latin America (LATAM)", "Colombia"])

        # URL encode locations
        location_param = ",".join(locations).replace(" ", "+").replace("(", "%28").replace(")", "%29")

        return f"{self.jobs_url}?location={location_param}"

    async def _load_jobs_until_cutoff(self, job_limit: int = 0, max_age_days: int = 7) -> None:
        """
        Click 'More Jobs' button until we see jobs older than max_age_days.

        Args:
            job_limit: Maximum number of jobs to load (0 = unlimited)
            max_age_days: Stop loading when jobs older than this appear (default: 7 days = 1 week)
        """
        if not self.page:
            return

        log_to_console(f"📥 Loading jobs (stopping at {max_age_days}+ days old)...")

        # Button selector for "More Jobs"
        button_selectors = [
            'button:has-text("More Jobs")',
            'button:has-text("Load More")',
            'button:has-text("Show More")',
            'a:has-text("More Jobs")',
            '[class*="load-more"]',
        ]

        click_count = 0
        while click_count < 100:  # Safety limit
            try:
                # Check for old job markers (2wks ago, etc.)
                page_text = await self.page.content()

                # Stop if we see jobs that are 2+ weeks old
                if "2wks ago" in page_text or "3wks ago" in page_text or "1mo ago" in page_text:
                    log_to_console(f"   Found jobs older than {max_age_days} days, stopping load")
                    break

                # Count current jobs
                job_cards = await self.page.query_selector_all('[data-testid="job-list-item"], .job-card, article[class*="job"]')
                if not job_cards:
                    # Try alternate selector
                    job_cards = await self.page.query_selector_all('a[href*="/remote-jobs/"][href*="-"]')

                job_count = len(job_cards)

                # Check if we've reached the limit
                if job_limit > 0 and job_count >= job_limit:
                    log_to_console(f"   Reached job limit of {job_limit}")
                    break

                # Find and click "More Jobs" button
                found_button = None
                for selector in button_selectors:
                    button = await self.page.query_selector(selector)
                    if button:
                        is_visible = await button.is_visible()
                        if is_visible:
                            found_button = button
                            break

                if not found_button:
                    log_to_console(f"   No 'More Jobs' button found - all jobs may be loaded")
                    break

                await found_button.click()
                await self.page.wait_for_timeout(2000)
                click_count += 1

                # Count jobs after click
                job_cards_after = await self.page.query_selector_all('a[href*="/remote-jobs/"][href*="-"]')
                log_to_console(f"   Click {click_count}: Now showing ~{len(job_cards_after)} job links")

            except Exception as e:
                log_to_console(f"   Error during load: {e}")
                break

        log_to_console(f"✅ Finished loading jobs after {click_count} clicks")

    async def _extract_job_slugs(self) -> list[str]:
        """
        Extract job slugs from the job listing page.

        Returns:
            List of job slugs
        """
        if not self.page:
            return []

        log_to_console("📋 Extracting job slugs...")

        # Find job links in the software-development category (not nav links)
        # Format: /remote-jobs/software-development/job-slug-123456
        job_links = await self.page.query_selector_all('a[href*="/remote-jobs/software-development/"]')

        slugs = []
        seen_slugs = set()

        for link in job_links:
            href = await link.get_attribute('href')
            if not href:
                continue

            # Extract slug from URL
            # URLs look like: /remote-jobs/software-development/senior-python-developer-123456
            parts = href.rstrip('/').split('/')

            # Get the last part as the slug (job-title-with-id)
            if len(parts) >= 4:  # /remote-jobs/software-development/slug
                slug = parts[-1]
                # Skip if already seen
                if slug and slug not in seen_slugs:
                    # Job slugs end with a numeric ID
                    if any(c.isdigit() for c in slug.split('-')[-1]):
                        slugs.append(slug)
                        seen_slugs.add(slug)

        log_to_console(f"✅ Found {len(slugs)} unique job slugs")
        return slugs

    async def _scrape_job_details(self, slug: str) -> dict[str, Any] | None:
        """
        Scrape details for a single job.

        Args:
            slug: Job slug

        Returns:
            Job data dictionary or None if failed
        """
        if not self.page:
            return None

        try:
            # Navigate to job detail page - need full path with category
            job_url = f"{self.base_url}/remote-jobs/software-development/{slug}"
            await self.page.goto(job_url, wait_until="networkidle")
            await self.page.wait_for_timeout(1000)

            # Title - in h1, format: "[Hiring] Job Title @CompanyName"
            title_elem = await self.page.query_selector('h1')
            raw_title = await title_elem.inner_text() if title_elem else slug.replace('-', ' ').title()
            raw_title = raw_title.strip()

            # Parse title and company from format: "[Hiring] Senior Developer @A.Team"
            title = raw_title
            company = "Unknown"

            # Remove "[Hiring]" prefix if present (only from start, not all occurrences)
            if title.startswith('[Hiring]'):
                title = title[len('[Hiring]'):].strip()

            # Extract company from "@CompanyName" suffix
            if '@' in title:
                parts = title.rsplit('@', 1)
                title = parts[0].strip()
                company = parts[1].strip()

            # Description - extract from page body text
            # The job content is between the title line and "Similar Remote Jobs" section
            description = ""
            body = await self.page.query_selector('body')
            if body:
                body_text = await body.inner_text()
                lines = body_text.split('\n')

                # Find the job content section
                start_idx = None
                end_idx = len(lines)

                for i, line in enumerate(lines):
                    line_stripped = line.strip()
                    # Start after the title line (usually contains company name)
                    if start_idx is None and company in line_stripped and len(line_stripped) > 50:
                        start_idx = i + 1
                    # End before "Similar Remote Jobs" or company info repeat
                    if start_idx is not None and ("Similar Remote Jobs" in line_stripped or
                                                   "NOT YOUR TECH STACK" in line_stripped):
                        end_idx = i
                        break

                if start_idx is not None:
                    # Extract and clean the description
                    desc_lines = []
                    for line in lines[start_idx:end_idx]:
                        line = line.strip()
                        if line and len(line) > 1:  # Skip empty and single-char lines
                            desc_lines.append(line)
                    description = '\n\n'.join(desc_lines)

            # Location
            location = "Remote"
            location_selectors = [
                '[data-testid="location"]',
                '.location',
                '[class*="location"]',
            ]
            for selector in location_selectors:
                loc_elem = await self.page.query_selector(selector)
                if loc_elem:
                    loc_text = await loc_elem.inner_text()
                    if loc_text:
                        location = loc_text.strip()
                        break

            # Tags/Skills
            tags = []
            tag_selectors = [
                '[data-testid="tag"]',
                '.tag',
                '.badge',
                '[class*="skill"]',
            ]
            for selector in tag_selectors:
                tag_elems = await self.page.query_selector_all(selector)
                for tag_elem in tag_elems[:15]:
                    tag_text = await tag_elem.inner_text()
                    if tag_text and len(tag_text.strip()) < 50:
                        tags.append(tag_text.strip().lower())

            # Apply button - get the real job URL
            apply_url = None
            resolved_url = None

            # Look for "Apply for this position" buttons - need the one with href (not onclick)
            apply_buttons = await self.page.query_selector_all('a:has-text("Apply for this position")')

            for btn in apply_buttons:
                href = await btn.get_attribute('href')
                # Skip buttons without href (they use onclick for JS)
                if href and href.startswith('http'):
                    apply_url = href
                    # Resolve redirect to get actual job URL
                    resolved_url = await resolve_redirect_url(apply_url)
                    break

            # Full job page URL on Remotive
            full_url = job_url

            return {
                "id": slug,
                "url": resolved_url or apply_url or full_url,
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
                    "remotive_url": full_url,
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
        Scrape jobs from Remotive.

        Args:
            since_days: Number of days to look back (used to determine when to stop loading)
            progress_callback: Optional async callback for progress updates
            job_limit: Maximum number of jobs to load (0 = unlimited)
            existing_slugs: Set of job slugs already in database

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
                await progress_callback("Logging in to Remotive...", "info")
            if not await self.login():
                log_to_console("❌ Login failed, cannot continue")
                return jobs

            # Navigate to jobs page with filters
            filter_url = self._get_filter_url()
            log_to_console(f"🔍 Navigating to {filter_url}")
            if progress_callback:
                await progress_callback("Applying location filters...", "info")

            await self.page.goto(filter_url, wait_until="networkidle")
            await self.page.wait_for_timeout(2000)

            # Load jobs until we see old ones
            posted_days = self.settings.get("posted_days", 7)
            if progress_callback:
                await progress_callback(f"Loading jobs (last {posted_days} days)...", "info")
            await self._load_jobs_until_cutoff(job_limit=job_limit, max_age_days=posted_days)

            # Extract job slugs
            all_slugs = await self._extract_job_slugs()

            # Apply limit
            if job_limit > 0 and len(all_slugs) > job_limit:
                all_slugs = all_slugs[:job_limit]

            # Filter out existing slugs
            new_slugs = [slug for slug in all_slugs if slug not in existing_slugs]
            skipped_count = len(all_slugs) - len(new_slugs)

            log_to_console(f"\n📊 Job Summary:")
            log_to_console(f"  Total jobs found: {len(all_slugs)}")
            log_to_console(f"  ✅ New jobs to scrape: {len(new_slugs)}")
            log_to_console(f"  ⏭️  Already in database: {skipped_count}")

            if progress_callback:
                await progress_callback(
                    f"Found {len(all_slugs)} jobs: {len(new_slugs)} new, {skipped_count} existing",
                    "success"
                )

            # Scrape only new jobs
            log_to_console(f"\n📝 Scraping {len(new_slugs)} new jobs...")

            scraped_count = 0
            for i, slug in enumerate(all_slugs, 1):
                if slug in existing_slugs:
                    log_to_console(f"  [{i}/{len(all_slugs)}] ⏭️  SKIP: {slug} (already exists)")
                    continue

                scraped_count += 1
                log_to_console(f"  [{i}/{len(all_slugs)}] 📝 SCRAPING: {slug}")
                if progress_callback:
                    await progress_callback(f"Scraping job {i}/{len(all_slugs)}: {slug}", "info")

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
            if progress_callback:
                await progress_callback(f"Scraping failed: {str(e)}", "error")

        finally:
            # Close browser
            if self.browser:
                await self.browser.close()
            if playwright:
                await playwright.stop()
            log_to_console("🔒 Browser closed")

        return jobs
