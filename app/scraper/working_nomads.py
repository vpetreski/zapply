"""Working Nomads job scraper."""

import re
from typing import Any

from playwright.async_api import async_playwright, Browser, Page

from app.config import settings
from app.scraper.base import BaseScraper


class WorkingNomadsScraper(BaseScraper):
    """Scraper for Working Nomads job board."""

    def __init__(self) -> None:
        """Initialize Working Nomads scraper."""
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
            print(f"🔐 Logging in to Working Nomads as {self.username}...")

            # Navigate to login page
            await self.page.goto(self.login_url, wait_until="networkidle")

            # Fill in login form
            await self.page.fill('input[name="user[email]"]', self.username)
            await self.page.fill('input[name="user[password]"]', self.password)

            # Submit form
            await self.page.click('button[type="submit"]')

            # Wait for navigation to jobs page
            await self.page.wait_for_url(f"{self.jobs_url}*", timeout=10000)

            print("✅ Login successful!")
            return True

        except Exception as e:
            print(f"❌ Login failed: {str(e)}")
            return False

    async def _set_filters(self) -> None:
        """Set job filters: Development category + Anywhere,Colombia locations."""
        if not self.page:
            return

        print("🔍 Setting filters (Development + Anywhere,Colombia)...")

        # Navigate to jobs page with filters
        filter_url = f"{self.jobs_url}?category=development&location=anywhere,colombia"
        await self.page.goto(filter_url, wait_until="networkidle")

        print("✅ Filters applied!")

    async def _load_all_jobs(self) -> None:
        """Click 'Show more jobs' button until all jobs are loaded."""
        if not self.page:
            return

        print("📥 Loading all jobs...")

        while True:
            try:
                # Look for "Show more jobs" button
                show_more_button = await self.page.query_selector('button:has-text("Show more jobs")')

                if not show_more_button:
                    break

                # Check if button is visible and enabled
                is_visible = await show_more_button.is_visible()
                if not is_visible:
                    break

                # Click the button
                await show_more_button.click()

                # Wait for new jobs to load
                await self.page.wait_for_timeout(1000)

            except Exception as e:
                print(f"No more jobs to load: {str(e)}")
                break

        print("✅ All jobs loaded!")

    async def _extract_job_slugs(self) -> list[str]:
        """
        Extract job slugs from the job listing.

        Returns:
            List of job slugs (e.g., ['lead-rpg-designer-devsu', ...])
        """
        if not self.page:
            return []

        print("📋 Extracting job slugs...")

        # Get all job links
        job_links = await self.page.query_selector_all('a[href*="?"][href*="job="]')

        slugs = []
        for link in job_links:
            href = await link.get_attribute('href')
            if href:
                # Extract job slug from URL parameter
                # e.g., /jobs?category=development&location=anywhere,colombia&job=lead-rpg-designer-devsu
                match = re.search(r'job=([^&]+)', href)
                if match:
                    slug = match.group(1)
                    if slug not in slugs:
                        slugs.append(slug)

        print(f"✅ Found {len(slugs)} unique jobs!")
        return slugs

    async def _scrape_job_details(self, slug: str) -> dict[str, Any] | None:
        """
        Scrape details for a single job.

        Args:
            slug: Job slug (e.g., 'lead-rpg-designer-devsu')

        Returns:
            Job data dictionary or None if failed
        """
        if not self.page:
            return None

        try:
            # Navigate to job detail page
            job_url = f"{self.jobs_url}?category=development&location=anywhere,colombia&job={slug}"
            await self.page.goto(job_url, wait_until="networkidle")

            # Extract job details
            title = await self.page.text_content('h1') or ""
            title = title.strip()

            # Company name - usually in a specific element
            company_elem = await self.page.query_selector('.company-name, [class*="company"]')
            company = await company_elem.text_content() if company_elem else "Unknown"
            company = company.strip()

            # Description - get the main job description
            description_elem = await self.page.query_selector('.job-description, [class*="description"]')
            description = await description_elem.text_content() if description_elem else ""
            description = description.strip()

            # Tags
            tag_elements = await self.page.query_selector_all('.tag, .badge, [class*="tag"]')
            tags = []
            for tag_elem in tag_elements:
                tag_text = await tag_elem.text_content()
                if tag_text:
                    tags.append(tag_text.strip())

            # Location
            location_elem = await self.page.query_selector('[class*="location"]')
            location = await location_elem.text_content() if location_elem else None
            location = location.strip() if location else None

            # Extract "Apply for this position" URL
            apply_button = await self.page.query_selector('a:has-text("Apply"), a[href*="apply"]')
            apply_url = await apply_button.get_attribute('href') if apply_button else None

            # If apply_url is relative, make it absolute
            if apply_url and not apply_url.startswith('http'):
                apply_url = f"{self.base_url}{apply_url}"

            # Full job URL
            full_url = f"{self.base_url}/jobs/{slug}"

            return {
                "id": slug,
                "url": apply_url or full_url,  # Prefer apply URL, fallback to job page
                "title": title,
                "company": company,
                "description": description,
                "requirements": None,  # Could extract if there's a separate section
                "location": location,
                "salary": None,  # Could extract if available
                "tags": tags,
                "raw_data": {
                    "slug": slug,
                    "job_page_url": full_url,
                    "apply_url": apply_url,
                }
            }

        except Exception as e:
            print(f"❌ Failed to scrape job {slug}: {str(e)}")
            return None

    async def scrape(self, since_days: int = 1) -> list[dict[str, Any]]:
        """
        Scrape jobs from Working Nomads.

        Args:
            since_days: Not used for initial implementation (we scrape all filtered jobs)

        Returns:
            List of normalized job dictionaries
        """
        jobs = []

        try:
            # Launch browser
            print("🚀 Launching browser...")
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
            self.page = await self.browser.new_page()

            # Login
            if not await self.login():
                return jobs

            # Set filters
            await self._set_filters()

            # Load all jobs
            await self._load_all_jobs()

            # Extract job slugs
            slugs = await self._extract_job_slugs()

            # Scrape each job
            print(f"📝 Scraping {len(slugs)} jobs...")
            for i, slug in enumerate(slugs, 1):
                print(f"  [{i}/{len(slugs)}] Scraping {slug}...")

                job_data = await self._scrape_job_details(slug)
                if job_data:
                    normalized_job = self.normalize_job(job_data)
                    jobs.append(normalized_job)

            print(f"✅ Successfully scraped {len(jobs)} jobs!")

        except Exception as e:
            print(f"❌ Scraping failed: {str(e)}")

        finally:
            # Close browser
            if self.browser:
                await self.browser.close()
                print("🔒 Browser closed")

        return jobs

    def get_source_name(self) -> str:
        """Get source name."""
        return "working_nomads"
