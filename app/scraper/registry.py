"""Scraper registry for dynamic source management."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.scraper.base import BaseScraper


class ScraperRegistry:
    """
    Registry for scraper implementations.

    This registry allows scrapers to self-register using a decorator,
    enabling dynamic discovery and instantiation of scrapers at runtime.

    Example usage:
        @ScraperRegistry.register("my_source")
        class MySourceScraper(BaseScraper):
            ...

        # Later, to create an instance:
        scraper = ScraperRegistry.create_instance("my_source", credentials={...})
    """

    _scrapers: dict[str, type["BaseScraper"]] = {}

    @classmethod
    def register(cls, name: str):
        """
        Decorator to register a scraper class.

        Args:
            name: The unique identifier for this scraper source (e.g., "working_nomads")

        Returns:
            Decorator function that registers the class
        """
        def decorator(scraper_class: type["BaseScraper"]):
            if name in cls._scrapers:
                raise ValueError(f"Scraper '{name}' is already registered")
            cls._scrapers[name] = scraper_class
            return scraper_class
        return decorator

    @classmethod
    def get(cls, name: str) -> type["BaseScraper"] | None:
        """
        Get a scraper class by name.

        Args:
            name: The scraper source name

        Returns:
            The scraper class or None if not found
        """
        return cls._scrapers.get(name)

    @classmethod
    def get_all(cls) -> dict[str, type["BaseScraper"]]:
        """
        Get all registered scrapers.

        Returns:
            Dictionary mapping source names to scraper classes
        """
        return cls._scrapers.copy()

    @classmethod
    def get_names(cls) -> list[str]:
        """
        Get all registered scraper names.

        Returns:
            List of registered source names
        """
        return list(cls._scrapers.keys())

    @classmethod
    def create_instance(
        cls,
        name: str,
        credentials: dict | None = None,
        settings: dict | None = None
    ) -> "BaseScraper | None":
        """
        Create a scraper instance by name.

        Args:
            name: The scraper source name
            credentials: Optional credentials dict (username, password, api_key, etc.)
            settings: Optional settings dict for the scraper

        Returns:
            A new scraper instance or None if scraper not found
        """
        scraper_class = cls.get(name)
        if scraper_class:
            return scraper_class(credentials=credentials, settings=settings)
        return None

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        Check if a scraper is registered.

        Args:
            name: The scraper source name

        Returns:
            True if scraper is registered
        """
        return name in cls._scrapers

    @classmethod
    def clear(cls) -> None:
        """
        Clear all registered scrapers.

        This is mainly useful for testing.
        """
        cls._scrapers.clear()
