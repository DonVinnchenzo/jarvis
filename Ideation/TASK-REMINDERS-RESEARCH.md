# Task Reminders — Ideation Research

**Date:** 2026-06-09

---

## Problem Statement

Vincent and Christianne run a two-person household with a constant stream of things that need doing: rent needs to be confirmed, meetings need to be scheduled, tickets need to be booked, appointments need to be made, bills need to be paid. Right now these tasks live in their heads, get mentioned once in conversation, and then forgotten. There is no shared, persistent, proactive system to capture household tasks and follow up until they are done.

Jarvis already tracks *people and dates* (Social Circle) and delivers *daily context* (Morning Briefing). What is missing is the third pillar: **actionable tasks with deadlines, assignment, and accountability**. The "we need to do X by Y" items that are the core of household coordination.

Without a shared task system, things fall through the cracks: the rent check gets forgotten until the landlord follows up, the meeting with Cory never gets scheduled, the concert tickets sell out because neither person remembered to book them. This module closes the gap between knowing what is happening and actually getting things done.

The solution is not another task app (Apple Reminders, Todoist, etc.) — those require context-switching. Vincent and Christianne already live in Telegram for Jarvis. If they can say "remind me to check rent is paid" and Jarvis tracks it, nags them if it is overdue, and marks it done when they confirm, tasks stop falling through the cracks without adding another app to their lives.

---

## User Scenarios

### From Vincent's examples

1. **"Remind me to check the rent is paid"** — Recurring monthly task. Should fire on a specific day each month (e.g., the 1st). Assigned to both (either can confirm). Once confirmed, mark done for this cycle and auto-create next month's occurrence.

2. **"Schedule a meeting with Cory"** — One-time task, linked to Cory's contact in Social Circle. No hard deadline, but Jarvis should suggest a timeframe and nag if it sits undone too long.

3. **"Book tickets for the show"** — One-time task with an implicit deadline (show date). Jarvis asks "When is the show?" and sets the due date a few days before so tickets can still be booked.

### Expanded household scenarios

4. **Bills and utilities** — "Pay electricity bill by the 15th" (recurring monthly), "Renew renter's insurance" (recurring yearly). Predictable dates, high stakes if missed.

5. **Groceries and shopping** — "We need milk and eggs", "Buy new vacuum bags". Simple one-off tasks. A full grocery list module may come later, but single tasks cover the 80% case now.

6. **Apartment maintenance** — "Call the landlord about the leaky faucet" (one-time), "Replace HVAC filter" (every 3 months). Low urgency individually, but the kind of things that never happen without a reminder.

7. **Travel planning** — "Book flights to Amsterdam for Christmas" (one-time with soft deadline), "Renew passport by December" (one-time, high priority). Could spawn related tasks (hotel, pet sitter).

8. **Doctor appointments** — "Book a dentist appointment for Chris" (one-time, assigned to Christianne), "Schedule annual physical" (recurring yearly).

9. **Contact-linked tasks** — "Buy a present for Mark's birthday" (one-time, linked to Mark's contact via `contact_id`). Jarvis can auto-suggest this 14 days before Mark's birthday via cross-module integration with Social Circle.

10. **Seasonal tasks** — "Turn on heating", "Schedule AC maintenance before summer", "Tax filing deadline April 15" (recurring yearly).

11. **Errands** — "Pick up dry cleaning", "Drop off package at UPS". No hard deadline, soft expiry. Should not linger forever without a nudge.

---

## Interaction Patterns

All interaction is natural language via Telegram. No slash commands required (though `/tasks` could be a shortcut). Claude interprets intent and calls the backend API. Follows the Christianne-first UX rule: no surprises, no jargon, no syntax.

### Creating tasks

| User says | Jarvis interprets |
|---|---|
| "Remind me to check rent is paid" | Title: "Check rent is paid", recurrence: monthly (1st), assigned: both |
| "We need to book flights to Amsterdam" | Title: "Book flights to Amsterdam", assigned: both, due: asks user |
| "Chris needs to call the dentist" | Title: "Call the dentist", assigned: Christianne |
| "I'll handle the electricity bill" | Title: "Pay electricity bill", assigned: Vincent |
| "Buy a present for Mark's birthday" | Title: "Buy present for Mark", contact: Mark, due: 7 days before Mark's birthday (auto-derived from Social Circle) |
| "Add a task to renew renter's insurance by September 1" | Title: "Renew renter's insurance", due: Sep 1, recurrence: yearly |
| "Remind me to pay rent on the 1st of every month" | Title: "Pay rent", due: next 1st, recurrence: monthly on 1st, assigned: both |
| "Christianne, can you call the plumber?" | Title: "Call the plumber", assigned: Christianne |

**Smart defaults:**
- If no due date given, Jarvis asks "When should I remind you?"
- If user says "remind me" without specifics, default to tomorrow at 09:00
- If user mentions a contact name that exists in Social Circle, auto-link via `contact_id`
- Default assignment is "both" unless the user specifies otherwise
- Default priority is "medium"
- Default visibility is "shared"
- Claude confirms before creating: "Got it — 'Pay rent', monthly on the 1st, assigned to both of you. Sound right?"

### Completing tasks

| User says | Jarvis interprets |
|---|---|
| "Rent is paid" | Fuzzy-match to "Check rent is paid" task, mark complete |
| "Done" (in reply to a reminder message) | Complete the task referenced in the reminder |
| "I booked the flights" | Match to "Book flights to Amsterdam", mark complete |
| "Mark the dentist thing as done" | Fuzzy-match to dentist task, mark complete |
| "We booked the Hamilton tickets" | Match to "Book tickets for Hamilton", mark complete |
| "Cancel the plumber task" | Set status to cancelled (not done — different semantics) |

**Completion behavior:**
- For one-time tasks: status changes to "done", `completed_at` and `completed_by` recorded
- For recurring tasks: current occurrence marked done, next occurrence auto-created based on recurrence rule
- Jarvis confirms: "Got it, marked 'Check rent is paid' as done. Next reminder: July 1."
- Ambiguity: if multiple tasks match, Claude lists them and asks which one

### Snoozing

| User says | Jarvis interprets |
|---|---|
| "Push it to tomorrow" | Snooze task, set `snoozed_until` to tomorrow 09:00 |
| "Remind me about that on Friday" | Snooze to Friday 09:00 |
| "Not now" | Snooze 3 hours |
| "Remind me later" | Snooze to tomorrow 09:00 |
| "Push the rent check to the 5th" | Set snoozed_until to the 5th |
| "Snooze the plumber call for a week" | Snooze to today + 7 days |

### Listing tasks

| User says | Jarvis interprets |
|---|---|
| "What's on my plate?" | Show pending + overdue tasks assigned to current user or "both" |
| "What do we need to do?" | Show all shared pending + overdue tasks |
| "What's overdue?" | Show only overdue tasks |
| "What tasks does Chris have?" | Show tasks assigned to Christianne |
| "Anything due this week?" | Filter by due_date within current week |
| "Show me completed tasks this month" | List tasks completed in current month |
| "Any tasks related to Cory?" | Filter by contact_id matching Cory |

**Display format:** Group by overdue (warning), today, upcoming (next 7 days), no date. Priority indicators on high-priority tasks.

### Overdue nudges

Proactive messages for overdue tasks, sent during the daily cron window:

```
Hey Vincent, you have 2 overdue tasks:

- "Pay rent" was due June 1 (3 days ago) — assigned to both
- "Call dentist" was due May 28 (7 days ago) — assigned to you

Reply "done with [task]" to mark complete, or "snooze [task]" to push it back.
```

**Nudge frequency:**
- Day of deadline (evening, if not completed): "Hey, 'Check rent is paid' was due today. Done or need more time?"
- 1 day overdue: message the assigned user(s)
- 3 days overdue: escalate — message both users even if assigned to one
- Daily for first 7 days, then weekly
- After 30 days: "This task has been overdue for a month. Should I cancel it?"

Nudge logic runs as part of the proactive engine (daily cron). No separate cron needed.

### Assignment

- Default: **both** (shared household responsibility)
- Explicit: "that's for Chris", "I'll do it", "assign to me"
- Reassignment: "actually, Chris can you handle the dentist?"
- Anyone can complete any task regardless of assignment — assignment determines who gets reminders, not permissions. `completed_by` records who actually did it.

---

## Data Model Design

Following the existing patterns from `Contact` and `ContactEvent`: UUID PKs with `gen_random_uuid()`, `server_default=func.now()` timestamps, `String` columns with explicit lengths, `CheckConstraint` for enums, composite indexes for common queries.

### Task table

```python
class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Scheduling
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_time: Mapped[time | None] = mapped_column(Time, nullable=True)

    # Status: "overdue" is computed (status=pending AND due_date < today),
    # not stored. Avoids needing a batch job to flip statuses.
    status: Mapped[str] = mapped_column(
        String(20), server_default="pending", nullable=False
    )  # pending, done, snoozed, cancelled

    priority: Mapped[str] = mapped_column(
        String(10), server_default="medium", nullable=False
    )  # low, medium, high

    # Assignment — simple string enum, not a user FK.
    # Only two users; a junction table would be overkill.
    assigned_to: Mapped[str] = mapped_column(
        String(20), server_default="both", nullable=False
    )  # vincent, christianne, both

    # Ownership & visibility (matches Contact pattern)
    created_by: Mapped[str] = mapped_column(String(50), nullable=False)
    visibility: Mapped[str] = mapped_column(
        String(20), server_default="shared", nullable=False
    )  # shared, personal

    # Completion tracking
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_by: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Snooze — datetime, not date. "Snooze to 3pm today" is valid.
    snoozed_until: Mapped[datetime | None] = mapped_column(nullable=True)

    # Cross-module link to Social Circle
    # ON DELETE SET NULL, not CASCADE — deleting a contact should not
    # delete household tasks, just unlink them.
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Recurrence — NULL means one-time task.
    # Simple pattern string (see Recurrence Patterns section).
    recurrence_rule: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    # Links recurring task occurrences to the original task.
    # When a recurring task is completed, a new Task row is created
    # with the next due date, pointing to the same parent.
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    contact: Mapped["Contact | None"] = relationship()
    reminders: Mapped[list["TaskReminder"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'done', 'snoozed', 'cancelled')",
            name="ck_task_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high')",
            name="ck_task_priority",
        ),
        CheckConstraint(
            "assigned_to IN ('vincent', 'christianne', 'both')",
            name="ck_task_assigned_to",
        ),
        Index("ix_tasks_status_due_date", "status", "due_date"),
        Index("ix_tasks_assigned_to", "assigned_to"),
        Index("ix_tasks_contact_id", "contact_id"),
    )
```

### TaskReminder table

Allows flexible reminder scheduling per task. A single task can have multiple reminders (1 day before, day of, overdue nudges). This mirrors the `ReminderConfig`/`SentReminder` pattern from Social Circle but is simpler because task reminders are explicit datetimes rather than "N days before" calculations.

```python
class TaskReminder(Base):
    __tablename__ = "task_reminders"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    remind_at: Mapped[datetime] = mapped_column(nullable=False)
    sent: Mapped[bool] = mapped_column(
        server_default=text("false"), nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(nullable=True)
    telegram_message_ids: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )

    # Relationships
    task: Mapped["Task"] = relationship(back_populates="reminders")

    __table_args__ = (
        Index("ix_task_reminders_remind_at_sent", "remind_at", "sent"),
    )
```

### Why separate from Social Circle's ReminderConfig/SentReminder

- Social Circle reminders are tied to `ContactEvent` via FK. Task reminders reference `Task`.
- Semantics differ: event reminders are "N days before an annually recurring date" (computed). Task reminders are "at this specific datetime" (explicit).
- Overdue nudge logic (re-remind daily until done or cancelled) does not exist in Social Circle.
- Keeping them separate avoids polluting the well-tested Social Circle engine with task-specific edge cases.

### Why separate Task rows per recurring occurrence (not one row that resets)

When "Pay rent" is completed, the system creates a new Task row for the next occurrence rather than resetting the existing row. This preserves history — Vincent can ask "did we pay rent in April?" and get a definitive answer with `completed_at` and `completed_by`. The `parent_task_id` links all occurrences in a chain for querying.

---

## Recurrence Patterns

### Simple pattern strings

Rather than full RRULE (RFC 5545) complexity, use readable pattern strings stored in `recurrence_rule`. These cover 95% of household use cases:

| Pattern | Meaning | Example |
|---|---|---|
| `daily` | Every day | "Take vitamins" |
| `weekly:monday` | Every week on Monday | "Put out trash" |
| `weekly:monday,thursday` | Twice a week | "Water plants" |
| `biweekly:friday` | Every other Friday | "Deep clean bathroom" |
| `monthly:1` | 1st of every month | "Check rent is paid" |
| `monthly:15` | 15th of every month | "Pay electricity bill" |
| `monthly:last` | Last day of month | "Submit expense report" |
| `quarterly:1` | 1st of Jan/Apr/Jul/Oct | "Quarterly review" |
| `yearly:09-01` | September 1 every year | "Renew renter's insurance" |

### How recurrence works

1. **User creates a task** with a recurrence rule. Example: "Pay rent, every month on the 1st." System creates a Task row with `due_date = next 1st`, `recurrence_rule = "monthly:1"`.

2. **User completes the task.** System marks the current Task row as `done` (`completed_at`, `completed_by` recorded) and auto-creates a new Task row:
   - Same title, description, priority, assigned_to, visibility, contact_id, recurrence_rule
   - `parent_task_id` pointing to the first task in the chain (or itself if it was the first)
   - `due_date` calculated as the next occurrence after today
   - Status: `pending`
   - Fresh TaskReminder rows based on default reminder timing

3. **Early completion.** If "Pay rent" (due June 1) is completed on May 28, it counts for the June cycle. Next occurrence is July 1.

4. **Overdue handling.** If a recurring task goes overdue, Jarvis nudges but does NOT auto-complete or auto-advance. The user must explicitly confirm (e.g., "rent is paid") before the next occurrence is created. This prevents silent skipping.

5. **Deletion.** Deleting a recurring task prompts: "Delete just this occurrence, or stop the recurring task entirely?" Stopping removes the recurrence_rule from the chain.

### Why not RRULE (RFC 5545)

- Complex parsing library needed
- Users would never say "FREQ=MONTHLY;BYMONTHDAY=1" — they say "every month on the 1st"
- The simple pattern strings map directly to natural language
- Household recurrence is inherently simple (daily/weekly/monthly/yearly covers nearly everything)
- If an exotic pattern arises later ("every third Tuesday"), add it as a new pattern type without refactoring

### Next-occurrence calculation

```python
def next_occurrence(rule: str, after: date) -> date:
    """Calculate the next due date after `after` given a recurrence rule."""
    if rule == "daily":
        return after + timedelta(days=1)
    elif rule.startswith("weekly:"):
        # Parse target day(s) of week, find the next one after `after`
        ...
    elif rule.startswith("monthly:"):
        day_or_keyword = rule.split(":")[1]
        if day_or_keyword == "last":
            # Last day of next month
            ...
        else:
            target_day = int(day_or_keyword)
            # Next month's target_day (handle months with fewer days)
            ...
    elif rule.startswith("yearly:"):
        # Parse MM-DD, find next occurrence
        ...
```

This is deterministic, testable, and does not need external libraries.

---

## Integration with Existing Modules

### Morning Briefing (002)

The morning briefing (07:00 CT) currently includes weather + Divvy + Social Circle events. Tasks are a natural addition:

```
Good morning Vincent! ...

[weather + bikes section]

[Social Circle events for today]

📋 Tasks today:
  - Check rent is paid (due today)
  - Schedule dentist cleaning (due in 3 days)

⚠️ Overdue:
  - Call plumber (2 days overdue, assigned to Christianne)
```

**Implementation:** The briefing endpoint (`POST /api/briefing/run`) calls `GET /api/tasks/today?assigned_to={user}` and appends to the message. Today's tasks and anything overdue are always shown. Tasks due within the next 3 days are included as a heads-up.

### Social Circle (001)

Two integration points:

1. **Auto-suggest tasks from upcoming events.** When a birthday reminder fires 7 days before, Jarvis asks: "Mark's birthday is in 7 days. Want me to add a task to buy a gift?" If yes, creates a task with `contact_id = Mark's UUID`, title "Buy birthday gift for Mark", due date = 2 days before the birthday. This is a Claude-level behavior (prompt instruction in the birthday reminder skill), not a backend feature.

2. **Contact-linked task display.** When viewing a contact (e.g., `/notes Mark` or "tell me about Cory"), Claude also shows pending tasks linked to that contact: "Pending tasks: Schedule meeting with Cory." Gives Social Circle a richer, more actionable view.

3. **Event-to-task pipeline.** When adding a new contact event (anniversary, custom event), offer to create a preparation task automatically.

### Cross-module query

When the user asks "what do I have today?", Jarvis aggregates across all modules:
- Morning Briefing: weather + bikes (if relevant)
- Social Circle: events today or soon (birthdays, anniversaries)
- Task Reminders: tasks due today + overdue

This becomes the single-prompt daily overview — one message, everything you need to know.

---

## API Endpoints

Following the existing pattern: all endpoints under `/api/`, authenticated via `X-API-Key` header, JSON request/response.

```
# Task CRUD
POST   /api/tasks                     — Create a task
GET    /api/tasks                     — List tasks (with query params)
GET    /api/tasks/{id}                — Get a single task with its reminders
PUT    /api/tasks/{id}                — Update task fields
DELETE /api/tasks/{id}                — Delete a task

# Task actions
PATCH  /api/tasks/{id}/complete       — Mark task as done
                                        Records completed_by, completed_at.
                                        If recurring, auto-creates next occurrence.
PATCH  /api/tasks/{id}/snooze         — Snooze task
                                        Body: { "until": "2026-06-10T09:00:00" }
                                        Updates snoozed_until, creates new TaskReminder.

# Filtered views (convenience endpoints for common queries)
GET    /api/tasks/overdue             — Pending tasks with due_date < today
GET    /api/tasks/today               — Tasks due today + overdue (for morning briefing)
GET    /api/tasks/upcoming?days=7     — Tasks due in the next N days

# Proactive engine (called by cron)
POST   /api/tasks/reminders/run       — Check for due reminders, send Telegram messages,
                                        mark TaskReminder.sent = true. Also send overdue
                                        nudges for tasks past their due date.
```

### Query parameters for `GET /api/tasks`

| Param | Type | Description |
|---|---|---|
| `status` | string | Filter: `pending`, `done`, `snoozed`, `cancelled` |
| `assigned_to` | string | Filter: `vincent`, `christianne`, `both` |
| `due_date_gte` | date | Due on or after this date |
| `due_date_lte` | date | Due on or before this date |
| `priority` | string | Filter: `low`, `medium`, `high` |
| `contact_id` | UUID | Tasks linked to a specific contact |
| `q` | string | Full-text search on title and description |
| `include_done` | bool | Include completed tasks (default: false) |
| `limit` | int | Pagination limit (default: 50) |
| `offset` | int | Pagination offset (default: 0) |

### Proactive engine design

**Recommended: hourly cron from 08:00 to 21:00 CT.** This allows intra-day reminders (snooze to 3pm, get reminded at 3pm). A single daily run would limit reminders to once per day.

Each cron run:
1. Query `TaskReminder` where `remind_at <= now()` and `sent = false`.
2. For each unsent reminder, check if the task is still `pending` (skip if done/cancelled).
3. Send Telegram message to the assigned user(s).
4. Mark `sent = true`, record `sent_at` and `telegram_message_ids`.
5. Query overdue tasks that have not been nudged today — send overdue nudge.
6. Log summary: "Processed N reminders, sent M, skipped K."

### Default reminder creation on task create

When a task is created, auto-create TaskReminder rows:
- **Has due date, no specific time:** Remind at 09:00 on the due date
- **Has due date and time:** Remind 1 hour before + at the time
- **High priority with due date:** Also remind 1 day before at 09:00
- **No due date:** No automatic reminder (user can add one manually)

---

## Skills Needed

Four new operational skills for `.claude/skills/`:

### `add-task`
- Parse natural language to extract: title, due date, due time, assignment, priority, recurrence, contact link
- If a contact name is mentioned, search Social Circle and link `contact_id`
- Confirm details with user before creating
- Call `POST /api/tasks` with extracted fields
- Auto-create default TaskReminder rows
- Confirm back: "Created 'Pay rent', due July 1, monthly, assigned to both."

### `list-tasks`
- Parse intent: "my tasks", "our tasks", "overdue", "this week", "what's due"
- Call `GET /api/tasks` with appropriate filters
- Format response: grouped by overdue / today / upcoming / no date
- Show priority indicators, assignment, and days overdue
- Overdue tasks always listed first with warning

### `complete-task`
- Parse: "done", "rent is paid", "mark X as done", reply to reminder
- Fuzzy-match task title if not replying to a specific reminder
- If ambiguous (multiple matches), list options and ask user to clarify
- Call `PATCH /api/tasks/{id}/complete`
- If recurring, confirm next occurrence: "Done! Next reminder: July 1."

### `snooze-task`
- Parse: "push to tomorrow", "remind me Friday", "not now", "later"
- Calculate `snoozed_until` datetime from natural language
- Call `PATCH /api/tasks/{id}/snooze`
- Update or create TaskReminder with new `remind_at`
- Confirm: "Snoozed 'Call plumber' until Friday at 9:00 AM."

---

## Alternatives Considered

### Why not use a third-party tool?

Apple Reminders, Todoist, Google Tasks all exist, but:
- They do not integrate with Social Circle (no "buy gift for Mark's birthday" auto-suggestion)
- They do not feed into the Morning Briefing
- They require switching apps — Jarvis's value is one Telegram interface for everything
- Shared household task management in third-party tools is clunky (shared lists, permissions, separate accounts)
- Self-hosted = full control, no data leaving the Mac mini

### Why not extend Social Circle?

ContactEvent already has dates and reminders. But tasks are fundamentally different:
- Events are date-anchored facts (Mark's birthday IS June 14). Tasks are actionable items with a lifecycle (pending -> done/cancelled).
- Events do not have status, assignment, completion tracking, or snoozing.
- Task recurrence creates new instances that need individual completion. Event recurrence is a fixed date that repeats forever.
- Bolting task fields onto ContactEvent would violate single responsibility and complicate the existing reminder engine.

Separate module is the right call per Key Rule 5: "Modules are self-contained. Adding one never breaks another."

---

## Scope Boundaries

### In scope (v1)

- Task CRUD (create, read, update, delete)
- Status lifecycle: pending -> done / cancelled / snoozed
- Assignment: vincent, christianne, or both
- Due dates (optional) with automatic reminders
- Recurring tasks (daily, weekly, biweekly, monthly, quarterly, yearly)
- Snooze (push to a specific date/time)
- Contact linking (optional FK to Social Circle)
- Overdue nudges (daily for 7 days, then weekly)
- Morning Briefing integration (today's tasks section)
- Natural language interaction via Claude
- Completion and snooze via natural language
- Task search via title/description

### Out of scope (v2+)

- **Subtasks / checklists** — Keep v1 flat. Two-person household does not need nested task hierarchy.
- **Task categories / tags** — Natural language search + contact linking is sufficient for ~20 active tasks.
- **Calendar sync** (export to Google Calendar / Apple Calendar) — separate module.
- **Location-based reminders** ("remind me when I'm near the post office") — requires geofencing, way out of scope.
- **Task templates** ("Create a packing list template for trips") — power-user feature, defer.
- **Inline keyboard buttons** (Done / Snooze on reminder messages) — would be a great UX win but depends on Grammy + Claude Agent SDK support. Investigate for v1 if feasible, otherwise v2.
- **Recurring task editing** — v1: delete and recreate. v2: edit pattern and regenerate.
- **Priority-based smart ordering** — v1 shows all tasks. v2 orders by priority + urgency.

---

## Open Questions (for Spec Discussion)

1. **Timezone.** The household is in Chicago (America/Chicago per Morning Briefing). Social Circle uses Europe/Amsterdam. Should Task Reminders use America/Chicago? Should there be a single household timezone setting? **Recommendation:** Use America/Chicago to match Morning Briefing (the users are physically in Chicago). Address a unified timezone config as a cross-module concern.

2. **Overdue nudge recipients.** Should overdue nudges go to both users or only the assigned user? **Recommendation:** Only the assigned user(s). If assigned_to = "both", both get nudged. If assigned to one person, only they get nudged — unless overdue for 3+ days, then escalate to both.

3. **Completion authority.** Can Vincent mark Christianne's task as done? **Recommendation:** Yes. Full-trust household. `completed_by` records who actually marked it done for auditability.

4. **Early completion of recurring tasks.** If "Pay rent" is due June 1 but paid on May 28, does it count for the June cycle? **Recommendation:** Yes. Mark current as done, next occurrence is July 1.

5. **Maximum nudge duration.** When should the system stop nagging about an overdue task? **Recommendation:** Daily for 7 days, weekly for 3 weeks, then a final message: "This task has been overdue for a month. Should I cancel it?"

6. **Inline keyboard buttons.** Telegram supports inline buttons (Done / Snooze / Details) on reminder messages. One-tap completion would be a major UX win. **Recommendation:** Investigate Grammy + Claude Agent SDK support. If feasible without significant effort, include in v1. Otherwise v2.

---

## Effort Estimate

- **Data model:** 1 session (Task + TaskReminder models, Alembic migration)
- **API endpoints:** 1-2 sessions (CRUD + actions + filtered views + query params)
- **Proactive engine extension:** 1 session (reminder sending, overdue nudges, cron plist)
- **Skills (4):** 1-2 sessions (add-task, list-tasks, complete-task, snooze-task)
- **Morning Briefing integration:** 0.5 session (tasks section in briefing message)
- **Social Circle integration:** 0.5 session (auto-suggest tasks from events, contact-linked display)
- **Testing:** 1 session (unit + integration: recurrence calculation, reminder timing, fuzzy matching, overdue logic)

**Total: ~6-8 sessions.** Comparable to Social Circle in scope. No external APIs needed (unlike Morning Briefing), which simplifies the implementation.

---

## Recommendation

**Build this.** Task Reminders is the third pillar of Jarvis alongside Social Circle (people) and Morning Briefing (daily context). Together, they form the household automation triangle:

1. **Social Circle** — Who matters to us and when to reach out
2. **Morning Briefing** — What does today look like
3. **Task Reminders** — What do we need to do

The data model is simple (two tables), the interaction patterns are natural ("remind me to..." is one of the most intuitive things you can say to an assistant), and the integration points are obvious and valuable (tasks in the morning briefing, auto-suggested tasks from Social Circle events). The recurrence engine is the only non-trivial component, and the simple pattern string approach keeps it manageable. Ninety-five percent of household recurring tasks are daily/weekly/monthly/yearly.

This module directly addresses Vincent's stated need and fills the most obvious gap in Jarvis's current capabilities. It is arguably more immediately useful day-to-day than Social Circle (which is event-driven and spiky) — tasks would be used multiple times per week by both users.

**Proceed to spec.**

---

## References

- `specs/001-social-circle.md` — Data model patterns, proactive engine, reminder design
- `specs/002-morning-briefing.md` — Morning briefing integration point
- `backend/src/models/contact.py` — SQLAlchemy model pattern (UUID PK, timestamps, String lengths)
- `backend/src/models/event.py` — CheckConstraint, Index, FK patterns
- `backend/src/models/reminder.py` — ReminderConfig/SentReminder pattern
- `Ideation/BACKLOG.md` — Related backlog items (Household Chores, Grocery Lists, Bill Reminders, Home Maintenance)
- `CLAUDE.md` — Architecture, key rules (especially #2 Proactive > Reactive, #5 Extensible by design, #10 Christianne-first UX)
