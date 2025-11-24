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

    # Job Sources - Working Nomads
    working_nomads_username: str = ""
    working_nomads_password: str = ""

    # Scheduler
    scheduler_interval_minutes: int = 60
    scraper_initial_days: int = 14  # Fetch last 2 weeks on first run

    # User Profile
    user_name: str = "Vanja Petreski"
    user_email: str = "vanja@petreski.co"
    user_location: str = "Colombia"
    user_rate: str = "$10,000/month"
    user_cv_path: str = "docs/Resume-Vanja-Petreski.pdf"

    # Application Settings
    max_concurrent_applications: int = 3
    application_delay_seconds: int = 5

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


# Global settings instance
settings = Settings()
