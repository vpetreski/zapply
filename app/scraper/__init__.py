"""Job scraper module."""

from app.scraper.base import BaseScraper
from app.scraper.registry import ScraperRegistry

# Import scraper implementations to trigger registration
# Each scraper uses @ScraperRegistry.register() decorator
from app.scraper.working_nomads import WorkingNomadsScraper
from app.scraper.weworkremotely import WeWorkRemotelyScraper

__all__ = ["BaseScraper", "ScraperRegistry", "WorkingNomadsScraper", "WeWorkRemotelyScraper"]
