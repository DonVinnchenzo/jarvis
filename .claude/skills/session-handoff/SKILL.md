---
description: Update STATUS.md before a session ends or after any significant action. Use at the end of every conversation, when the user says "I'm done", "gotta go", "let's stop here", "save progress", or when Claude detects the conversation is wrapping up.
---

# Session Handoff

## When to Use

- **End of every conversation** — before the session closes
- **After any significant action** — spec approved, code committed, feature shipped, decision made
- **When the user says goodbye** or indicates they're leaving
- **Proactively** — if the conversation has been long, update periodically so nothing is lost

## Why This Matters

Claude Code sessions don't persist context across chats. If this conversation ends, the next Claude session starts fresh. STATUS.md is the bridge — it tells the next session exactly what happened and what to do next.

## Steps

1. **Read current STATUS.md** — `Read /Users/vincent/jarvis/STATUS.md`
2. **Update these sections:**

   - **Current Phase** — Which roadmap phase are we in?
   - **Current Step** — What specific step are we on? Be precise. Not "building", but "Backend Phase 1: CRUD endpoints done, writing integration tests for /api/upcoming"
   - **What to do next** — Numbered list. The next session should be able to start working immediately without asking questions.
   - **Key decisions already made** — Add any new decisions from this session
   - **Recent history** — Append what was done in this session (date + summary)

3. **Write the updated file** — Save to `/Users/vincent/jarvis/STATUS.md`
4. **Commit** — `git add STATUS.md && git commit -m "docs: update STATUS.md with session progress"`
5. **Push** — `git push` so the file is available even if the local session data is lost

## Rules

- STATUS.md must ALWAYS reflect the true current state. Never leave it stale.
- The "What to do next" section must be actionable — a fresh Claude session should be able to follow it without asking the user "where were we?"
- Be specific about file names, spec numbers, and step numbers. "Continue building" is useless. "Run `pytest backend/tests/test_upcoming.py` to verify the failing test, then implement the fix in `backend/src/routes/upcoming.py:45`" is useful.
- If there are open questions or blockers, list them explicitly.
- Keep the file concise — it's a status update, not a journal. New sessions shouldn't have to read 500 lines.
