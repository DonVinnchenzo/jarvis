# Specs — CLAUDE.md

## Purpose

Feature specifications live here. Every significant feature needs a spec before implementation.

## Numbering

Sequential: `NNN-feature-name.md`. Check highest existing: `ls specs/*.md | tail -5`

## Status Flow

Draft -> In Review -> Approved -> Implementing -> Shipped

## Mandatory Review Gate

Before implementation, specs should be reviewed from multiple perspectives:
1. **Backend review** — Data model, API design, performance
2. **Product review** — User value, scope, missing use cases
3. **Security review** — Privacy, data handling, auth

## Template

Use `TEMPLATE.md` in this folder for new specs.

## Rules

- Acceptance criteria must be specific and measurable
- Cross-reference related specs
- Update spec status as implementation progresses
- Spec is living document — update as code evolves
