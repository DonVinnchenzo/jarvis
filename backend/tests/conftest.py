"""Shared fixtures for Jarvis Social Circle backend tests.

Uses in-memory SQLite (aiosqlite) to avoid requiring PostgreSQL for tests.
Overrides get_db and get_settings so the FastAPI app talks to the test DB.
"""

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import JSON
from sqlalchemy import event as sa_event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database import Base, get_db
from src.main import app
from src.models.child import ContactChild
from src.models.contact import Contact
from src.models.event import ContactEvent
from src.models.note import ContactNote
from src.models.reminder import ReminderConfig, SentReminder

# ---------------------------------------------------------------------------
# SQLite compatibility: patch PostgreSQL-specific column types and defaults
# at the metadata level BEFORE any tables are created.
# ---------------------------------------------------------------------------

for _table in Base.metadata.tables.values():
    for _col in _table.columns:
        # Replace JSONB -> JSON
        if isinstance(_col.type, JSONB):
            _col.type = JSON()

        # Remove PostgreSQL-specific server_defaults that SQLite can't parse
        if _col.server_default is not None:
            sd_arg = _col.server_default.arg
            sd_text = str(sd_arg) if sd_arg is not None else ""
            # gen_random_uuid() is PG-only; we generate UUIDs in Python
            if "gen_random_uuid" in sd_text:
                _col.server_default = None
            # '{}'::jsonb is PG cast syntax
            elif "::jsonb" in sd_text:
                _col.server_default = None

# ---------------------------------------------------------------------------
# Test settings
# ---------------------------------------------------------------------------

TEST_API_KEY = "test-key"

# ---------------------------------------------------------------------------
# Database engine (in-memory SQLite via aiosqlite)
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite://"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# SQLite compatibility: generate UUIDs and defaults in Python since SQLite
# has no gen_random_uuid(), no JSONB, and different boolean handling.
# ---------------------------------------------------------------------------


def _set_sqlite_defaults(target, args, kwargs):
    """Set Python-generated UUIDs and other defaults for SQLite.

    The ``init`` event passes (target, args, kwargs).
    """
    from sqlalchemy import inspect as sa_inspect

    mapper = sa_inspect(type(target))
    for column in mapper.columns:
        current_value = kwargs.get(column.key, getattr(target, column.key, None))

        # Generate UUID for primary keys
        if current_value is None and column.primary_key and column.type.__class__.__name__ == "Uuid":
            setattr(target, column.key, uuid.uuid4())

        # Handle remaining server_defaults that SQLite may not process
        if current_value is None and column.server_default is not None:
            sd_arg = column.server_default.arg
            sd_text = str(sd_arg) if sd_arg is not None else ""
            if sd_text in ("true", "'true'"):
                setattr(target, column.key, True)
            elif sd_text in ("false", "'false'"):
                setattr(target, column.key, False)
            elif sd_text == "'shared'":
                setattr(target, column.key, "shared")
            elif sd_text == "now()":
                setattr(target, column.key, datetime.now(tz=None))

        # Generate UUID and default dict/datetime for non-PK columns that
        # had their server_default stripped above
        if current_value is None and column.server_default is None and not column.primary_key:
            type_name = column.type.__class__.__name__
            if type_name == "Uuid" and not column.nullable:
                setattr(target, column.key, uuid.uuid4())
            elif isinstance(column.type, JSON) and not column.nullable:
                setattr(target, column.key, {})


# Register the listener for all models
for _model_cls in [Contact, ContactEvent, ContactChild, ContactNote, ReminderConfig, SentReminder]:
    sa_event.listen(_model_cls, "init", _set_sqlite_defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
async def _setup_db():
    """Create all tables before each test and drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a fresh async DB session for direct database access in tests."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncSession, None]:
    """Yield an httpx AsyncClient wired to the FastAPI app with test DB."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db

    # Patch get_settings so API key matches our test key
    with patch("src.main.get_settings") as mock_settings:
        settings_obj = mock_settings.return_value
        settings_obj.JARVIS_API_KEY = TEST_API_KEY
        settings_obj.TIMEZONE = "UTC"
        settings_obj.TELEGRAM_BOT_TOKEN = ""
        settings_obj.ALLOWED_USER_IDS = ""
        settings_obj.allowed_user_ids_list = []
        settings_obj.user_names_dict = {}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def api_headers() -> dict[str, str]:
    """Return headers with the test API key."""
    return {"X-API-Key": TEST_API_KEY}


# ---------------------------------------------------------------------------
# Helper to create a contact via the API (used across many test files)
# ---------------------------------------------------------------------------


async def create_test_contact(
    client: AsyncClient,
    headers: dict[str, str],
    name: str = "Mark de Vries",
    relationship_type: str = "friend",
    created_by: str = "vincent",
) -> dict:
    """Create a contact via the API and return the JSON response."""
    resp = await client.post(
        "/api/contacts",
        json={
            "name": name,
            "relationship_type": relationship_type,
            "created_by": created_by,
        },
        headers=headers,
    )
    assert resp.status_code == 201, f"Failed to create contact: {resp.text}"
    return resp.json()


async def create_test_event(
    client: AsyncClient,
    headers: dict[str, str],
    contact_id: str,
    event_type: str = "birthday",
    day: int = 14,
    month: int = 6,
    year: int | None = 1990,
    label: str | None = None,
    recurring: bool = True,
) -> dict:
    """Create an event via the API and return the JSON response."""
    payload: dict = {
        "event_type": event_type,
        "day": day,
        "month": month,
        "recurring": recurring,
    }
    if year is not None:
        payload["year"] = year
    if label is not None:
        payload["label"] = label
    resp = await client.post(
        f"/api/contacts/{contact_id}/events",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 201, f"Failed to create event: {resp.text}"
    return resp.json()
