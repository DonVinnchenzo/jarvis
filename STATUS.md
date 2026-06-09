# STATUS.md — Current State of Jarvis

**Any new Claude session: READ THIS FIRST before doing anything.**

This file is the single source of truth for where the project stands. It is updated after every significant action. If this chat disconnects, the next session reads this file and picks up exactly where we left off.

---

## Current Phase

**Phase 1: Foundation + Social Circle**

## Current Step

**Building: Steps 3-4 in progress (CRUD routes + proactive engine)**

Steps 0-2 are complete. Steps 3-4 are being built by a sub-agent. When they finish, proceed to Step 5 (tests).

## Completed Steps

- **Step 0: Prerequisites** — DONE. PostgreSQL 16 installed (Homebrew), `jarvis` database created, Python 3.12 venv set up.
- **Step 1: Backend scaffold** — DONE. FastAPI app with API key middleware, Pydantic settings, SQLAlchemy async engine, Alembic setup. Verified: health returns OK, wrong API key returns 401.
- **Step 2: Models + migration** — DONE. 6 models (Contact, ContactEvent, ContactChild, ContactNote, ReminderConfig, SentReminder). First Alembic migration applied. 3 default ReminderConfig rows seeded (7, 1, 0 days). CHECK constraints and UNIQUE constraint verified.
- **Steps 3-4: CRUD routes + engine** — IN PROGRESS. Sub-agent building schemas, routes, proactive engine.

## What to do next

1. **If Steps 3-4 just completed** — Verify by running:
   ```bash
   cd /Users/vincent/jarvis/backend && source .venv/bin/activate && ruff check .
   ```
   Then start the server and smoke test CRUD endpoints. See implementation plan Step 3 "What to test" section.
2. **Step 5: Tests** — Write test suite (5 files, 40+ cases). See implementation plan.
3. **Step 6: Bot scaffold** — Fork Claudegram into bot/. Can run in parallel with Step 5.
4. **Step 7: User identity** — Dynamic CURRENT_USER injection.
5. **Step 8: Deployment** — launchd plists.
6. **Step 9: Go live** — Seed contacts, monitor.

## Key files for current work

- `backend/src/main.py` — FastAPI app entry point
- `backend/src/models/` — All 6 SQLAlchemy models
- `backend/src/routes/` — Route files (being created)
- `backend/src/schemas/` — Pydantic schemas (being created)
- `backend/src/engine/` — Proactive engine (being created)
- `Ideation/SOCIAL-CIRCLE-IMPLEMENTATION-PLAN.md` — Full build plan

## Key decisions already made

- **Hosting**: Self-hosted on Mac mini (localhost only)
- **Bot architecture**: Claude Code agent via Claudegram fork (Grammy + Claude Agent SDK)
- **AI cost model**: Claude Code Max subscription (flat rate)
- **User identity**: System prompt includes `CURRENT_USER: {name} (Telegram ID: {id})`
- **Data visibility**: Default shared, optional personal
- **Reminders**: 7 days, 1 day, and day-of (0 days) as defaults
- **Feb 29**: Use Feb 28 in non-leap years
- **Timezone**: Europe/Amsterdam
- **Natural language first**: Slash commands are optional shortcuts, not primary interface
- **Spec approved**: SPEC-001 approved 2026-06-09
- **Database URL**: postgresql+asyncpg://vincent@localhost/jarvis
- **API key**: Stored in .env as JARVIS_API_KEY

## Recent history

- 2026-06-09: Created GitHub repo (github.com/DonVinnchenzo/jarvis)
- 2026-06-09: Set up ClaryBook-style framework, 19 skills, session continuity
- 2026-06-09: SPEC-001 written, reviewed (3-way), approved
- 2026-06-09: Implementation plan written (9 steps, 60+ files)
- 2026-06-09: Step 0 complete — PostgreSQL 16 installed, jarvis DB created
- 2026-06-09: Steps 1-2 complete — Backend scaffold, models, migration, seeded reminders
- 2026-06-09: Steps 3-4 in progress — CRUD routes and proactive engine being built

---

*Updated: 2026-06-09*
