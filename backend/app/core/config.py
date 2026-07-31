from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from .env
    """

    app_name: str
    app_version: str

    environment: str

    database_url: str

    jwt_secret: str
    jwt_algorithm: str
    access_token_expire_minutes: int

    google_client_id: str
    google_client_secret: str
    frontend_url: str = "http://localhost:3000"
    gemini_api_key: str | None = None
    # "gemini-2.0-flash" and "gemini-2.5-flash*" return 429 (zero free-tier
    # quota) or 404 ("no longer available to new users") for newer projects.
    # "gemini-flash-latest" is Google's maintained alias to whatever current
    # flash model is actually available -- confirmed working.
    gemini_model: str = "gemini-flash-latest"
    gemini_embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 1536

    # Both sender and recipient for alert/briefing emails -- unset means the
    # notification service no-ops (see notification_service.NotificationService).
    ses_sender_email: str | None = None
    aws_region: str = "ap-south-1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
