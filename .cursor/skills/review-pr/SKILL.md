---
name: review-pr
description: Reviews a Lyrx pull request against its ticket's acceptance criteria, the spec, and project review rules, then hands it to Victor or requests one round of changes. Use when Victor asks to review a pull request or check an agent's work.
disable-model-invocation: true
---

# Review a pull request

Bugbot handles general bug finding. This review checks that the pull request does what its ticket asked, and nothing more.

## Gather

1. `gh pr view <n> --json number,title,body,headRefName,isDraft,files,additions,deletions,statusCheckRollup,comments`
2. `gh pr diff <n>`
3. The linked issue from "Closes #<issue>": `gh issue view <issue> --json title,body`
4. Only the spec sections that the ticket names under "Spec and build phase".
5. `.cursor/BUGBOT.md` for the project checklist.

Read other files only to confirm a specific concern.

## Check

- Every acceptance criterion: met, partly met, or missing. Point at the file and line.
- Nothing outside the ticket's scope or "Out of scope" list. Any edit to `AGENTS.md` or `specs/` is blocking.
- Every item in `.cursor/BUGBOT.md`.
- CI status from `statusCheckRollup`. A failing or missing check is blocking.
- Tests cover the new behavior, and no test was weakened or removed.

## Decide

Count earlier reviews: comments on the pull request containing `<!-- lyrx-review -->`.

- **Ready for Victor:** no blocking findings. Post the review comment, then `gh issue edit <issue> --remove-label agent:in-progress --add-label agent:review`.
- **Changes needed, no earlier review:** post the review comment listing each blocking finding. If the worker agent's ID is known in this chat, resume that agent with the findings; otherwise tell Victor to send the comment to the agent.
- **Changes needed after an earlier review, or out-of-scope work:** post the review comment, then `gh issue edit <issue> --add-label needs-human`, and tell Victor why.

Post with `gh pr comment <n> --body-file <file>`. The comment format:

```markdown
<!-- lyrx-review -->
## Ticket review: <Ready for Victor | Changes needed | Needs Victor>

### Acceptance criteria
- [x] <criterion> — <evidence>
- [ ] <criterion> — <what is missing>

### Blocking findings
- <file:line> <problem> → <expected fix>

### Notes
- <non-blocking observations, if any>
```

Never approve, merge, or close the pull request. Merging is Victor's decision.
