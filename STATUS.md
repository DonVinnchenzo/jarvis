# STATUS.md — Current State of Jarvis

**Any new Claude session: READ THIS FIRST before doing anything.**

---

## Current Phase

**Phase 1: Social Circle** — Steps 0-5 done, Steps 6-9 remain
**Phase 2: Morning Briefing** — Spec approved, implementation plan written, ready to build
**Phase 3: Task Reminders** — Spec approved, needs implementation plan before build

## What to do next

1. **Social Circle Step 6: Bot scaffold** — Fork Claudegram into `bot/`. This needs the Telegram bot token from Vincent (created via @BotFather). See implementation plan Step 6.
2. **Social Circle Step 7: User identity** — Dynamic CURRENT_USER injection.
3. **Social Circle Step 8: Deployment** — launchd plists.
4. **Social Circle Step 9: Go live** — Seed contacts, monitor.
5. **Morning Briefing: Build** — Follow `Ideation/MORNING-BRIEFING-IMPLEMENTATION-PLAN.md`. Can be built in parallel with Social Circle Steps 7-9.
6. **Task Reminders: Implementation plan** — Run `implementation-plan` skill against SPEC-003 before building.
7. **Task Reminders: Build** — After plan is written.

## Blocking on Vincent

- **Telegram bot token** — Vincent needs to create a bot via @BotFather and provide the token. This blocks Steps 6-9 (bot scaffold, deployment, go-live).

## Completed

### Social Circle (SPEC-001)
- Steps 0-4: Backend fully built (FastAPI, PostgreSQL, 6 models, 8 routes, proactive engine)
- Step 5: Test suite — 47 tests, all passing (contacts, events, upcoming, search, reminder engine)

### Morning Briefing (SPEC-002)
- Ideation research done
- Spec written, reviewed, approved
- Implementation plan written (9 steps)

### Task Reminders (SPEC-003)
- Ideation research done (comprehensive — data model, recurrence, interactions, integrations)
- Spec written, reviewed, approved

### Framework
- 19 skills, CLAUDE.md hierarchy, STATUS.md continuity, git workflow

## Key decisions

- Hosting: Self-hosted on Mac mini (localhost only)
- Bot: Claude Code agent via Claudegram fork (Grammy + Claude Agent SDK)
- AI cost: Claude Code Max subscription (flat rate)
- Database: postgresql+asyncpg://vincent@localhost/jarvis
- Social Circle timezone: Europe/Amsterdam
- Morning Briefing timezone: America/Chicago (07:00 CT)
- Task Reminders timezone: America/Chicago (same as Morning Briefing)
- APIs: Open-Meteo (weather, free), Divvy GBFS (bikes, free)
- Task recurrence: simple pattern strings (daily, weekly:monday, monthly:1, yearly:09-01)

## Key files

- `specs/001-social-circle.md` — Approved
- `specs/002-morning-briefing.md` — Approved
- `specs/003-task-reminders.md` — Approved
- `Ideation/SOCIAL-CIRCLE-IMPLEMENTATION-PLAN.md` — Steps 5 done, 6-9 remain
- `Ideation/MORNING-BRIEFING-IMPLEMENTATION-PLAN.md` — Ready to execute
- `Ideation/TASK-REMINDERS-RESEARCH.md` — Research complete
- `backend/src/` — All Social Circle backend code

## Recent history

- 2026-06-09: Created repo, framework, 19 skills
- 2026-06-09: SPEC-001 approved, implementation plan, Steps 0-5 built
- 2026-06-09: SPEC-002 approved, implementation plan written
- 2026-06-09: SPEC-003 ideation researched, spec approved

---

*Updated: 2026-06-09*
