# Proposed completion hook: activation pending

The exact proposed definition is [`.codex/hooks.json`](../../.codex/hooks.json); its command is [`tools/stop_review.py`](../../tools/stop_review.py). It runs the existing model-free check command when this repository's main agent stops. A failed check requests continuation. After passing checks, the first Stop requests one final review through `filter-complete`; a passing Stop with `stop_hook_active: true` allows completion.

This enforces the local check boundary and triggers a review opportunity. It does not independently establish that a review was competent, that CI passed, or that GitHub problems were recorded. It never publishes, changes permissions, starts another model, or reads transcripts. Check failure continues to block until fixed or the user interrupts/disables the hook.

## Observed runtime state

On 2026-10-22, the Mac app's bundled binary reported `codex-cli 0.163.0-alpha.11`; the shell CLI reported `0.157.0`. Both expose the hooks feature. A disposable metadata-only app-server from the bundled binary discovered `filter-complete` in the clean lead worktree, but not in the existing lead's external task directory or the old canonical checkout. No agent turn or model call was started by that probe.

The clean lead worktree has no persisted project-trust entry. The probe returned no project hooks there, including after testing the documented JSON and inline representations. Therefore neither discovery nor execution of this hook is established. The canonical checkout's existing trust entry is not evidence of hook trust or activation in the new worktree.

The exact local paths, current lead identity, probe output, and the proposed user action are recorded in the lead's local activation handoff. They are not portable repository settings.

## Required user-mediated activation

Official [hook documentation](https://developers.openai.com/codex/hooks) requires a trusted project layer and review/trust of the exact non-managed hook definition. A changed definition requires review again. Use the normal Codex project-trust flow if prompted, then `/hooks` to inspect and trust this repository's Stop command. Do not use a hook-trust bypass or edit the trust database.

The existing lead must also operate with the clean repository/worktree as its working directory. Setting a shell command's cwd does not change the lead's skill/hook discovery root. Preserve the dirty canonical checkout; do not reset or overwrite it just to activate the hook.

## Disposable activation test after approval

1. Confirm `/hooks` lists this exact command, its source file and trusted hash. If absent, stop and diagnose the runtime; do not call the hook active.
2. Run one ephemeral, non-executive Codex test turn in the clean worktree using the same binary/build that will run the lead. Ask it for a short acknowledgment with no file edits or publication. Capture JSON/event output locally.
3. Require actual Stop-hook start/completion events, passing command execution, the review continuation, and subsequent completion. A direct invocation of the Python file is only a contract test, not this activation test.
4. Interrupt the disposable process if it does not settle after the expected continuation. Keep evidence; restore any test-only files. Do not change global settings.

The direct command contract and unit tests pass: first passing Stop requests continuation, second passing Stop permits completion, and failed/invalid checks block. The real lifecycle activation test remains pending user trust and an observed event. This file is not proof of activation.
