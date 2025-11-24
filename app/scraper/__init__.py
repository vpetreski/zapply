"""Job scraper module."""

from app.scraper.base import BaseScraper
from app.scraper.working_nomads import WorkingNomadsScraper

__all__ = ["BaseScraper", "WorkingNomadsScraper"]
