# Task Reminders

**Status:** Approved
**Author:** Claude Code
**Date:** 2026-06-09

---

## Overview

Track household tasks with due dates, recurring schedules, and proactive reminders. Tasks range from one-time errands ("book Hamilton tickets") to recurring obligations ("pay rent on the 1st"). Both Vincent and Christianne can create, complete, snooze, and view tasks via natural language in Telegram.

This is the third Jarvis module. It closes the gap between knowing what's happening (Social Circle events, Morning Briefing conditions) and actually getting things done. Where Social Circle tracks date-anchored facts (Mark's birthday IS June 14), Task Reminders tracks actionable items with a lifecycle (pending -> done/cancelled/snoozed).

---

## Requirements

### Functional Requirements

- [ ] **REQ-001:** Create tasks via natural language. Claude interprets intent (title, due date, recurrence, assignment, contact link) and calls the API. Claude confirms task details before creating: "Got it -- 'Pay rent', monthly on the 1st, assigned to both of you. Sound right?"
- [ ] **REQ-002:** Task lifecycle management. Tasks have status: `pending` (default), `done`, `cancelled`, `snoozed`. Transitions: pending -> done, pending -> cancelled, pending -> snoozed (with snoozed_until date). Snoozed tasks revert to pending when snoozed_until date arrives.
- [ ] **REQ-003:** Due dates are optional. Tasks with a due date get automatic reminders (1 day before, day-of). Tasks without a due date appear in task lists but do not trigger proactive reminders unless the user manually sets one.
- [ ] **REQ-004:** Recurring tasks. Supported patterns: daily, weekly, biweekly, monthly, quarterly, yearly. When a recurring task is completed, the system auto-creates the next occurrence as a new Task row (preserving history). The original completed task stays in history for auditability ("did we pay rent in April?").
- [ ] **REQ-005:** Assignment. Each task is assigned to `vincent`, `christianne`, or `both` (default: `both`). Assignment determines who receives overdue nudges and who sees the task in their personal task list.
- [ ] **REQ-006:** Contact linking. Tasks can optionally reference a Social Circle contact via `contact_id` FK. Enables cross-module features: "Schedule meeting with Cory" links to Cory's contact record. When Claude shows contact detail, it includes pending tasks for that contact.
- [ ] **REQ-007:** Overdue nudge proactive messages. For tasks past their due date and still pending: daily nudge for 7 days, then weekly nudge for 3 weeks, then a final warning ("This task has been overdue for a month -- should I cancel it?"). Nudges go only to the assigned user(s).
- [ ] **REQ-008:** Morning Briefing integration. The morning briefing includes a tasks section showing today's due tasks and overdue tasks. The briefing endpoint calls `GET /api/tasks/today?user_id={id}` to pull task data.
- [ ] **REQ-009:** Task search via the existing `/api/search` endpoint. Task title and description are added to the search index alongside contacts and notes.
- [ ] **REQ-010:** Task listing with filters. Users can ask "what's on my plate?", "what tasks do we have?", "what's overdue?", "show me completed tasks this month", "any tasks related to Cory?". Filters: status, assigned_to, due date range, contact_id, completion date range.
- [ ] **REQ-011:** Both users can add and edit all tasks. No permission hierarchy -- single shared household. `completed_by` records who marked a task done for auditability.
- [ ] **REQ-012:** Snooze tasks to a specific date. "Remind me later" snoozes until tomorrow. "Push the rent check to the 5th" snoozes until the 5th. While snoozed, the task is excluded from overdue nudges and task lists. Un-snooze via "bring back the plumber task" (sets snoozed_until = null, status = pending) or re-snooze to a different date via "actually, push the plumber to next Monday".

### Non-Functional Requirements

- [ ] **NFR-001:** Performance -- Task CRUD operations respond in < 200ms.
- [ ] **NFR-002:** Overdue nudges respect the nudge frequency schedule (daily for 7 days, weekly for 3 weeks, final warning at ~30 days). No duplicate nudges on the same day. Idempotent engine (safe to re-run).
- [ ] **NFR-003:** Recurring task completion atomically creates the next occurrence. The complete endpoint marks the current task as done AND creates the next task in a single database transaction. No orphaned states.

---

## Acceptance Criteria

- [ ] **AC-001:** Vincent says "Remind me to pay rent on the 1st of every month." Claude creates a task with title "Pay rent", due_date = next 1st, recurrence = monthly on 1st, assigned_to = both. Task appears in `/api/tasks`.
- [ ] **AC-002:** Vincent says "Rent is paid." Claude fuzzy-matches to the "Pay rent" task, marks it done, and auto-creates the next occurrence (next month's 1st). Response: "Marked 'Pay rent' as done. Next reminder: July 1st."
- [ ] **AC-003:** A task due yesterday triggers a daily overdue nudge to the assigned user(s) at the morning check time.
- [ ] **AC-004:** After 7 daily nudges, the nudge frequency drops to weekly. After 3 more weekly nudges, a final "should I cancel?" message is sent.
- [ ] **AC-005:** No duplicate nudges: if the reminder engine runs twice on the same day, only one nudge is sent per task.
- [ ] **AC-006:** The morning briefing includes a "Today's tasks" and "Overdue" section with task data from `GET /api/tasks/today`.
- [ ] **AC-007:** Vincent says "What's on my plate?" and sees pending tasks assigned to him or "both", grouped by: overdue, today, upcoming, no date.
- [ ] **AC-008:** Christianne says "Snooze the plumber call for a week." The task disappears from active lists and overdue nudges until the snooze date, then reappears as pending.
- [ ] **AC-009:** A task created with `contact_id` pointing to Cory's contact shows up when Claude displays Cory's contact detail: "You have 1 pending task for Cory: Schedule meeting."
- [ ] **AC-010:** Searching "plumber" via `/api/search` returns matching tasks alongside contacts and notes.
- [ ] **AC-011:** Vincent says "Cancel the plumber task." Task status changes to cancelled. It no longer appears in active lists or triggers nudges.
- [ ] **AC-012:** A task with no due date sits in the task list indefinitely without triggering overdue nudges.

---

## Technical Notes

### Constraints

- Single household, two Telegram users. Assignment is a simple enum, not a user FK.
- Backend (FastAPI) runs on localhost:8000, only the bot calls it.
- Claude calls the API via Bash (curl). Never direct SQL.
- No external APIs needed -- this module is entirely self-contained.

### Proactive Engine Extension

The existing proactive engine runs daily crons for Social Circle (08:00 Europe/Amsterdam) and Morning Briefing (07:00 America/Chicago). Task reminders hook into the same cron infrastructure:

- **Option A (recommended): Same cron, new endpoint.** The cron calls `POST /api/tasks/reminders/run` alongside the existing reminder endpoints. Keeps modules independent per Key Rule 5.
- The task reminder engine runs at the same time as Morning Briefing (07:00 America/Chicago) so that overdue nudges and morning briefing tasks are synchronized.

### Timezone Handling

Tasks use dates (not datetimes) for `due_date`. The proactive engine computes "today" in `America/Chicago` (same as Morning Briefing). The `due_time` field on Task is optional and used for display only ("call before 5pm"), not for reminder scheduling.

### Overdue Nudge Engine Logic

```
0. Un-snooze expired tasks: UPDATE task SET status = 'pending', snoozed_until = NULL
   WHERE status = 'snoozed' AND snoozed_until <= today.
   This runs first so that un-snoozed tasks are immediately visible in list queries
   and eligible for overdue nudges.
1. Load all tasks where status = 'pending' AND due_date < today
2. For each overdue task:
   a. Calculate days_overdue = today - due_date
   b. Determine nudge frequency:
      - days 1-7:   daily nudge
      - days 8-13:  no nudge (intentional break after daily cadence)
      - days 14, 21, 28: weekly nudge
      - day 30+:    final warning (single message, then stop nagging)
   c. Check TaskReminder for existing sent reminder on today's date for this task
   d. If no reminder sent today AND frequency says to nudge today:
      - Send nudge to assigned user(s) only
      - Record in TaskReminder (sent = true, sent_at = now)
3. Log summary: "Processed N overdue tasks, sent M nudges, skipped K"
```

### Recurring Task Completion Logic

```
1. User completes a task that has a TaskRecurrence record (SELECT FROM task_recurrence WHERE task_id = ?)
2. In a single transaction:
   a. Set current task: status = 'done', completed_by = user_id, completed_at = now()
   b. Calculate next_due_date from recurrence pattern:
      - daily: current due_date + 1 day (NOT today + 1, to prevent drift on early completion)
      - weekly: current due_date + 7 days
      - biweekly: current due_date + 14 days
      - monthly: same day_of_month, next month (handle month-end: Jan 31 -> Feb 28)
      - quarterly: same day_of_month, +3 months
      - yearly: same day + month, next year (handle Feb 29 -> Feb 28 in non-leap)
   c. Create new Task row: same title, description, assigned_to, contact_id, priority,
      visibility. New due_date = next_due_date. Status = pending.
   d. Create new TaskRecurrence row with task_id = new task's ID (copy pattern and day fields)
   e. Create default TaskReminder rows for the new task (1 day before, day-of)
3. Return both the completed task and the newly created next occurrence
```

### Early Completion of Recurring Tasks

If a recurring task is completed before its due date (e.g., "Pay rent" due June 1 but paid May 28), it counts for the current cycle. The next occurrence is calculated from the original due date (July 1), not from the completion date. This prevents date drift.

### Patterns to Follow

- Same CRUD pattern as `/api/contacts` -- RESTful with convenience action endpoints
- Same proactive engine pattern as Social Circle (cron -> endpoint -> send -> dedup)
- Same `X-API-Key` authentication on all endpoints
- UUID PKs with `gen_random_uuid()` database default
- All timestamps use `now()` database default
- `created_by` tracking on all mutations

### Implementation Hints

- The `complete` endpoint is the most complex -- it must handle recurrence atomically. Use a database transaction.
- Fuzzy matching for task completion ("rent is paid" -> "Pay rent") should match against pending task titles. If ambiguous, return candidates and let Claude ask the user.
- The `/api/tasks/today` endpoint should return tasks grouped: `{ overdue: [...], today: [...], upcoming_3_days: [...] }` for easy Morning Briefing integration.
- Overdue status is computed, never stored. A task is overdue when `status = 'pending' AND due_date < today`. No batch job needed to flip statuses.

---

## Dependencies

### Depends On

- PostgreSQL database (same instance as Social Circle)
- Telegram bot (same bot, new skills)
- FastAPI backend (same backend, new module)
- Morning Briefing module (for briefing integration -- `POST /api/briefing/run` calls tasks endpoint)
- Social Circle module (for `contact_id` FK and contact detail integration)

### Blocked By

- Nothing -- can begin implementation immediately. Social Circle and Morning Briefing schemas already exist.

### Blocks

- Future modules: Grocery Lists (simple shopping tasks migrate here), Bill Reminders (subset of recurring tasks)

---

## Out of Scope

- **Subtasks / checklists** -- Keep v1 flat. Subtasks add complexity without proportional value for a two-person household.
- **Task categories / tags** -- Natural language search is sufficient for ~20 active tasks.
- **Calendar sync** (Google Calendar, Apple Calendar) -- Separate module if needed later.
- **Location-based reminders** ("remind me when I'm near the post office") -- Requires geofencing, way out of scope.
- **Time-based intra-day reminders** ("remind me at 3pm") -- v1 sends all reminders during the morning check window. Intra-day is v2.
- **Task templates** ("packing list template for trips") -- Power-user feature. Defer.
- **Priority-based ordering** -- v1 has a priority field but the morning briefing shows all tasks. Smart ordering by priority + due date is v2.
- **Recurring pattern editing** -- v1: to change a recurrence pattern, delete and recreate. v2: edit the pattern and regenerate future occurrences.

---

## Open Questions

1. **Q:** Timezone -- use `America/Chicago` (same as Morning Briefing)?
   **A:** Yes. Tasks and Morning Briefing are tightly coupled (briefing shows today's tasks). Using the same timezone avoids "today" disagreements. If Vincent and Christianne move, update the single household timezone setting.

2. **Q:** Overdue nudge channel -- only assigned user(s)?
   **A:** Yes. Nudges go only to the assigned user(s). If assigned_to = "vincent", only Vincent gets nudges. If "both", both get nudges. Christianne should not be nagged about Vincent's personal tasks.

3. **Q:** Completion authority -- anyone can mark any task done?
   **A:** Yes. Full-trust household model. Anyone can complete any task. `completed_by` records who actually did it for auditability.

4. **Q:** Recurring completion before due date -- does early completion count for the current cycle?
   **A:** Yes. Mark current as done, next occurrence calculated from the original due date (not completion date) to prevent drift. "Pay rent" due June 1, paid May 28 -> next due July 1.

5. **Q:** Max overdue nudge duration?
   **A:** Daily for 7 days, weekly for 3 weeks (days 14, 21, 28), then a final warning at ~30 days: "This task has been overdue for a month -- should I cancel it?" After the final warning, no more nudges. The task stays pending but silent until the user acts.

---

## User Stories

### Story 1: Recurring bill payment

**As** Vincent
**I want** to set up a monthly rent reminder on the 1st
**So that** we never forget to confirm rent is paid

### Story 2: Person-linked task

**As** Vincent
**I want** to create a task "Schedule meeting with Cory" linked to Cory's contact
**So that** I see pending tasks when I look up Cory's details

### Story 3: Shared household errand

**As** Christianne
**I want** to add a task "Buy wedding gift for Mark & Lisa" assigned to both
**So that** either of us can handle it and we both see it on our lists

### Story 4: Overdue nudge

**As** Vincent
**I want** Jarvis to nudge me daily when a task is overdue
**So that** things don't fall through the cracks

### Story 5: Morning briefing tasks

**As** Christianne
**I want** to see today's tasks and overdue items in the morning briefing
**So that** I start the day knowing what needs doing

### Story 6: Snooze and come back

**As** Vincent
**I want** to snooze a task to a specific date
**So that** I stop getting nudged about it until I'm ready to deal with it

### Story 7: Task completion history

**As** Vincent
**I want** to ask "did we pay rent in April?"
**So that** I can verify past completions without checking bank records

---

## API / Interface

### Backend Endpoints (FastAPI)

```
# Task CRUD
POST   /api/tasks                  -- Create a task
GET    /api/tasks                  -- List tasks (filter: status, assigned_to, due_date_from,
                                      due_date_to, contact_id, completed_from, completed_to).
                                      Paginated: limit (default 50), offset. History grows from
                                      recurring tasks, so pagination is required.
GET    /api/tasks/{id}             -- Get task detail (includes recurrence and reminders)
PUT    /api/tasks/{id}             -- Update task (title, description, due_date, priority,
                                      assigned_to, contact_id)
DELETE /api/tasks/{id}             -- Delete task (cascades to recurrence and reminders)

# Task Actions
POST   /api/tasks/{id}/complete    -- Mark task as done. Body: { completed_by: telegram_user_id }.
                                      If recurring: auto-creates next occurrence in same transaction.
                                      Returns: { completed_task, next_occurrence (nullable) }
POST   /api/tasks/{id}/cancel      -- Set status to cancelled, cancelled_at = now()
POST   /api/tasks/{id}/snooze      -- Snooze task. Body: { snoozed_until: "2026-06-15" }.
                                      Sets status to 'snoozed' and snoozed_until date.
                                      To un-snooze: PUT /api/tasks/{id} with snoozed_until = null,
                                      status = 'pending'. Re-snooze: call snooze again with new date.

# Convenience Endpoints
GET    /api/tasks/today             -- Today's tasks + overdue for a user.
         ?user_id={telegram_id}       Returns: { overdue: [...], today: [...], upcoming_3_days: [...] }
POST   /api/tasks/reminders/run    -- Trigger task reminder engine (cron). Processes overdue nudges
                                      and upcoming task reminders. Idempotent.

# Search (existing endpoint, extended)
GET    /api/search?q=term          -- Now also returns matching tasks (title, description)
```

### Operational Skills

Claude uses these when users interact:

- `add-task` -- Create a new task with optional due date, recurrence, assignment, contact link
- `list-tasks` -- Show pending tasks with filters (my tasks, all tasks, overdue, by contact)
- `complete-task` -- Mark a task as done (fuzzy match on title, handles recurrence)
- `snooze-task` -- Snooze a task to a specific date

---

## Data Model

```
Task
  - id: UUID (PK)
  - title: string (required, max 300 chars)
  - description: text (nullable -- extra context)
  - due_date: date (nullable -- some tasks have no hard deadline)
  - due_time: time (nullable -- most household tasks don't need a specific time)
  - priority: enum ("low", "normal", "high") -- default "normal"
  - status: enum ("pending", "done", "snoozed", "cancelled") -- default "pending"
  - assigned_to: enum ("vincent", "christianne", "both") -- default "both"
  - created_by: string (Telegram user ID)
  - completed_by: string (nullable -- Telegram user ID of whoever marked it done)
  - completed_at: timestamp (nullable)
  - cancelled_at: timestamp (nullable)
  - snoozed_until: date (nullable -- when to resurface a snoozed task)
  - contact_id: UUID (FK -> Contact, nullable, ON DELETE SET NULL)
  - visibility: enum ("shared", "personal") -- default "shared"
  - created_at: timestamp
  - updated_at: timestamp

TaskRecurrence
  - id: UUID (PK)
  - task_id: UUID (FK -> Task, ON DELETE CASCADE)
  - pattern: enum ("daily", "weekly", "biweekly", "monthly", "quarterly", "yearly")
  - day_of_month: int (nullable -- for monthly/quarterly/yearly: "on the 1st")
  - day_of_week: int (nullable -- for weekly/biweekly: 0=Monday through 6=Sunday)
  - month_of_year: int (nullable -- for yearly: which month, 1-12)
  - created_at: timestamp
  Note: FK goes from TaskRecurrence -> Task (not the other way around).
  Each Task occurrence gets its own TaskRecurrence row (copied on recurring
  completion). Deleting a Task cascades to its TaskRecurrence. No orphans.

TaskReminder
  - id: UUID (PK)
  - task_id: UUID (FK -> Task, ON DELETE CASCADE)
  - remind_at: date (when to send the reminder)
  - remind_time: time (nullable -- defaults to morning briefing time)
  - sent: bool (default false)
  - sent_at: timestamp (nullable)
  - created_at: timestamp
  Note: Overdue nudge count is computed, not stored. The engine counts sent
  reminders per task: SELECT COUNT(*) FROM task_reminder WHERE task_id = ?
  AND sent = true. This avoids stale counters.

Indexes:
  - Task: (status, due_date) -- for overdue and today queries
  - Task: (assigned_to) -- for per-user task lists
  - Task: (contact_id) -- for contact-linked task lookups
  - Task: GIN index on title (for search)
  - TaskReminder: UNIQUE (task_id, remind_at) -- prevents duplicate reminders on same day
  - TaskReminder: (sent, remind_at) -- for reminder engine: unsent reminders due today

DB Defaults:
  - All UUID PKs use gen_random_uuid() as database default
  - All timestamps use now() as database default
  - Task.status defaults to 'pending'
  - Task.priority defaults to 'normal'
  - Task.assigned_to defaults to 'both'
  - Task.visibility defaults to 'shared'
  - TaskReminder.sent defaults to false
```

### Data Model Design Decisions

- **`assigned_to` is a simple enum, not a user FK.** There are only two users. A string enum is clearer than a junction table.
- **`contact_id` uses ON DELETE SET NULL.** If a linked contact is deleted, the task survives but loses its contact reference. Tasks should not cascade-delete with contacts.
- **`task_id` FK lives on TaskRecurrence (not the other way around).** This matches the research doc design and avoids orphan rows: deleting a Task cascades to its TaskRecurrence. Each completed occurrence's new Task gets its own copy of the TaskRecurrence row, so there are no shared-state bugs.
- **No separate `overdue` status.** A task is overdue when `status = 'pending' AND due_date < today`. Computed, not stored. No batch job needed.
- **Separate TaskReminder table (not reusing Social Circle's ReminderConfig/SentReminder).** Different semantics: event reminders are "N days before a date" (computed), task reminders are "on this specific date" (explicit). Overdue nudge logic (re-remind until done) does not exist in Social Circle. Keeping them separate avoids polluting the tested Social Circle engine.
- **Overdue nudge count is computed, not stored.** The engine counts `SELECT COUNT(*) FROM task_reminder WHERE task_id = ? AND sent = true` to determine escalation from daily to weekly to final warning. No stale counter fields.
- **`cancelled_at` timestamp added** for symmetry with `completed_at`. Enables history queries ("when did we cancel that task?").

---

## Client Requirements

**Clients:** Telegram bot (both Vincent and Christianne).

No web UI, no mobile app. The Telegram bot is the sole interface. Both users interact with the same bot and see the same shared data (filtered by assignment where relevant).

---

## Security Considerations

- [ ] All task endpoints require `X-API-Key` header (same as Social Circle).
- [ ] Backend bound to `127.0.0.1` -- not accessible externally.
- [ ] Telegram user ID whitelist enforced -- only Vincent and Christianne can interact.
- [ ] Input validation on task title (max 300 chars), description (max 5000 chars), due_date (valid date), snoozed_until (must be >= today).
- [ ] No sensitive data in logs -- log task IDs and actions, not task titles or descriptions.
- [ ] `contact_id` validated against existing contacts before creating task (return 400 if contact not found).
- [ ] `completed_by` and `created_by` validated against allowed Telegram user IDs.

---

## Testing Strategy

### Unit Tests

- **Recurring next-date calculation** -- All 6 patterns. Edge cases: month-end (Jan 31 monthly -> Feb 28), yearly on Feb 29 (-> Feb 28 in non-leap), biweekly crossing month boundary.
- **Overdue nudge frequency** -- Given days_overdue, verify correct nudge schedule (daily 1-7, weekly 8-28, final at 30).
- **Fuzzy task matching** -- "rent is paid" matches "Pay rent". "done with Cory" matches "Schedule meeting with Cory". No match returns empty. Multiple matches returns candidates.
- **Snooze logic** -- Snoozed task excluded from overdue queries. Snooze expiry re-includes task.

### Integration Tests

- **Task CRUD endpoints** -- Create, read, update, delete. Verify cascading deletes (task -> reminders).
- **Complete with recurrence** -- Complete a recurring task, verify next occurrence created with correct due date. Verify original task is done.
- **Reminder engine** -- Seed overdue tasks, run engine, verify correct nudges generated. Run again, verify no duplicates.
- **Contact-linked tasks** -- Create task with contact_id, delete contact, verify task still exists with contact_id = NULL.
- **Morning Briefing integration** -- Call `/api/tasks/today`, verify correct grouping (overdue, today, upcoming).

### E2E Tests

- **Natural language flow** -- Mock Telegram, user says "remind me to pay rent monthly on the 1st", verify task + recurrence created.
- **Completion flow** -- Seed recurring task, user says "rent is paid", verify completion + next occurrence.
- **Nudge delivery** -- Seed overdue task, run reminder engine, verify Telegram message sent to correct user.

---

## Message Format Examples

### Overdue Nudge

```
Hey Vincent, you have 2 overdue tasks:

- "Pay rent" was due June 1 (3 days ago) -- assigned to both
- "Call dentist" was due May 28 (7 days ago) -- assigned to you

Reply "done with [task]" to mark complete, or "snooze [task]" to push it back.
```

### Task Completion Confirmation (Recurring)

```
Marked "Pay rent" as done. Nice!

Next occurrence: July 1st (monthly). I'll remind you the day before.
```

### Task Completion Confirmation (One-time)

```
Marked "Book Hamilton tickets" as done. One less thing to worry about!
```

### Morning Briefing Tasks Section

```
Today's tasks:
- Pay rent (due today, assigned to both)

Coming up:
- Schedule dentist cleaning (due in 3 days, assigned to Vincent)
- Book flights to Amsterdam (due in 2 days, assigned to both)

Overdue:
- Call plumber (2 days overdue, assigned to Christianne)
```

### Final Overdue Warning

```
Hey Vincent, "Call dentist" has been overdue for a month (due May 28).

Should I cancel it, snooze it, or is it still on your list?
```

---

## Rollout Plan

1. **Phase 1: Backend -- Data Model + CRUD** -- Create PostgreSQL tables (Task, TaskRecurrence, TaskReminder). Implement CRUD endpoints, complete/snooze/cancel action endpoints, and `/api/tasks/today`. Write unit and integration tests.
2. **Phase 2: Recurring Task Engine** -- Implement the atomic complete-and-create-next logic. Test all 6 recurrence patterns including edge cases.
3. **Phase 3: Overdue Nudge Engine** -- Implement `POST /api/tasks/reminders/run`. Nudge frequency logic, dedup via TaskReminder, Telegram sends. Create launchd plist (or extend existing Morning Briefing cron).
4. **Phase 4: Morning Briefing Integration** -- Extend `POST /api/briefing/run` to call `/api/tasks/today` and include tasks section in the briefing message.
5. **Phase 5: Skills + Search** -- Create operational skills (add-task, list-tasks, complete-task, snooze-task). Extend `/api/search` to include tasks. Test natural language flows.
6. **Phase 6: Go Live** -- Seed initial tasks (rent, recurring bills). Monitor nudges for a week. Fix issues.

---

## References

- `Ideation/TASK-REMINDERS-RESEARCH.md` -- Ideation research (data model exploration, user scenarios, alternatives considered)
- `specs/001-social-circle.md` -- Data model patterns, proactive engine, reminder design
- `specs/002-morning-briefing.md` -- Morning briefing integration point, timezone conventions
- `specs/TEMPLATE.md` -- Spec template

---

## Changelog

- 2026-06-09 -- Claude Code -- Initial draft
- 2026-06-09 -- Claude Code -- Addressed 2-way review (backend + product):
  - B-001: Reversed FK direction -- TaskRecurrence.task_id -> Task ON DELETE CASCADE (no orphans)
  - B-002: Removed nudge_count field -- overdue count computed via COUNT query (no stale counters)
  - B-003: Added explicit snooze-to-pending transition in reminder engine (step 0: un-snooze expired)
  - B-004: Clarified weekly nudge schedule -- intentional gap days 8-13 before weekly cadence
  - P-001: Added un-snooze and re-snooze interaction patterns and API documentation
  - P-002: Added "Coming up" section to morning briefing message format (next 3 days)
  - Added cancelled_at timestamp for history queries (backend suggestion S-001)
  - Clarified daily recurrence uses due_date + 1, not today + 1 (backend suggestion S-002)
  - Added pagination to GET /api/tasks (backend suggestion S-003)
  - Status -> Approved
