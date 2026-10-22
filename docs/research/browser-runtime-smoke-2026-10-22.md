# Browser runtime smoke check — 2026-10-22

Scope: actual in-app Chromium browser, an isolated current-main worktree based on `3b0661cf17dad7fc09fe23f074005305b314537a`, fresh loopback origins, and synthetic fixtures. No user feed, login state, private labels, or model weights were used. Existing public runtime packages were copied locally; no new package or model download was needed.

## Observed in the browser

- The normal harness initialized from its real ES modules, including installed `@opendecider/web@0.9.0` and `@r4ai/laya-web@0.2.0`. Its import map and allowed local distribution assets resolved sufficiently to initialize the app. Browser reported Chromium 155, WebGPU available, cross-origin isolation true, and 10 logical cores.
- Default selection was OpenDecider / webgpu / q8f16. The installed official manifest pins revision `53da62af62275ff5076e29b962dd965f38107c50`, q8f16 asset size 469,218,222 bytes, SHA-256 `80436dbed1a284548b5e6c3975bb26df81fb493fc4e64629e5a6ef490bf0e0ae`. This is the configured model, not a claim that weights or a GPU session loaded.
- A second fresh test origin added `Content-Security-Policy: connect-src 'self'` to deliberately prevent external downloads. Clicking the real default loader failed at the tokenizer download with visible `Load failed`; clicking again retried and returned to an enabled UI. A subsequent run action said `Load a model first` and produced zero scores. This exercises the actual loader's failure path without mocking its return value, downloading weights, or allocating an inference session.
- The labeling UI accepted a synthetic keep label and an uncertain label for an unreadable post; both survived reload. Malformed saved JSON then disabled editing and preserved the source cases.
- The inference UI initially mishandled the same malformed saved JSON: its development-input button raised an uncaught promise rejection with no new user-visible error. The fix includes HTTP status checks and moves fetch/parse into the guarded transaction, preserving current cases until validation succeeds.
- After the fix, malformed JSON and missing-file HTTP 404 each produced visible errors while preserving all four smoke cases. Restoring valid synthetic data and clicking again loaded one reviewed development case; save succeeded locally with zero inference rows.

## Deterministic checks and limits

28 Node and 47 Python tests pass. The new regression covers network failure, HTTP failure, malformed JSON, invalid case schema, preserved prior inputs, and a successful retry excluding held-out cases. Two independent reviewers found no blockers. These tests complement the real browser observations; their stubbed model is not inference evidence.

No successful model load, ONNX/WASM session, GPU inference, or quality measurement was performed. AV had compute priority. Complete module initialization and a tokenizer-download failure do not establish that the full model/WASM asset path works. Next bounded step: obtain a compute slot and reuse the exact pinned q8f16 weights for one fixed four-post smoke run on the advertised WebGPU backend. Record actual backend/dtype/revision and output cardinality; do not substitute CPU q8 or interpret synthetic smoke output as quality evidence. If weights cannot be reused, request approval for the 469 MB download first.
