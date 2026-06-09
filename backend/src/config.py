import json
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Jarvis backend configuration. Reads from .env at project root."""

    DATABASE_URL: str = "postgresql+asyncpg://vincent@localhost/jarvis"
    JARVIS_API_KEY: str = "changeme"
    TELEGRAM_BOT_TOKEN: str = ""
    ALLOWED_USER_IDS: str = ""  # Comma-separated string, parsed below
    USER_NAMES: str = "{}"  # JSON string, parsed below
    TIMEZONE: str = "Europe/Amsterdam"

    model_config = {
        "env_file": str(Path(__file__).resolve().parent.parent.parent / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def allowed_user_ids_list(self) -> list[int]:
        """Parse ALLOWED_USER_IDS from comma-separated string to list[int]."""
        if not self.ALLOWED_USER_IDS:
            return []
        return [int(uid.strip()) for uid in self.ALLOWED_USER_IDS.split(",") if uid.strip()]

    @property
    def user_names_dict(self) -> dict[str, str]:
        """Parse USER_NAMES from JSON string to dict."""
        return json.loads(self.USER_NAMES)

    @property
    def sync_database_url(self) -> str:
        """Return a synchronous database URL for scripts."""
        return self.DATABASE_URL.replace("asyncpg", "psycopg2").replace("+asyncpg", "+psycopg2")


_settings: Settings | None = None


def get_settings() -> Settings:
    """Get cached settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
