"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app import __version__
from app.config import settings
from app.database import engine
from app.routers import admin, health, jobs, profile, runs, scraper, stats
from app.services.scheduler_service import start_scheduler, stop_scheduler, get_scheduler_status
from app.utils import log_to_console

# Configure logging - simple format for console output
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{__version__}")
    logger.info(f"Database: {settings.database_url.split('@')[-1]}")  # Hide credentials

    # Validate configuration
    if not settings.anthropic_api_key:
        logger.warning("⚠️  ANTHROPIC_API_KEY not configured - AI matching will not work")
        logger.warning("⚠️  Set ANTHROPIC_API_KEY in .env to enable job matching")
        log_to_console("⚠️  ANTHROPIC_API_KEY not configured - AI matching will not work")
    else:
        logger.info("✓ Anthropic API key configured")
        logger.info(f"✓ API key length: {len(settings.anthropic_api_key)} characters")
        logger.info(f"✓ Anthropic model: {settings.anthropic_model}")

    # Start scheduler
    try:
        start_scheduler()
        status = get_scheduler_status()
        if status["running"]:
            logger.info(f"✓ Scheduler started with {len(status['jobs'])} configured jobs")
            for job in status["jobs"]:
                logger.info(f"  - {job['name']}: next run at {job['next_run_time']}")
        else:
            logger.warning("⚠️  Scheduler failed to start")
    except Exception as e:
        logger.error(f"❌ Failed to start scheduler: {e}")

    # TODO: Initialize Playwright browser

    yield

    # Shutdown
    logger.info("Shutting down...")

    # Stop scheduler
    try:
        stop_scheduler()
        logger.info("✓ Scheduler stopped")
    except Exception as e:
        logger.error(f"❌ Error stopping scheduler: {e}")

    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="AI-powered remote job application automation system",
    lifespan=lifespan,
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
app.include_router(profile.router, prefix="/api/profile", tags=["Profile"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": __version__,
        "message": "AI-powered job application automation",
    }
