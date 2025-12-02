"""Database models for Zapply."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, DateTime, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now():
    """Get current UTC time - helper for SQLAlchemy default."""
    return datetime.now(timezone.utc).replace(tzinfo=None)  # Returns timezone-naive UTC time for PostgreSQL compatibility


class JobStatus(str, Enum):
    """Job processing status."""

    NEW = "new"
    MATCHED = "matched"
    REJECTED = "rejected"
    APPLIED = "applied"
    FAILED = "failed"
    REPORTED = "reported"


class JobSource(str, Enum):
    """Job source platforms."""

    WORKING_NOMADS = "working_nomads"
    WE_WORK_REMOTELY = "we_work_remotely"
    REMOTIVE = "remotive"


class Job(Base):
    """Job posting from various sources."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Source information
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)

    # Job details
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    company: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requirements: Mapped[Optional[str]] = mapped_column(Text)
    location: Mapped[Optional[str]] = mapped_column(String(200))
    salary: Mapped[Optional[str]] = mapped_column(String(200))
    tags: Mapped[Optional[list]] = mapped_column(JSON)

    # Raw data from source
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON)

    # Processing status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=JobStatus.NEW.value, index=True
    )

    # Matching information
    match_reasoning: Mapped[Optional[str]] = mapped_column(Text)
    match_score: Mapped[Optional[float]] = mapped_column()

    # Application information
    application_data: Mapped[Optional[dict]] = mapped_column(JSON)
    application_error: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )
    matched_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    reported_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    def __repr__(self) -> str:
        return f"<Job {self.id}: {self.title} at {self.company} ({self.status})>"


class UserProfile(Base):
    """User profile and preferences."""

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Basic information
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    location: Mapped[str] = mapped_column(String(200))
    rate: Mapped[str] = mapped_column(String(100))
    linkedin: Mapped[Optional[str]] = mapped_column(String(500))
    github: Mapped[Optional[str]] = mapped_column(String(500))

    # CV file storage (PDF stored as binary data)
    cv_filename: Mapped[Optional[str]] = mapped_column(String(500))
    cv_data: Mapped[Optional[bytes]] = mapped_column(LargeBinary)
    cv_text: Mapped[Optional[str]] = mapped_column(Text)  # Extracted text from CV

    # Custom instructions for AI (user's preferences and requirements)
    custom_instructions: Mapped[Optional[str]] = mapped_column(Text)

    # AI-generated profile data (for matching)
    skills: Mapped[Optional[list]] = mapped_column(JSON)
    preferences: Mapped[Optional[dict]] = mapped_column(JSON)
    ai_generated_summary: Mapped[Optional[str]] = mapped_column(Text)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    def __repr__(self) -> str:
        return f"<UserProfile {self.id}: {self.name}>"


class ApplicationLog(Base):
    """Log of application attempts and results."""

    __tablename__ = "application_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    job_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Application details
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    screenshots: Mapped[Optional[list]] = mapped_column(JSON)

    # AI interaction
    ai_prompts: Mapped[Optional[list]] = mapped_column(JSON)
    ai_responses: Mapped[Optional[list]] = mapped_column(JSON)

    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_seconds: Mapped[Optional[float]] = mapped_column()

    def __repr__(self) -> str:
        return f"<ApplicationLog {self.id}: Job {self.job_id} ({self.status})>"


class RunStatus(str, Enum):
    """Run execution status."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class RunPhase(str, Enum):
    """Phases of a run."""

    SCRAPING = "scraping"
    MATCHING = "matching"
    APPLYING = "applying"
    REPORTING = "reporting"


class RunTriggerType(str, Enum):
    """How a run was triggered."""

    MANUAL = "manual"
    SCHEDULED_DAILY = "scheduled_daily"
    SCHEDULED_HOURLY = "scheduled_hourly"


class Run(Base):
    """Track each execution run of the automation pipeline."""

    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Run metadata
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RunStatus.RUNNING.value, index=True
    )
    phase: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )
    trigger_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RunTriggerType.MANUAL.value, index=True
    )

    # Statistics and logs
    stats: Mapped[Optional[dict]] = mapped_column(JSON)  # Phase-specific stats
    logs: Mapped[Optional[list]] = mapped_column(JSON)  # Log messages with timestamps
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, index=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_seconds: Mapped[Optional[float]] = mapped_column()

    def __repr__(self) -> str:
        return f"<Run {self.id}: {self.phase} ({self.status})>"


class AppSettings(Base):
    """Application settings stored in database."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    def __repr__(self) -> str:
        return f"<AppSettings {self.key}={self.value}>"
