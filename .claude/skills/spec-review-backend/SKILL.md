---
description: Review a spec from backend engineering perspective. Invoked by spec-writer.
---

# Spec Review — Backend

## When to Use
Called by `/spec-writer` during parallel review gate.

## Steps

1. Read the spec being reviewed
2. Evaluate against these criteria:
   - **Data model**: Are entities well-defined? Relationships correct? Missing fields?
   - **API design**: RESTful? Consistent with existing endpoints? Proper error handling?
   - **Performance**: Will queries scale? Need indexes? Pagination needed?
   - **Migration safety**: Any destructive changes? Backward compatibility?
   - **Scheduling**: Are cron jobs / scheduled tasks well-defined? Edge cases (timezone, DST)?
3. Classify findings as **Blocking** (must fix) or **Suggestion** (nice to have)
4. Return structured review

## Validation
Done when review is returned with classified findings.
