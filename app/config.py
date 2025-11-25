"""Application configuration management."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "Zapply"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://zapply:zapply@localhost:5432/zapply"

    # Anthropic API
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5-20250929"

    # Job Sources - Working Nomads
    working_nomads_username: str = ""
    working_nomads_password: str = ""

    # Scheduler
    scheduler_interval_minutes: int = 60
    scraper_initial_days: int = 14  # Fetch last 2 weeks on first run

    # User Profile (legacy - now managed via UI at /profile)
    # These settings are deprecated and no longer used
    user_name: str = ""
    user_email: str = ""
    user_location: str = ""
    user_rate: str = ""

    # Matching Settings
    matching_min_score_threshold: float = 60.0
    matching_log_interval: int = 10  # Log every N jobs
    matching_commit_interval: int = 25  # Commit every N jobs (balance between safety and performance)

    # Application Settings
    max_concurrent_applications: int = 3
    application_delay_seconds: int = 5

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


# Global settings instance
settings = Settings()
