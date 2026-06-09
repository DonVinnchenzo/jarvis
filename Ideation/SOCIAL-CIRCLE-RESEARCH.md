# Social Circle Module -- Ideation Research

**Project:** Jarvis (household automation assistant)
**Module:** Social Circle
**Users:** Vincent & Christianne (shared Telegram bot)
**Date:** 2026-06-09
**Phase:** Ideation

---

## 1. Problem Statement

Maintaining a social circle takes effort, and the overhead is invisible until you miss something.

**The core pains:**

- **Forgetting birthdays is embarrassing.** You find out via someone else's Instagram story, or worse, a week late. This damages relationships disproportionately -- the person remembers that you forgot.
- **Couples have asymmetric social knowledge.** Christianne knows her friends' kids' names and birthdays. Vincent knows his. Neither has a shared, queryable view. When you're at a dinner party and can't remember if their daughter is called Emma or Eva, you feel it.
- **Anniversary and life-event tracking falls through the cracks.** Wedding anniversaries of close friends, new babies, moves to a new city -- these are things you want to acknowledge but have no system for.
- **Free-form context matters.** "Jan mentioned he's thinking about switching jobs" or "Sophie is training for a marathon" -- remembering these details makes you a better friend. Right now this knowledge lives in two separate heads and decays over time.

This isn't about networking or "relationship management" in the LinkedIn sense. It's about being thoughtful friends who don't rely purely on memory.

---

## 2. Existing Solutions

### What's out there

| Tool | What it does | Why it falls short |
|---|---|---|
| **Phone contacts + calendar** | Store birthdays in contact cards, get OS-level reminders | No shared view for couples. No notes. No proactive "3 days before" nudges. Reminder UX is terrible. |
| **Monica HQ** | Open-source personal CRM. Tracks contacts, relationships, activities, reminders. | Designed for individual use, not couples. Requires opening a web app -- not integrated into daily flow. Overkill UI for a simple need. Self-hostable, which is good. |
| **Dex** | Personal CRM that syncs with your phone contacts and LinkedIn. | Cloud-hosted (privacy concern). Individual-focused. Geared toward professional networking, not personal friendships. Paid. |
| **Clay** | Aggregates contact info from email, calendar, social. AI-powered relationship intelligence. | Enterprise/professional tool. Way too heavy. Cloud-only. Not designed for "remind me about my friend's kid's birthday." |
| **Birthday reminder apps** (e.g., Birday, Birthday Countdown)** | Single-purpose: store birthdays, get notifications. | No couple sharing. No notes. No context beyond the date. Just a glorified calendar entry. |
| **Shared Apple/Google Calendar** | Put birthdays as recurring events. | Works in theory, clutters the calendar in practice. No structured data -- you can't ask "whose birthday is in the next 2 weeks?" No notes or relationship context. |
| **Notion / shared spreadsheet** | DIY database of friends and dates. | Not proactive. You have to remember to check it. No reminders unless you bolt on another tool. |

### The gap

No existing tool is:
1. **Couple-first** -- shared data, both users can add/query/update
2. **Proactive** -- pushes reminders to you at the right time, in a channel you already check (Telegram)
3. **Lightweight** -- just contacts, dates, notes, reminders. Not a CRM.
4. **Self-hosted** -- this is personal data about friends and their families. It shouldn't live on someone else's server.
5. **Conversational** -- add a contact by sending a message, not by filling out a form

---

## 3. Simplest Valuable Version

The MVP does four things:

1. **Store contacts with dates.** Name, birthday, optional: partner name, anniversary, kids + their birthdays.
2. **Store free-form notes per contact.** "Loves Italian wine." "Just bought a house in Utrecht." Timestamped.
3. **Send proactive reminders via Telegram.** "Sophie's birthday is in 3 days (turning 32). Last note: training for Rotterdam marathon."
4. **Answer queries.** "Whose birthday is coming up?" / "What do we know about Jan?" / "Who has kids?"

**What's NOT in the MVP:**
- Gift tracking or suggestions
- Automatic ingestion from phone contacts or social media
- Interaction history ("last time we saw them")
- NLP-powered conversational input (v1 can use simple commands)
- Multiple reminder schedules per event (just one: N days before, configurable)

**Interaction model (Telegram):**

Both Vincent and Christianne share one Telegram group or bot chat. Example interactions:

```
Vincent:  /add Sophie van Dijk birthday 1994-08-15
Jarvis:   Added Sophie van Dijk. Birthday: Aug 15, 1994.

Christianne:  /note Sophie -- just got promoted to senior designer at Philips
Jarvis:   Note added to Sophie van Dijk.

[Aug 12, 08:00]
Jarvis:   Reminder: Sophie van Dijk's birthday is in 3 days (Aug 15, turning 32).
          Notes: "just got promoted to senior designer at Philips" (added Jun 9)

Vincent:  /upcoming
Jarvis:   Upcoming events (next 30 days):
          - Aug 15: Sophie van Dijk's birthday (turning 32)
          - Aug 22: Jan & Marieke's wedding anniversary (3 years)
```

---

## 4. Data Model Sketch

Four entities. Intentionally simple.

### Contact

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| first_name | text | Required |
| last_name | text | Optional |
| relationship | text | e.g. "friend", "colleague", "family". Free-form, not an enum. |
| linked_contact_id | UUID | FK, nullable. Links partners (Sophie <-> Thomas). |
| created_by | text | "vincent" or "christianne" |
| created_at | timestamp | |
| updated_at | timestamp | |

### Event

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| contact_id | UUID | FK to Contact |
| event_type | text | "birthday", "anniversary", "custom" |
| label | text | Nullable. For custom events: "graduation", "due date", etc. |
| date | date | The date (year optional for recurring -- store year if known, use for age calc) |
| recurring | boolean | Default true. Birthdays recur; one-off events don't. |
| created_at | timestamp | |

### Note

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| contact_id | UUID | FK to Contact |
| content | text | Free-form. |
| created_by | text | "vincent" or "christianne" |
| created_at | timestamp | |

### Reminder

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| event_id | UUID | FK to Event |
| days_before | int | Default 3. How many days before the event to send the reminder. |
| sent_at | timestamp | Nullable. Null = not yet sent this cycle. Reset annually for recurring events. |

### Relationships

- Contact 1--* Event (a person can have a birthday + anniversary + custom events)
- Contact 1--* Note
- Event 1--* Reminder (could have a 7-day and a 1-day reminder)
- Contact *--1 Contact (optional partner link via linked_contact_id)

Kids are just Contacts with `relationship = "child of [parent name]"` or linked via a simple parent_id. No need for a separate entity in v1 -- a child is a contact with events and notes like anyone else.

---

## 5. Privacy Considerations

This module stores names, birthdays, family relationships, and personal notes about people in our social circle. They haven't consented to being in a database.

**Hard rules:**

- **Self-hosted only.** Runs on Vincent's Mac mini or a VPS he controls. No SaaS, no cloud databases managed by third parties.
- **No external API calls with PII.** No sending contact data to OpenAI, Claude, or any other external service. If we add AI features later (e.g., natural language input parsing), it processes locally or uses only non-PII context.
- **No sharing, no export to third parties.** This data never leaves the system except as Telegram messages to Vincent and Christianne.
- **Database encryption at rest.** PostgreSQL with encrypted storage volume.
- **Telegram transport security.** Bot API uses HTTPS. Messages in the shared chat are visible to both users -- that's by design. No sensitive data beyond what you'd say out loud.

This is a personal address book with reminders. Treat it with the same care as a physical notebook -- don't leave it lying around, don't let strangers read it.

---

## 6. Architecture Fit

Social Circle is the first module in Jarvis. The architecture should support adding more modules later (grocery lists, household tasks, shared calendar, etc.) without rewriting the foundation.

### Stack

| Layer | Choice | Rationale |
|---|---|---|
| **Database** | PostgreSQL | Structured relational data. Rock-solid. Easy to add tables for future modules. Already familiar from ClaryBook. |
| **Backend** | FastAPI (Python) | Lightweight, async, easy to extend. Proven in ClaryBook. Handles bot webhook + future API if we ever add a web UI. |
| **Telegram bot** | grammY (TypeScript) or python-telegram-bot | grammY if we want consistency with Claudegram. python-telegram-bot if we want a single-language stack. Leaning python-telegram-bot for simplicity -- one language, one process. |
| **Scheduler** | APScheduler or cron | Daily job at 08:00 CET: query upcoming events, send reminders. APScheduler runs inside the FastAPI process. Cron is simpler but separate. Start with APScheduler. |
| **Hosting** | Mac mini (local) or small VPS | Self-hosted. No Railway needed for a personal tool. |

### Module boundaries

```
jarvis/
  shared/           # DB connection, config, Telegram bot instance, scheduler
  modules/
    social_circle/  # Models, handlers, reminder logic
    [future]/       # grocery, tasks, calendar, etc.
  bot/              # Telegram command routing, dispatches to modules
  main.py           # App entry point
```

Each module registers its own:
- Database models (SQLAlchemy or raw SQL)
- Telegram command handlers
- Scheduled jobs

The shared layer provides the bot instance, DB session, and scheduler. Modules are self-contained.

### Why not just a spreadsheet + Google Calendar?

Because the point of Jarvis is to build a personal automation platform. Social Circle is the proving ground for the architecture. If the module system works here, it works for everything else. The investment in proper infrastructure pays off across all future modules.

---

## 7. Recommendation

**Proceed to spec.**

The problem is real (we've both forgotten birthdays this year). The solution is straightforward. No existing tool fits the couple-first, self-hosted, Telegram-native niche. The MVP is small enough to build in a few focused sessions.

**Next steps:**

1. Write a functional spec for the Social Circle module (commands, reminder logic, edge cases).
2. Define the Telegram interaction contract (group chat vs. direct bot, command syntax, response formats).
3. Set up the Jarvis project skeleton (repo, DB, bot, module structure).
4. Build and ship v1.

Estimated effort for a working MVP: 2-3 evenings.
