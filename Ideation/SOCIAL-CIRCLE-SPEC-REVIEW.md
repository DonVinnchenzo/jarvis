# SPEC-001 Social Circle — 3-Way Review Summary

**Date:** 2026-06-09
**Reviewers:** Backend, Product, Security (parallel sub-agents)

---

## Blocking Issues (All Resolved)

### Backend Review

- **BLOCKING-01: Child birthdays duplicate ContactEvent logic.** ContactChild had its own birthday fields, creating parallel code paths in the engine, upcoming queries, and reminder config. **Fix:** Children's birthdays are now ContactEvent rows with `event_type = "child_birthday"` and a `child_id` FK. Single code path for all date logic.
- **BLOCKING-05: Year-boundary logic unspecified.** A Jan 2 event with 7-day lead fires Dec 26. Engine must check both this year's and next year's occurrences. **Fix:** Engine flow now explicitly computes both years.

### Product Review

- **BLOCKING-4d: No day-of reminder.** Default was 7 days + 1 day, but no day-of safety net. **Fix:** Default is now 7, 1, and 0 days.
- **BLOCKING-6a: Reminders feel like database notifications, not an assistant.** Notes existed but weren't surfaced in reminders. **Fix:** Reminder messages now include the contact's most recent notes for context.

### Security Review

- **BLOCK-1: Backend API has no authentication.** Telegram whitelist protects the bot, but the FastAPI API was unprotected. **Fix:** API key (`X-API-Key` header) required for all endpoints. Self-hosted: bind to 127.0.0.1.

---

## Suggestions Adopted

- Simplified v1: global reminder config only (no per-event overrides)
- Dropped `notify_users` from ReminderConfig (always notify all whitelisted users)
- Added `updated_at` to ContactEvent
- Added CHECK constraints on day/month at DB level
- Specified `Europe/Amsterdam` timezone (not "CET")
- Added heartbeat monitoring for cron reliability
- Added GDPR household exemption documentation note
- Added `gen_random_uuid()` as DB default for all UUID PKs
- Expanded Out of Scope with v2 items (relationship decay, interactive buttons, per-event overrides)

---

## Suggestions Deferred to v2

- Relationship decay detection ("haven't seen X in 3 months" nudges)
- Interactive inline keyboard buttons on reminders (Show notes / Snooze / Mark as handled)
- Per-event reminder overrides
- Per-user notification preferences
- Duplicate contact detection during `/add`
- Contact archive/inactive status for life changes
- "Whose friend is this" context field

---

## Verdict

All 5 blocking issues resolved. Spec updated to "In Review" status. Ready for user approval → Approved → Implementation.
