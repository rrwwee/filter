# Publication and completion checks

The issue-state incident on PR #21 came from a negated closing phrase: GitHub parsed the embedded keyword and reference and closed issue #18 when the PR merged. Use affirmative **Related to** wording for unresolved work. Keep closing examples in test fixtures, never PR descriptions or commit/squash messages.

`tools/check.py` retains its ordinary model-free check command. Its `publication` and `receipt` modes are read-only: they never push, merge, dispatch, comment, or change issue state. Repeating a check cannot duplicate those actions. They do not grant publication authority or install branch protection/hooks.

## Publication

Every PR body declares the intended completed-issue set once, including an explicit empty set:

```html
<!-- filter-completed-issues: [] -->
```

For intentional closures, list canonical `owner/repo#number` strings. The set is a reviewed assertion of completed issues, not evidence that acceptance criteria passed. Use Related-to prose for all unfinished work.

Before creating the PR, place its exact body, proposed full squash title/body and intended JSON list in temporary files, then run:

```sh
python3 tools/check.py publication --repo rrwwee/filter --base origin/main \
  --body /tmp/pr-body.md --squash /tmp/squash-message.txt \
  --completed-issues /tmp/completed-issues.json
```

This scans every branch commit message after the merge base, the proposed body and the entire squash message. Negation and quoting are not exemptions. Bare, qualified and GitHub URL references are normalized; unexpected references fail. Metadata-only success explicitly says the forge was not checked.

Before merging, run that command again with `--pr NUMBER` against the exact reviewed head and final messages. It reads **every** `closingIssuesReferences` page, checks population counts/cursors and stable PR metadata, compares the complete set with intent, and rejects a changed head/body. Missing fields, GraphQL errors, partial populations and unavailable state fail; none means an empty set. Unexpected manual links are caught even when no closing phrase appears in text.

PR CI runs the same gate using the event's body/title and explicit marker, with read-only token permissions and the actual PR head checkout. Body edits rerun it. A final manual live check is still required: manual links or the chosen squash message can change after CI. CI uses the proposed PR title/body as its squash-message candidate; pass the actual chosen full message in the final check.

## Completion receipt

A receipt is local evidence for one assignment, not another issue database. Keep it outside tracked source. Required fields are `schema: 1`, a concrete `assignment`, exact reviewed `head`, `landingRequired`, `status`, an explicit `completedIssues` list, and nonempty `acceptance` criteria. Each criterion has a unique `id`, boolean `complete`, evidence when complete, and an optional canonical GitHub `issue`. Blocked work also needs `blocker`.

Supported status values:

- `local_complete`: the slice is ready locally; this is not assignment completion.
- `waiting_for_landing`: publication/checks/landing remain.
- `blocked`: name the exact unresolved action or requirement.
- `assignment_complete`: all criteria have evidence; required landing has been read back.

```sh
python3 tools/check.py receipt --repo rrwwee/filter --file /tmp/receipt.json --pr NUMBER
```

With a PR, the reviewed head must match. A merged partial slice must leave every linked unfinished criterion's issue open and outside the PR's closing set. Final assignment completion with required landing additionally checks the PR's merged state, merge ancestry on the default branch, and fully paginated successful post-merge checks including `contracts`. Declared completed issues must also read back closed after landing. An issue with unfinished acceptance cannot appear in that list. Missing, queued, failed or wrong-head checks block final completion. Receipts without required landing can validate a fully completed local-only assignment.

Evidence strings remain human assertions: the validator cannot prove review quality, label truth, or that the assignment was scoped correctly. It makes those assertions explicit and checks the forge consequences.

## Sources

[GitHub's linking rules](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue) describe the keyword forms, commit-message behavior and manual links. The [basic implement workflow](https://www.aihero.dev/skills-implement) ends at a commit and explicitly leaves tracker reconciliation outside its scope; [implement-spec](https://github.com/mattpocock/skills/blob/main/skills/engineering/implement-spec/SKILL.md) describes the broader progression. This repository adopts only the metadata guard and explicit completion evidence, not their orchestration machinery.
