---
description: Verify implementation matches spec acceptance criteria. Use after build phase.
---

# Spec Verify

## When to Use
After implementation is complete, as final review gate.

## Steps

1. Read the spec for this feature
2. Go through each acceptance criterion:
   - Find the code that implements it
   - Verify it works as specified
   - Check edge cases mentioned in spec
3. Report: which AC pass, which fail, which are untestable
4. If any AC fail, implementation needs fixes before shipping

## Validation
Done when all acceptance criteria are verified pass/fail.
