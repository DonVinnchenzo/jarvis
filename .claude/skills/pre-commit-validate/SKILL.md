---
description: Run full validation suite before committing. Use before every commit.
---

# Pre-Commit Validate

## When to Use
Before every `git commit`.

## Steps

1. Run backend validation:
   ```bash
   cd backend && ruff check . && pytest
   ```
2. Run bot validation:
   ```bash
   cd bot && npm run lint && npm run typecheck
   ```
3. If any step fails, fix the issue before committing
4. Report results

## Validation
Done when all checks pass.
