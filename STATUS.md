# STATUS.md — Current State of Jarvis

**Any new Claude session: READ THIS FIRST before doing anything.**

This file is the single source of truth for where the project stands. It is updated after every significant action. If this chat disconnects, the next session reads this file and picks up exactly where we left off.

---

## Current Phase

**Phase 1: Foundation + Social Circle** (build in progress)
**Phase 2: Morning Briefing** (spec approved, not yet built)

## Current Step

**Social Circle: Steps 0-4 complete. Step 5 (tests) is next.**
**Morning Briefing: SPEC-002 approved. Implementation plan needed before build.**

## Completed Steps

### Social Circle (SPEC-001)
- **Step 0: Prerequisites** — DONE. PostgreSQL 16 installed (Homebrew), `jarvis` database created, Python 3.12 venv set up.
- **Step 1: Backend scaffold** — DONE. FastAPI app with API key middleware, Pydantic settings, SQLAlchemy async engine, Alembic setup.
- **Step 2: Models + migration** — DONE. 6 models (Contact, ContactEvent, ContactChild, ContactNote, ReminderConfig, SentReminder). First Alembic migration applied. 3 default ReminderConfig rows seeded.
- **Steps 3-4: CRUD routes + proactive engine** — DONE. 8 route files, 7 schema files, 4 engine files. Lint passes, smoke tests pass (create, add event, add note, upcoming, search, delete all work).

### Morning Briefing (SPEC-002)
- **Ideation research** — DONE. API research in `Ideation/MORNING-BRIEFING-RESEARCH.md`.
- **Spec** — DONE. `specs/002-morning-briefing.md` — written, reviewed (product + backend), blockers resolved, approved.

## What to do next

1. **Social Circle Step 5: Tests** — Write test suite (5 files, 40+ cases). See `Ideation/SOCIAL-CIRCLE-IMPLEMENTATION-PLAN.md` Step 5.
   ```bash
   cd /Users/vincent/jarvis/backend && source .venv/bin/activate && pytest
   ```
2. **Social Circle Step 6: Bot scaffold** — Fork Claudegram into `bot/`. Can run in parallel with Step 5. See implementation plan Step 6.
3. **Social Circle Step 7: User identity** — Dynamic CURRENT_USER injection into Claude Code system prompt per message.
4. **Social Circle Step 8: Deployment** — 3 launchd plists (backend, bot, reminder cron).
5. **Social Circle Step 9: Go live** — Seed contacts, monitor.
6. **Morning Briefing: Implementation plan** — Run `implementation-plan` skill against SPEC-002 before building.
7. **Morning Briefing: Build** — After plan is written, follow it. Weather fetcher, Divvy fetcher, briefing engine, 07:00 CT cron, new operational skills.

## Key files for current work

- `backend/src/main.py` — FastAPI app entry point
- `backend/src/models/` — All 6 SQLAlchemy models
- `backend/src/routes/` — 8 route files (contacts, events, children, notes, upcoming, search, reminders, health)
- `backend/src/schemas/` — 7 Pydantic schema files
- `backend/src/engine/` — Proactive engine (reminder_engine, message_builder, telegram_sender, heartbeat)
- `Ideation/SOCIAL-CIRCLE-IMPLEMENTATION-PLAN.md` — Full build plan (Steps 5-9 remain)
- `specs/001-social-circle.md` — Approved spec
- `specs/002-morning-briefing.md` — Approved spec

## Key decisions already made

- **Hosting**: Self-hosted on Mac mini (localhost only)
- **Bot architecture**: Claude Code agent via Claudegram fork (Grammy + Claude Agent SDK)
- **AI cost model**: Claude Code Max subscription (flat rate)
- **User identity**: System prompt includes `CURRENT_USER: {name} (Telegram ID: {id})`
- **Data visibility**: Default shared, optional personal
- **Reminders**: 7 days, 1 day, and day-of (0 days) as defaults
- **Feb 29**: Use Feb 28 in non-leap years
- **Social Circle timezone**: Europe/Amsterdam
- **Morning Briefing timezone**: America/Chicago (07:00 CT)
- **Morning Briefing v1**: Hardcode all config, no ModuleConfig table
- **Morning Briefing APIs**: Open-Meteo (weather) + Divvy GBFS (bikes), both free/no-auth
- **Morning Briefing fetch**: Parallel via asyncio.gather(return_exceptions=True)
- **Morning Briefing weekends**: Skip (no commute)
- **Natural language first**: Slash commands are optional shortcuts, not primary interface
- **Database URL**: postgresql+asyncpg://vincent@localhost/jarvis
- **API key**: Stored in .env as JARVIS_API_KEY

## Recent history

- 2026-06-09: Created GitHub repo (github.com/DonVinnchenzo/jarvis)
- 2026-06-09: Set up ClaryBook-style framework, 19 skills, session continuity
- 2026-06-09: SPEC-001 written, reviewed (3-way), approved
- 2026-06-09: Implementation plan written (9 steps, 60+ files)
- 2026-06-09: Steps 0-4 complete — PostgreSQL, backend scaffold, models, migration, CRUD routes, proactive engine
- 2026-06-09: SPEC-002 Morning Briefing — researched, written, reviewed, blockers resolved, approved
- 2026-06-09: Updated STATUS.md with full current state

---

*Updated: 2026-06-09*
