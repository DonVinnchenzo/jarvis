---
description: Log incident and update system to prevent recurrence. Use after any bug or failure.
---

# Post-Incident

## When to Use
After any bug, failure, or unexpected behavior in production.

## Steps

1. Document the incident:
   - What happened?
   - What was the impact?
   - Root cause?
   - How was it fixed?
2. Identify which CLAUDE.md, skill, or hook needs updating
3. Update the relevant file with a prevention rule
4. If pattern is critical, add a hook to `.claude/settings.json`

## Validation
Done when incident is documented and prevention rule is encoded.
