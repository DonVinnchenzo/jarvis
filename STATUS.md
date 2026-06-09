# STATUS.md — Current State of Jarvis

**Any new Claude session: READ THIS FIRST before doing anything.**

This file is the single source of truth for where the project stands. It is updated after every significant action. If this chat disconnects, the next session reads this file and picks up exactly where we left off.

---

## Current Phase

**Phase 1: Foundation + Social Circle**

## Current Step

**Spec approved → Next: Write implementation plan**

SPEC-001 (Social Circle) has been written, reviewed (3-way: backend, product, security), and all blocking issues resolved. Architecture decisions finalized. The spec is ready for approval.

## What to do next

1. **Get Vincent's approval on SPEC-001** — Ask: "The spec is ready. Want to approve it so I can write the implementation plan?"
2. **Write implementation plan** — Use the `implementation-plan` skill. Save to `Ideation/SOCIAL-CIRCLE-IMPLEMENTATION-PLAN.md`. Map all files, dependencies, execution order.
3. **Get Vincent's approval on the plan** — Present the plan, get go-ahead.
4. **Build Phase 1: Backend + Data Model** — PostgreSQL schema, FastAPI CRUD endpoints, tests.
5. **Build Phase 2: Telegram Bot** — Fork Claudegram, adapt for Jarvis, user identity.
6. **Build Phase 3: Proactive Engine** — Cron reminder system, SentReminder dedup, heartbeat.
7. **Build Phase 4: Seed & Go Live** — Add contacts, monitor, fix issues.

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

## Key files to read for context

- `CLAUDE.md` — Architecture, skills framework, rules (READ THIS)
- `specs/001-social-circle.md` — The full spec for what we're building
- `Ideation/SOCIAL-CIRCLE-SPEC-REVIEW.md` — Review findings and resolutions
- `ROADMAP.md` — What's planned beyond Phase 1
- `docs/PRINCIPLES.md` — Building principles

## Recent history

- 2026-06-09: Created GitHub repo (github.com/DonVinnchenzo/jarvis)
- 2026-06-09: Set up full ClaryBook-style framework (CLAUDE.md hierarchy, 10 principles, spec template)
- 2026-06-09: Wrote SPEC-001 Social Circle, ran 3-way parallel review, resolved all blockers
- 2026-06-09: Architecture decisions: self-hosted Mac mini, Claudegram fork, Claude Code agent
- 2026-06-09: Created 18 skills (9 dev, 6 operational, 3 meta) including build-skill, report-issue, help
- 2026-06-09: Added user identity system, shared/personal visibility, Christianne-first UX rule

---

*Updated: 2026-06-09*
