"""Morning Briefing engine -- orchestrates fetch, build, and send."""

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from src.briefing.constants import BRIEFING_TIMEZONE
from src.briefing.divvy import build_divvy_data, fetch_free_bikes, fetch_station_status
from src.briefing.message_builder import (
    build_briefing_message,
    build_on_demand_bikes_message,
    build_on_demand_weather_message,
)
from src.briefing.weather import WeatherData, fetch_weather
from src.config import Settings

logger = logging.getLogger(__name__)


async def _fetch_todays_events(db: AsyncSession, tz_name: str) -> list[str]:
    """Cross-module: get Social Circle events happening today.

    Returns a list of human-readable event strings for the briefing.
    If Social Circle module is not available, returns empty list.
    """
    try:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from src.engine.reminder_engine import ReminderEngine
        from src.models.event import ContactEvent

        tz = ZoneInfo(tz_name)
        today = datetime.now(tz).date()

        stmt = (
            select(ContactEvent)
            .where(ContactEvent.recurring.is_(True))
            .options(
                selectinload(ContactEvent.contact),
                selectinload(ContactEvent.child),
            )
        )
        result = await db.execute(stmt)
        events = result.scalars().all()

        today_events: list[str] = []
        for event in events:
            # _make_occurrence_date signature: (year, month, day)
            occ = ReminderEngine._make_occurrence_date(today.year, event.month, event.day)
            if occ is None:
                continue
            if occ != today:
                continue

            contact_name = event.contact.name if event.contact else "Someone"
            if event.event_type == "birthday":
                age_str = ""
                if event.year is not None:
                    age = today.year - event.year
                    age_str = f" (turns {age})"
                today_events.append(f"\U0001f382 {contact_name}'s birthday{age_str}")
            elif event.event_type == "anniversary":
                label = event.label or f"{contact_name}'s anniversary"
                today_events.append(f"\U0001f48d {label}")
            elif event.event_type == "child_birthday":
                child_name = event.child.name if event.child else "Child"
                age_str = ""
                if event.year is not None:
                    age = today.year - event.year
                    age_str = f" (turns {age})"
                today_events.append(f"\U0001f388 {child_name} ({contact_name}'s child) birthday{age_str}")
            elif event.event_type == "custom":
                label = event.label or f"{contact_name}'s event"
                today_events.append(f"\U0001f4c5 {label}")

        return today_events

    except Exception:
        logger.debug("Could not fetch Social Circle events (module may not be ready)", exc_info=True)
        return []


class BriefingEngine:
    """Orchestrates the morning briefing: fetch data, build messages, send."""

    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def run(self) -> dict:
        """Run the full morning briefing for all users.

        Fetches weather and Divvy data in parallel, builds per-user messages,
        sends via Telegram. Returns a summary dict.
        """
        # Skip on weekends
        tz = ZoneInfo(BRIEFING_TIMEZONE)
        now = datetime.now(tz)
        if now.weekday() in (5, 6):  # Saturday=5, Sunday=6
            logger.info("Skipping morning briefing on weekend (%s)", now.strftime("%A"))
            return {"status": "skipped", "reason": "weekend"}

        # Parallel fetch: weather, station_status, free_bikes
        weather_result, station_result, free_bikes_result = await asyncio.gather(
            fetch_weather(),
            fetch_station_status(),
            fetch_free_bikes(),
            return_exceptions=True,
        )

        # Unwrap results (gather with return_exceptions=True returns exceptions as values)
        weather: WeatherData | None = None
        if isinstance(weather_result, WeatherData):
            weather = weather_result
        elif isinstance(weather_result, Exception):
            logger.error("Weather fetch raised exception: %s", weather_result)

        station_status = None
        if isinstance(station_result, dict):
            station_status = station_result
        elif isinstance(station_result, Exception):
            logger.error("Station status fetch raised exception: %s", station_result)

        free_bikes = None
        if not isinstance(free_bikes_result, Exception):
            free_bikes = free_bikes_result
        else:
            logger.error("Free bikes fetch raised exception: %s", free_bikes_result)

        # Build DivvyData from raw results
        divvy = build_divvy_data(station_status, free_bikes)

        # Cross-module: get today's Social Circle events
        todays_events = await _fetch_todays_events(self.db, self.settings.TIMEZONE)

        # Build and send per-user messages
        from src.engine.telegram_sender import send_to_user

        user_names = self.settings.user_names_dict
        sent_count = 0
        errors: list[str] = []

        for user_id_str, user_name in user_names.items():
            user_id = int(user_id_str)
            message = build_briefing_message(user_name, weather, divvy, todays_events)

            try:
                await send_to_user(message, user_id, self.settings)
                sent_count += 1
                logger.info("Sent morning briefing to %s (%s)", user_name, user_id)
            except Exception as e:
                logger.exception("Failed to send briefing to %s", user_name)
                errors.append(f"Send failed for {user_name}: {e}")

        status = "completed" if not errors else "completed_with_errors"
        return {
            "status": status,
            "sent": sent_count,
            "weather_available": weather is not None,
            "divvy_available": station_status is not None,
            "todays_events": len(todays_events),
            "errors": errors,
        }

    async def get_briefing_for_user(self, user_name: str) -> str:
        """Generate an on-demand briefing for a single user (not sent, just returned)."""
        weather_result, station_result, free_bikes_result = await asyncio.gather(
            fetch_weather(),
            fetch_station_status(),
            fetch_free_bikes(),
            return_exceptions=True,
        )

        weather = weather_result if isinstance(weather_result, WeatherData) else None
        station_status = station_result if isinstance(station_result, dict) else None
        free_bikes = free_bikes_result if not isinstance(free_bikes_result, Exception) else None

        divvy = build_divvy_data(station_status, free_bikes)
        todays_events = await _fetch_todays_events(self.db, self.settings.TIMEZONE)

        return build_briefing_message(user_name, weather, divvy, todays_events)

    @staticmethod
    async def get_bikes_status() -> str:
        """Get current Divvy status for all tracked stations (on-demand)."""
        station_result, free_bikes_result = await asyncio.gather(
            fetch_station_status(),
            fetch_free_bikes(),
            return_exceptions=True,
        )

        station_status = station_result if isinstance(station_result, dict) else None
        free_bikes = free_bikes_result if not isinstance(free_bikes_result, Exception) else None
        divvy = build_divvy_data(station_status, free_bikes)

        return build_on_demand_bikes_message(divvy)

    @staticmethod
    async def get_weather_status() -> str:
        """Get current weather (on-demand)."""
        weather = await fetch_weather()
        return build_on_demand_weather_message(weather)
