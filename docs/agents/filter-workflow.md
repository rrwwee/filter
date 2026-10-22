# Filter workflow

One persistent Filter lead owns task selection, evidence, review, and the GitHub backlog. The shepherd coordinates across projects. Bounded reviewers support the lead; this repository does not create or dispatch another executive thread.

## Small completion slice

Use `.agents/skills/filter-complete/SKILL.md` before closing a slice. `npm run check` runs the existing artifact guard, Node/Python regression tests, and syntax checks from one entrypoint shared with GitHub Actions. It downloads no models. Passing it does not validate model quality, live browser behavior, or independent review.

GitHub Issues is the durable technical problem buffer. The existing [planning map](https://github.com/rrwwee/filter/issues/1) and its tickets remain authoritative. Search before filing; attach measured findings to the relevant issue. The [batch score discrepancy](https://github.com/rrwwee/filter/issues/18) remains open even though its evidence is published. `docs/research/problem-buffer.md` is only an index into that backlog.

## Activation and local ownership

The skill is a normal repository-local skill under `.agents/skills/`. Verify discovery in the actual Codex session; a lead running from an external task directory can read the file explicitly, but file creation alone is not proof of automatic discovery. The local checkout path, lead thread identity, dirty-checkout state, and active worktree belong in the lead's local handoff, not a portable repository configuration.

The base workflow runs checks explicitly and in CI. A proposed opt-in Stop hook and its pending activation gates are documented in [Stop-hook activation](stop-hook-activation.md); no trust setting, scheduler, or runtime security policy is changed. Activation requires supported host behavior, any required trust approval through the normal UI, and a real invocation before claiming success. Existing unrelated user configuration is not changed.

## Sources used, not installed

This narrow setup follows the small, composable guidance in [Matt Pocock's skills](https://github.com/mattpocock/skills), the installed writing-for-agents/skill-creator guidance, and the pstack principles [encode lessons in structure](https://github.com/backnotprop/pstack/blob/main/skills/principle-encode-lessons-in-structure/SKILL.md) and [prove the real result](https://github.com/backnotprop/pstack/blob/main/skills/principle-prove-it-works/SKILL.md). The latter repository is a standalone mirror of Cursor's pstack. Sources were inspected on 2026-10-22; no upstream skill bundle or executable hook was installed.
