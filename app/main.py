"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import settings
from app.database import engine
from app.routers import admin, health, jobs, runs, scraper, stats


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    print(f"Starting {settings.app_name} v{__version__}")
    print(f"Database: {settings.database_url.split('@')[-1]}")  # Hide credentials

    # TODO: Start scheduler here
    # TODO: Initialize Playwright browser

    yield

    # Shutdown
    print("Shutting down...")
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="AI-powered remote job application automation system",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Vue.js dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(runs.router, tags=["Runs"])
app.include_router(stats.router, prefix="/api/stats", tags=["Statistics"])
app.include_router(scraper.router, prefix="/api/scraper", tags=["Scraper"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": __version__,
        "message": "AI-powered job application automation",
    }
