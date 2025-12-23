from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", case_sensitive=False)

    # Telegram
    telegram_token: Optional[str] = None
    telegram_chat_id: Optional[int] = None

    # Slack
    slack_bot_token: Optional[str] = None
    slack_signing_secret: Optional[str] = None
    slack_channel_id: Optional[str] = None

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


@lru_cache()
def get_settings() -> Settings:
    return Settings()
