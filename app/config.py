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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Strip whitespace from API key
        if self.anthropic_api_key:
            self.anthropic_api_key = self.anthropic_api_key.strip()

    # Job Sources - Working Nomads
    working_nomads_username: str = ""
    working_nomads_password: str = ""

    # Matching Settings
    matching_min_score_threshold: float = 60.0
    matching_log_interval: int = 1  # Log every job for real-time UI updates

    # Authentication
    admin_email: str = ""
    admin_password: str = ""
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 43200  # 30 days

    # CORS - comma-separated list of allowed origins for production
    cors_origins: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


# Global settings instance
settings = Settings()
