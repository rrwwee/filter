# Agent instructions

## Agent skills

### Issue tracker

Track issues and specs in GitHub Issues using `gh`. Before issue operations, read `docs/agents/issue-tracker.md`.

### Triage labels

Use the five default triage labels. Before triaging or applying triage labels, read `docs/agents/triage-labels.md`.

### Domain docs

Use a single-context layout: root `GLOSSARY.md` and `docs/adr/`. Before exploring the codebase, read `docs/agents/domain.md`.

## Filter lead and completion

Keep one persistent Filter lead; use bounded reviewers for individual slices. Before reporting a completed slice or blocked finding, read `.agents/skills/filter-complete/SKILL.md`. GitHub Issues is the technical backlog; the cross-project buffer stays outside this repository. See `docs/agents/filter-workflow.md` for the setup's scope and activation limits.
