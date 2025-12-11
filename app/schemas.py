"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class JobBase(BaseModel):
    """Base job schema."""

    source: str
    source_id: str
    url: str
    title: str
    company: str
    description: str
    requirements: Optional[str] = None
    location: Optional[str] = None
    salary: Optional[str] = None
    tags: Optional[list[str]] = None


class JobCreate(JobBase):
    """Schema for creating a new job."""

    raw_data: Optional[dict[str, Any]] = None


class JobResponse(JobBase):
    """Schema for job response."""

    id: int
    status: str
    matching_source: str = "auto"
    match_reasoning: Optional[str] = None
    match_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    matched_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None
    application_data: Optional[dict[str, Any]] = None
    application_error: Optional[str] = None

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Schema for job list response."""

    jobs: list[JobResponse]
    total: int
    page: int
    page_size: int


class JobStatusUpdate(BaseModel):
    """Schema for updating job status."""

    status: str
    matching_source: Optional[str] = None
    match_reasoning: Optional[str] = None
    match_score: Optional[float] = None
    application_data: Optional[dict[str, Any]] = None
    application_error: Optional[str] = None


class UserProfileResponse(BaseModel):
    """Schema for user profile response."""

    id: int
    cv_filename: Optional[str] = None
    cv_text: Optional[str] = None
    custom_instructions: Optional[str] = None
    skills: Optional[list[str]] = None
    preferences: Optional[dict[str, Any]] = None
    ai_generated_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    """Schema for statistics response."""

    total_jobs: int
    new_jobs: int
    matched_jobs: int
    rejected_jobs: int


class HealthResponse(BaseModel):
    """Schema for health check response."""

    status: str
    version: str
    database: str
    scheduler: str


# =============================================================================
# Scraper Source Schemas
# =============================================================================


class ScraperSourceResponse(BaseModel):
    """Schema for scraper source response."""

    id: int
    name: str
    label: str
    description: Optional[str] = None
    enabled: bool
    priority: int
    credentials_env_prefix: Optional[str] = None
    settings: Optional[dict[str, Any]] = None
    credentials_configured: Optional[dict[str, bool]] = None  # Added dynamically
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScraperSourceUpdate(BaseModel):
    """Schema for updating a scraper source."""

    enabled: Optional[bool] = None
    priority: Optional[int] = None
    settings: Optional[dict[str, Any]] = None


class RegisteredScraperResponse(BaseModel):
    """Schema for registered scraper metadata."""

    name: str
    label: str
    description: str
    requires_login: bool


# =============================================================================
# Source Run Schemas
# =============================================================================


class SourceRunResponse(BaseModel):
    """Schema for source run response."""

    id: int
    run_id: int
    source_name: str
    status: str
    jobs_found: int
    jobs_new: int
    jobs_duplicate: int
    jobs_failed: int
    error_message: Optional[str] = None
    logs: Optional[list[dict[str, Any]]] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    class Config:
        from_attributes = True


class SourceRunListResponse(BaseModel):
    """Schema for list of source runs."""

    source_runs: list[SourceRunResponse]
    total: int


# =============================================================================
# Run Schemas (extended)
# =============================================================================


class RunResponse(BaseModel):
    """Schema for run response with source runs."""

    id: int
    status: str
    phase: str
    trigger_type: str
    stats: Optional[dict[str, Any]] = None
    logs: Optional[list[dict[str, Any]]] = None
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    source_runs: Optional[list[SourceRunResponse]] = None

    class Config:
        from_attributes = True


class RunListResponse(BaseModel):
    """Schema for list of runs."""

    runs: list[RunResponse]
    total: int
    page: int
    page_size: int
