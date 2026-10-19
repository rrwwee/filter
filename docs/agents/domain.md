# Domain Docs

This repo uses a single-context layout: `GLOSSARY.md` at the repo root and architecture decision records in `docs/adr/`.

## Before exploring

Read `GLOSSARY.md` and the ADRs in `docs/adr/` that touch the area being explored.

If these files do not exist, proceed silently. The `/domain-modeling` skill creates them lazily when terms or decisions are resolved.

## Use the glossary's vocabulary

When naming domain concepts in issues, refactor proposals, hypotheses, or tests, use the terms defined in `GLOSSARY.md`.

If a concept is missing, reconsider whether it belongs to the domain or note the gap for `/domain-modeling`.

## Flag ADR conflicts

If a proposal contradicts an existing ADR, surface the conflict explicitly and explain why the decision should be revisited.
