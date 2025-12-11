"""API routes for scraper source management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import get_current_user, User
from app.schemas import (
    RegisteredScraperResponse,
    ScraperSourceResponse,
    ScraperSourceUpdate,
)
from app.services.source_service import (
    check_source_credentials,
    get_all_sources,
    get_registered_scrapers,
    get_source_by_name,
    sync_sources_with_registry,
    update_source,
)

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("", response_model=list[ScraperSourceResponse])
async def list_sources(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[ScraperSourceResponse]:
    """
    List all scraper sources.

    Returns sources from database with credentials status.
    """
    sources = await get_all_sources(db)

    result = []
    for source in sources:
        source_dict = {
            "id": source.id,
            "name": source.name,
            "label": source.label,
            "description": source.description,
            "enabled": source.enabled,
            "priority": source.priority,
            "credentials_env_prefix": source.credentials_env_prefix,
            "settings": source.settings,
            "credentials_configured": check_source_credentials(source),
            "created_at": source.created_at,
            "updated_at": source.updated_at,
        }
        result.append(ScraperSourceResponse(**source_dict))

    return result


@router.get("/registered", response_model=list[RegisteredScraperResponse])
async def list_registered_scrapers(
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[RegisteredScraperResponse]:
    """
    List all registered scraper classes.

    These are scrapers available in the code that can be enabled in the database.
    """
    scrapers = get_registered_scrapers()
    return [RegisteredScraperResponse(**s) for s in scrapers]


@router.post("/sync")
async def sync_sources(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Sync database sources with registered scrapers.

    Creates database records for any registered scrapers that don't have one.
    Also reports orphaned database records (scrapers no longer in code).
    """
    result = await sync_sources_with_registry(db)
    return {
        "added": result["added"],
        "orphaned": result["orphaned"],
        "message": f"Added {len(result['added'])} new sources. {len(result['orphaned'])} orphaned sources found."
    }


@router.get("/{name}", response_model=ScraperSourceResponse)
async def get_source(
    name: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ScraperSourceResponse:
    """
    Get a specific scraper source by name.
    """
    source = await get_source_by_name(db, name)
    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{name}' not found")

    return ScraperSourceResponse(
        id=source.id,
        name=source.name,
        label=source.label,
        description=source.description,
        enabled=source.enabled,
        priority=source.priority,
        credentials_env_prefix=source.credentials_env_prefix,
        settings=source.settings,
        credentials_configured=check_source_credentials(source),
        created_at=source.created_at,
        updated_at=source.updated_at,
    )


@router.patch("/{name}", response_model=ScraperSourceResponse)
async def update_source_endpoint(
    name: str,
    update_data: ScraperSourceUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ScraperSourceResponse:
    """
    Update a scraper source.

    Can update: enabled, priority, settings.
    """
    source = await update_source(
        db,
        name,
        enabled=update_data.enabled,
        priority=update_data.priority,
        settings=update_data.settings,
    )

    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{name}' not found")

    return ScraperSourceResponse(
        id=source.id,
        name=source.name,
        label=source.label,
        description=source.description,
        enabled=source.enabled,
        priority=source.priority,
        credentials_env_prefix=source.credentials_env_prefix,
        settings=source.settings,
        credentials_configured=check_source_credentials(source),
        created_at=source.created_at,
        updated_at=source.updated_at,
    )
