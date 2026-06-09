---
description: Report a problem, bug, or something that went wrong. Use when a user says "something broke", "this isn't working", "I got the wrong reminder", "that was wrong", "there's a bug", "Jarvis made a mistake", "the reminder didn't come", or any complaint about incorrect behavior.
---

# Report Issue

## When to Use
When either user reports something that isn't working correctly, went wrong, or could be better. This is the user-friendly front door to the incident system. Christianne and Vincent should both be able to just describe what happened naturally — Claude handles the rest.

## Steps

1. **Acknowledge warmly** — "Got it, I'll look into that." Don't make the user feel like they're filing a bug report. They're just telling Jarvis something went wrong.

2. **Gather the details conversationally** — Ask only what's missing. Don't interrogate. If the user already said enough, skip straight to investigation.
   - What happened? (or what didn't happen?)
   - When did it happen? (or when was it expected?)
   - Who was affected? (just you, or both of you?)

   Example: If Christianne says "Mark's birthday reminder didn't come" — you already know what, when (today or recently), and who. Don't ask more.

3. **Investigate immediately** — Use available tools to diagnose:
   - Check the backend logs: `curl -s -H "X-API-Key: $JARVIS_API_KEY" http://localhost:8000/api/health`
   - Check if the event exists: `curl -s -H "X-API-Key: $JARVIS_API_KEY" "http://localhost:8000/api/search?q=Mark"`
   - Check SentReminder table for what was sent
   - Check the cron heartbeat
   - Read recent git log for related changes: `git log --oneline -10`

4. **Explain what happened** — In plain language, not technical jargon:
   - Good: "Mark's birthday is set to June 14, but the reminder was configured for 7 days before, which was June 7. That was a Saturday and the cron ran correctly. Let me check if the Telegram message was sent..."
   - Bad: "The SentReminder row shows event_id abc123 was processed at 08:00:01 UTC with status 200..."

5. **Fix it if possible** — If the fix is within Claude's capability:
   - Data issue: Fix via API calls
   - Code bug: Fix the code, run tests, commit
   - Config issue: Update the config
   - If NOT fixable right now: Explain what needs to happen and create a todo

6. **Log the incident** — Create `docs/incidents/INC-{NNN}-{short-description}.md`:
   ```markdown
   # INC-{NNN}: {Short description}

   **Reported by:** {Vincent/Christianne}
   **Date:** {today}
   **Severity:** {low/medium/high}
   **Status:** {resolved/investigating/open}

   ## What happened
   {Plain language description}

   ## Root cause
   {What went wrong technically}

   ## Fix applied
   {What was done to fix it}

   ## Prevention
   {What was updated to prevent recurrence — skill, CLAUDE.md, hook, or code}
   ```

7. **Update the system** — This is the critical step. Load the `post-incident` skill:
   - Update CLAUDE.md if a new rule is needed
   - Update or create a skill if a process was inconsistent
   - Add a test case if the bug is in code
   - Commit all changes

8. **Confirm with the user** — "Fixed! Here's what happened: {summary}. I've updated the system so this won't happen again."

## Severity Guide

- **High**: Missed reminder (the one thing Jarvis must never fail at), data loss, wrong data sent to wrong user
- **Medium**: Incorrect data displayed, slow response, formatting issue in reminders
- **Low**: Minor annoyance, cosmetic issue, feature works but awkwardly

## Rules

- NEVER be defensive about mistakes. Jarvis made an error, own it, fix it, prevent it.
- NEVER use technical jargon with Christianne unless she asks for details. Vincent can handle tech talk.
- ALWAYS log the incident, even if it seems minor. Pattern detection requires data.
- ALWAYS update something to prevent recurrence — if you can't identify a prevention, escalate to Vincent.
- The user should NEVER have to learn a special format or command to report an issue. "The reminder was wrong" is enough.
- If the issue is urgent (missed reminder for today), fix/workaround FIRST, investigate/document AFTER.
