"""Seed default ReminderConfig rows (7, 1, 0 days_before).

Usage:
    cd /Users/vincent/jarvis/backend
    source .venv/bin/activate
    python scripts/seed_reminders.py
"""

import sys
from pathlib import Path

# Ensure the backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src.config import get_settings


def seed_reminders() -> None:
    """Insert 3 default global ReminderConfig rows idempotently."""
    settings = get_settings()

    # Use a sync connection for simplicity in scripts
    sync_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url)

    defaults = [7, 1, 0]

    with Session(engine) as session:
        for days_before in defaults:
            # Check if this default config already exists (global = event_id IS NULL)
            result = session.execute(
                text(
                    "SELECT id FROM reminder_configs "
                    "WHERE event_id IS NULL AND days_before = :days_before"
                ),
                {"days_before": days_before},
            )
            existing = result.fetchone()

            if existing:
                print(f"  [skip] Global reminder config days_before={days_before} already exists")
            else:
                session.execute(
                    text(
                        "INSERT INTO reminder_configs (id, event_id, days_before, enabled) "
                        "VALUES (gen_random_uuid(), NULL, :days_before, true)"
                    ),
                    {"days_before": days_before},
                )
                print(f"  [created] Global reminder config days_before={days_before}")

        session.commit()

    print("Seed complete.")
    engine.dispose()


if __name__ == "__main__":
    seed_reminders()
