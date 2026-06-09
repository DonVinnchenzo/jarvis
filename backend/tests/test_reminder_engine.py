"""Tests for the proactive reminder engine.

15 tests: 7-day, 1-day, day-of reminders, year wrap, Feb 29, idempotency,
note surfacing, multiple events, disabled config, message format,
age calculation in message, no configs, non-recurring skipped,
multiple configs fire for same event, and empty database.
"""

import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.engine.reminder_engine import ReminderEngine
from src.models.child import ContactChild
from src.models.contact import Contact
from src.models.event import ContactEvent
from src.models.note import ContactNote
from src.models.reminder import ReminderConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(**overrides) -> Settings:
    """Create a minimal Settings object for tests."""
    defaults = {
        "DATABASE_URL": "sqlite+aiosqlite://",
        "JARVIS_API_KEY": "test-key",
        "TELEGRAM_BOT_TOKEN": "fake-token",
        "ALLOWED_USER_IDS": "123,456",
        "USER_NAMES": '{"123": "Vincent", "456": "Christianne"}',
        "TIMEZONE": "UTC",
    }
    defaults.update(overrides)
    return Settings(**defaults)


async def _create_contact(db: AsyncSession, name: str = "Mark") -> Contact:
    contact = Contact(
        id=uuid.uuid4(),
        name=name,
        relationship_type="friend",
        created_by="vincent",
        visibility="shared",
        created_at=datetime.now(tz=None),
        updated_at=datetime.now(tz=None),
    )
    db.add(contact)
    await db.flush()
    return contact


async def _create_event(
    db: AsyncSession,
    contact: Contact,
    event_type: str = "birthday",
    day: int = 14,
    month: int = 6,
    year: int | None = 1990,
    recurring: bool = True,
    label: str | None = None,
    child: ContactChild | None = None,
) -> ContactEvent:
    event = ContactEvent(
        id=uuid.uuid4(),
        contact_id=contact.id,
        event_type=event_type,
        label=label,
        child_id=child.id if child else None,
        day=day,
        month=month,
        year=year,
        recurring=recurring,
        created_at=datetime.now(tz=None),
        updated_at=datetime.now(tz=None),
    )
    db.add(event)
    await db.flush()
    # Attach contact relationship for message_builder access
    event.contact = contact
    event.child = child
    return event


async def _create_config(
    db: AsyncSession,
    days_before: int = 7,
    enabled: bool = True,
) -> ReminderConfig:
    config = ReminderConfig(
        id=uuid.uuid4(),
        event_id=None,
        days_before=days_before,
        enabled=enabled,
        created_at=datetime.now(tz=None),
        updated_at=datetime.now(tz=None),
    )
    db.add(config)
    await db.flush()
    return config


async def _create_note(
    db: AsyncSession,
    contact: Contact,
    text: str = "Just got promoted",
) -> ContactNote:
    note = ContactNote(
        id=uuid.uuid4(),
        contact_id=contact.id,
        note_text=text,
        created_by="vincent",
        created_at=datetime.now(tz=None),
    )
    db.add(note)
    await db.flush()
    return note


# ---------------------------------------------------------------------------
# 1. 7-day reminder fires 7 days before event
# ---------------------------------------------------------------------------


async def test_7day_reminder(db_session: AsyncSession):
    contact = await _create_contact(db_session, name="Mark")
    await _create_event(db_session, contact, day=20, month=6, year=1990)
    await _create_config(db_session, days_before=7)

    settings = _make_settings()
    engine = ReminderEngine(db_session, settings)

    with patch("src.engine.reminder_engine.send_to_all_users", new_callable=AsyncMock, return_value={"123": 1}):
        with patch("src.engine.reminder_engine.write_heartbeat"):
            result = await engine.run(today=date(2025, 6, 13))

    assert result.reminders_sent == 1
    assert result.status == "completed"


# ---------------------------------------------------------------------------
# 2. 1-day reminder fires 1 day before
# ---------------------------------------------------------------------------


async def test_1day_reminder(db_session: AsyncSession):
    contact = await _create_contact(db_session, name="Lisa")
    await _create_event(db_session, contact, day=15, month=6, year=1985)
    await _create_config(db_session, days_before=1)

    settings = _make_settings()
    engine = ReminderEngine(db_session, settings)

    with patch("src.engine.reminder_engine.send_to_all_users", new_callable=AsyncMock, return_value={"123": 1}):
        with patch("src.engine.reminder_engine.write_heartbeat"):
            result = await engine.run(today=date(2025, 6, 14))

    assert result.reminders_sent == 1


# ---------------------------------------------------------------------------
# 3. Day-of reminder (0 days before)
# ---------------------------------------------------------------------------


async def test_day_of_reminder(db_session: AsyncSession):
    contact = await _create_contact(db_session, name="Alice")
    await _create_event(db_session, contact, day=10, month=6, year=1992)
    await _create_config(db_session, days_before=0)

    settings = _make_settings()
    engine = ReminderEngine(db_session, settings)

    with patch("src.engine.reminder_engine.send_to_all_users", new_callable=AsyncMock, return_value={"123": 1}):
        with patch("src.engine.reminder_engine.write_heartbeat"):
            result = await engine.run(today=date(2025, 6, 10))

    assert result.reminders_sent == 1


# ---------------------------------------------------------------------------
# 4. Year wrap — Dec event fires reminder from late December
# ---------------------------------------------------------------------------


async def test_year_wrap_reminder(db_session: AsyncSession):
    contact = await _create_contact(db_session, name="NewYear")
    await _create_event(db_session, contact, day=3, month=1, year=None)
    await _create_config(db_session, days_before=7)

    settings = _make_settings()
    engine = ReminderEngine(db_session, settings)

    # Jan 3 next year (2026) minus 7 days = Dec 27, 2025
    with patch("src.engine.reminder_engine.send_to_all_users", new_callable=AsyncMock, return_value={"123": 1}):
        with patch("src.engine.reminder_engine.write_heartbeat"):
            result = await engine.run(today=date(2025, 12, 27))

    assert result.reminders_sent == 1


# ---------------------------------------------------------------------------
# 5. Feb 29 in non-leap year uses Feb 28
# ---------------------------------------------------------------------------


async def test_feb29_non_leap_year(db_session: AsyncSession):
    contact = await _create_contact(db_session, name="LeapBaby")
    await _create_event(db_session, contact, day=29, month=2, year=1992)
    await _create_config(db_session, days_before=0)

    settings = _make_settings()
    engine = ReminderEngine(db_session, settings)

    # 2025 is NOT a leap year, so Feb 29 -> Feb 28
    with patch("src.engine.reminder_engine.send_to_all_users", new_callable=AsyncMock, return_value={"123": 1}):
        with patch("src.engine.reminder_engine.write_heartbeat"):
            result = await engine.run(today=date(2025, 2, 28))

    assert result.reminders_sent == 1


# ---------------------------------------------------------------------------
# 6. Idempotency — running twice on the same day skips duplicate
# ---------------------------------------------------------------------------


async def test_idempotency(db_session: AsyncSession):
    contact = await _create_contact(db_session, name="Mark")
    await _create_event(db_session, contact, day=20, month=6, year=1990)
    await _create_config(db_session, days_before=7)

    settings = _make_settings()

    # First run
    engine1 = ReminderEngine(db_session, settings)
    with patch("src.engine.reminder_engine.send_to_all_users", new_callable=AsyncMock, return_value={"123": 1}):
        with patch("src.engine.reminder_engine.write_heartbeat"):
            result1 = await engine1.run(today=date(2025, 6, 13))
    assert result1.reminders_sent == 1

    # Second run same day — should skip
    engine2 = ReminderEngine(db_session, settings)
    with patch("src.engine.reminder_engine.send_to_all_users", new_callable=AsyncMock, return_value={"123": 1}):
        with patch("src.engine.reminder_engine.write_heartbeat"):
            result2 = await engine2.run(today=date(2025, 6, 13))
    assert result2.reminders_sent == 0
    assert result2.reminders_skipped == 1


# ---------------------------------------------------------------------------
# 7. Note surfacing in reminder message
# ---------------------------------------------------------------------------


async def test_note_surfacing(db_session: AsyncSession):
    contact = await _create_contact(db_session, name="Bob")
    await _create_event(db_session, contact, day=20, month=6, year=1990)
    await _create_note(db_session, contact, text="Just got promoted to senior manager")
    await _create_config(db_session, days_before=7)

    settings = _make_settings()
    engine = ReminderEngine(db_session, settings)

    sent_messages = []

    async def capture_message(message, settings):
        sent_messages.append(message)
        return {"123": 1}

    with patch("src.engine.reminder_engine.send_to_all_users", side_effect=capture_message):
        with patch("src.engine.reminder_engine.write_heartbeat"):
            result = await engine.run(today=date(2025, 6, 13))

    assert result.reminders_sent == 1
    assert len(sent_messages) == 1
    assert "promoted" in sent_messages[0]


# ---------------------------------------------------------------------------
# 8. Multiple events — each gets its own reminder
# ---------------------------------------------------------------------------


async def test_multiple_events(db_session: AsyncSession):
    c1 = await _create_contact(db_session, name="Mark")
    c2 = await _create_contact(db_session, name="Lisa")
    await _create_event(db_session, c1, day=20, month=6)
    await _create_event(db_session, c2, day=20, month=6)
    await _create_config(db_session, days_before=7)

    settings = _make_settings()
    engine = ReminderEngine(db_session, settings)

    with patch("src.engine.reminder_engine.send_to_all_users", new_callable=AsyncMock, return_value={"123": 1}):
        with patch("src.engine.reminder_engine.write_heartbeat"):
            result = await engine.run(today=date(2025, 6, 13))

    assert result.reminders_sent == 2
    assert result.total_events == 2


# ---------------------------------------------------------------------------
# 9. Disabled config is ignored
# ---------------------------------------------------------------------------


async def test_disabled_config_ignored(db_session: AsyncSession):
    contact = await _create_contact(db_session, name="Mark")
    await _create_event(db_session, contact, day=20, month=6)
    await _create_config(db_session, days_before=7, enabled=False)

    settings = _make_settings()
    engine = ReminderEngine(db_session, settings)

    with patch("src.engine.reminder_engine.send_to_all_users", new_callable=AsyncMock, return_value={"123": 1}):
        with patch("src.engine.reminder_engine.write_heartbeat"):
            result = await engine.run(today=date(2025, 6, 13))

    assert result.reminders_sent == 0
    assert result.total_events == 0  # no configs loaded means early return


# ---------------------------------------------------------------------------
# 10. Message format — 7-day message includes "in 7 days"
# ---------------------------------------------------------------------------


async def test_message_format_7day(db_session: AsyncSession):
    contact = await _create_contact(db_session, name="Mark")
    await _create_event(db_session, contact, day=20, month=6, year=1990)
    await _create_config(db_session, days_before=7)

    settings = _make_settings()
    engine = ReminderEngine(db_session, settings)

    sent_messages = []

    async def capture(message, settings):
        sent_messages.append(message)
        return {"123": 1}

    with patch("src.engine.reminder_engine.send_to_all_users", side_effect=capture):
        with patch("src.engine.reminder_engine.write_heartbeat"):
            await engine.run(today=date(2025, 6, 13))

    assert len(sent_messages) == 1
    msg = sent_messages[0]
    assert "in 7 days" in msg
    assert "Mark" in msg
    assert "June 20" in msg


# ---------------------------------------------------------------------------
# 11. Age calculation in message — "turns 35"
# ---------------------------------------------------------------------------


async def test_age_in_message(db_session: AsyncSession):
    contact = await _create_contact(db_session, name="Mark")
    await _create_event(db_session, contact, day=20, month=6, year=1990)
    await _create_config(db_session, days_before=0)

    settings = _make_settings()
    engine = ReminderEngine(db_session, settings)

    sent_messages = []

    async def capture(message, settings):
        sent_messages.append(message)
        return {"123": 1}

    with patch("src.engine.reminder_engine.send_to_all_users", side_effect=capture):
        with patch("src.engine.reminder_engine.write_heartbeat"):
            await engine.run(today=date(2025, 6, 20))

    assert len(sent_messages) == 1
    assert "turns 35" in sent_messages[0]


# ---------------------------------------------------------------------------
# 12. No configs — engine returns early with 0 sent
# ---------------------------------------------------------------------------


async def test_no_configs(db_session: AsyncSession):
    contact = await _create_contact(db_session, name="Mark")
    await _create_event(db_session, contact, day=20, month=6)

    settings = _make_settings()
    engine = ReminderEngine(db_session, settings)

    with patch("src.engine.reminder_engine.write_heartbeat"):
        result = await engine.run(today=date(2025, 6, 13))

    assert result.reminders_sent == 0
    assert result.total_events == 0
    assert result.status == "completed"


# ---------------------------------------------------------------------------
# 13. Non-recurring event is skipped
# ---------------------------------------------------------------------------


async def test_non_recurring_skipped(db_session: AsyncSession):
    contact = await _create_contact(db_session, name="Mark")
    await _create_event(db_session, contact, day=20, month=6, recurring=False)
    await _create_config(db_session, days_before=7)

    settings = _make_settings()
    engine = ReminderEngine(db_session, settings)

    with patch("src.engine.reminder_engine.send_to_all_users", new_callable=AsyncMock, return_value={"123": 1}):
        with patch("src.engine.reminder_engine.write_heartbeat"):
            result = await engine.run(today=date(2025, 6, 13))

    assert result.reminders_sent == 0
    assert result.total_events == 0  # non-recurring filtered out in query


# ---------------------------------------------------------------------------
# 14. Multiple configs fire for same event on same day
# ---------------------------------------------------------------------------


async def test_multiple_configs_same_event(db_session: AsyncSession):
    contact = await _create_contact(db_session, name="Mark")
    # Event on June 20
    await _create_event(db_session, contact, day=20, month=6)
    # Two configs that both match today
    await _create_config(db_session, days_before=7)  # triggers June 13
    await _create_config(db_session, days_before=1)  # triggers June 19

    settings = _make_settings()
    engine = ReminderEngine(db_session, settings)

    # Run on June 13 — only the 7-day config should fire
    with patch("src.engine.reminder_engine.send_to_all_users", new_callable=AsyncMock, return_value={"123": 1}):
        with patch("src.engine.reminder_engine.write_heartbeat"):
            result = await engine.run(today=date(2025, 6, 13))

    assert result.reminders_sent == 1


# ---------------------------------------------------------------------------
# 15. Empty database — no events at all
# ---------------------------------------------------------------------------


async def test_empty_database(db_session: AsyncSession):
    await _create_config(db_session, days_before=7)

    settings = _make_settings()
    engine = ReminderEngine(db_session, settings)

    with patch("src.engine.reminder_engine.send_to_all_users", new_callable=AsyncMock, return_value={"123": 1}):
        with patch("src.engine.reminder_engine.write_heartbeat"):
            result = await engine.run(today=date(2025, 6, 13))

    assert result.reminders_sent == 0
    assert result.total_events == 0
    assert result.status == "completed"
