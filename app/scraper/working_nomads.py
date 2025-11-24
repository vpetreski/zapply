"""Working Nomads job scraper."""

from typing import Any

from app.config import settings
from app.scraper.base import BaseScraper


class WorkingNomadsScraper(BaseScraper):
    """Scraper for Working Nomads job board."""

    def __init__(self) -> None:
        """Initialize Working Nomads scraper."""
        self.username = settings.working_nomads_username
        self.password = settings.working_nomads_password
        self.base_url = "https://www.workingnomads.com"

    async def login(self) -> bool:
        """
        Login to Working Nomads.

        TODO: Implement Playwright-based login
        """
        # TODO: Implement login with Playwright
        return True

    async def scrape(self, since_days: int = 1) -> list[dict[str, Any]]:
        """
        Scrape jobs from Working Nomads.

        Args:
            since_days: Number of days to look back for jobs

        Returns:
            List of normalized job dictionaries

        TODO: Implement Playwright-based scraping
        """
        # TODO: Implement scraping with Playwright
        # 1. Navigate to Working Nomads
        # 2. Login if needed
        # 3. Filter for jobs from last N days
        # 4. Extract job data
        # 5. Normalize and return

        return []

    def get_source_name(self) -> str:
        """Get source name."""
        return "working_nomads"
