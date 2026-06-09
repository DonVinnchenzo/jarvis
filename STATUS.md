# STATUS.md — Current State of Jarvis

**Any new Claude session: READ THIS FIRST before doing anything.**

This file is the single source of truth for where the project stands. It is updated after every significant action. If this chat disconnects, the next session reads this file and picks up exactly where we left off.

---

## Current Phase

**Phase 1: Foundation + Social Circle**

## Current Step

**Implementation plan written → Next: Vincent approves plan, then start building (Step 0: Prerequisites)**

SPEC-001 is approved. The implementation plan is written with 9 detailed steps. Awaiting Vincent's go-ahead to start building.

## What to do next

1. **Get Vincent's approval on the implementation plan** — He's seen the summary. If he says go, start at Step 0.
2. **Step 0: Prerequisites** — Install PostgreSQL via Homebrew, create `jarvis` database, create bot via BotFather, set up `.env`, Python venv, Node.js deps. See `Ideation/SOCIAL-CIRCLE-IMPLEMENTATION-PLAN.md` for full details.
3. **Step 1: Backend scaffold** — FastAPI app, config, database engine, Alembic setup. 9 files.
4. **Step 2: Database models + migration** — 6 SQLAlchemy models, first Alembic migration, seed 3 default reminder configs.
5. **Step 3: CRUD routes** — 8 route files + 7 schema files. Contacts, events, children, notes, upcoming, search, reminders, health.
6. **Step 4: Proactive engine** — reminder_engine.py, message_builder.py, telegram_sender.py, heartbeat.
7. **Step 5: Tests** — 5 test files, 40+ cases. Critical: year-boundary, Feb 29, idempotency, note surfacing.
8. **Step 6: Bot scaffold** — Fork Claudegram into bot/, strip unnecessary features, wire to Jarvis project.
9. **Step 7: User identity** — Dynamic system prompt with CURRENT_USER injection per message.
10. **Step 8: Deployment** — 3 launchd plists (backend, bot, cron), install script.
11. **Step 9: Go live** — Seed contacts via conversation, monitor, iterate.

> Note: Steps 1-5 (backend) and Step 6 (bot) can run in parallel — no dependency between them.

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

## Key files to read for context

- `CLAUDE.md` — Architecture, skills framework, rules
- `specs/001-social-circle.md` — The approved spec
- `Ideation/SOCIAL-CIRCLE-IMPLEMENTATION-PLAN.md` — **THE BUILD PLAN (step-by-step)**
- `Ideation/SOCIAL-CIRCLE-SPEC-REVIEW.md` — Review findings and resolutions
- `ROADMAP.md` — What's planned beyond Phase 1
- `docs/PRINCIPLES.md` — Building principles

## Recent history

- 2026-06-09: Created GitHub repo (github.com/DonVinnchenzo/jarvis)
- 2026-06-09: Set up ClaryBook-style framework (CLAUDE.md, 11 principles, spec template)
- 2026-06-09: Wrote SPEC-001, ran 3-way parallel review, resolved all blockers
- 2026-06-09: Architecture decisions: self-hosted Mac mini, Claudegram fork, Claude Code agent
- 2026-06-09: Created 19 skills (9 dev, 7 operational, 4 meta) including build-skill, report-issue, help, session-handoff
- 2026-06-09: Added session continuity system (STATUS.md + session-handoff skill)
- 2026-06-09: SPEC-001 approved by Vincent
- 2026-06-09: Implementation plan written (9 steps, 60+ files mapped)

---

*Updated: 2026-06-09*
