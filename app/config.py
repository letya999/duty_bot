from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Telegram
    telegram_token: str

    # Slack
    slack_bot_token: str
    slack_signing_secret: str

    # Database
    database_url: str

    # Application
    timezone: str = "UTC"
    morning_digest_time: str = "09:00"  # HH:MM format
    reminder_before_minutes: int = 30
    escalation_timeout_minutes: int = 15
    log_level: str = "INFO"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
