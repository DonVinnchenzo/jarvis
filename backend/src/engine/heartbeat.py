import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

HEARTBEAT_FILE = Path("/Users/vincent/jarvis/backend/.heartbeat")


def write_heartbeat(tz_name: str = "Europe/Amsterdam") -> None:
    """Write current timestamp to heartbeat file."""
    try:
        tz = ZoneInfo(tz_name)
        now = datetime.now(tz)
        HEARTBEAT_FILE.write_text(now.isoformat())
        logger.info("Heartbeat written: %s", now.isoformat())
    except Exception:
        logger.exception("Failed to write heartbeat")


def read_heartbeat() -> datetime | None:
    """Read last heartbeat timestamp. Returns None if no heartbeat file."""
    try:
        content = HEARTBEAT_FILE.read_text().strip()
        return datetime.fromisoformat(content)
    except (FileNotFoundError, ValueError):
        return None
