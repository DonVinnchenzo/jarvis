# Building Principles — Jarvis

Non-negotiable principles that govern every decision.

---

## 1. CORRECTNESS OVER SPEED

Plan thoroughly, verify exhaustively. Use Plan agent before changes touching 3+ files. A bug in personal reminders (missed birthday) costs trust.

## 2. SPECS ARE THE SOURCE OF TRUTH

If it's not in a spec, it doesn't exist. Specs survive context switches and agent sessions. AI agents have no persistence — specs are institutional memory.

## 3. EVERY FAILURE MAKES THE SYSTEM SMARTER

Don't just fix bugs — encode the lesson. Incidents update CLAUDE.md, skills, hooks. Same mistake never happens twice.

## 4. PROACTIVE BY DEFAULT

Jarvis should anticipate needs, not wait to be asked. Reminders days/weeks ahead. Contextual suggestions. The value is in what you don't have to remember.

## 5. SIMPLICITY IS A FEATURE

Delete rather than add. No speculative features. Every abstraction is future maintenance burden. Two users, one household — keep it simple.

## 6. CONTEXT IS SCARCE — SPEND IT WISELY

Root CLAUDE.md under 200 lines. Skills loaded on demand. Prune what Claude already knows from reading code.

## 7. DETERMINISTIC OVER ADVISORY

Rules that must never be violated -> hooks (guaranteed execution). Judgment calls -> CLAUDE.md (advisory).

## 8. PARALLEL BY DEFAULT

Independent work runs concurrently. Multiple agents with fresh perspectives. Don't serialize what can be parallelized.

## 9. PRIVACY IS NON-NEGOTIABLE

This is data about friends and family. No third-party analytics. No cloud processing of personal info beyond what's needed. Self-hosted where possible.

## 10. EXTENSIBLE MODULES

Architecture supports plugging in new life domains (social, household, groceries, travel, health) without refactoring core. Each module owns its data, reminders, and bot commands.
