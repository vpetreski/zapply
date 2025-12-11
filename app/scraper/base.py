"""Base scraper interface."""

from abc import ABC, abstractmethod
from typing import Any


class BaseScraper(ABC):
    """
    Base class for all job scrapers.

    Subclasses should:
    1. Set class-level metadata (SOURCE_NAME, SOURCE_LABEL, etc.)
    2. Use @ScraperRegistry.register decorator
    3. Implement scrape() and login() methods
    """

    # Class-level metadata - override in subclasses
    SOURCE_NAME: str = ""
    SOURCE_LABEL: str = ""
    SOURCE_DESCRIPTION: str = ""
    REQUIRES_LOGIN: bool = False

    def __init__(
        self,
        credentials: dict[str, str] | None = None,
        settings: dict[str, Any] | None = None
    ):
        """
        Initialize scraper with credentials and settings.

        Args:
            credentials: Dict with credentials (e.g., username, password, api_key)
            settings: Dict with scraper-specific settings (e.g., filters, limits)
        """
        self.credentials = credentials or {}
        self.settings = settings or {}

    @abstractmethod
    async def scrape(self, since_days: int = 1, **kwargs) -> list[dict[str, Any]]:
        """
        Scrape jobs from the source.

        Args:
            since_days: Number of days to look back for jobs
            **kwargs: Additional arguments (progress_callback, job_limit, existing_slugs, etc.)

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
            Normalized job dictionary ready for database insertion
        """
        return {
            "source": self.get_source_name(),
            "source_id": raw_job.get("id", ""),
            "url": raw_job.get("url", ""),
            "resolved_url": raw_job.get("resolved_url"),  # For cross-source dedup
            "title": raw_job.get("title", ""),
            "company": raw_job.get("company", ""),
            "description": raw_job.get("description", ""),
            "requirements": raw_job.get("requirements"),
            "location": raw_job.get("location"),
            "salary": raw_job.get("salary"),
            "tags": raw_job.get("tags", []),
            "raw_data": raw_job,
        }

    def get_source_name(self) -> str:
        """Get the name of this job source."""
        return self.SOURCE_NAME

    def get_source_label(self) -> str:
        """Get the display label of this job source."""
        return self.SOURCE_LABEL

    def get_source_description(self) -> str:
        """Get the description of this job source."""
        return self.SOURCE_DESCRIPTION

    @classmethod
    def get_metadata(cls) -> dict[str, Any]:
        """
        Get scraper metadata for API responses.

        Returns:
            Dict with source name, label, description, and login requirement
        """
        return {
            "name": cls.SOURCE_NAME,
            "label": cls.SOURCE_LABEL,
            "description": cls.SOURCE_DESCRIPTION,
            "requires_login": cls.REQUIRES_LOGIN,
        }
