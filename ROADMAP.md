# Jarvis — Roadmap

**Last updated:** 2026-06-09

---

## Phase 1: Foundation + Social Circle (Current)

The minimum viable Jarvis: know our friends, remind us about important dates, help us be thoughtful.

### SPEC-001: Social Circle — Friends & Events Tracker

**Status:** In Review (awaiting Vincent's approval)

**What it includes:**
- Contact management (friends, family, their kids)
- Birthday, anniversary, and kid birthday tracking
- Free-form timestamped notes per contact
- Proactive reminders (7 days, 1 day, day-of) with contextual notes
- Natural language Telegram bot for both Vincent & Christianne
- User identity tracking (who added what)
- Shared/personal visibility per contact

**Implementation phases (after spec approval):**
1. Backend + Data Model — PostgreSQL, FastAPI CRUD, tests
2. Telegram Bot — Claudegram fork, user identity, natural language
3. Proactive Engine — Daily cron, SentReminder dedup, heartbeat
4. Seed & Go Live — Add contacts, monitor, iterate

### Framework (Done)
- CLAUDE.md hierarchy with architecture, rules, user identity
- 18 skills across 4 categories (dev, operational, meta)
- Spec template, 3-way review process
- Incident tracking system
- Christianne-first UX principle
- STATUS.md for session continuity

---

## Phase 2: Household Modules (Future — not yet scoped)

Potential modules to add once Phase 1 is stable:

- Household tasks & chores
- Grocery/shopping lists
- Meal planning
- Travel planning
- Bill reminders & household finance
- Health check-ups & appointments
- Gift ideas tracker (ties into Social Circle)
- Seasonal reminders (winter tires, tax deadlines, garden)
- Relationship decay detection ("haven't seen X in 3 months")

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
