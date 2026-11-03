---
name: dispatch-ticket
description: Hands one approved Lyrx GitHub issue to a Cursor cloud agent with a scoped prompt, after checking dependencies and conflicts. Use when Victor asks to dispatch, start, assign, or hand off a ticket or issue to an agent.
disable-model-invocation: true
---

# Dispatch a ticket

## Preflight

Stop and tell Victor instead of dispatching if any check fails.

1. Read the issue: `gh issue view <n> --json number,title,body,labels,state`.
2. It must be open and labelled `agent:ready`.
3. Every issue under "Depends on" must be closed: `gh issue view <dep> --json state`.
4. Conflicts: list running work with `gh issue list --label agent:in-progress --json number,title,body`. If this ticket and a running one both touch `backend/app/contracts.py`, `frontend/src/contracts.ts`, `backend/app/models.py`, or `backend/alembic/`, do not dispatch.
5. Cloud agents start from the remote `main`. Confirm `git fetch && git status` shows local `main` is not ahead of `origin/main`. If it is, ask Victor to push first.

## Launch

Use the Task tool with `environment: "cloud"`, `cloud_base_branch: "main"`, `subagent_type: "generalPurpose"`, `run_in_background: true`, and description `Ticket #<n>: <short title>`. The prompt:

```text
You are implementing GitHub issue #<n> in the Lyrx repository (itsvictorvelma/lyrx).

<paste the full issue title and body>

How to work:
- Start by reading only the files under "Context". Read more only if you must, and list any extra files and why in the pull request.
- Follow AGENTS.md and the rules in .cursor/rules/. Stay inside "Out of scope".
- Work on a branch named agent/<n>-<short-slug>.
- Verify with scripts/check.sh. Follow .cursor/rules/execution-guardrail.mdc exactly:
  at most two failed check runs, then write the failure report, open a draft pull request,
  post the report as a pull request comment, label issue #<n> needs-human, and stop.
- Update docs/codebase.md if you add a folder, route, setting, or data field.
- When checks pass, open a pull request against main with:
  gh pr create --base main --title "<title>" --body-file <file>
  The body has: "Closes #<n>", a short summary, the acceptance criteria as checked boxes,
  extra files read and why, and the tests added.
- If you cannot open a pull request, finish by reporting your branch name and why.
- Never merge, never edit AGENTS.md or specs/, never reset the check guardrail.
```

## After launch

1. Relabel: `gh issue edit <n> --remove-label agent:ready --add-label agent:in-progress`.
2. Comment on the issue with the agent link: `gh issue comment <n> --body "Dispatched to a Cursor cloud agent: <link>"`.
3. Tell Victor the agent link and what to expect next: a pull request, or a draft pull request with a failure report.
