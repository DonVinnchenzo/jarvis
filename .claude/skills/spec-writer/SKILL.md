---
description: Write a feature specification. Use after ideation research is complete and the recommendation is to proceed.
---

# Spec Writer

## When to Use
After ideation research recommends proceeding. Creates a spec from the template with 3 parallel reviews.

## Steps

1. Read `specs/TEMPLATE.md`
2. Read the ideation research document for this feature
3. Determine next spec number: `ls specs/*.md | tail -5`
4. Write the spec following the template, filling in all sections relevant to this feature
5. Launch 3 parallel review agents (use Task tool):
   - `/spec-review-backend` — data model, API, performance, migration safety
   - `/spec-review-product` — user value, scope, missing use cases, Jarvis philosophy fit
   - Security review — privacy implications, data handling, personal info protection
6. Collect all blocking issues from reviews
7. Address all blocking issues in the spec
8. Update spec status to "In Review" then "Approved" once all blockers resolved

## Validation
Done when spec exists, all 3 reviews completed, all blocking issues resolved.

## References
- `specs/CLAUDE.md`
- `specs/TEMPLATE.md`
