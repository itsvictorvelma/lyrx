---
name: plan-tickets
description: Turns a Lyrx spec into small, dependency-ordered GitHub issues in the agent-task format, and creates them only after Victor approves. Use when Victor asks to plan, break down, or create tickets for a spec or build phase.
disable-model-invocation: true
---

# Plan tickets

## Read only this context

1. The spec Victor named, under `specs/`.
2. The "Build sequence" and "Canonical contracts" sections of `AGENTS.md`.
3. `docs/codebase.md`, which describes what already exists.
4. Existing issues: `gh issue list --state all --limit 100 --json number,title,state,labels`.

Do not read the rest of the codebase unless a ticket's Context list cannot be written without it.

## Sizing rules

- One ticket is one pull request in one area (`area:backend`, `area:frontend`, `area:import`, `area:library`, `area:learn-song`, `area:player`, `area:tooling`).
- Aim for a diff a human can review in 15 minutes.
- Contracts, models, and migrations come first, in their own ticket. Screens depend on them.
- Each ticket's tests must be writable before or alongside the code, and `scripts/check.sh` must pass at the end.
- Skip anything already done or already ticketed. Never ticket deferred or out-of-scope work from AGENTS.md.

## Ticket body

Use exactly these headings so the body matches `.github/ISSUE_TEMPLATE/agent-task.yml`:

```markdown
### Spec and build phase
specs/<spec>/spec.md, phase <n> (<name>)

### Goal
<one or two sentences>

### Acceptance criteria
- [ ] <verifiable item>

### Context
@<path> @<path>

### Out of scope
- <nearby work this ticket must not do>

### Test plan
- <tests to add or update>

### Depends on
#<n> or none
```

Context lists only the paths a worker should open first: the spec, the contract files, and the one or two modules it will change. Use real paths from `docs/codebase.md`.

## Workflow

1. Draft every ticket and show them to Victor as a numbered list with title, area, depends-on, and the full body. Use draft numbers (T1, T2) for dependencies between new tickets.
2. Wait for Victor to approve, edit, or drop tickets. Do not create anything before that.
3. Create approved tickets in dependency order so real issue numbers exist when later tickets reference them:

```bash
gh issue create --title "<title>" --body-file <tmp-file> --label agent:ready --label <area-label>
```

4. Replace draft numbers with real issue numbers in later bodies before creating them.
5. Reply with the created issue links and the order they can be dispatched in.
