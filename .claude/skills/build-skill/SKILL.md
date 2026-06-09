---
description: Create a new skill when a repeating pattern is detected or a new operation is needed. Use when Claude notices it is doing something repeatedly without a skill, when a user asks "make this a standard process", or when a new module needs operational skills.
---

# Build Skill

## When to Use

- When Claude performs the same multi-step operation more than once without an existing skill
- When a user says "make this a standard process" or "this should always work this way"
- When a new module is built and needs operational skills (the `add-module` skill triggers this)
- When a post-incident review identifies a process that should be standardized

## Pattern Recognition — Triggers

Claude should PROACTIVELY suggest creating a skill when it detects:
1. **Repeated tool sequences** — Same 3+ tool calls in the same order, twice or more
2. **User corrections** — User says "no, do it like you did last time" or "you forgot to do X again"
3. **Complex multi-step operations** — Any operation that requires 4+ steps and has a risk of being done inconsistently
4. **New module operations** — Every module should have skills for its core CRUD and query operations
5. **Workarounds** — If Claude is working around a limitation the same way repeatedly

## Skill Anatomy

Every skill MUST have this structure:

```markdown
---
description: One line. When to use this skill. Include trigger phrases the user might say.
---

# Skill Name

## When to Use
Clear conditions for when Claude should load this skill.

## Steps
Numbered steps. Each step is concrete and actionable.
Include actual API calls, file paths, or commands where applicable.

## Rules
Non-negotiable constraints specific to this skill.

## Validation (optional)
How to know the skill executed correctly.
```

## Steps

1. **Identify the pattern** — What is the repeating operation? What steps does it involve? What varies between executions (parameters) vs what stays the same (process)?

2. **Name it well** — The skill name should be:
   - Lowercase, hyphenated: `add-contact`, `report-issue`, `weekly-review`
   - Action-oriented (verb-noun): `track-expense`, `plan-meal`, `check-health`
   - Obvious from the name what it does

3. **Write the description line** — This is how Claude decides whether to load the skill. Include:
   - What it does in one sentence
   - Trigger phrases users might say (natural language patterns)
   - Example: `description: Report an issue or something that went wrong. Use when a user says "something broke", "this isn't working", "I got the wrong reminder", "there's a problem with..."`

4. **Define the steps** — Write each step as if instructing a new agent who has never seen the codebase:
   - Include actual `curl` commands for API calls
   - Include actual file paths
   - Include decision points ("if X, then Y; otherwise Z")
   - Show example inputs/outputs where helpful

5. **Add rules** — Constraints that prevent mistakes:
   - What must NEVER happen
   - What must ALWAYS happen
   - Edge cases to watch for

6. **Write the file** — Save to `.claude/skills/{skill-name}/SKILL.md`

7. **Register in CLAUDE.md** — Add the skill to the appropriate section (Development or Operational) in the root CLAUDE.md under the Skills Framework heading

8. **Test it** — Ask Claude to execute the new skill with a real or example input to verify it works end-to-end

9. **Commit** — `git add .claude/skills/{skill-name}/SKILL.md CLAUDE.md && git commit -m "feat: add {skill-name} skill"`

## Skill Categories

When creating a skill, classify it:

- **Development skills** — Used during the build process (spec writing, code review, testing)
- **Operational skills** — Used when users interact with Jarvis (add contact, search, report issue)
- **Meta skills** — Used to improve the system itself (this skill, post-incident, add-module)
- **Scheduled skills** — Used by automated processes (proactive reminders, health checks)

## Rules

- Every skill MUST have a `description` front matter line — this is how Claude matches user intent to skills
- Description MUST include natural language trigger phrases — think about how BOTH Vincent and Christianne would ask for this
- Steps MUST be concrete enough that a fresh Claude session can follow them without additional context
- Skills MUST NOT duplicate logic that belongs in the backend API — skills orchestrate, APIs execute
- When in doubt, create the skill. A skill that exists but is rarely used costs nothing. A missing skill leads to inconsistency.
- If a skill becomes too long (>100 lines), split it into sub-skills
