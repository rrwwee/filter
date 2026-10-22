# Local feedback before publication

Run `npm run check:fast` while editing. It uses the same `tools/check.py` runner as CI: tracked-artifact checks, Python and JavaScript syntax checks, all Python unit tests, and the non-listening Node tests. It excludes only `tests/test_server.mjs`, whose integration tests bind disposable loopback ports. A failed command stops the runner and preserves its exit code.

Run `npm run check` before publication. This remains the CI gate and includes the server tests. `npm test` runs all Node/Python tests through the same runner, without the extra artifact and syntax checks. No models are downloaded or run by these commands. Rendered browser checks still require their separate evidence.

The fast gate is explicit, not an automatic hook. No Git or Codex hook is installed or enabled, and no settings change is required. It checks the working directory, not a separate snapshot of the staged index or a proposed remote ref. A fast pass does not replace the full exact-head CI or publication/receipt readback in [publication checks](publication-checks.md).

## CI notification audit, 22 October 2026

At inspection, GitHub retained 49 runs, all completed successfully on attempt 1. The failure-filtered query returned no runs; there were no cancelled or superseded failed attempts in the retained list. Current main `b194a6f524ade96e999d7a5f7f4321727dccf5e3` passed [run 39831381792](https://github.com/rrwwee/filter/actions/runs/39831381792). No current CI regression or notification failure cause was established. An exact notification/run URL is needed to identify a failure outside this retained history; do not treat an old notification as evidence that current main fails.
