---
description: Review a spec from product/user value perspective. Invoked by spec-writer.
---

# Spec Review — Product

## When to Use
Called by `/spec-writer` during parallel review gate.

## Steps

1. Read the spec being reviewed
2. Evaluate against these criteria:
   - **User value**: Does this save Vincent & Christianne real time/effort?
   - **Proactive fit**: Does it embody "remind before you ask" philosophy?
   - **Scope**: Is scope tight enough for first version? Over-engineered?
   - **Missing use cases**: What obvious scenarios are not covered?
   - **Both users**: Does the design work well for two people sharing one system?
   - **Jarvis philosophy**: Does it feel like a helpful assistant, not a chore tracker?
3. Classify findings as **Blocking** or **Suggestion**
4. Return structured review

## Validation
Done when review is returned with classified findings.
