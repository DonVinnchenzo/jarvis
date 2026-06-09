# CLAUDE.md — Jarvis

Household automation assistant for Vincent & Christianne.

---

## What is Jarvis

A personal household assistant that proactively helps Vincent & Christianne stay on top of their social life, household tasks, and life admin. Telegram bot interface for both users. Named after Iron Man's AI — starts focused, expands over time.

---

## Architecture

- **Bot**: TypeScript Telegram bot (Grammy + Claude Agent SDK), forked from Claudegram. Each user message goes through a Claude Code session pointed at THIS project directory. Claude reads these skills, CLAUDE.md files, and the codebase to reason about requests.
- **Backend**: Python FastAPI API on localhost:8000 — single source of truth for all data. Only the bot (same machine) calls it. Authenticated via `X-API-Key` header.
- **Database**: PostgreSQL (Homebrew, localhost). All household data.
- **Proactive engine**: Daily cron at 08:00 Europe/Amsterdam. Deterministic — no AI needed. Checks dates, sends Telegram reminders.
- **Hosting**: Self-hosted on Vincent's Mac mini. Backend bound to 127.0.0.1. Bot connects to Telegram API. PostgreSQL local.

### How Claude Code fits in

The bot IS a Claude Code agent. When Vincent or Christianne sends a Telegram message, it goes to a Claude Code session with `cwd` set to this project directory. Claude has access to:
- All skills in `.claude/skills/` — loaded on demand
- The backend API via Bash (curl localhost:8000)
- The database via the API (never direct SQL from Claude)
- The codebase itself (can read, edit, write files to improve the system)
- Git (version control for all changes)

This means users can say things naturally:
- "Add my friend Mark, birthday June 14, he just got promoted" → Claude calls the API
- "We should track dentist appointments too" → Claude writes a spec, follows the workflow
- "The reminder for Lisa came too late" → Claude investigates and fixes the issue

---

## User Identity

**Critical: Claude MUST know who is talking.**

The Telegram bot passes the user's identity to the Claude Code session via the system prompt:
- `CURRENT_USER: Vincent (Telegram ID: <id>)` or `CURRENT_USER: Christianne (Telegram ID: <id>)`
- All data mutations (contacts, notes, events) record `created_by` with the Telegram user ID
- When displaying data, indicate who added it: "Added by Vincent, 3 weeks ago"
- Both users can see and edit everything — but authorship is always tracked

### Shared vs Personal items

Some data is shared (friends, events). Some may be personal (individual to-dos, health items). The system distinguishes via:
- `visibility: "shared" | "personal"` field on applicable entities
- Shared = both users see it (default for Social Circle contacts)
- Personal = only the creator sees it
- Default is `shared` unless the user says otherwise

---

## 5-Phase Workflow

Every feature follows: **Ideation -> Specs -> Planning -> Build -> Review**

- **Small changes** (<3 files): Skip to Build -> PR Review -> deploy
- **Bug fixes**: Build -> Review -> `/post-incident`
- See `.claude/skills/` for phase-specific skills
- Claude MUST use the appropriate skill for each phase — no freestyling

---

## Skills Framework

Skills live in `.claude/skills/`. Each skill is a repeatable process that ensures consistency. Claude loads the relevant skill before executing any phase.

### Development Skills
- `ideation-research` — Research before committing to build
- `spec-writer` — Write specs from template with 3-way parallel review
- `spec-review-backend` — Backend engineering review
- `spec-review-product` — Product/user value review
- `implementation-plan` — Map files, dependencies, execution order
- `pre-commit-validate` — Run linters and tests before commit
- `pr-review` — Multi-agent code review
- `spec-verify` — Verify implementation matches spec acceptance criteria
- `post-incident` — Document failures and encode prevention rules

### Operational Skills (Claude uses these when users interact)
- `add-contact` — Add a new contact with events and notes
- `search` — Search contacts, notes, and events
- `add-note` — Add a note to a contact
- `upcoming` — Show upcoming events
- `manage-reminders` — Configure reminder preferences
- `add-module` — Propose and build a new Jarvis module (follows full workflow)

When a user asks something, Claude picks the right skill. If no skill exists for the request, Claude proposes creating one.

---

## Key Rules

1. **Two users, one household** — Both Vincent and Christianne have equal access. Track who did what. Support shared AND personal items.
2. **Proactive > Reactive** — The bot should remind us before we ask.
3. **Backend is source of truth** — Claude calls the API, never writes to the DB directly.
4. **Privacy matters** — Self-hosted, no third-party analytics, personal data stays local.
5. **Extensible by design** — Modules are self-contained. Adding one never breaks another.
6. **Specs are the source of truth** — New features follow the 5-phase workflow.
7. **Every failure makes the system smarter** — Incidents update CLAUDE.md and skills.
8. **Skills ensure consistency** — Every repeatable process is a skill. Claude follows skills, doesn't improvise.
9. **Git tracks everything** — All codebase changes go through git. Claude commits with Conventional Commits.

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

Self-hosted on Vincent's Mac mini:
- FastAPI backend: `127.0.0.1:8000` (systemd/launchd managed)
- Telegram bot: Grammy process (launchd managed, same as Claudegram)
- PostgreSQL: Homebrew, local socket
- Cron: launchd plist for 08:00 daily reminder run

---

## Key References

- `specs/` — Feature specifications
- `docs/PRINCIPLES.md` — Building principles
- `Ideation/BACKLOG.md` — Ideas parking lot
- `ROADMAP.md` — Delivery roadmap
- `code/claudegram/` — Reference implementation for bot architecture
