---
description: Multi-agent code review before merging. Use after implementation is complete.
---

# PR Review

## When to Use
After implementation, before merging/deploying.

## Steps

1. Read all changed files in the PR/branch
2. Launch parallel review agents (use Task tool):
   - **Correctness agent**: Does the code do what the spec says? Logic bugs? Edge cases?
   - **Security agent**: Privacy issues? Input validation? Data exposure?
   - **Quality agent**: Code style? Duplication? Test coverage? Error handling?
3. Collect findings, classify as Blocking or Suggestion
4. Address all blocking issues
5. Re-review if blocking changes were made

## Validation
Done when all blocking issues resolved.
