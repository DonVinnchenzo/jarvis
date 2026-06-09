# Task Reminders — Ideation Research

**Date:** 2026-06-09

---

## Problem Statement

Vincent and Christianne share a household with a constant stream of things that need doing: rent needs to be confirmed, meetings need to be scheduled, tickets need to be booked, appointments need to be made, bills need to be paid. Right now, these tasks live in heads, random notes apps, or get mentioned once in conversation and then forgotten.

Jarvis already tracks *people* (Social Circle) and delivers *proactive information* (Morning Briefing). But neither module handles **actionable tasks with deadlines** — the "we need to do X by Y" items that are the core of household coordination. Without a shared task system, things fall through the cracks: the rent check gets forgotten until the landlord follows up, the meeting with Cory never gets scheduled, the concert tickets sell out.

This module closes the gap between knowing what's happening (Social Circle events) and actually getting things done.

---

## User Scenarios

### From Vincent's Examples

1. **"Remind me to check the rent is paid"** — Recurring monthly task. Should fire on a specific day each month (e.g., the 1st). Both users should see it. Once confirmed, mark as done for this cycle and auto-recreate for next month.

2. **"Schedule a meeting with Cory"** — One-time task, related to a person. No hard deadline, but should nag if it sits undone for too long. Ideally links to the Contact record for Cory in Social Circle.

3. **"Book tickets for [event]"** — One-time task with a real deadline (tickets go on sale or sell out by a date). Needs a due date, and increasingly urgent reminders as the deadline approaches.

### Additional Household Scenarios

4. **Recurring bills** — "Pay electricity bill" (monthly), "Renew renter's insurance" (annually). Predictable dates, high stakes if missed.

5. **Appointments** — "Schedule dentist cleaning" (every 6 months), "Book annual physical" (yearly). These are "schedule it" tasks, not calendar entries (yet).

6. **Home maintenance** — "Replace HVAC filter" (every 3 months), "Test smoke detectors" (every 6 months). Low urgency individually, but the kind of thing that never happens without a reminder.

7. **Travel prep** — "Book flights to Amsterdam for Christmas" (one-time, deadline), "Renew passport" (one-time, deadline = expiry minus 6 months), "Pack for trip" (one-time, date-anchored).

8. **Errands** — "Pick up dry cleaning", "Drop off package at UPS". No hard deadline, but should not linger forever. Soft expiry after a week if not completed.

9. **Shared household coordination** — "Buy a wedding gift for Mark & Lisa" (one-time, linked to a Social Circle event), "Call the plumber about the leak" (one-time, assigned to one person). The assignment aspect matters: Christianne should not assume Vincent is handling something just because it exists.

10. **Grocery/shopping** — "Buy new vacuum bags", "Get lightbulbs for kitchen". Could evolve into a full grocery list module later, but simple one-off tasks cover the 80% case now.

---

## Data Model Considerations

### Task Entity

```
Task
  - id: UUID (PK)
  - title: string (required, max 300 chars)
  - description: text (optional — extra context)
  - due_date: date (nullable — some tasks have no hard date)
  - due_time: time (nullable — most household tasks don't need a specific time)
  - priority: enum ("low", "normal", "high") — default "normal"
  - status: enum ("pending", "done", "snoozed", "cancelled") — default "pending"
  - assigned_to: enum ("vincent", "christianne", "both") — default "both"
  - created_by: string (Telegram user ID)
  - completed_by: string (nullable — Telegram user ID of whoever marked it done)
  - completed_at: timestamp (nullable)
  - snoozed_until: date (nullable — if snoozed, when to resurface)
  - contact_id: UUID (FK -> Contact, nullable — link to Social Circle person)
  - visibility: enum ("shared", "personal") — default "shared"
  - created_at: timestamp
  - updated_at: timestamp
```

**Key design decisions:**

- **`assigned_to` is a simple enum, not a user FK.** There are only two users. A string enum ("vincent", "christianne", "both") is clearer and simpler than a junction table. If Jarvis ever goes multi-household (it won't), this would need rethinking.
- **`contact_id` is optional.** Many tasks are not about a person ("pay rent"). But when they are ("schedule meeting with Cory"), linking to the Contact gives context and enables cross-module features (show pending tasks on the contact detail).
- **`due_time` is usually null.** Household tasks rarely need a specific time. But "call the dentist before 5pm" is a valid use case.
- **`snoozed_until` handles snooze state.** When a user says "remind me tomorrow", set `snoozed_until` to tomorrow's date. The proactive engine skips snoozed tasks until that date, then treats them as pending again.
- **No separate `overdue` status.** A task is overdue when `status = 'pending' AND due_date < today`. Computed, not stored. This avoids needing a batch job to flip statuses.

### TaskRecurrence Entity

```
TaskRecurrence
  - id: UUID (PK)
  - task_id: UUID (FK -> Task, ON DELETE CASCADE)
  - pattern: enum ("daily", "weekly", "biweekly", "monthly", "quarterly", "yearly")
  - day_of_month: int (nullable — for monthly: "on the 1st")
  - day_of_week: int (nullable — for weekly: 0=Monday through 6=Sunday)
  - month_of_year: int (nullable — for yearly: which month)
  - created_at: timestamp
```

**Why a separate table instead of cron expressions:**

- Cron syntax is powerful but unreadable for a household assistant. Christianne should never see `0 0 1 * *`.
- The patterns cover 95% of household recurrence: daily (take vitamins), weekly (take out trash on Tuesday), monthly (check rent), quarterly (replace HVAC filter), yearly (renew insurance).
- The proactive engine needs to compute "when is the next occurrence?" — a simple enum with optional day fields is far easier to compute than parsing cron.
- If an exotic pattern is needed later, a `custom_interval_days: int` field could be added.

**How recurring tasks work:**

1. User creates a task: "Check rent is paid, every month on the 1st."
2. System creates a `Task` (due_date = next 1st of the month) and a `TaskRecurrence` (pattern = "monthly", day_of_month = 1).
3. User completes the task: "Rent is paid."
4. System marks the current Task as `done` and **auto-creates the next occurrence** — a new Task row with due_date = 1st of next month, linked to the same recurrence config.
5. The original completed task stays in history (queryable, auditable).

**Alternative considered: single task row that resets.** Simpler (fewer rows), but loses history. Vincent should be able to ask "did we pay rent in April?" and get a definitive answer. Separate rows per occurrence win.

### TaskReminder Entity

```
TaskReminder
  - id: UUID (PK)
  - task_id: UUID (FK -> Task, ON DELETE CASCADE)
  - remind_at: date (when to send the reminder)
  - remind_time: time (nullable — defaults to morning briefing time)
  - sent: bool (default false)
  - sent_at: timestamp (nullable)
  - created_at: timestamp
```

**Why a separate reminder table instead of reusing ReminderConfig/SentReminder from Social Circle:**

- Social Circle reminders are tied to `ContactEvent` via foreign key. Task reminders need to reference `Task` instead.
- The semantics differ: event reminders are "N days before a date" (computed). Task reminders are "on this specific date" (explicit). A task due June 15 might have reminders on June 13, June 14, and June 15 — but also overdue nudges on June 16, 17, etc.
- Overdue nudge logic (re-remind daily until done or cancelled) does not exist in Social Circle at all.
- Keeping them separate avoids polluting the well-tested Social Circle engine with task-specific edge cases.

**Default reminder schedule for tasks with a due date:**

- 1 day before due date
- Day-of (morning)
- If overdue: daily nudge until done, snoozed, or cancelled (cap at 7 days, then weekly)

**Tasks without a due date:** No automatic reminders. They show up in "what's on my plate?" queries but do not generate proactive messages. The user can manually set a reminder: "remind me about the Cory meeting on Friday."

---

## Interaction Patterns

### Creating Tasks

Natural language is the primary interface. Claude interprets intent and calls the API.

| User says | Claude interprets |
|---|---|
| "Remind me to check rent is paid" | Task: "Check rent is paid", assigned_to: creator, no due date initially. Claude asks: "Should this be monthly? What day?" |
| "Remind me to pay rent on the 1st of every month" | Task: "Pay rent", due_date: next 1st, recurrence: monthly on 1st, assigned_to: creator |
| "We need to schedule a meeting with Cory" | Task: "Schedule meeting with Cory", assigned_to: both, contact_id: Cory's UUID (if found), no due date |
| "Book tickets for Hamilton before June 20" | Task: "Book tickets for Hamilton", due_date: June 20, assigned_to: both, priority: normal |
| "Christianne, can you call the plumber?" | Task: "Call the plumber", assigned_to: christianne, no due date |
| "I need to renew my passport by December" | Task: "Renew passport", due_date: Dec 1, assigned_to: creator, priority: high |

**Key UX principle:** Claude should confirm the task details before creating it. A one-line summary: "Got it — 'Pay rent', monthly on the 1st, assigned to both of you. Sound right?" This follows the Christianne-first UX rule: no surprises, no jargon.

### Completing Tasks

| User says | Claude does |
|---|---|
| "Rent is paid" | Fuzzy match against pending tasks. Find "Pay rent" or "Check rent is paid". Mark as done. If recurring, auto-create next occurrence. Confirm: "Marked 'Pay rent' as done. Next reminder: July 1st." |
| "Done with the Cory meeting" | Mark "Schedule meeting with Cory" as done. |
| "We booked the Hamilton tickets" | Mark "Book tickets for Hamilton" as done. |
| "Cancel the plumber task" | Set status to cancelled. |

**Ambiguity handling:** If "rent is paid" matches multiple tasks, Claude lists them and asks which one. If zero match, Claude asks for clarification.

### Snoozing

| User says | Claude does |
|---|---|
| "Remind me later" (in response to a nudge) | Snooze until tomorrow. |
| "Push the rent check to the 5th" | Set snoozed_until to the 5th. |
| "Snooze the plumber call for a week" | Set snoozed_until to today + 7 days. |

### Listing Tasks

| User says | Claude does |
|---|---|
| "What's on my plate?" | List pending tasks assigned to the requesting user or "both". Group by: overdue, today, upcoming, no date. |
| "What tasks do we have?" | List all pending shared tasks. |
| "What's overdue?" | List tasks where due_date < today and status = pending. |
| "Show me completed tasks this month" | List tasks completed in the current month. |
| "Any tasks related to Cory?" | Filter by contact_id matching Cory. |

### Overdue Nudges

Proactive messages for overdue tasks. Sent during the morning briefing window or as standalone nudges.

```
Hey Vincent, you have 2 overdue tasks:

- "Pay rent" was due June 1 (3 days ago) - assigned to both
- "Call dentist" was due May 28 (7 days ago) - assigned to you

Reply "done with [task]" to mark complete, or "snooze [task]" to push it back.
```

**Nudge frequency:** Daily for the first 7 days overdue, then weekly. This prevents reminder fatigue while keeping tasks visible.

---

## Integration with Existing Modules

### Morning Briefing (002)

The morning briefing already includes Social Circle events for the day (per Open Question 1 in the Morning Briefing spec). Tasks are a natural addition:

```
Good morning Vincent!

[weather + bikes section]

Today's tasks:
- Pay rent (due today)
- Schedule dentist cleaning (due in 3 days)

Overdue:
- Call plumber (2 days overdue, assigned to Christianne)
```

**Implementation:** The briefing endpoint (`POST /api/briefing/run`) would call a new `GET /api/tasks/today?user_id={id}` endpoint to pull the task section. Same pattern as cross-referencing Social Circle events.

### Social Circle (001)

Two integration points:

1. **Auto-suggest tasks from events.** When a birthday reminder fires 7 days before, the system could suggest: "Mark's birthday is in 7 days. Want me to create a task to buy a gift?" This is a Claude-level behavior (prompt instruction), not a backend feature. The skill for birthday reminders would include this suggestion.

2. **Contact-linked tasks.** Tasks with a `contact_id` show up on the contact detail. When Claude shows contact info, it includes pending tasks: "You have 1 pending task for Cory: Schedule meeting." This gives Social Circle a richer, more actionable view.

### Future Module: Grocery Lists

If a grocery/shopping list module is built later, simple shopping tasks ("buy vacuum bags") could be migrated or cross-referenced. For now, they live as regular tasks. The boundary is clear: Task Reminders handles items with a "do by" nature. A dedicated grocery module would handle a running list with quantities and categories.

---

## Technical Considerations

### Proactive Engine Extension

The existing proactive engine runs at 08:00 Europe/Amsterdam for Social Circle. Task reminders should hook into the same cron infrastructure:

- **Option A: Same cron, new endpoint.** The 08:00 cron calls both `POST /api/reminders/run` (Social Circle) and `POST /api/tasks/reminders/run` (Task Reminders). Simple, same pattern.
- **Option B: Unified proactive engine.** A single `POST /api/proactive/run` endpoint that dispatches to all modules. More extensible as modules grow.

**Recommendation:** Option A for now. Keep modules independent per Key Rule 5 ("Modules are self-contained. Adding one never breaks another."). A unified engine can be refactored in later if the number of modules warrants it.

### Timezone Handling

Tasks use dates (not datetimes) for due_date, same as Social Circle events. The proactive engine computes "today" in the household timezone (America/Chicago based on current location, though this may need to be configurable if they move back to Amsterdam). The `due_time` field on Task is optional and only used for display ("call before 5pm"), not for reminder scheduling.

### API Endpoints (Preliminary)

```
POST   /api/tasks                  — Create a task
GET    /api/tasks                  — List tasks (filter by status, assigned_to, due date range)
GET    /api/tasks/{id}             — Get task detail
PUT    /api/tasks/{id}             — Update task
DELETE /api/tasks/{id}             — Delete task
POST   /api/tasks/{id}/complete    — Mark task as done (handles recurrence)
POST   /api/tasks/{id}/snooze      — Snooze task (set snoozed_until)
GET    /api/tasks/today             — Today's tasks + overdue (for morning briefing)
POST   /api/tasks/reminders/run    — Trigger task reminder engine (cron)
```

Follows the same patterns as `/api/contacts` — RESTful CRUD with convenience endpoints for common actions (`complete`, `snooze`, `today`).

### Search

Tasks should be searchable via the existing `/api/search` endpoint. Add task title and description to the search index alongside contacts and notes. When a user says "search plumber," results should include matching tasks as well as contacts and notes.

---

## Alternatives Considered

### Why Not Use a Third-Party Tool?

Apple Reminders, Todoist, Google Tasks — all exist and work. But:

- They don't integrate with Social Circle (no "buy gift for Mark's birthday" auto-suggestion).
- They don't feed into the Morning Briefing.
- They require switching apps. The whole point of Jarvis is one Telegram interface for everything.
- Shared household task management in third-party tools is clunky (shared lists, permissions, separate accounts).
- Self-hosted = full control, no data leaving the Mac mini.

### Why Not Extend Social Circle?

ContactEvent already has dates and reminders. Why not add a "task" event type?

- **Semantics are fundamentally different.** Events are date-anchored facts (Mark's birthday IS June 14). Tasks are actionable items that have a lifecycle (pending -> done/cancelled). Events don't have status, assignment, or completion tracking.
- **Recurrence works differently.** A birthday recurs on the same date forever. A task recurrence creates new instances that need individual completion.
- **Data model would get messy.** Bolting task fields (status, assigned_to, completed_by, snoozed_until) onto ContactEvent would violate single responsibility and complicate the existing, well-tested reminder engine.

Separate module is the right call.

---

## Scope Boundaries (for Spec)

### In Scope (v1)

- Task CRUD (create, read, update, delete)
- Status lifecycle: pending -> done / cancelled / snoozed
- Assignment: vincent, christianne, or both
- Due dates (optional) with automatic reminders
- Recurring tasks (daily, weekly, biweekly, monthly, quarterly, yearly)
- Snooze (push to a specific date)
- Contact linking (optional FK to Social Circle)
- Overdue nudges (daily, then weekly)
- Morning Briefing integration (today's tasks section)
- Natural language interaction via Claude
- Task search via existing search endpoint

### Out of Scope (v2+)

- **Subtasks / checklists** — Keep v1 flat. Subtasks add complexity without proportional value for a two-person household.
- **Task categories / tags** — Natural language search is good enough for two people with ~20 active tasks.
- **Calendar sync** (export tasks to Google Calendar / Apple Calendar) — separate module.
- **Location-based reminders** ("remind me when I'm near the post office") — requires geofencing, way out of scope.
- **Time-based reminders at specific hours** — v1 sends all reminders during the morning briefing window. Intra-day reminders (e.g., "remind me at 3pm") are v2.
- **Task templates** — "Create a packing list template for trips" is a power-user feature. Defer.
- **Priority-based ordering** — v1 has a priority field but the morning briefing shows all tasks. Smart ordering by priority + due date is v2.
- **Recurring task editing** — v1: to change a recurrence pattern, delete and recreate. v2: edit the pattern and regenerate future occurrences.

---

## Open Questions (for Spec Discussion)

1. **Timezone:** The household is currently in Chicago (America/Chicago per Morning Briefing). Social Circle uses Europe/Amsterdam. Should Task Reminders use the same timezone as Morning Briefing since they are co-located? Or should there be a single household timezone setting?

2. **Overdue nudge channel:** Should overdue nudges go to both users or only the assigned user? Recommendation: only the assigned user (or both if assigned_to = "both"). Christianne does not need daily pings about Vincent's tasks.

3. **Completion authority:** Can Vincent mark Christianne's task as done? Recommendation: yes. Trust model is full-trust household. But `completed_by` records who actually marked it done for auditability.

4. **Recurring task completion before due date:** If "Pay rent" is due June 1 but Vincent pays on May 28, should it count for the June cycle? Recommendation: yes. Mark current as done, next occurrence is July 1.

5. **Maximum overdue nudge duration:** After how long should the system stop nagging? Recommendation: daily for 7 days, then weekly for 3 weeks, then a final "This task has been overdue for a month — should I cancel it?" message.

---

## Recommendation

**Build.** This is a core household need — arguably more immediately useful day-to-day than Social Circle (which is event-driven and spiky). Task Reminders would be used multiple times per week by both users.

It fits naturally into Jarvis's existing architecture:
- Same bot interface (natural language via Claude)
- Same backend pattern (FastAPI CRUD + proactive engine)
- Same data conventions (UUID PKs, created_by tracking, visibility field)
- Direct integration with Morning Briefing and Social Circle

The scope is well-defined. The data model is straightforward. No external APIs needed (unlike Morning Briefing). This is a self-contained module that relies entirely on Jarvis's own infrastructure.

**Suggested priority:** Next module after Morning Briefing ships. It fills the biggest gap in Jarvis's current household coverage.

---

## References

- `specs/001-social-circle.md` — Data model patterns, proactive engine, reminder design
- `specs/002-morning-briefing.md` — Morning briefing integration point
- `Ideation/BACKLOG.md` — Related backlog items: Household Chores, Grocery Lists, Bill Reminders, Home Maintenance
- `CLAUDE.md` — Architecture, key rules (especially #2: Proactive > Reactive, #5: Extensible by design, #10: Christianne-first UX)
