"""Base scraper interface."""

from abc import ABC, abstractmethod
from typing import Any


class BaseScraper(ABC):
    """Base class for all job scrapers."""

    @abstractmethod
    async def scrape(self, since_days: int = 1) -> list[dict[str, Any]]:
        """
        Scrape jobs from the source.

        Args:
            since_days: Number of days to look back for jobs

        Returns:
            List of job dictionaries in standardized format
        """
        pass

    @abstractmethod
    async def login(self) -> bool:
        """
        Login to the job source if required.

        Returns:
            True if login successful, False otherwise
        """
        pass

    def normalize_job(self, raw_job: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize job data to internal format.

        Args:
            raw_job: Raw job data from source

        Returns:
            Normalized job dictionary
        """
        return {
            "source": self.get_source_name(),
            "source_id": raw_job.get("id", ""),
            "url": raw_job.get("url", ""),
            "title": raw_job.get("title", ""),
            "company": raw_job.get("company", ""),
            "description": raw_job.get("description", ""),
            "requirements": raw_job.get("requirements"),
            "location": raw_job.get("location"),
            "salary": raw_job.get("salary"),
            "tags": raw_job.get("tags", []),
            "raw_data": raw_job,
        }

    @abstractmethod
    def get_source_name(self) -> str:
        """Get the name of this job source."""
        pass
