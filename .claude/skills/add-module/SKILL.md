---
description: Propose and build a new Jarvis module. Use when a user says "we should track X", "can we add Y", "I want Jarvis to handle Z". This triggers the full 5-phase workflow.
---

# Add Module

## When to Use
When a user requests a new capability that doesn't exist yet — a new life domain for Jarvis to manage.

## Steps

1. **Acknowledge the idea** — Confirm what the user wants and why
2. **Add to backlog** — Update `Ideation/BACKLOG.md` with the idea
3. **Ask: research now or later?** — The user might want to explore immediately or just park the idea
4. **If now, follow the 5-phase workflow:**

   a. **Phase 1: Ideation** — Load skill `ideation-research`. Research the idea with 3 parallel validation agents (feasibility, user value, architecture fit). Save to `Ideation/{MODULE}-RESEARCH.md`

   b. **Phase 2: Specs** — Load skill `spec-writer`. Write the spec from template. Run 3-way parallel review (backend, product, security). Address blockers. Save to `specs/NNN-module-name.md`

   c. **Phase 3: Planning** — Load skill `implementation-plan`. Map files, dependencies, execution steps. Save to `Ideation/{MODULE}-IMPLEMENTATION-PLAN.md`. Get user approval.

   d. **Phase 4: Build** — Implement per plan. Use `pre-commit-validate` before each commit. Git commit after each step.

   e. **Phase 5: Review** — Load skill `spec-verify`. Verify all acceptance criteria. Load skill `pr-review` for code review.

5. **Update ROADMAP.md** with the new module
6. **Commit everything** with Conventional Commits

## Rules
- NEVER skip phases. Even if the user says "just build it", at minimum write a lightweight spec
- Every phase produces a git commit
- The user approves the spec and implementation plan before building
- New modules MUST NOT break existing modules
- Update CLAUDE.md if the new module introduces new patterns or rules
