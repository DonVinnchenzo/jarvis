import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class ContactEvent(Base):
    __tablename__ = "contact_events"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    child_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contact_children.id", ondelete="CASCADE"),
        nullable=True,
    )
    day: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recurring: Mapped[bool] = mapped_column(server_default=text("true"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    contact: Mapped["Contact"] = relationship(back_populates="events")  # noqa: F821
    child: Mapped["ContactChild | None"] = relationship()  # noqa: F821

    __table_args__ = (
        CheckConstraint("day >= 1 AND day <= 31", name="ck_event_day"),
        CheckConstraint("month >= 1 AND month <= 12", name="ck_event_month"),
        Index("ix_contact_events_month_day", "month", "day"),
    )
