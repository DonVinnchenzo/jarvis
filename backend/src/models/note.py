import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class ContactNote(Base):
    __tablename__ = "contact_notes"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    # Relationships
    contact: Mapped["Contact"] = relationship(back_populates="notes")  # noqa: F821

    # Note: GIN index on to_tsvector('english', note_text) is created
    # directly in the Alembic migration using raw SQL, since Alembic's
    # autogenerate cannot render REGCONFIG literals.
