"""Service for managing scraper sources."""

import os

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ScraperSource
from app.scraper import ScraperRegistry


async def get_all_sources(db: AsyncSession) -> list[ScraperSource]:
    """
    Get all scraper sources from database.

    Args:
        db: Database session

    Returns:
        List of all ScraperSource records ordered by priority
    """
    result = await db.execute(
        select(ScraperSource).order_by(ScraperSource.priority, ScraperSource.name)
    )
    return list(result.scalars().all())


async def get_enabled_sources(db: AsyncSession) -> list[ScraperSource]:
    """
    Get all enabled scraper sources, ordered by priority.

    Args:
        db: Database session

    Returns:
        List of enabled ScraperSource records ordered by priority (lower first)
    """
    result = await db.execute(
        select(ScraperSource)
        .where(ScraperSource.enabled == True)  # noqa: E712
        .order_by(ScraperSource.priority, ScraperSource.name)
    )
    return list(result.scalars().all())


async def get_source_by_name(db: AsyncSession, name: str) -> ScraperSource | None:
    """
    Get a specific scraper source by name.

    Args:
        db: Database session
        name: Source name (e.g., "working_nomads")

    Returns:
        ScraperSource or None if not found
    """
    result = await db.execute(
        select(ScraperSource).where(ScraperSource.name == name)
    )
    return result.scalar_one_or_none()


async def update_source(
    db: AsyncSession,
    name: str,
    enabled: bool | None = None,
    priority: int | None = None,
    settings: dict | None = None
) -> ScraperSource | None:
    """
    Update a scraper source.

    Args:
        db: Database session
        name: Source name
        enabled: New enabled status (optional)
        priority: New priority (optional)
        settings: New settings dict (optional)

    Returns:
        Updated ScraperSource or None if not found
    """
    source = await get_source_by_name(db, name)
    if not source:
        return None

    if enabled is not None:
        source.enabled = enabled
    if priority is not None:
        source.priority = priority
    if settings is not None:
        source.settings = settings

    await db.commit()
    await db.refresh(source)
    return source


def get_source_credentials(source: ScraperSource) -> dict[str, str]:
    """
    Get credentials for a source from environment variables.

    The source's credentials_env_prefix determines which env vars to read.
    For example, prefix="WORKING_NOMADS" will look for:
    - WORKING_NOMADS_USERNAME
    - WORKING_NOMADS_PASSWORD

    Args:
        source: ScraperSource with credentials_env_prefix

    Returns:
        Dict with credentials (may have empty values if env vars not set)
    """
    prefix = source.credentials_env_prefix
    if not prefix:
        return {}

    return {
        "username": os.getenv(f"{prefix}_USERNAME", ""),
        "password": os.getenv(f"{prefix}_PASSWORD", ""),
        "api_key": os.getenv(f"{prefix}_API_KEY", ""),
        "token": os.getenv(f"{prefix}_TOKEN", ""),
    }


def check_source_credentials(source: ScraperSource) -> dict[str, bool]:
    """
    Check which credentials are configured for a source.

    Only checks credentials that the scraper actually requires.

    Args:
        source: ScraperSource to check

    Returns:
        Dict with credential name -> configured (True/False)
    """
    # Get required credentials from scraper class
    scraper_class = ScraperRegistry.get(source.name)
    if not scraper_class:
        return {}

    required = getattr(scraper_class, "REQUIRED_CREDENTIALS", [])
    if not required:
        return {}

    credentials = get_source_credentials(source)
    return {
        key: bool(credentials.get(key))
        for key in required
    }


def get_registered_scrapers() -> list[dict]:
    """
    Get metadata for all registered scraper classes.

    Returns:
        List of dicts with scraper metadata (name, label, description, requires_login)
    """
    result = []
    for name, scraper_class in ScraperRegistry.get_all().items():
        result.append(scraper_class.get_metadata())
    return result


async def sync_sources_with_registry(db: AsyncSession) -> dict[str, list[str]]:
    """
    Synchronize database sources with registered scrapers.

    This ensures that:
    1. All registered scrapers have a corresponding database record
    2. Database records for unregistered scrapers are flagged

    Args:
        db: Database session

    Returns:
        Dict with 'added' and 'orphaned' source names
    """
    registered_names = set(ScraperRegistry.get_names())
    db_sources = await get_all_sources(db)
    db_names = {s.name for s in db_sources}

    added = []
    orphaned = []

    # Find registered scrapers without DB records
    for name in registered_names - db_names:
        scraper_class = ScraperRegistry.get(name)
        if scraper_class:
            metadata = scraper_class.get_metadata()
            source = ScraperSource(
                name=metadata["name"],
                label=metadata["label"],
                description=metadata["description"],
                credentials_env_prefix=metadata.get("credentials_env_prefix", ""),
                enabled=True,  # New sources start enabled by default
                priority=100,
            )
            db.add(source)
            added.append(name)

    # Find DB records without registered scrapers
    for name in db_names - registered_names:
        orphaned.append(name)

    if added:
        await db.commit()

    return {"added": added, "orphaned": orphaned}
