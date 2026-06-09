import uuid
from datetime import datetime

from sqlalchemy import Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False)
    visibility: Mapped[str] = mapped_column(String(20), server_default="shared", nullable=False)
    created_by: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    events: Mapped[list["ContactEvent"]] = relationship(  # noqa: F821
        back_populates="contact",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    children: Mapped[list["ContactChild"]] = relationship(  # noqa: F821
        back_populates="contact",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    notes: Mapped[list["ContactNote"]] = relationship(  # noqa: F821
        back_populates="contact",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_contacts_name", "name"),
    )
