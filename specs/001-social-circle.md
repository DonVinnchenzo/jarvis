# Social Circle

**Status:** Approved
**Author:** Claude Code
**Date:** 2026-06-09

---

## Overview

Track friends and family, their important dates (birthdays, anniversaries), children, and free-form notes. Proactively remind Vincent & Christianne via Telegram before events so nothing slips through the cracks.

This is the first Jarvis module. It establishes the patterns for data modeling, Telegram bot commands, and the proactive reminder engine that future modules will reuse.

---

## Requirements

### Functional Requirements

- [ ] **REQ-001:** Add, edit, and delete contacts. Each contact has a name and a relationship label (friend, family, colleague, or custom string).
- [ ] **REQ-002:** Track birthdays per contact (day + month required, year optional). Birthdays recur annually.
- [ ] **REQ-003:** Track marriage/relationship anniversaries per contact-pair (e.g., "Mark & Lisa — anniversary June 15"). Stored as a ContactEvent linked to one contact, with the pair described in the label.
- [ ] **REQ-004:** Track children per contact (child name, birthday day + month, year optional).
- [ ] **REQ-005:** Add free-form timestamped notes to any contact (e.g., "Mark got promoted at work", "Lisa is training for a marathon"). Notes are append-only by default but can be deleted.
- [ ] **REQ-006:** Proactive reminders with configurable lead times. Default: 7 days before, 1 day before, and day-of (0 days) for each event. Global defaults only in v1; per-event overrides deferred to v2.
- [ ] **REQ-007:** Reminders sent to BOTH Vincent & Christianne via Telegram (individual messages, not a group chat).
- [ ] **REQ-008:** List upcoming events (next 30 days) on demand via bot command.
- [ ] **REQ-009:** Search contacts and notes via bot. Search matches against contact name, relationship label, note text, and child names.
- [ ] **REQ-010:** Telegram bot commands: `/add`, `/contacts`, `/upcoming`, `/notes`, `/addnote`, `/search`, `/settings` (see Telegram Bot Commands section).
- [ ] **REQ-011:** Both users can add and edit all data. No permission hierarchy — single shared household.

### Non-Functional Requirements

- [ ] **NFR-001:** Reliability — Reminders must fire reliably. A missed reminder is a product failure. The proactive engine must be idempotent (safe to re-run) and must log every send/skip decision.
- [ ] **NFR-002:** Performance — Response time < 2s for all bot commands.
- [ ] **NFR-003:** Storage — Data stored in PostgreSQL, backed up daily. Backups encrypted at rest.

---

## Acceptance Criteria

- [ ] **AC-001:** Vincent can add a contact "Mark" with relationship "friend" and birthday June 14 via `/add`, and the contact appears in `/contacts`.
- [ ] **AC-002:** Seven days before June 14, both Vincent and Christianne receive a Telegram reminder about Mark's birthday.
- [ ] **AC-003:** One day before June 14, both receive a second reminder.
- [ ] **AC-003a:** On June 14 itself, both receive a day-of reminder ("Today is Mark's birthday!").
- [ ] **AC-004:** No duplicate reminders are sent if the cron job runs multiple times on the same day.
- [ ] **AC-005:** Christianne can add a note to Mark's contact, and Vincent can see it via `/notes Mark`.
- [ ] **AC-006:** `/upcoming` returns all birthdays, anniversaries, and children's birthdays within the next 30 days, sorted by date.
- [ ] **AC-007:** `/search marathon` returns Lisa's contact because of the note "Lisa is training for a marathon".
- [ ] **AC-008:** A contact-pair anniversary (e.g., "Mark & Lisa — June 15") triggers reminders to both users.
- [ ] **AC-008a:** When a birthday reminder fires, the message includes the contact's most recent notes (if any), providing conversational context.
- [ ] **AC-009:** A February 29 birthday still triggers reminders in non-leap years (treat as March 1 or February 28 — see Open Questions).
- [ ] **AC-010:** Year-end wrap-around works: a reminder configured for 7 days before a January 2 event fires on December 26.

---

## Technical Notes

### Constraints

- Single household, two Telegram users. No multi-tenant concerns.
- Personal data about real people — self-hosted on Mac mini, no third-party analytics.
- The bot IS a Claude Code agent (forked from Claudegram). Natural language input, not rigid commands.
- Backend (FastAPI) runs on localhost:8000, only the bot calls it.
- Claude calls the API via Bash (curl). Never direct SQL.

### User Identity

The bot identifies each user by Telegram user ID and passes it to the Claude Code session:
- System prompt includes: `CURRENT_USER: Vincent (Telegram ID: <id>)` or `CURRENT_USER: Christianne (Telegram ID: <id>)`
- All data mutations record `created_by` with the Telegram user ID
- Contact data is shared by default (both users see it)
- `visibility` field on Contact supports "shared" (default) or "personal" for future use
- Notes show attribution: "Added by Christianne, 3 weeks ago"

### Patterns to Follow

- Grammy + Claude Agent SDK for the bot (TypeScript), forked from Claudegram architecture
- Claude Code session with `cwd` set to the jarvis project directory — skills and CLAUDE.md loaded automatically via `settingSources: ['project', 'user']`
- FastAPI for the backend API (Python)
- Conventional Commits for all changes
- Every operation has a matching skill in `.claude/skills/` — Claude follows skills, doesn't improvise

### Implementation Hints

- Fork Claudegram's bot scaffolding. Key files to adapt: `agent.ts` (system prompt, working directory), `config.ts` (env vars), `bot.ts` (command registration)
- The system prompt appended to `claude_code` preset must include user identity and Jarvis-specific instructions
- Use `launchd` plist for the daily 08:00 reminder cron (not embedded in bot process)
- The proactive engine is a standalone POST endpoint (`/api/reminders/run`) — testable independently
- Users interact naturally ("add my friend Mark, birthday June 14") — Claude parses intent and calls the API
- Explicit `/add`, `/upcoming` etc. commands are optional shortcuts, not the primary interface
- Store Telegram user IDs in env var `ALLOWED_USER_IDS` and a name mapping in `USER_NAMES` (e.g., `{"12345":"Vincent","67890":"Christianne"}`)

---

## Dependencies

### Depends On

- PostgreSQL database provisioned and accessible
- Telegram bot token created via BotFather
- Grammy bot scaffolding (bot project setup)
- FastAPI backend scaffolding (backend project setup)

### Blocked By

- Nothing — this is the first module

### Blocks

- Future modules (gift tracking, household tasks) depend on the patterns established here
- The proactive engine pattern will be reused for all future reminder-based features

---

## Out of Scope

- **Calendar sync** (Google Calendar, Apple Calendar) — future enhancement, separate spec
- **Gift tracking** — separate module later (will reference Social Circle contacts)
- **Group/event planning** — future module
- **Multi-household support** — not needed, single household only
- **Contact import** (from phone contacts, CSV, etc.) — manual entry only for now
- **Profile photos** for contacts — unnecessary complexity
- **Relationship decay detection** ("haven't seen X in 3 months") — natural v2 enhancement, arguably more valuable than date reminders
- **Interactive reminder buttons** (inline keyboard: Show notes / Snooze / Mark as handled) — v2
- **Per-event reminder overrides** — global defaults only in v1
- **Per-user notification preferences** — both users always get all reminders in v1

---

## Open Questions

1. **Q:** How should Feb 29 birthdays be handled in non-leap years?
   **A:** Use February 28. Simpler (same month), matches user intuition, avoids sending a March reminder for a February birthday.

2. **Q:** Should the daily cron run once or multiple times as a safety net?
   **A:** Single run at 08:00 Europe/Amsterdam. Add a heartbeat check — if the engine didn't run by 09:00, the bot alerts Vincent. Idempotent design via SentReminder makes re-runs safe if added later.

3. **Q:** Should `/add` support adding multiple events in one flow?
   **A:** No. `/add` covers name + relationship + birthday. Anniversaries and children added separately via follow-up commands. Keep the flow short and simple.

4. **Q:** Deployment target — Railway or self-hosted on Mac mini?
   **A:** Self-hosted on Mac mini. Keeps data fully local, zero cost, infra already proven (Claudegram runs there). FastAPI bound to 127.0.0.1. Bot + backend managed via launchd.

5. **Q:** Claude Code agent or direct API calls for the bot?
   **A:** Claude Code agent (Max subscription, flat rate). Bot is a fork of Claudegram — same Grammy + Claude Agent SDK pattern. Users interact naturally; Claude interprets intent and calls the backend API. This also lets users improve the system itself through conversation.

---

## User Stories

### Story 1: Add a friend

**As** Vincent
**I want** to add my friend Mark with his birthday
**So that** Jarvis reminds me and Christianne before Mark's birthday

### Story 2: Never forget a birthday

**As** Christianne
**I want** to receive a reminder 7 days and 1 day before any tracked birthday
**So that** we have time to buy a gift or plan something

### Story 3: Remember life updates

**As** Vincent
**I want** to jot down notes about friends (e.g., "Mark got promoted", "Lisa started a new job")
**So that** we can reference them before meeting up and stay thoughtful

### Story 4: Quick lookup before a dinner

**As** Christianne
**I want** to search for a friend and see their notes and upcoming events
**So that** I'm prepared for social interactions

### Story 5: Track couple anniversaries

**As** Vincent
**I want** to record that Mark & Lisa's anniversary is June 15
**So that** we can send them a congratulations message on time

---

## API / Interface

### Backend Endpoints (FastAPI)

```
# Contacts
POST   /api/contacts                — Create a contact
GET    /api/contacts                — List all contacts (paginated)
GET    /api/contacts/{id}           — Get contact with events, children, notes
PUT    /api/contacts/{id}           — Update contact
DELETE /api/contacts/{id}           — Delete contact (cascades to events, children, notes)

# Events
POST   /api/contacts/{id}/events   — Add event to contact
PUT    /api/events/{id}             — Update event
DELETE /api/events/{id}             — Delete event

# Children
POST   /api/contacts/{id}/children — Add child to contact
PUT    /api/children/{id}           — Update child
DELETE /api/children/{id}           — Delete child

# Notes
POST   /api/contacts/{id}/notes    — Add note to contact
GET    /api/contacts/{id}/notes     — List notes for contact (chronological)
DELETE /api/notes/{id}              — Delete note

# Upcoming & Search
GET    /api/upcoming?days=30        — List upcoming events within N days
GET    /api/search?q=term           — Search contacts and notes

# Reminder Configuration
GET    /api/reminders/config        — Get current reminder settings
POST   /api/reminders/config        — Set reminder preferences (global or per-event)

# Proactive Engine (internal, called by cron)
POST   /api/reminders/run           — Trigger reminder check and send
```

### Telegram Bot Commands

```
/add                  — Interactive flow: add a new contact
                        Asks: name -> relationship -> birthday (optional) -> done
/contacts             — List all contacts, paginated (inline keyboard for pages)
/upcoming             — Show events in the next 30 days, sorted by date
/notes <name>         — Show all notes for a contact (fuzzy match on name)
/addnote <name>       — Add a note to a contact (next message = note text)
/search <query>       — Search contacts and notes, return matching results
/settings             — View/edit reminder preferences (days before, enable/disable)
```

---

## Data Model

```
Contact
  - id: UUID (PK)
  - name: string (required, max 200 chars)
  - relationship_type: string (required — "friend", "family", "colleague", or custom)
  - visibility: enum ("shared", "personal") — default "shared"
  - created_by: string (Telegram user ID of whoever created it)
  - created_at: timestamp
  - updated_at: timestamp

ContactEvent
  - id: UUID (PK)
  - contact_id: UUID (FK -> Contact, ON DELETE CASCADE)
  - event_type: enum ("birthday", "anniversary", "child_birthday", "custom")
  - label: string (nullable — used for custom events, anniversary descriptions,
            and child birthdays, e.g., "Emma (Mark's daughter)")
  - child_id: UUID (FK -> ContactChild, nullable, ON DELETE CASCADE)
            — set when event_type = "child_birthday"
  - day: int (1-31, required, CHECK day >= 1 AND day <= 31)
  - month: int (1-12, required, CHECK month >= 1 AND month <= 12)
  - year: int (nullable — null means recurring without a known start year)
  - recurring: bool (default true)
  - created_at: timestamp
  - updated_at: timestamp

ContactChild
  - id: UUID (PK)
  - contact_id: UUID (FK -> Contact, ON DELETE CASCADE)
  - name: string (required, max 200 chars)
  - created_at: timestamp
  Note: Children's birthdays are stored as ContactEvent rows with
  event_type = "child_birthday" and a nullable child_id FK. This avoids
  duplicating date/reminder logic across two tables. The /upcoming query,
  the proactive engine, and ReminderConfig all work against a single
  events table.

ContactNote
  - id: UUID (PK)
  - contact_id: UUID (FK -> Contact, ON DELETE CASCADE)
  - note_text: text (required)
  - created_by: string (Telegram user ID)
  - created_at: timestamp

ReminderConfig
  - id: UUID (PK)
  - event_id: UUID (FK -> ContactEvent, nullable)
    -- null = global default config
    -- non-null = override for a specific event
  - days_before: int (required, e.g., 7 or 1)
  - enabled: bool (default true)
  - created_at: timestamp
  - updated_at: timestamp
  Note: In v1, all whitelisted Telegram users are always notified (read from
  ALLOWED_USER_IDS env var). Per-user notification preferences deferred to v2.

SentReminder
  - id: UUID (PK)
  - event_id: UUID (FK -> ContactEvent)
  - reminder_config_id: UUID (FK -> ReminderConfig)
  - event_date: date (the specific occurrence date this reminder was for,
                       e.g., 2026-06-14 — prevents re-sending for same year)
  - sent_at: timestamp
  - telegram_message_ids: jsonb (message IDs per user, for reference)

Indexes:
  - Contact: name (for search)
  - ContactEvent: (month, day) (for upcoming queries — covers all event types including child_birthday)
  - ContactNote: GIN index on note_text (for full-text search)
  - SentReminder: UNIQUE (event_id, reminder_config_id, event_date) — prevents duplicates

DB Defaults:
  - All UUID PKs use gen_random_uuid() as database default
  - All timestamps use now() as database default
```

---

## Client Requirements

**Clients:** Telegram bot only (both Vincent and Christianne).

No web UI, no mobile app. The Telegram bot is the sole interface. Both users interact with the same bot and see the same shared data.

---

## Security Considerations

- [ ] **Backend API authentication** — The FastAPI backend MUST require an API key (`X-API-Key` header) for all endpoints. The key is shared between the bot, the cron job, and the backend via environment variable. When self-hosted, bind to `127.0.0.1` as defense in depth.
- [ ] **Telegram user ID whitelist** — Only Vincent's and Christianne's Telegram user IDs are authorized. All other messages are silently ignored (same pattern as Claudegram).
- [ ] **No third-party analytics** — Personal data about friends and family stays in our database. No external tracking, no telemetry.
- [ ] **Self-hosted preferred** — Keep data on infrastructure we control. If using Railway, ensure EU region and no data leaks to third-party services.
- [ ] **Database backups encrypted** — Daily backups with encryption at rest. If self-hosted, ensure FileVault is enabled.
- [ ] **Input validation** — Sanitize all user input (names, notes) before storing. Prevent injection in search queries.
- [ ] **No sensitive data in logs** — Log event IDs and actions, not contact names or note contents. Production log level MUST be INFO or above.
- [ ] **GDPR household exemption** — Data covered under Article 2(2)(c) household exemption. If app scope expands beyond the household, a data protection review is required.

---

## Testing Strategy

### Unit Tests
- **Reminder calculation logic** — Given today's date and an event date, calculate which reminders are due. Edge cases:
  - February 29 birthdays in non-leap years
  - Year-end wrap-around (December -> January)
  - DST transitions (CET -> CEST)
  - Events today (0 days before)
  - Multiple reminder windows overlapping
- **Upcoming events query** — Given a set of events, return the correct ones for a date range
- **Search** — Fuzzy matching, partial matches, case insensitivity

### Integration Tests
- **API endpoint CRUD** — Create, read, update, delete for all entities. Verify cascading deletes.
- **Reminder engine** — Run the engine against a seeded database, verify correct reminders are generated and SentReminder records are created.
- **Idempotency** — Run the reminder engine twice on the same day, verify no duplicate sends.

### E2E Tests
- **Bot command flows** — Mock Telegram API, walk through `/add` conversation flow, verify contact is created in the database.
- **Reminder delivery** — Seed an event due tomorrow, run the engine, verify both users receive the message (mocked Telegram sends).

---

## Proactive Engine

The proactive engine is the core differentiator of Jarvis. It runs independently of the bot.

### Flow

1. **Cron trigger** fires daily at 08:00 Europe/Amsterdam (POST to `/api/reminders/run` with `X-API-Key` header).
2. **Load all active ReminderConfigs** (global defaults in v1).
3. **For each recurring ContactEvent** (where recurring=true — covers birthdays, anniversaries, child_birthdays, custom):
   a. Calculate **both this year's and next year's** occurrence dates. This handles year-end wrap-around: a Jan 2 event with 7-day lead fires on Dec 26.
   b. For Feb 29 events in non-leap years, use Feb 28 as the occurrence date.
   c. For each applicable ReminderConfig, calculate the reminder date (occurrence - days_before).
   d. If today matches a reminder date, check SentReminder for a matching (event_id, reminder_config_id, event_date) row.
   e. If no matching SentReminder exists: **send reminder** to all whitelisted users.
4. **Build reminder message** — include event info + last 1-2 notes for the contact (if any). This turns reminders from notifications into contextual assistant messages.
5. **Send Telegram message** to each user individually.
6. **Record SentReminder** with the Telegram message IDs.
7. **Log summary**: "Processed N events, sent M reminders, skipped K (already sent)."
8. **Write heartbeat** — update `last_successful_run` timestamp. If the bot doesn't see a fresh heartbeat by 09:00, it alerts Vincent: "Reminder engine didn't run today."

### Message Format

```
Reminders 7 days before:
  "Hey! Mark's birthday is in 7 days (June 14). Any gift ideas? 🎂
   📝 Recent note: Mark got promoted at work (3 weeks ago)"

  "Hey! Mark & Lisa's anniversary is in 7 days (June 15) 💍"

  "Hey! Emma (Mark's daughter) turns 5 in 7 days (June 16) 🎈"

Reminders 1 day before:
  "Reminder: Mark's birthday is tomorrow (June 14)! 🎂"

Day-of:
  "Today is Mark's birthday! Happy birthday Mark! 🎉"
```

---

## Rollout Plan

1. **Phase 1: Backend + Data Model** — Install PostgreSQL via Homebrew, create schema, implement FastAPI CRUD endpoints + search + upcoming, write unit and integration tests. Run on localhost:8000.
2. **Phase 2: Telegram Bot (Claudegram fork)** — Fork Claudegram bot code into `bot/`. Adapt system prompt to include Jarvis instructions + user identity. Point `cwd` at this project directory. Register with BotFather. Test natural language interactions against the backend API.
3. **Phase 3: Proactive Engine** — Implement the cron-based reminder engine endpoint (`/api/reminders/run`), SentReminder dedup, Telegram sends with note context. Create launchd plist for 08:00 daily trigger. Test edge cases.
4. **Phase 4: Seed & Go Live** — Vincent and Christianne add their contacts via natural conversation. Monitor for a week. Fix issues. Run `/post-incident` for anything that goes wrong.

---

## References

- `jarvis/CLAUDE.md` — Project-level rules and architecture
- `jarvis/specs/TEMPLATE.md` — Spec template
- Grammy Conversations plugin: https://grammy.dev/plugins/conversations
- FastAPI docs: https://fastapi.tiangolo.com

---

## Changelog

- 2026-06-09 — Claude Code — Initial draft
- 2026-06-09 — Claude Code — Addressed 3-way review (backend, product, security):
  - Unified child birthdays into ContactEvent (child_birthday type) to eliminate parallel code paths
  - Added day-of (0 days) to default reminders
  - Added contextual note surfacing in reminder messages
  - Added backend API key authentication requirement
  - Resolved Feb 29 handling (use Feb 28)
  - Specified Europe/Amsterdam timezone (not CET)
  - Added year-boundary logic to proactive engine
  - Added heartbeat monitoring for cron reliability
  - Simplified v1: global reminder config only, all users always notified
  - Added DB-level CHECK constraints on day/month
  - Added GDPR household exemption note
- 2026-06-09 — Claude Code — Architecture decisions:
  - Self-hosted on Mac mini (resolved Q4)
  - Claude Code agent via Claudegram fork (resolved Q5)
  - User identity passed via system prompt (CURRENT_USER)
  - Added visibility field (shared/personal) to Contact
  - Natural language as primary interface, slash commands as shortcuts
  - Skills framework for all operations (add-contact, search, add-note, upcoming, manage-reminders, add-module)
