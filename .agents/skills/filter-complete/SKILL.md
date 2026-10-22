---
name: filter-complete
description: Finish a Filter code or research slice with verified evidence, exact-head review and CI, and deduplicated GitHub problem tracking. Use before reporting a Filter task complete or handing off a blocked finding.
---

# Complete a Filter slice

The current product is an experimental browser harness. Runtime smoke, aggregate arithmetic, model quality, and a shipped extension are distinct outcomes.

1. Inspect `git status --short`, the current branch, and `git remote -v`. Preserve existing user edits. Work in an isolated worktree when the canonical checkout has unrelated files; keep private captures and weights in ignored local storage.
2. Name the requested outcome and the actual evidence. For browser behavior, exercise the real UI and verify saved effects with synthetic inputs. A stub or Node check cannot stand in for a successful browser/model run. Record the actual provider, dtype, revision, and bounds of any experiment. Coordinate sustained GPU work with the other local projects.
3. Run `npm run check`. This is the model-free local/CI gate. Add a regression for an observed code failure when it can be checked deterministically; retain failed scientific controls as failures. See the command output for the executed checks.
4. Review the final diff against its fixed base. Obtain independent review for code or experimental conclusions. Resolve findings, then recheck the changed behavior. Record the reviewed head; a later edit invalidates that head's review/CI evidence.
5. Before publication, run the metadata gate in `python3 tools/check.py publication --help`; before merge, include the live PR readback. Follow [publication and receipt checks](../../../docs/agents/publication-checks.md). For publication authorized by the user, create a focused draft PR, verify GitHub author attribution, and inspect CI on the exact head before merging. Do not infer success from a queued workflow or another commit's checks. Verify the remote merge SHA and post-merge CI. If approval rejects an action, retain its exact reason and stop that action until materially relevant authorization resolves it.
6. Record unresolved technical problems in GitHub Issues. First read `docs/agents/issue-tracker.md` and search existing open/closed issues. Update the matching issue rather than creating a duplicate; otherwise create one concise issue with the observed failure, reproducible evidence, practical consequence, and next bounded step. Use `docs/agents/triage-labels.md`. Do not close a problem merely because its evidence PR merged.
7. Validate a completion receipt with `python3 tools/check.py receipt --help`, distinguishing local completion, waiting for landing, blocked work, and assignment completion. Report the outcome, tests/review, PR or evidence link, unresolved issue links, and next useful step. Release owned test servers/model sessions. Leave the cross-project summary to the shepherd; do not start a second persistent Filter lead.

A blocked slice can be handed off with preserved local evidence and its exact blocker. It is not a completed publication or validated runtime claim.

This skill is explicitly invoked guidance. It does not install a Stop hook, schedule work, grant permissions, or enforce review judgment. Check actual tool discovery before claiming it activates automatically in a session.
