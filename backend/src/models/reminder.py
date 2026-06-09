import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Integer, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class ReminderConfig(Base):
    __tablename__ = "reminder_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contact_events.id", ondelete="CASCADE"),
        nullable=True,
    )
    days_before: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(server_default=text("true"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SentReminder(Base):
    __tablename__ = "sent_reminders"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contact_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    reminder_config_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reminder_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    telegram_message_ids: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "reminder_config_id",
            "event_date",
            name="uq_sent_reminder_event_config_date",
        ),
    )
