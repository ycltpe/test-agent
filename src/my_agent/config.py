"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "my-agent"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000
    a2a_port: int = 8001
    anthropic_api_key: str | None = None
    anthropic_base_url: str | None = None
    default_model: str = "claude-3-5-sonnet-20241022"


settings = Settings()
