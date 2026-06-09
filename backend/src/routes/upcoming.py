import calendar
import logging
from datetime import date
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config import get_settings
from src.database import get_db
from src.models.event import ContactEvent
from src.schemas.upcoming import UpcomingEvent, UpcomingResponse

logger = logging.getLogger(__name__)

router = APIRouter()

MONTH_NAMES = [
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def _make_occurrence_date(year: int, month: int, day: int) -> date | None:
    """Create a date, handling Feb 29 in non-leap years by falling back to Feb 28."""
    if month == 2 and day == 29:
        if not calendar.isleap(year):
            return date(year, 2, 28)
        return date(year, 2, 29)
    try:
        return date(year, month, day)
    except ValueError:
        # Invalid date (e.g., June 31)
        logger.warning("Invalid date: %d-%02d-%02d, skipping", year, month, day)
        return None


@router.get("/upcoming", response_model=UpcomingResponse)
async def get_upcoming(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to look ahead"),
    db: AsyncSession = Depends(get_db),
):
    """Get upcoming events within N days."""
    settings = get_settings()
    tz = ZoneInfo(settings.TIMEZONE)
    today = date.today() if settings.TIMEZONE == "UTC" else _get_today(tz)

    # Query all recurring events with their contacts eagerly loaded
    stmt = (
        select(ContactEvent)
        .where(ContactEvent.recurring.is_(True))
        .options(selectinload(ContactEvent.contact))
    )
    result = await db.execute(stmt)
    events = result.scalars().all()

    upcoming: list[UpcomingEvent] = []

    for event in events:
        # Calculate occurrences for this year and next year
        for year in [today.year, today.year + 1]:
            occ = _make_occurrence_date(year, event.month, event.day)
            if occ is None:
                continue

            delta = (occ - today).days
            if delta < 0:
                continue
            if delta > days:
                continue

            # Calculate age if birth year is known
            age = None
            if event.year is not None:
                age = occ.year - event.year

            # Build display label
            label = event.label
            if not label:
                if event.event_type == "birthday":
                    label = f"{event.contact.name}'s birthday"
                elif event.event_type == "anniversary":
                    label = f"{event.contact.name}'s anniversary"
                elif event.event_type == "child_birthday":
                    label = f"Child's birthday ({event.contact.name})"
                else:
                    label = f"{event.contact.name}'s event"

            date_display = f"{MONTH_NAMES[occ.month]} {occ.day}"

            upcoming.append(
                UpcomingEvent(
                    contact_name=event.contact.name,
                    contact_id=event.contact_id,
                    event_type=event.event_type,
                    label=label,
                    day=event.day,
                    month=event.month,
                    year=event.year,
                    days_until=delta,
                    date_display=date_display,
                    age=age,
                )
            )

    # Sort by soonest first
    upcoming.sort(key=lambda e: e.days_until)

    # Deduplicate: same contact+event_type should only appear once (nearest occurrence)
    seen = set()
    deduped: list[UpcomingEvent] = []
    for e in upcoming:
        key = (e.contact_id, e.event_type, e.day, e.month)
        if key not in seen:
            seen.add(key)
            deduped.append(e)

    return UpcomingResponse(events=deduped, total=len(deduped))


def _get_today(tz: ZoneInfo) -> date:
    """Get today's date in the specified timezone."""
    from datetime import datetime

    return datetime.now(tz).date()
