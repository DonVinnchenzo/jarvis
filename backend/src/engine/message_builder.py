import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

from src.models.event import ContactEvent
from src.models.note import ContactNote
from src.models.reminder import ReminderConfig

logger = logging.getLogger(__name__)

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

EVENT_EMOJIS = {
    "birthday": "\U0001f382",       # birthday cake
    "anniversary": "\U0001f48d",    # ring
    "child_birthday": "\U0001f388", # balloon
    "custom": "\U0001f4c5",         # calendar
}


def _format_relative_time(dt: datetime, tz_name: str = "Europe/Amsterdam") -> str:
    """Format a datetime as a relative time string like '3 weeks ago'."""
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)

    # Make dt timezone-aware if it isn't already
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)

    delta = now - dt
    days = delta.days

    if days < 1:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 7:
        return f"{days} days ago"
    if days < 14:
        return "1 week ago"
    if days < 30:
        weeks = days // 7
        return f"{weeks} weeks ago"
    if days < 60:
        return "1 month ago"
    if days < 365:
        months = days // 30
        return f"{months} months ago"
    years = days // 365
    if years == 1:
        return "1 year ago"
    return f"{years} years ago"


def _get_event_description(event: ContactEvent, occurrence_date: date) -> str:
    """Get a human-readable description of the event."""
    contact_name = event.contact.name if event.contact else "Someone"

    if event.event_type == "birthday":
        desc = f"{contact_name}'s birthday"
        if event.year is not None:
            age = occurrence_date.year - event.year
            desc += f" (turns {age})"
        return desc

    if event.event_type == "anniversary":
        if event.label:
            desc = event.label
        else:
            desc = f"{contact_name}'s anniversary"
        if event.year is not None:
            years = occurrence_date.year - event.year
            desc += f" ({years} years)"
        return desc

    if event.event_type == "child_birthday":
        child_name = event.child.name if event.child else "Child"
        desc = f"{child_name} ({contact_name}'s child)'s birthday"
        if event.year is not None:
            age = occurrence_date.year - event.year
            desc = f"{child_name} ({contact_name}'s child) turns {age}"
        return desc

    # custom
    if event.label:
        return event.label
    return f"{contact_name}'s event"


def _format_date(d: date) -> str:
    """Format a date as 'Month Day'."""
    return f"{MONTH_NAMES[d.month]} {d.day}"


def _build_notes_section(notes: list[ContactNote], tz_name: str = "Europe/Amsterdam") -> str:
    """Build the notes section of a reminder message (last 1-2 notes)."""
    if not notes:
        return ""

    # Sort by most recent first, take at most 2
    sorted_notes = sorted(notes, key=lambda n: n.created_at, reverse=True)[:2]
    lines = []
    for note in sorted_notes:
        time_ago = _format_relative_time(note.created_at, tz_name)
        # Truncate long notes
        text = note.note_text
        if len(text) > 100:
            text = text[:97] + "..."
        lines.append(f"\U0001f4dd {text} ({time_ago})")

    return "\n".join(lines)


def build_reminder_message(
    event: ContactEvent,
    config: ReminderConfig,
    occurrence_date: date,
    recent_notes: list[ContactNote] | None = None,
    tz_name: str = "Europe/Amsterdam",
) -> str:
    """Build a reminder message for an event.

    Templates vary by days_before:
    - 0 (day-of): "Today is {description}! {emoji}"
    - 1 (tomorrow): "Reminder: {description} is tomorrow ({date})! {emoji}"
    - 2+ days: "Hey! {description} is in {N} days ({date}). Any gift ideas? {emoji}"
    """
    emoji = EVENT_EMOJIS.get(event.event_type, "\U0001f4c5")
    description = _get_event_description(event, occurrence_date)
    date_str = _format_date(occurrence_date)
    notes = recent_notes or []

    if config.days_before == 0:
        # Day-of
        contact_name = event.contact.name if event.contact else "them"
        msg = f"Today is {description}! Happy birthday {contact_name}! {emoji}"
        if event.event_type == "anniversary":
            msg = f"Today is {description}! {emoji}"
        elif event.event_type == "child_birthday":
            msg = f"Today is {description}! {emoji}"
        elif event.event_type == "custom":
            msg = f"Today is {description}! {emoji}"
    elif config.days_before == 1:
        # Tomorrow
        msg = f"Reminder: {description} is tomorrow ({date_str})! {emoji}"
    else:
        # 2+ days out
        msg = f"Hey! {description} is in {config.days_before} days ({date_str}). Any gift ideas? {emoji}"

    # Append notes section
    notes_section = _build_notes_section(notes, tz_name)
    if notes_section:
        msg += f"\n\n{notes_section}"

    return msg
