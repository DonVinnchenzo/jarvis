import calendar
import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config import Settings
from src.engine.heartbeat import write_heartbeat
from src.engine.message_builder import build_reminder_message
from src.engine.telegram_sender import send_to_all_users
from src.models.event import ContactEvent
from src.models.note import ContactNote
from src.models.reminder import ReminderConfig, SentReminder
from src.schemas.reminder import ReminderRunResponse

logger = logging.getLogger(__name__)


class ReminderEngine:
    """Core reminder engine. Checks all recurring events against all enabled configs,
    sends Telegram reminders, and records sent reminders for idempotency.
    """

    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def run(self, today: date | None = None) -> ReminderRunResponse:
        """Run the reminder engine for a given date.

        If today is None, uses current date in the configured timezone.
        """
        if today is None:
            tz = ZoneInfo(self.settings.TIMEZONE)
            today = datetime.now(tz).date()

        logger.info("Running reminder engine for date: %s", today)

        # Load all global configs (event_id IS NULL, enabled=True)
        configs = await self._load_configs()
        if not configs:
            logger.info("No enabled reminder configs found")
            write_heartbeat(self.settings.TIMEZONE)
            return ReminderRunResponse(
                status="completed",
                reminders_sent=0,
                reminders_skipped=0,
                total_events=0,
            )

        # Load all recurring events with contact and notes eager-loaded
        events = await self._load_recurring_events()
        logger.info("Found %d recurring events and %d configs", len(events), len(configs))

        reminders_sent = 0
        reminders_skipped = 0
        errors: list[str] = []

        for event in events:
            # Calculate occurrences for this year and next year
            occurrences = self._calculate_occurrences(event, today)

            for occ in occurrences:
                for config in configs:
                    reminder_date = occ - timedelta(days=config.days_before)
                    if reminder_date != today:
                        continue

                    # Check SentReminder for dedup
                    already_sent = await self._check_already_sent(event.id, config.id, occ)
                    if already_sent:
                        logger.debug(
                            "Skipping duplicate: event=%s, config=%s, date=%s",
                            event.id,
                            config.id,
                            occ,
                        )
                        reminders_skipped += 1
                        continue

                    # Get recent notes for this contact
                    recent_notes = await self._get_recent_notes(event.contact_id)

                    # Build message
                    message = build_reminder_message(
                        event=event,
                        config=config,
                        occurrence_date=occ,
                        recent_notes=recent_notes,
                        tz_name=self.settings.TIMEZONE,
                    )

                    # Send to all users
                    try:
                        message_ids = await send_to_all_users(message, self.settings)
                    except Exception:
                        logger.exception("Failed to send reminder for event %s", event.id)
                        errors.append(f"Send failed for event {event.id}")
                        continue

                    # Record sent reminder
                    sent = SentReminder(
                        event_id=event.id,
                        reminder_config_id=config.id,
                        event_date=occ,
                        telegram_message_ids=message_ids,
                    )
                    self.db.add(sent)
                    # Flush each individual reminder so partial failures
                    # don't roll back successful sends
                    try:
                        await self.db.flush()
                    except Exception:
                        logger.exception("Failed to record SentReminder for event %s", event.id)
                        errors.append(f"DB record failed for event {event.id}")
                        continue

                    reminders_sent += 1
                    contact_name = event.contact.name if event.contact else "Unknown"
                    logger.info(
                        "Sent reminder: %s's %s (%d days before, date=%s)",
                        contact_name,
                        event.event_type,
                        config.days_before,
                        occ,
                    )

        # Write heartbeat
        write_heartbeat(self.settings.TIMEZONE)

        status = "completed" if not errors else "completed_with_errors"
        logger.info(
            "Reminder engine finished: sent=%d, skipped=%d, errors=%d",
            reminders_sent,
            reminders_skipped,
            len(errors),
        )

        return ReminderRunResponse(
            status=status,
            reminders_sent=reminders_sent,
            reminders_skipped=reminders_skipped,
            total_events=len(events),
            errors=errors,
        )

    async def _load_configs(self) -> list[ReminderConfig]:
        """Load all global, enabled reminder configs."""
        stmt = (
            select(ReminderConfig)
            .where(ReminderConfig.event_id.is_(None))
            .where(ReminderConfig.enabled.is_(True))
            .order_by(ReminderConfig.days_before.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _load_recurring_events(self) -> list[ContactEvent]:
        """Load all recurring events with contact and child eager-loaded."""
        stmt = (
            select(ContactEvent)
            .where(ContactEvent.recurring.is_(True))
            .options(
                selectinload(ContactEvent.contact),
                selectinload(ContactEvent.child),
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    def _calculate_occurrences(self, event: ContactEvent, today: date) -> list[date]:
        """Calculate event occurrences for this year and next year."""
        occurrences: list[date] = []
        for year in [today.year, today.year + 1]:
            occ = self._make_occurrence_date(year, event.month, event.day)
            if occ is not None:
                occurrences.append(occ)
        return occurrences

    @staticmethod
    def _make_occurrence_date(year: int, month: int, day: int) -> date | None:
        """Create a date, handling Feb 29 in non-leap years."""
        if month == 2 and day == 29:
            if not calendar.isleap(year):
                return date(year, 2, 28)
            return date(year, 2, 29)
        try:
            return date(year, month, day)
        except ValueError:
            logger.warning("Invalid date: %d-%02d-%02d, skipping", year, month, day)
            return None

    async def _check_already_sent(
        self,
        event_id: object,
        config_id: object,
        event_date: date,
    ) -> bool:
        """Check if a reminder was already sent for this event+config+date."""
        stmt = select(SentReminder).where(
            SentReminder.event_id == event_id,
            SentReminder.reminder_config_id == config_id,
            SentReminder.event_date == event_date,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _get_recent_notes(self, contact_id: object) -> list[ContactNote]:
        """Get the 2 most recent notes for a contact."""
        stmt = (
            select(ContactNote)
            .where(ContactNote.contact_id == contact_id)
            .order_by(ContactNote.created_at.desc())
            .limit(2)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
