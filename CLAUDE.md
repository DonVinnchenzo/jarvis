# CLAUDE.md — Jarvis

Household automation assistant for Vincent & Christianne.

---

## What is Jarvis

A personal household assistant that proactively helps Vincent & Christianne stay on top of their social life, household tasks, and life admin. Telegram bot interface for both users. Named after Iron Man's AI — starts focused, expands over time.

---

## Architecture

- **Bot**: TypeScript Telegram bot (Grammy + Claude Agent SDK), shared with both users
- **Backend**: Python FastAPI API — single source of truth for all data
- **Database**: PostgreSQL with scheduled jobs
- **Proactive engine**: Cron-based notification system that sends reminders before events

---

## 5-Phase Workflow

Every feature follows: **Ideation -> Specs -> Planning -> Build -> Review**

- **Small changes** (<3 files): Skip to Build -> PR Review -> deploy
- **Bug fixes**: Build -> Review -> `/post-incident`
- See `.claude/skills/` for phase-specific skills

---

## Key Rules

1. **Two users, one household** — Both Vincent and Christianne have equal access. No multi-tenant complexity; single household, two Telegram users.
2. **Proactive > Reactive** — The bot should remind us before we ask. Birthday in 5 days? Remind us. Anniversary next week? Suggest a plan.
3. **Backend is source of truth** — Bot is a thin display/input layer. All logic, scheduling, and data in the backend.
4. **Privacy matters** — This is personal data about friends and family. Self-hosted preferred. No third-party analytics.
5. **Extensible by design** — First module is "Social Circle" (friends, events, reminders). Architecture must support adding new modules (household tasks, groceries, travel, etc.) without refactoring.
6. **Specs are the source of truth** — If it's not in a spec, it doesn't exist.
7. **Every failure makes the system smarter** — Incidents update CLAUDE.md so the same mistake never recurs.

---

## Build & Validation

```bash
# Backend
cd backend && ruff check . && pytest

# Bot
cd bot && npm run lint && npm run typecheck
```

Run before EVERY commit.

---

## Commit Guidelines

- Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`)
- Run validation before commit
- Commit after each task (don't batch)

---

## Deployment

TBD — likely Railway or self-hosted on Mac mini.

---

## Key References

- `specs/` — Feature specifications
- `docs/PRINCIPLES.md` — Building principles
- `Ideation/BACKLOG.md` — Ideas parking lot
- `ROADMAP.md` — Delivery roadmap
