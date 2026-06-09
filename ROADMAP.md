# Jarvis — Roadmap

**Last updated:** 2026-06-09

---

## Phase 1: Foundation + Social Circle (In Progress)

The minimum viable Jarvis: know our friends, remind us about important dates, help us be thoughtful.

### SPEC-001: Social Circle — Friends & Events Tracker

**Status:** In Progress (Steps 0-5 complete, Steps 6-9 remain)

**What it includes:**
- Contact management (friends, family, their kids)
- Birthday, anniversary, and kid birthday tracking
- Free-form timestamped notes per contact
- Proactive reminders (7 days, 1 day, day-of) with contextual notes
- Natural language Telegram bot for both Vincent & Christianne
- User identity tracking (who added what)
- Shared/personal visibility per contact

**Completed:**
- Backend scaffold (FastAPI, PostgreSQL, Alembic)
- 6 data models with constraints and indexes
- 8 CRUD route files, 7 Pydantic schema files
- Proactive engine (reminder engine, message builder, Telegram sender, heartbeat)
- Test suite: 47 tests, all passing

**Remaining:**
- Step 6: Bot scaffold (Claudegram fork)
- Step 7: User identity (CURRENT_USER injection)
- Step 8: Deployment (launchd plists)
- Step 9: Go live (seed contacts, monitor)

### Framework (Done)
- CLAUDE.md hierarchy with architecture, rules, user identity
- 19 skills across 4 categories (dev, operational, meta, scheduled)
- Spec template, multi-agent review process
- Incident tracking system
- Christianne-first UX principle
- STATUS.md for session continuity

---

## Phase 2: Morning Briefing (Spec Approved)

Daily proactive information delivery for the commute.

### SPEC-002: Morning Briefing — Weather + Bikes + Clothing

**Status:** Approved (implementation plan in progress)

**What it includes:**
- Daily 07:00 CT message with weather forecast (Open-Meteo)
- Clothing suggestion optimized for biking
- Live Divvy bike/ebike/scooter availability at home station
- Dock availability at office stations (Optiver for Vincent, Adyen for Christianne)
- Biking recommendation (weather + bike availability combined)
- On-demand checks ("are there bikes?")
- Per-user personalization
- Partial failure handling (weather or Divvy down → send what we have)
- Cross-module: includes Social Circle events for the day

---

## Phase 3: Task Reminders (Research Complete)

Shared household task management — the "we need to do X by Y" system.

### SPEC-003: Task Reminders — Household Tasks & Recurring Reminders

**Status:** Research complete, spec in progress

**What it includes:**
- Task CRUD with natural language creation
- Lifecycle: pending → done / cancelled / snoozed
- Recurring tasks (daily, weekly, monthly, quarterly, yearly) with auto-creation on completion
- Assignment (vincent, christianne, or both)
- Due dates with automatic reminders
- Overdue nudges (daily → weekly → final warning)
- Contact linking (task related to a Social Circle person)
- Morning Briefing integration (today's tasks section)
- Search integration

---

## Future Modules (Not Yet Scoped)

Potential modules once Phases 1-3 are stable:

- Grocery/shopping lists
- Meal planning
- Travel planning
- Household finance / bill tracking
- Health check-ups & appointments
- Gift ideas tracker (ties into Social Circle)
- Seasonal reminders (winter tires, tax deadlines, garden)
- Relationship decay detection ("haven't seen X in 3 months")
- Calendar sync (export events/tasks to Google/Apple Calendar)

> These are ideas, not commitments. Each requires ideation + spec before building via the `add-module` skill.

---

## Status Legend

- **Researching** — Ideation phase, gathering info
- **Draft** — Spec written, not yet reviewed
- **In Review** — Spec reviewed, awaiting approval
- **Approved** — Ready to build
- **In Progress** — Implementation started
- **Blocked** — Waiting on dependency
- **Shipped** — Live in production
- **Deferred** — Postponed, may revisit
