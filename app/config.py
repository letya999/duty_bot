from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # Telegram
    telegram_token: Optional[str] = None
    telegram_chat_id: Optional[int] = None

    # Slack
    slack_bot_token: Optional[str] = None
    slack_signing_secret: Optional[str] = None
    slack_channel_id: Optional[str] = None

    # Slack OAuth (for web panel)
    slack_client_id: Optional[str] = None
    slack_client_secret: Optional[str] = None
    slack_redirect_uri: Optional[str] = None

    # Database
    database_url: str

    # Application
    timezone: str = "UTC"
    morning_digest_time: str = "09:00"  # HH:MM format
    reminder_before_minutes: int = 30
    escalation_timeout_minutes: int = 15
    log_level: str = "INFO"

    # Admin configuration
    admin_telegram_ids: str = ""  # Comma-separated IDs
    admin_slack_ids: str = ""     # Comma-separated IDs

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    def get_admin_ids(self, platform: str) -> list[str]:
        """Parse admin IDs from config"""
        if platform == 'telegram':
            return [id.strip() for id in self.admin_telegram_ids.split(',') if id.strip()]
        elif platform == 'slack':
            return [id.strip() for id in self.admin_slack_ids.split(',') if id.strip()]
        return []


@lru_cache()
def get_settings() -> Settings:
    return Settings()
