# SPEC-001: Social Circle -- Implementation Plan

**Spec:** `specs/001-social-circle.md` (Approved)
**Date:** 2026-06-09
**Author:** Claude Code

---

This plan is designed so that a fresh Claude Code session can pick up at any step and know exactly what to do. Each step ends with a working, testable state and a git commit.

---

## Step 0: Prerequisites

Things to install and configure before writing any code. These are one-time setup tasks.

### 0.1 Install Homebrew PostgreSQL 16

```bash
brew install postgresql@16
brew services start postgresql@16
```

Verify: `psql --version` should show 16.x. If `psql` is not on PATH, add the Homebrew bin to your shell profile:

```bash
echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### 0.2 Create the database

```bash
createdb jarvis
psql jarvis -c "SELECT 1;"  # Should return 1
```

### 0.3 Create the Telegram bot

1. Message @BotFather on Telegram
2. `/newbot` -> name: `Jarvis` -> username: pick something like `JarvisHouseholdBot`
3. Copy the bot token

### 0.4 Generate an API key

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Save the output -- this becomes `JARVIS_API_KEY`.

### 0.5 Create `.env` file

Create `/Users/vincent/jarvis/.env` with all required variables:

```env
# Database
DATABASE_URL=postgresql+asyncpg://vincent@localhost/jarvis

# API authentication
JARVIS_API_KEY=<generated-key-from-step-0.4>

# Telegram
TELEGRAM_BOT_TOKEN=<token-from-botfather>
ALLOWED_USER_IDS=<vincent-telegram-id>,<christianne-telegram-id>
USER_NAMES={"<vincent-telegram-id>":"Vincent","<christianne-telegram-id>":"Christianne"}

# Timezone (used by reminder engine)
TIMEZONE=Europe/Amsterdam

# Claude Agent SDK (bot uses these)
WORKSPACE_DIR=/Users/vincent/jarvis
BOT_NAME=Jarvis
BOT_MODE=prod
STREAMING_MODE=streaming
DANGEROUS_MODE=true
CLAUDE_SDK_LOG_LEVEL=basic
CANCEL_ON_NEW_MESSAGE=false
MAX_MESSAGE_LENGTH=4000
STREAMING_DEBOUNCE_MS=500

# TTS (disabled for now)
TTS_ENABLED=false
```

Also create `/Users/vincent/jarvis/.env.example` as a template (same keys, placeholder values, committed to git).

### 0.6 Python virtual environment

```bash
cd /Users/vincent/jarvis/backend
python3 -m venv .venv
source .venv/bin/activate
```

### 0.7 Node.js dependencies (bot -- done in Step 6)

Deferred until Step 6 when the bot scaffold is created.

### Verification

- [ ] `psql jarvis -c "SELECT 1;"` returns 1
- [ ] `.env` file exists at `/Users/vincent/jarvis/.env` with all variables populated
- [ ] `.env.example` exists at `/Users/vincent/jarvis/.env.example` (committed to git)
- [ ] Python venv activates without error

**No git commit for Step 0** -- environment setup only. The `.env` file is gitignored. The `.env.example` is committed in Step 1.

---

## Step 1: Backend Scaffold

Create the FastAPI application skeleton with configuration, database connection, and API key middleware. No models or routes yet -- just the shell.

### Files to create

#### `backend/pyproject.toml`

Python project config and dependencies.

```toml
[project]
name = "jarvis-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "sqlalchemy[asyncio]>=2.0.30",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "python-telegram-bot>=21.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.3.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
    "ruff>=0.5.0",
    "aiosqlite>=0.20.0",
]

[tool.ruff]
target-version = "py311"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

#### `backend/src/__init__.py`

Empty file. Makes `src` a Python package.

#### `backend/src/config.py`

Pydantic Settings class. Reads from `.env` at project root.

- `DATABASE_URL: str` -- PostgreSQL async connection string
- `JARVIS_API_KEY: str` -- API key for X-API-Key header authentication
- `TELEGRAM_BOT_TOKEN: str` -- For sending reminder messages
- `ALLOWED_USER_IDS: list[int]` -- Parsed from comma-separated string
- `USER_NAMES: dict[str, str]` -- JSON string parsed to dict mapping Telegram user ID -> display name
- `TIMEZONE: str` -- Default "Europe/Amsterdam"

The `env_file` points to `/Users/vincent/jarvis/.env` (one level up from `backend/`).

#### `backend/src/database.py`

SQLAlchemy async engine and session factory.

- `create_async_engine(settings.DATABASE_URL)`
- `async_sessionmaker` bound to the engine
- `get_db()` async generator for FastAPI `Depends()`
- `Base = declarative_base()` -- shared base for all models

#### `backend/src/main.py`

FastAPI application with:

- `app = FastAPI(title="Jarvis API", version="0.1.0")`
- **API key middleware**: Check `X-API-Key` header on all `/api/*` requests. Return 401 if missing or wrong. Skip for `/docs` and `/openapi.json` (dev convenience, removed in prod).
- **CORS**: Not needed (bot calls from same machine, no browser client). Omit CORS middleware entirely.
- **Host binding**: `uvicorn.run(app, host="127.0.0.1", port=8000)` -- localhost only.
- Health check route at `GET /api/health` that returns `{"status": "ok"}` (no auth required -- but still behind API key for consistency, or exempt it for heartbeat monitoring from the bot).

Design decision: Exempt `/api/health` from API key middleware so the heartbeat check script can call it without credentials. All other `/api/*` routes require the key.

#### `backend/alembic.ini`

Alembic configuration file. Points `sqlalchemy.url` at the same `DATABASE_URL` from settings. Use `script_location = alembic`.

#### `backend/alembic/env.py`

Alembic environment. Imports `Base.metadata` from `src.database` and all models from `src.models` so autogenerate works. Uses async engine.

#### `backend/alembic/versions/` (empty directory)

Will contain migration files.

#### `backend/alembic/script.py.mako`

Alembic migration template (standard boilerplate).

#### `/Users/vincent/jarvis/.env.example`

Template of `.env` with placeholder values (committed to git).

### What to test

```bash
cd /Users/vincent/jarvis/backend
source .venv/bin/activate
pip install -e ".[dev]"
alembic --help  # Should show alembic commands
python -c "from src.config import get_settings; s = get_settings(); print(s.DATABASE_URL)"
python -c "from src.main import app; print(app.title)"
uvicorn src.main:app --host 127.0.0.1 --port 8000 &
curl -s http://localhost:8000/api/health  # Should return {"status": "ok"}
curl -s -H "X-API-Key: wrong" http://localhost:8000/api/contacts  # Should return 401
kill %1
```

### Git commit

```
feat: backend scaffold with FastAPI, config, database, and API key auth

- pyproject.toml with all dependencies
- Pydantic settings loading from .env
- SQLAlchemy async engine and session factory
- API key middleware (X-API-Key header)
- Health check endpoint at GET /api/health
- Alembic setup for migrations
- .env.example template
```

---

## Step 2: Database Models + First Migration

Create all SQLAlchemy models matching the spec's data model, generate the first Alembic migration, and write a seed script for default ReminderConfig rows.

### Files to create

#### `backend/src/models/__init__.py`

Imports and re-exports all models so Alembic and route files can do `from src.models import Contact, ContactEvent, ...`.

#### `backend/src/models/contact.py`

```python
class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[uuid.UUID]           # PK, server_default=gen_random_uuid()
    name: Mapped[str]               # VARCHAR(200), NOT NULL
    relationship_type: Mapped[str]  # VARCHAR(100), NOT NULL
    visibility: Mapped[str]         # VARCHAR(20), default "shared"
    created_by: Mapped[str]         # VARCHAR(50), Telegram user ID
    created_at: Mapped[datetime]    # server_default=now()
    updated_at: Mapped[datetime]    # server_default=now(), onupdate=now()

    # Relationships
    events: Mapped[list["ContactEvent"]]
    children: Mapped[list["ContactChild"]]
    notes: Mapped[list["ContactNote"]]
```

Index on `name` for search.

#### `backend/src/models/event.py`

```python
class ContactEvent(Base):
    __tablename__ = "contact_events"

    id: Mapped[uuid.UUID]
    contact_id: Mapped[uuid.UUID]   # FK -> contacts.id, ON DELETE CASCADE
    event_type: Mapped[str]         # "birthday", "anniversary", "child_birthday", "custom"
    label: Mapped[str | None]       # Nullable, for custom events / anniversary descriptions
    child_id: Mapped[uuid.UUID | None]  # FK -> contact_children.id, ON DELETE CASCADE, nullable
    day: Mapped[int]                # CHECK 1..31
    month: Mapped[int]              # CHECK 1..12
    year: Mapped[int | None]        # Nullable
    recurring: Mapped[bool]         # Default True
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

Composite index on `(month, day)` for upcoming queries.

#### `backend/src/models/child.py`

```python
class ContactChild(Base):
    __tablename__ = "contact_children"

    id: Mapped[uuid.UUID]
    contact_id: Mapped[uuid.UUID]   # FK -> contacts.id, ON DELETE CASCADE
    name: Mapped[str]               # VARCHAR(200)
    created_at: Mapped[datetime]
```

#### `backend/src/models/note.py`

```python
class ContactNote(Base):
    __tablename__ = "contact_notes"

    id: Mapped[uuid.UUID]
    contact_id: Mapped[uuid.UUID]   # FK -> contacts.id, ON DELETE CASCADE
    note_text: Mapped[str]          # TEXT, NOT NULL
    created_by: Mapped[str]         # Telegram user ID
    created_at: Mapped[datetime]
```

GIN index on `note_text` for full-text search.

#### `backend/src/models/reminder.py`

```python
class ReminderConfig(Base):
    __tablename__ = "reminder_configs"

    id: Mapped[uuid.UUID]
    event_id: Mapped[uuid.UUID | None]  # FK -> contact_events.id, nullable (null = global)
    days_before: Mapped[int]            # e.g., 7, 1, 0
    enabled: Mapped[bool]               # Default True
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

class SentReminder(Base):
    __tablename__ = "sent_reminders"

    id: Mapped[uuid.UUID]
    event_id: Mapped[uuid.UUID]            # FK -> contact_events.id
    reminder_config_id: Mapped[uuid.UUID]  # FK -> reminder_configs.id
    event_date: Mapped[date]               # The occurrence date this reminder was for
    sent_at: Mapped[datetime]
    telegram_message_ids: Mapped[dict]     # JSONB
```

UNIQUE constraint on `(event_id, reminder_config_id, event_date)` on `sent_reminders` for idempotency.

#### First Alembic migration

```bash
cd /Users/vincent/jarvis/backend
source .venv/bin/activate
alembic revision --autogenerate -m "initial schema: contacts, events, children, notes, reminders"
alembic upgrade head
```

Verify by inspecting the database:

```bash
psql jarvis -c "\dt"
```

Should show all 5 tables.

#### `backend/scripts/seed_reminders.py`

Standalone script that inserts 3 default ReminderConfig rows if they don't exist:

- `days_before=7, event_id=NULL, enabled=True` (global 7-day reminder)
- `days_before=1, event_id=NULL, enabled=True` (global 1-day reminder)
- `days_before=0, event_id=NULL, enabled=True` (global day-of reminder)

Uses a sync connection (simpler for scripts). Idempotent -- checks before inserting.

```bash
cd /Users/vincent/jarvis/backend
source .venv/bin/activate
python scripts/seed_reminders.py
```

### What to test

```bash
cd /Users/vincent/jarvis/backend
source .venv/bin/activate

# Run migration
alembic upgrade head

# Verify tables
psql jarvis -c "\dt" | grep -E "contacts|contact_events|contact_children|contact_notes|reminder_configs|sent_reminders"

# Verify CHECK constraints
psql jarvis -c "INSERT INTO contact_events (id, contact_id, event_type, day, month, recurring) VALUES (gen_random_uuid(), gen_random_uuid(), 'birthday', 32, 1, true);"
# Should fail with CHECK constraint violation

# Verify UNIQUE constraint
psql jarvis -c "SELECT constraint_name FROM information_schema.table_constraints WHERE table_name='sent_reminders' AND constraint_type='UNIQUE';"

# Seed reminders
python scripts/seed_reminders.py
psql jarvis -c "SELECT days_before, enabled FROM reminder_configs WHERE event_id IS NULL ORDER BY days_before;"
# Should show: 0, 1, 7

# Run seed again to verify idempotency
python scripts/seed_reminders.py
psql jarvis -c "SELECT count(*) FROM reminder_configs WHERE event_id IS NULL;"
# Should still be 3

# Lint
ruff check .
```

### Git commit

```
feat: database models and initial migration

- Contact, ContactEvent, ContactChild, ContactNote models
- ReminderConfig and SentReminder models with idempotency constraint
- CHECK constraints on day (1-31) and month (1-12)
- GIN index on note_text, composite index on (month, day)
- Alembic migration: initial schema
- Seed script for default reminder configs (7, 1, 0 days)
```

---

## Step 3: CRUD Routes

Implement all API endpoints from the spec. Each route file handles one entity. Pydantic schemas handle request/response validation.

### Files to create

#### `backend/src/schemas/__init__.py`

Empty init.

#### `backend/src/schemas/contact.py`

Pydantic models:

- `ContactCreate` -- name (str), relationship_type (str), created_by (str), visibility (str, default "shared")
- `ContactUpdate` -- name (str | None), relationship_type (str | None), visibility (str | None)
- `ContactResponse` -- all fields including id, created_at, updated_at
- `ContactDetailResponse` -- ContactResponse + nested events, children, notes

#### `backend/src/schemas/event.py`

- `EventCreate` -- event_type (str), label (str | None), child_id (UUID | None), day (int, 1-31), month (int, 1-12), year (int | None), recurring (bool, default True)
- `EventUpdate` -- all fields optional
- `EventResponse` -- all fields including id, contact_id

#### `backend/src/schemas/child.py`

- `ChildCreate` -- name (str)
- `ChildUpdate` -- name (str | None)
- `ChildResponse` -- all fields including id, contact_id

#### `backend/src/schemas/note.py`

- `NoteCreate` -- note_text (str), created_by (str)
- `NoteResponse` -- all fields including id, contact_id, created_at

#### `backend/src/schemas/reminder.py`

- `ReminderConfigCreate` -- days_before (int), enabled (bool, default True)
- `ReminderConfigResponse` -- all fields
- `ReminderRunResponse` -- summary of what was sent/skipped

#### `backend/src/schemas/upcoming.py`

- `UpcomingEvent` -- contact_name (str), contact_id (UUID), event_type (str), label (str | None), day (int), month (int), year (int | None), days_until (int), date_display (str)
- `UpcomingResponse` -- list of UpcomingEvent

#### `backend/src/schemas/search.py`

- `SearchResult` -- contact_id (UUID), contact_name (str), match_type (str: "name" | "note" | "child" | "relationship"), match_text (str)
- `SearchResponse` -- list of SearchResult

#### `backend/src/routes/__init__.py`

Empty init.

#### `backend/src/routes/contacts.py`

```
POST   /api/contacts           -- Create contact
GET    /api/contacts           -- List all contacts (optional ?visibility=shared|personal filter)
GET    /api/contacts/{id}      -- Get contact with events, children, notes (eager loaded)
PUT    /api/contacts/{id}      -- Update contact fields
DELETE /api/contacts/{id}      -- Delete contact (cascade handled by DB)
```

Implementation details:
- List: query all contacts, ordered by name. Return `ContactResponse` list.
- Detail: eager-load relationships (selectinload for events, children, notes). Return `ContactDetailResponse`.
- Create: validate name not empty. Return 201 with `ContactResponse`.
- Delete: return 204. Cascade deletes all child records.

#### `backend/src/routes/events.py`

```
POST   /api/contacts/{contact_id}/events  -- Add event to contact
PUT    /api/events/{id}                    -- Update event
DELETE /api/events/{id}                    -- Delete event
```

Implementation details:
- Create: validate contact_id exists (404 if not). Validate day/month ranges at Pydantic level.
- If `event_type=child_birthday` and `child_id` is provided, verify the child belongs to the same contact.

#### `backend/src/routes/children.py`

```
POST   /api/contacts/{contact_id}/children  -- Add child to contact
PUT    /api/children/{id}                    -- Update child name
DELETE /api/children/{id}                    -- Delete child (cascade deletes linked events)
```

#### `backend/src/routes/notes.py`

```
POST   /api/contacts/{contact_id}/notes  -- Add note to contact
GET    /api/contacts/{contact_id}/notes   -- List notes for contact (chronological, newest first)
DELETE /api/notes/{id}                    -- Delete note
```

#### `backend/src/routes/upcoming.py`

```
GET /api/upcoming?days=30  -- List upcoming events within N days
```

This is the most complex query. Implementation:

1. Get today's date in Europe/Amsterdam timezone.
2. Query all `ContactEvent` rows where `recurring=True`.
3. For each event, calculate the next occurrence:
   - Start with this year's date (`(event.month, event.day)` in the current year).
   - If that date has already passed, use next year.
   - **Feb 29 special case**: If `month=2, day=29` and the target year is not a leap year, use Feb 28.
4. Filter: keep events where `next_occurrence - today <= days`.
5. Sort by `next_occurrence` ascending.
6. Join with Contact to get the contact name.
7. Return `UpcomingResponse`.

**Year-boundary logic**: Because we check both this year and next year, a Jan 2 event will correctly appear when queried in late December with `days=30`.

The calculation happens in Python, not SQL, because the Feb 29 and year-wrapping logic is cleaner in application code. Query all recurring events, compute dates in Python, filter and sort.

#### `backend/src/routes/search.py`

```
GET /api/search?q=term  -- Full-text search across contacts + notes + children
```

Implementation:

1. Normalize query: lowercase, strip whitespace.
2. Search across three tables using `ILIKE '%{term}%'`:
   - `contacts.name`
   - `contacts.relationship_type`
   - `contact_notes.note_text`
   - `contact_children.name`
3. Return deduplicated results, grouped by contact, with match context.
4. Use PostgreSQL `to_tsvector` / `plainto_tsquery` for the notes GIN index when available, with `ILIKE` fallback for names.
5. Order: exact name matches first, then partial name matches, then note matches, then child name matches.

#### `backend/src/routes/reminders.py`

```
GET    /api/reminders/config  -- Get all global reminder configs
POST   /api/reminders/config  -- Create or update a reminder config
POST   /api/reminders/run     -- Trigger the reminder engine (called by cron)
```

The `/run` endpoint is implemented in Step 4 (Proactive Engine). In this step, register the route but have it return a stub response: `{"status": "not_implemented"}`.

#### `backend/src/routes/health.py`

```
GET /api/health  -- Health check (already created in Step 1, but now add heartbeat data)
```

Enhance to include `last_successful_reminder_run` timestamp. Read from a simple file or DB table. Initially returns `null` for the timestamp.

#### Wire routes into `backend/src/main.py`

Add all routers using `app.include_router()`:

```python
from src.routes import contacts, events, children, notes, upcoming, search, reminders, health

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(contacts.router, prefix="/api", tags=["contacts"])
app.include_router(events.router, prefix="/api", tags=["events"])
app.include_router(children.router, prefix="/api", tags=["children"])
app.include_router(notes.router, prefix="/api", tags=["notes"])
app.include_router(upcoming.router, prefix="/api", tags=["upcoming"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(reminders.router, prefix="/api", tags=["reminders"])
```

### What to test

Manual smoke test with curl (all require `X-API-Key` header except `/api/health`):

```bash
cd /Users/vincent/jarvis/backend
source .venv/bin/activate
uvicorn src.main:app --host 127.0.0.1 --port 8000 &

API_KEY="<your-key>"

# Create a contact
curl -s -X POST -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  http://localhost:8000/api/contacts \
  -d '{"name": "Mark", "relationship_type": "friend", "created_by": "12345"}'

# List contacts
curl -s -H "X-API-Key: $API_KEY" http://localhost:8000/api/contacts

# Add birthday event (use the contact ID from above)
curl -s -X POST -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  http://localhost:8000/api/contacts/<contact-id>/events \
  -d '{"event_type": "birthday", "day": 14, "month": 6}'

# Add a note
curl -s -X POST -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  http://localhost:8000/api/contacts/<contact-id>/notes \
  -d '{"note_text": "Just got promoted at work", "created_by": "12345"}'

# Get contact detail
curl -s -H "X-API-Key: $API_KEY" http://localhost:8000/api/contacts/<contact-id>

# Upcoming (should show Mark's birthday if within 30 days)
curl -s -H "X-API-Key: $API_KEY" "http://localhost:8000/api/upcoming?days=365"

# Search
curl -s -H "X-API-Key: $API_KEY" "http://localhost:8000/api/search?q=promoted"

# Delete contact (cascade)
curl -s -X DELETE -H "X-API-Key: $API_KEY" http://localhost:8000/api/contacts/<contact-id>

# Verify cascade: notes and events should be gone
curl -s -H "X-API-Key: $API_KEY" http://localhost:8000/api/contacts

# Lint
ruff check .

kill %1
```

### Git commit

```
feat: CRUD routes for contacts, events, children, notes, upcoming, and search

- Pydantic schemas for all entities with validation
- Contact CRUD with cascade delete
- Event CRUD nested under contacts
- Child CRUD nested under contacts
- Note CRUD with chronological listing
- Upcoming events query with year-boundary and Feb 29 logic
- Full-text search across contacts, notes, and children
- Reminder config endpoint (run endpoint stubbed for Step 4)
- All routes wired into main.py with proper prefixes
```

---

## Step 4: Proactive Engine

The reminder engine is the core of the Social Circle module. It runs as a standalone HTTP endpoint, triggered daily by cron.

### Files to create

#### `backend/src/engine/__init__.py`

Empty init.

#### `backend/src/engine/reminder_engine.py`

Core logic. Called by `POST /api/reminders/run`.

**Algorithm:**

```
function run_reminders(today: date):
    configs = load all ReminderConfig where event_id IS NULL and enabled=True
    events = load all ContactEvent where recurring=True, eager-load contact and notes

    reminders_sent = 0
    reminders_skipped = 0

    for each event in events:
        # Calculate next occurrence (this year and next year)
        occurrences = []
        for year in [today.year, today.year + 1]:
            try:
                if event.month == 2 and event.day == 29:
                    if not is_leap_year(year):
                        occ = date(year, 2, 28)
                    else:
                        occ = date(year, 2, 29)
                else:
                    occ = date(year, event.month, event.day)
                occurrences.append(occ)
            except ValueError:
                # Invalid date (e.g., June 31) -- skip
                log warning
                continue

        for occ in occurrences:
            for config in configs:
                reminder_date = occ - timedelta(days=config.days_before)
                if reminder_date == today:
                    # Check SentReminder for dedup
                    existing = query SentReminder where
                        event_id = event.id AND
                        reminder_config_id = config.id AND
                        event_date = occ
                    if existing:
                        reminders_skipped += 1
                        continue

                    # Build message
                    message = build_reminder_message(event, config, occ)

                    # Send to all users
                    message_ids = send_to_all_users(message)

                    # Record sent reminder
                    insert SentReminder(
                        event_id=event.id,
                        reminder_config_id=config.id,
                        event_date=occ,
                        telegram_message_ids=message_ids
                    )
                    reminders_sent += 1

    # Write heartbeat
    write_heartbeat(now())

    return summary(sent=reminders_sent, skipped=reminders_skipped, total_events=len(events))
```

Key details:
- Uses `zoneinfo.ZoneInfo("Europe/Amsterdam")` to determine "today".
- The `today` parameter can be overridden for testing.
- All database operations happen within a single async session. Each reminder send is committed individually (so partial failures don't roll back successful sends).

#### `backend/src/engine/message_builder.py`

Functions to format reminder messages based on template:

```python
def build_reminder_message(
    event: ContactEvent,
    config: ReminderConfig,
    occurrence_date: date,
    contact: Contact,
    recent_notes: list[ContactNote],  # last 1-2 notes
) -> str:
```

Templates:

- **7+ days before** (`days_before >= 2`):
  ```
  Hey! {contact_name}'s birthday is in {days} days ({month} {day}). Any gift ideas?
  Recent note: {note_text} ({time_ago})
  ```

- **1 day before** (`days_before == 1`):
  ```
  Reminder: {contact_name}'s birthday is tomorrow ({month} {day})!
  Recent note: {note_text} ({time_ago})
  ```

- **Day of** (`days_before == 0`):
  ```
  Today is {contact_name}'s birthday! Happy birthday {contact_name}!
  ```

Event type variations:
- `birthday`: "{name}'s birthday"
- `anniversary`: "{label}" (e.g., "Mark & Lisa's anniversary")
- `child_birthday`: "{child_name} ({contact_name}'s child) turns {age}" (if year known) or "{child_name} ({contact_name}'s child)'s birthday"
- `custom`: "{label}"

Age calculation: If `event.year` is set, compute `occurrence_date.year - event.year`. Include in message: "turns {age}".

Note surfacing: Include last 1-2 notes for the contact, with relative time ("3 weeks ago", "2 months ago"). Only if notes exist.

#### `backend/src/engine/telegram_sender.py`

Sends Telegram messages using `python-telegram-bot`:

```python
async def send_to_all_users(message: str, settings: Settings) -> dict[str, int]:
    """Send message to all whitelisted users. Returns {user_id: message_id}."""
    from telegram import Bot

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    message_ids = {}

    for user_id in settings.ALLOWED_USER_IDS:
        try:
            result = await bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="Markdown",
            )
            message_ids[str(user_id)] = result.message_id
        except Exception as e:
            logger.error(f"Failed to send to user {user_id}: {e}")
            # Don't fail the whole run if one user's send fails

    return message_ids
```

#### `backend/src/engine/heartbeat.py`

Simple heartbeat mechanism:

```python
HEARTBEAT_FILE = "/Users/vincent/jarvis/backend/.heartbeat"

def write_heartbeat():
    """Write current timestamp to heartbeat file."""
    with open(HEARTBEAT_FILE, "w") as f:
        f.write(datetime.now(ZoneInfo("Europe/Amsterdam")).isoformat())

def read_heartbeat() -> datetime | None:
    """Read last heartbeat timestamp. Returns None if no heartbeat file."""
    try:
        with open(HEARTBEAT_FILE, "r") as f:
            return datetime.fromisoformat(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None
```

#### Update `backend/src/routes/reminders.py`

Replace the stub `POST /api/reminders/run` with the actual engine call:

```python
@router.post("/reminders/run")
async def run_reminders(db: AsyncSession = Depends(get_db)):
    engine = ReminderEngine(db, get_settings())
    result = await engine.run()
    return result
```

#### Update `backend/src/routes/health.py`

Add heartbeat data to health response:

```python
@router.get("/health")
async def health():
    last_run = read_heartbeat()
    return {
        "status": "ok",
        "last_successful_reminder_run": last_run.isoformat() if last_run else None,
    }
```

### What to test

```bash
cd /Users/vincent/jarvis/backend
source .venv/bin/activate
uvicorn src.main:app --host 127.0.0.1 --port 8000 &

API_KEY="<your-key>"

# Create test contact with birthday = today + 7 days
# (calculate the actual date)
curl -s -X POST -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  http://localhost:8000/api/contacts \
  -d '{"name": "Test Person", "relationship_type": "friend", "created_by": "12345"}'

# Add birthday event (7 days from now)
curl -s -X POST -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  http://localhost:8000/api/contacts/<id>/events \
  -d '{"event_type": "birthday", "day": <day>, "month": <month>}'

# Run reminder engine
curl -s -X POST -H "X-API-Key: $API_KEY" http://localhost:8000/api/reminders/run
# Should report 1 reminder sent

# Check Telegram -- both users should have received a message

# Run again -- should skip (idempotency)
curl -s -X POST -H "X-API-Key: $API_KEY" http://localhost:8000/api/reminders/run
# Should report 0 sent, 1 skipped

# Check health endpoint for heartbeat
curl -s http://localhost:8000/api/health
# Should show last_successful_reminder_run timestamp

# Clean up test data
curl -s -X DELETE -H "X-API-Key: $API_KEY" http://localhost:8000/api/contacts/<id>

kill %1
```

### Git commit

```
feat: proactive reminder engine with Telegram delivery and heartbeat

- Reminder engine: date calculation, year-boundary, Feb 29 handling
- Message builder: 7-day, 1-day, day-of templates with note surfacing
- Telegram sender: sends to all whitelisted users
- SentReminder dedup: prevents duplicate sends on re-run
- Heartbeat file: tracks last successful run
- Health endpoint enhanced with heartbeat data
```

---

## Step 5: Tests

Comprehensive test suite for all backend functionality. Tests run against an in-memory SQLite database (for speed) with a PostgreSQL integration test option.

### Files to create

#### `backend/tests/__init__.py`

Empty init.

#### `backend/tests/conftest.py`

Shared fixtures:

```python
@pytest.fixture
async def db_engine():
    """Create an in-memory SQLite async engine for tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(db_engine):
    """Create a fresh database session for each test."""
    async_session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session

@pytest.fixture
async def client(db_session):
    """Create a test client with the real app but test database."""
    # Override the get_db dependency to use test session
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(app=app, base_url="http://test") as client:
        client.headers["X-API-Key"] = "test-key"
        yield client
    app.dependency_overrides.clear()

@pytest.fixture
def settings():
    """Test settings with test API key."""
    # Override settings for tests
    return get_settings()  # With JARVIS_API_KEY="test-key" for test env
```

Note: SQLite doesn't support some PostgreSQL features (GIN indexes, gen_random_uuid()). The conftest must handle this:
- Use Python-generated UUIDs in test fixtures instead of relying on DB defaults.
- The GIN index on note_text won't exist in SQLite -- search tests use LIKE which works in both.
- CHECK constraints must be tested separately against PostgreSQL.

#### `backend/tests/test_contacts.py`

Tests:

1. **Create contact** -- POST, verify 201, verify returned fields
2. **List contacts** -- Create 3 contacts, GET list, verify count and ordering
3. **Get contact detail** -- Create contact with events/notes/children, GET detail, verify nested data
4. **Update contact** -- PUT with new name, verify change persists
5. **Delete contact** -- DELETE, verify 204, verify cascade (events, notes, children deleted)
6. **Create contact validation** -- Missing name returns 422
7. **Get nonexistent contact** -- Returns 404
8. **API key required** -- Request without X-API-Key returns 401

#### `backend/tests/test_events.py`

Tests:

1. **Add birthday event** -- POST to contact, verify created
2. **Add anniversary event** -- With label, verify stored
3. **Add child_birthday event** -- With child_id, verify linked
4. **Update event** -- Change day/month, verify persisted
5. **Delete event** -- Verify removed
6. **Invalid day** -- day=32 returns 422
7. **Invalid month** -- month=13 returns 422
8. **Contact not found** -- POST to nonexistent contact returns 404
9. **Cascade delete** -- Delete contact, verify events are gone

#### `backend/tests/test_upcoming.py`

Tests:

1. **Basic upcoming** -- Event 10 days from now appears in 30-day window
2. **Event outside window** -- Event 45 days from now does NOT appear in 30-day window
3. **Year-end wrap-around** -- Simulate today=Dec 26, event on Jan 2. With days=30, event appears. (Requires passing a mock `today` to the query logic or testing with a known date.)
4. **Feb 29 in non-leap year** -- Event on Feb 29, current year is not leap year. Upcoming shows it as Feb 28.
5. **Feb 29 in leap year** -- Event on Feb 29, current year IS leap year. Shows as Feb 29.
6. **Sorting** -- Multiple events at different future dates, verify sorted by soonest first
7. **Past event this year** -- Birthday was last month. Should show next year's occurrence.
8. **Today's event** -- Event today appears with days_until=0

#### `backend/tests/test_search.py`

Tests:

1. **Search by contact name** -- "Mark" matches contact named "Mark"
2. **Search by partial name** -- "mar" matches "Mark" (case insensitive)
3. **Search by note text** -- "promoted" matches note "Mark got promoted at work"
4. **Search by child name** -- "Emma" matches child named "Emma"
5. **Search by relationship** -- "colleague" matches contacts with that relationship
6. **No results** -- "xyz123" returns empty list
7. **Multiple matches** -- "Mark" matches contact name AND a note mentioning Mark

#### `backend/tests/test_reminder_engine.py`

**Critical tests** -- these validate the core reliability requirement (NFR-001).

1. **Normal 7-day reminder** -- Event in 7 days, config with days_before=7. Engine sends reminder.
2. **Normal 1-day reminder** -- Event tomorrow, config with days_before=1. Engine sends reminder.
3. **Day-of reminder** -- Event today, config with days_before=0. Engine sends reminder.
4. **Year-end wrap-around** -- Today=Dec 26, event on Jan 2, config days_before=7. Reminder date is Dec 26. Engine sends.
5. **Feb 29 non-leap year** -- Event on Feb 29, year 2025 (not leap). Engine treats as Feb 28. Reminder for 7 days before Feb 28 fires on Feb 21.
6. **Feb 29 leap year** -- Event on Feb 29, year 2028 (leap). Engine uses Feb 29. Reminder for 7 days before fires on Feb 22.
7. **Idempotency** -- Run engine twice on the same day. First run sends, second run skips. Verify SentReminder count = 1.
8. **Note surfacing** -- Contact has notes. Reminder message includes the most recent note.
9. **Multiple events same day** -- Two contacts with same birthday. Both get reminders.
10. **Disabled config** -- Config with enabled=False. No reminder sent.
11. **Non-recurring event** -- Event with recurring=False. No reminder sent.
12. **Message format: 7-day** -- Verify message contains "in 7 days" and event date.
13. **Message format: 1-day** -- Verify message contains "tomorrow".
14. **Message format: day-of** -- Verify message contains "Today is".
15. **Age calculation** -- Event with year set. Message includes "turns {age}".

For tests that involve Telegram sends, mock the `telegram_sender.send_to_all_users` function to capture messages without actually sending.

For date-dependent tests, inject a specific `today` date into the engine rather than using the real current date.

### What to test

```bash
cd /Users/vincent/jarvis/backend
source .venv/bin/activate

# Run all tests
pytest -v

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Lint
ruff check .
```

All tests must pass before proceeding to Step 6.

### Git commit

```
test: comprehensive test suite for backend

- Contact CRUD tests with cascade delete verification
- Event CRUD tests with validation edge cases
- Upcoming events: year-boundary, Feb 29, sorting, today's events
- Search: partial match, case insensitive, multi-table
- Reminder engine: 7-day, 1-day, day-of, year wrap, Feb 29,
  idempotency, note surfacing, multiple events, disabled config
- Test fixtures with in-memory SQLite
```

---

## Step 6: Bot Scaffold (Claudegram Fork)

Fork the relevant Claudegram files into `bot/` and adapt for Jarvis. The bot is a Grammy + Claude Agent SDK integration that passes user messages to a Claude Code session.

### Key architectural difference from Claudegram

Jarvis bot is much simpler than Claudegram. We strip out:
- Reddit fetching, Medium extraction, media download, TTS, Telegraph, voice transcription
- Multiple project support (Jarvis always points at `/Users/vincent/jarvis`)
- Complex command handlers (/plan, /explore, /loop, /teleport, etc.)

We keep:
- Core Grammy bot setup with auto-retry and sequentialize
- Auth middleware (user whitelist)
- Claude Agent SDK integration (`query()` function)
- Session management (Claude Code session persistence across messages)
- Message sender (streaming + wait modes)
- Conversation history tracking

### Files to create

#### `bot/package.json`

```json
{
  "name": "jarvis-bot",
  "version": "0.1.0",
  "description": "Jarvis household assistant Telegram bot",
  "type": "module",
  "main": "dist/index.js",
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js",
    "lint": "tsc --noEmit",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "@anthropic-ai/claude-agent-sdk": "^0.2.39",
    "@grammyjs/auto-retry": "^2.0.2",
    "@grammyjs/runner": "^2.0.3",
    "dotenv": "^16.4.7",
    "grammy": "^1.31.3",
    "zod": "^4.3.6"
  },
  "devDependencies": {
    "@types/node": "^20.17.14",
    "tsx": "^4.19.2",
    "typescript": "^5.7.3"
  }
}
```

#### `bot/tsconfig.json`

Same as Claudegram:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

#### `bot/src/config.ts`

Jarvis-specific configuration. Simplified from Claudegram:

```typescript
// Required env vars:
// TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS, USER_NAMES, JARVIS_API_KEY,
// WORKSPACE_DIR (default: /Users/vincent/jarvis), BOT_NAME (default: Jarvis),
// DANGEROUS_MODE, STREAMING_MODE, MAX_MESSAGE_LENGTH, STREAMING_DEBOUNCE_MS,
// CLAUDE_SDK_LOG_LEVEL, CANCEL_ON_NEW_MESSAGE
```

The `USER_NAMES` env var is a JSON string mapping Telegram user ID to display name:
```
USER_NAMES={"12345":"Vincent","67890":"Christianne"}
```

Parsed at startup into a `Map<number, string>`.

#### `bot/src/index.ts`

Entry point. Adapted from Claudegram `index.ts`:

```typescript
async function main() {
    console.log("Starting Jarvis...");
    const bot = await createBot();
    await bot.init();
    console.log(`Bot started as @${bot.botInfo.username}`);
    const runner = run(bot);

    // Graceful shutdown
    // ...same pattern as Claudegram
}
```

Differences from Claudegram:
- No caffeinate (launchd handles process lifecycle)
- No scheduler (reminders are cron-based, not in-process)
- No deduplication cleanup (simpler bot)

#### `bot/src/bot/bot.ts`

Grammy bot setup. Much simpler than Claudegram:

**Commands registered:**
- `/start` -- Welcome message with what Jarvis can do
- `/cancel` -- Cancel running query
- `/clear` -- Clear conversation history
- `/upcoming` -- Shortcut: runs "show me upcoming events" through Claude
- `/contacts` -- Shortcut: runs "list all contacts" through Claude
- `/search <query>` -- Shortcut: runs search through Claude
- `/help` -- What Jarvis can do

**Key difference**: Most commands are shortcuts that just pass the intent to Claude as natural language. The bot does NOT parse `/add` commands itself -- it passes "add contact..." to Claude, which uses the `add-contact` skill.

```typescript
// Middleware order:
// 1. authMiddleware (whitelist check)
// 2. /cancel (bypass sequentialize)
// 3. sequentialize (per-chat ordering)
// 4. Command handlers
// 5. Message handler (default: send to Claude)
```

#### `bot/src/bot/middleware/auth.middleware.ts`

Adapted from Claudegram. Same pattern: check `ctx.from.id` against `ALLOWED_USER_IDS`. Deny unauthorized users silently (no error message to strangers -- spec says "silently ignored").

#### `bot/src/claude/agent.ts`

The critical file. Adapted from Claudegram `agent.ts`.

**Key changes:**

1. **System prompt**: Completely rewritten for Jarvis. See Step 7 for full details.
2. **Working directory**: Always `/Users/vincent/jarvis` (no `/project` command needed).
3. **Permission mode**: `bypassPermissions` (DANGEROUS_MODE=true by default for household bot).
4. **Tools**: `{ type: 'preset', preset: 'claude_code' }` -- full Claude Code capabilities.
5. **Setting sources**: `['project', 'user']` -- loads CLAUDE.md and skills from the jarvis directory.
6. **No stripping of reasoning summary** -- Jarvis doesn't need this Claudegram feature.

Functions to keep from Claudegram:
- `sendToAgent()` -- core function, adapted
- `clearConversation()`
- `chatSessionIds` map for session persistence

Functions to remove:
- `sendLoopToAgent()` -- not needed
- `setModel()` / `getModel()` -- single model
- `stripReasoningSummary()` -- not needed

#### `bot/src/claude/session-manager.ts`

Simplified from Claudegram. Since Jarvis always uses the same working directory, the session manager just tracks:
- Claude Code session ID per chat (for conversation continuity)
- Last activity timestamp

No project switching, no stored working directories.

#### `bot/src/claude/request-queue.ts`

Copy from Claudegram with minimal changes. Handles per-chat request queuing so messages are processed in order.

#### `bot/src/bot/handlers/message.handler.ts`

Simplified from Claudegram. Handles:
- Regular text messages -> send to Claude agent
- Streaming mode support
- Queue position notification when busy

Removed: Reddit URL detection, Medium detection, media extraction, ForceReply handling for project/file/telegraph.

#### `bot/src/bot/handlers/command.handler.ts`

Simple command handlers:
- `/start` -- Welcome message
- `/cancel` -- Abort running query
- `/clear` -- Clear conversation + Claude session
- `/upcoming`, `/contacts`, `/search` -- Proxy to Claude as natural language
- `/help` -- Show capabilities

#### `bot/src/telegram/message-sender.ts`

Copy from Claudegram. Handles streaming message updates, chunking long messages for Telegram's 4096 char limit, MarkdownV2 formatting.

#### `bot/src/telegram/markdown.ts`

Copy from Claudegram. MarkdownV2 escaping utilities.

#### `bot/src/telegram/deduplication.ts`

Copy from Claudegram. Prevents processing the same message twice (Telegram retries).

### What to test

```bash
cd /Users/vincent/jarvis/bot
npm install
npm run typecheck  # Should pass with zero errors

# Start the bot in dev mode
npm run dev

# In Telegram:
# 1. Send /start to the bot -> should get welcome message
# 2. Send "hello" -> should get a response from Claude
# 3. Send from unauthorized user -> should be silently ignored
# 4. Send /cancel while idle -> should say nothing is running

# Kill the dev process
```

### Git commit

```
feat: Telegram bot scaffold forked from Claudegram

- Grammy bot with auth middleware and request queuing
- Claude Agent SDK integration with Jarvis system prompt
- Simplified from Claudegram: removed Reddit, Medium, TTS, multi-project
- Working directory fixed to /Users/vincent/jarvis
- settingSources: ['project', 'user'] for CLAUDE.md and skills
- Streaming message sender with MarkdownV2 formatting
- Commands: /start, /cancel, /clear, /upcoming, /contacts, /search, /help
```

---

## Step 7: Bot User Identity

The critical feature that makes Jarvis personal: each message carries the user's identity into the Claude Code session.

### Files to modify

#### `bot/src/claude/agent.ts` -- System prompt construction

The system prompt must include `CURRENT_USER` dynamically per message. This means the system prompt changes depending on who sent the message.

**Approach**: The `sendToAgent` function accepts the Telegram user context. Before calling `query()`, it constructs the full system prompt with the user's identity injected.

```typescript
function buildSystemPrompt(userId: number, userName: string): string {
    return `You are Jarvis, a household assistant for Vincent & Christianne.

CURRENT_USER: ${userName} (Telegram ID: ${userId})

You help manage their social circle: friends, family, important dates, and notes about people they care about. You communicate via Telegram.

How you work:
- You are a Claude Code agent with access to the Jarvis project directory
- You interact with the backend API via curl (http://localhost:8000)
- You ALWAYS include the X-API-Key header: -H "X-API-Key: $JARVIS_API_KEY"
- You NEVER access the database directly -- always through the API
- You follow the skills in .claude/skills/ for every operation
- You read CLAUDE.md for architecture and rules

API authentication:
- Every curl request to the API must include: -H "X-API-Key: $JARVIS_API_KEY"
- The JARVIS_API_KEY environment variable is available in your shell

When the user asks you to do something:
1. Identify the right skill (add-contact, search, add-note, upcoming, etc.)
2. Follow the skill's steps exactly
3. Use curl to call the API
4. Confirm what you did in a friendly, concise message

Data attribution:
- When creating contacts, events, or notes, always set created_by to "${userId}"
- When showing data, mention who added it (e.g., "Added by Vincent, 3 weeks ago")

Tone:
- Warm and helpful, like a thoughtful personal assistant
- Concise -- Telegram messages should be short
- Use emojis sparingly but naturally
- Never use jargon or technical language
- If Christianne is the user, be extra warm and example-driven (Christianne-first UX)

Response formatting:
- Keep responses short for Telegram (under 1000 chars when possible)
- Use bullet points for lists
- Bold names and dates for scannability`;
}
```

#### `bot/src/bot/handlers/message.handler.ts` -- Pass user identity

The message handler extracts user ID and name from the Telegram context and passes them to `sendToAgent`:

```typescript
const userId = ctx.from?.id;
const userName = config.USER_NAMES.get(userId) || `User ${userId}`;
// Pass to agent
await sendToAgent(chatId, text, { userId, userName, ... });
```

#### `bot/src/claude/agent.ts` -- `sendToAgent` accepts user identity

```typescript
interface AgentOptions {
    userId: number;
    userName: string;
    onProgress?: (text: string) => void;
    abortController?: AbortController;
}

export async function sendToAgent(
    chatId: number,
    message: string,
    options: AgentOptions
): Promise<AgentResponse> {
    const systemPrompt = buildSystemPrompt(options.userId, options.userName);

    const response = query({
        prompt: message,
        options: {
            cwd: "/Users/vincent/jarvis",
            systemPrompt: {
                type: "preset",
                preset: "claude_code",
                append: systemPrompt,
            },
            settingSources: ["project", "user"],
            permissionMode: "bypassPermissions",
            allowDangerouslySkipPermissions: true,
            tools: { type: "preset", preset: "claude_code" },
            model: "opus",
            resume: existingSessionId,
            // ...
        },
    });

    // ... process response
}
```

### What to test

```bash
cd /Users/vincent/jarvis/bot
npm run typecheck

# Start the bot
npm run dev

# Test as Vincent:
# 1. Send "who am I?" -> Claude should respond with Vincent's name and ID
# 2. Send "add my friend Mark, birthday June 14" -> Should create contact with created_by = Vincent's ID

# Test as Christianne:
# 1. Send "who am I?" -> Claude should respond with Christianne's name and ID
# 2. Send "show me Mark's contact" -> Should work and show the contact

# Verify in database:
psql jarvis -c "SELECT name, created_by FROM contacts WHERE name='Mark';"
# created_by should be Vincent's Telegram user ID
```

### Git commit

```
feat: user identity injection into Claude Code sessions

- System prompt dynamically includes CURRENT_USER per message
- USER_NAMES config maps Telegram IDs to display names
- All data mutations carry created_by with the user's Telegram ID
- Christianne-first UX: warmer tone detection based on user identity
```

---

## Step 8: Proactive Engine Deployment

Set up launchd plists so the backend, bot, and daily reminder cron run automatically on the Mac mini.

### Files to create

#### `deploy/com.jarvis.backend.plist`

launchd plist for the FastAPI backend. Starts on boot, restarts on crash.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.jarvis.backend</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/vincent/jarvis/backend/.venv/bin/uvicorn</string>
        <string>src.main:app</string>
        <string>--host</string>
        <string>127.0.0.1</string>
        <string>--port</string>
        <string>8000</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/vincent/jarvis/backend</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/Users/vincent/jarvis/backend/.venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/vincent/jarvis/logs/backend.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/vincent/jarvis/logs/backend.error.log</string>
</dict>
</plist>
```

#### `deploy/com.jarvis.bot.plist`

launchd plist for the Telegram bot. Same pattern as backend.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.jarvis.bot</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/node</string>
        <string>/Users/vincent/jarvis/bot/dist/index.js</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/vincent/jarvis/bot</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>NODE_ENV</key>
        <string>production</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/vincent/jarvis/logs/bot.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/vincent/jarvis/logs/bot.error.log</string>
</dict>
</plist>
```

#### `deploy/com.jarvis.reminder.plist`

launchd plist for the daily 08:00 Europe/Amsterdam reminder cron.

**Important**: launchd uses the system timezone. If the Mac mini is set to Europe/Amsterdam, `Hour=8` fires at 08:00 local time. Verify with `sudo systemsetup -gettimezone`.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.jarvis.reminder</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/vincent/jarvis/deploy/run_reminders.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/vincent/jarvis/logs/reminder.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/vincent/jarvis/logs/reminder.error.log</string>
</dict>
</plist>
```

#### `deploy/run_reminders.sh`

Shell script that calls the reminder engine endpoint:

```bash
#!/bin/bash
set -euo pipefail

# Load API key from .env
JARVIS_API_KEY=$(grep JARVIS_API_KEY /Users/vincent/jarvis/.env | cut -d'=' -f2)

echo "[$(date)] Running reminder engine..."

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  -H "X-API-Key: $JARVIS_API_KEY" \
  http://localhost:8000/api/reminders/run)

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -1)

echo "[$(date)] Response: HTTP $HTTP_CODE - $BODY"

if [ "$HTTP_CODE" != "200" ]; then
  echo "[$(date)] ERROR: Reminder engine returned HTTP $HTTP_CODE"
  exit 1
fi

echo "[$(date)] Reminder engine completed successfully"
```

Make executable: `chmod +x deploy/run_reminders.sh`

#### `deploy/install.sh`

Installation script for all launchd plists:

```bash
#!/bin/bash
set -euo pipefail

PLIST_DIR="/Users/vincent/jarvis/deploy"
LAUNCH_DIR="$HOME/Library/LaunchAgents"

# Create logs directory
mkdir -p /Users/vincent/jarvis/logs

# Build bot before installing
echo "Building bot..."
cd /Users/vincent/jarvis/bot && npm run build

# Copy plists
for plist in com.jarvis.backend.plist com.jarvis.bot.plist com.jarvis.reminder.plist; do
  cp "$PLIST_DIR/$plist" "$LAUNCH_DIR/$plist"
  echo "Installed $plist"
done

# Load services
launchctl load "$LAUNCH_DIR/com.jarvis.backend.plist"
launchctl load "$LAUNCH_DIR/com.jarvis.bot.plist"
launchctl load "$LAUNCH_DIR/com.jarvis.reminder.plist"

echo "All Jarvis services installed and started"
```

Make executable: `chmod +x deploy/install.sh`

#### Heartbeat check in the bot

Add a daily check to the bot (not a separate cron -- the bot checks at 09:00 if the reminder engine ran):

This can be done as a simple `setInterval` in the bot's `index.ts` or as a lightweight in-process scheduler:

```typescript
// In bot/src/index.ts, after bot starts:
// Check heartbeat every hour. Alert if stale (>25 hours since last run).
setInterval(async () => {
    const now = new Date();
    const hour = now.getHours(); // Local time (Europe/Amsterdam if system TZ is set)
    if (hour !== 9) return; // Only check at 09:xx

    try {
        const response = await fetch("http://localhost:8000/api/health");
        const data = await response.json();

        if (!data.last_successful_reminder_run) {
            await alertVincent("Reminder engine has never run successfully.");
            return;
        }

        const lastRun = new Date(data.last_successful_reminder_run);
        const hoursAgo = (now.getTime() - lastRun.getTime()) / (1000 * 60 * 60);

        if (hoursAgo > 25) {
            await alertVincent(
                `Reminder engine is stale. Last run: ${lastRun.toISOString()} (${Math.floor(hoursAgo)} hours ago)`
            );
        }
    } catch (error) {
        await alertVincent(`Health check failed: ${error}`);
    }
}, 60 * 60 * 1000); // Check every hour
```

The `alertVincent` function sends a Telegram message to Vincent's user ID using the bot API directly (not through Claude).

### What to test

```bash
# Verify system timezone
sudo systemsetup -gettimezone
# Should be Europe/Amsterdam

# Create logs directory
mkdir -p /Users/vincent/jarvis/logs

# Test run_reminders.sh manually
bash /Users/vincent/jarvis/deploy/run_reminders.sh
# Should show "completed successfully"

# Test launchd plists (load one at a time)
cp deploy/com.jarvis.backend.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.jarvis.backend.plist
curl -s http://localhost:8000/api/health
# Should return {"status": "ok", ...}

# Stop and clean up (if just testing)
launchctl unload ~/Library/LaunchAgents/com.jarvis.backend.plist

# Full installation
bash deploy/install.sh

# Verify all services are running
launchctl list | grep jarvis
# Should show 3 entries

# Verify bot responds
# Send a message to the bot in Telegram

# Verify reminder cron
# Wait for 08:00 or manually trigger:
bash deploy/run_reminders.sh

# Check logs
tail -20 /Users/vincent/jarvis/logs/backend.log
tail -20 /Users/vincent/jarvis/logs/bot.log
tail -20 /Users/vincent/jarvis/logs/reminder.log
```

### Git commit

```
feat: launchd deployment for backend, bot, and daily reminder cron

- com.jarvis.backend.plist: FastAPI auto-start and crash recovery
- com.jarvis.bot.plist: Telegram bot auto-start and crash recovery
- com.jarvis.reminder.plist: daily 08:00 Europe/Amsterdam cron
- run_reminders.sh: curl-based trigger for POST /api/reminders/run
- install.sh: one-command setup for all launchd services
- Heartbeat check: bot alerts Vincent if reminder engine is stale
```

---

## Step 9: Go Live

This step is not code -- it is the operational launch checklist.

### 9.1 Pre-launch verification

- [ ] All tests pass: `cd /Users/vincent/jarvis/backend && pytest -v`
- [ ] Bot type-checks: `cd /Users/vincent/jarvis/bot && npm run typecheck`
- [ ] Backend lint: `cd /Users/vincent/jarvis/backend && ruff check .`
- [ ] Backend is running: `curl -s http://localhost:8000/api/health`
- [ ] Bot is running: send `/start` in Telegram
- [ ] Reminder cron is loaded: `launchctl list | grep com.jarvis.reminder`
- [ ] System timezone is Europe/Amsterdam: `sudo systemsetup -gettimezone`
- [ ] `.env` has correct Telegram user IDs for both Vincent and Christianne
- [ ] Default reminder configs exist: `psql jarvis -c "SELECT * FROM reminder_configs WHERE event_id IS NULL;"`

### 9.2 Seed initial contacts

Start a conversation with the bot and add contacts naturally:

> "Add my friend Mark, he's a friend, birthday June 14. He just got promoted at work."

> "Mark and Lisa's anniversary is June 15."

> "Mark and Lisa have a daughter named Emma, her birthday is June 16."

> "Add my colleague Sarah, birthday November 3."

Continue until all key contacts are entered. Verify with:

> "Show me all contacts"

> "What's coming up in the next 30 days?"

### 9.3 First week monitoring

- [ ] Day 1: Verify both Vincent and Christianne can add contacts and notes
- [ ] Day 1: Verify `/upcoming` works correctly
- [ ] Day 1: Verify `/search` finds contacts by name and notes by content
- [ ] Day 2: Check `logs/reminder.log` -- did the 08:00 cron fire?
- [ ] Day 2: Check `logs/backend.log` and `logs/bot.log` for errors
- [ ] Day 7: Verify a 7-day reminder was sent (if any event is 7 days away)
- [ ] Day 7: Run `/post-incident` for any issues encountered

### 9.4 Post-launch

- [ ] Update `STATUS.md` with "Phase 1: Shipped" status
- [ ] Update `ROADMAP.md` with "Shipped" status for SPEC-001
- [ ] Update `specs/001-social-circle.md` status from "Approved" to "Shipped"
- [ ] Celebrate -- Jarvis is alive

### Git commit

```
docs: update status after go-live

- STATUS.md: Phase 1 shipped
- ROADMAP.md: SPEC-001 shipped
- specs/001-social-circle.md: status updated to Shipped
```

---

## Summary: File Map

All files created or modified by this plan, organized by step.

### Step 1: Backend Scaffold

```
backend/pyproject.toml                    -- NEW
backend/src/__init__.py                   -- NEW
backend/src/main.py                       -- NEW
backend/src/config.py                     -- NEW
backend/src/database.py                   -- NEW
backend/alembic.ini                       -- NEW
backend/alembic/env.py                    -- NEW
backend/alembic/script.py.mako            -- NEW
backend/alembic/versions/                 -- NEW (empty dir)
.env.example                              -- NEW
```

### Step 2: Database Models + Migration

```
backend/src/models/__init__.py            -- NEW
backend/src/models/contact.py             -- NEW
backend/src/models/event.py               -- NEW
backend/src/models/child.py               -- NEW
backend/src/models/note.py                -- NEW
backend/src/models/reminder.py            -- NEW
backend/alembic/versions/001_initial.py   -- NEW (autogenerated)
backend/scripts/seed_reminders.py         -- NEW
```

### Step 3: CRUD Routes

```
backend/src/schemas/__init__.py           -- NEW
backend/src/schemas/contact.py            -- NEW
backend/src/schemas/event.py              -- NEW
backend/src/schemas/child.py              -- NEW
backend/src/schemas/note.py               -- NEW
backend/src/schemas/reminder.py           -- NEW
backend/src/schemas/upcoming.py           -- NEW
backend/src/schemas/search.py             -- NEW
backend/src/routes/__init__.py            -- NEW
backend/src/routes/contacts.py            -- NEW
backend/src/routes/events.py              -- NEW
backend/src/routes/children.py            -- NEW
backend/src/routes/notes.py               -- NEW
backend/src/routes/upcoming.py            -- NEW
backend/src/routes/search.py              -- NEW
backend/src/routes/reminders.py           -- NEW
backend/src/routes/health.py              -- NEW (or MODIFIED if created in Step 1)
backend/src/main.py                       -- MODIFIED (wire routes)
```

### Step 4: Proactive Engine

```
backend/src/engine/__init__.py            -- NEW
backend/src/engine/reminder_engine.py     -- NEW
backend/src/engine/message_builder.py     -- NEW
backend/src/engine/telegram_sender.py     -- NEW
backend/src/engine/heartbeat.py           -- NEW
backend/src/routes/reminders.py           -- MODIFIED (replace stub)
backend/src/routes/health.py              -- MODIFIED (add heartbeat)
```

### Step 5: Tests

```
backend/tests/__init__.py                 -- NEW
backend/tests/conftest.py                 -- NEW
backend/tests/test_contacts.py            -- NEW
backend/tests/test_events.py              -- NEW
backend/tests/test_upcoming.py            -- NEW
backend/tests/test_search.py              -- NEW
backend/tests/test_reminder_engine.py     -- NEW
```

### Step 6: Bot Scaffold

```
bot/package.json                          -- NEW
bot/tsconfig.json                         -- NEW
bot/src/index.ts                          -- NEW
bot/src/config.ts                         -- NEW
bot/src/bot/bot.ts                        -- NEW
bot/src/bot/middleware/auth.middleware.ts  -- NEW
bot/src/bot/handlers/message.handler.ts   -- NEW
bot/src/bot/handlers/command.handler.ts   -- NEW
bot/src/claude/agent.ts                   -- NEW
bot/src/claude/session-manager.ts         -- NEW
bot/src/claude/request-queue.ts           -- NEW
bot/src/telegram/message-sender.ts        -- NEW
bot/src/telegram/markdown.ts              -- NEW
bot/src/telegram/deduplication.ts         -- NEW
```

### Step 7: Bot User Identity

```
bot/src/claude/agent.ts                   -- MODIFIED (dynamic system prompt)
bot/src/bot/handlers/message.handler.ts   -- MODIFIED (pass user identity)
bot/src/config.ts                         -- MODIFIED (USER_NAMES parsing)
```

### Step 8: Deployment

```
deploy/com.jarvis.backend.plist           -- NEW
deploy/com.jarvis.bot.plist               -- NEW
deploy/com.jarvis.reminder.plist          -- NEW
deploy/run_reminders.sh                   -- NEW
deploy/install.sh                         -- NEW
bot/src/index.ts                          -- MODIFIED (heartbeat check)
```

### Step 9: Go Live

```
STATUS.md                                 -- MODIFIED
ROADMAP.md                                -- MODIFIED
specs/001-social-circle.md                -- MODIFIED (status -> Shipped)
```

---

## Dependency Graph

```
Step 0 (Prerequisites)
  |
  v
Step 1 (Backend Scaffold) -----> Step 2 (Models + Migration)
                                    |
                                    v
                                  Step 3 (CRUD Routes)
                                    |
                                    v
                                  Step 4 (Proactive Engine)
                                    |
                                    v
                                  Step 5 (Tests)
                                    |
Step 6 (Bot Scaffold) ----------> Step 7 (User Identity)
  |                                 |
  v                                 v
Step 8 (Deployment) <------- [both Step 5 and Step 7 must be done]
  |
  v
Step 9 (Go Live)
```

Note: Steps 1-5 (backend) and Step 6 (bot scaffold) are independent and can be built in parallel by separate sessions. Step 7 depends on Step 6. Step 8 depends on both tracks being complete. Step 9 depends on Step 8.

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Feb 29 edge case missed in implementation | Dedicated test cases in test_upcoming.py and test_reminder_engine.py. Test with mock dates 2025 (non-leap) and 2028 (leap). |
| Year-boundary reminders fire twice (Dec and Jan runs) | SentReminder unique constraint on (event_id, config_id, event_date) prevents duplicates. Engine is idempotent by design. |
| Telegram send fails for one user | telegram_sender catches per-user errors, continues to other users. Logged but not fatal. |
| Mac mini restarts overnight, cron missed | launchd fires missed calendar events on next boot. Engine is idempotent. Heartbeat check alerts at 09:00 if stale. |
| SQLite test DB doesn't match PostgreSQL behavior | Critical edge cases (CHECK constraints, GIN index) tested manually against PostgreSQL. In-memory SQLite for speed on standard CRUD. |
| Bot session context exceeds Claude's context window | Claude Agent SDK handles compaction automatically. Jarvis conversations are typically short (one action per message). |
| Reminder messages too verbose | Message builder keeps messages under 500 chars. Notes truncated to last 1-2 entries. |

---

## Spec Requirements Traceability

| Requirement | Covered In |
|-------------|-----------|
| REQ-001: Add/edit/delete contacts | Step 3: routes/contacts.py |
| REQ-002: Track birthdays | Step 2: models/event.py, Step 3: routes/events.py |
| REQ-003: Track anniversaries | Step 2: models/event.py, Step 3: routes/events.py |
| REQ-004: Track children | Step 2: models/child.py, Step 3: routes/children.py |
| REQ-005: Free-form notes | Step 2: models/note.py, Step 3: routes/notes.py |
| REQ-006: Configurable reminders | Step 2: models/reminder.py, Step 4: reminder_engine.py |
| REQ-007: Reminders to both users | Step 4: telegram_sender.py |
| REQ-008: List upcoming events | Step 3: routes/upcoming.py |
| REQ-009: Search contacts + notes | Step 3: routes/search.py |
| REQ-010: Telegram bot commands | Step 6: bot/bot.ts |
| REQ-011: Both users, shared data | Step 7: user identity |
| NFR-001: Reliability + idempotency | Step 4: SentReminder dedup, Step 5: idempotency tests |
| NFR-002: Response time <2s | Step 3: indexed queries |
| NFR-003: PostgreSQL + backups | Step 0: PostgreSQL setup |
| AC-001 through AC-010 | Covered across Steps 3-7 and verified in Step 5 tests |
