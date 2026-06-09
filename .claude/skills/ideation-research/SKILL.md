---
description: Research a feature idea before committing to build. Use when exploring a new module or capability for Jarvis.
---

# Ideation Research

## When to Use
Before writing a spec for any new feature or module.

## Steps

1. Read `Ideation/BACKLOG.md` to understand the idea context
2. Research the problem space:
   - What existing tools solve this? (apps, bots, services)
   - What's the simplest version that delivers value?
   - What data model would this need?
   - What are the privacy implications?
3. Launch 3 parallel validation agents (use Task tool):
   - **Feasibility agent**: Can we build this with our stack (FastAPI + Grammy + PostgreSQL)? What's the complexity?
   - **User value agent**: Does this actually save Vincent & Christianne time/effort? What's the frequency of use?
   - **Architecture agent**: Does this fit the modular architecture? Any conflicts with existing modules?
4. Synthesize findings into `Ideation/[FEATURE]-RESEARCH.md`
5. Recommend: proceed to spec, needs more research, or park

## Validation
Done when research document exists and includes a clear recommendation.

## References
- `Ideation/CLAUDE.md`
- `docs/PRINCIPLES.md`
