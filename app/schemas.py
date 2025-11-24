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
    match_reasoning: Optional[str] = None
    match_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    matched_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None

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
    match_reasoning: Optional[str] = None
    match_score: Optional[float] = None
    application_data: Optional[dict[str, Any]] = None
    application_error: Optional[str] = None


class UserProfileResponse(BaseModel):
    """Schema for user profile response."""

    id: int
    name: str
    email: str
    location: str
    rate: str
    cv_path: str
    skills: Optional[list[str]] = None
    preferences: Optional[dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    """Schema for statistics response."""

    total_jobs: int
    new_jobs: int
    matched_jobs: int
    rejected_jobs: int
    applied_jobs: int
    failed_jobs: int
    success_rate: float = Field(description="Percentage of successful applications")


class HealthResponse(BaseModel):
    """Schema for health check response."""

    status: str
    version: str
    database: str
    scheduler: str
