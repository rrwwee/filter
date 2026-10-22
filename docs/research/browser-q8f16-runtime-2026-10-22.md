# Cached default-model browser smoke — 2026-10-22

The default OpenDecider path successfully loaded and ran in the real browser on main `086dbeb2e96df360dd9a10dd4aee91eca28d9b68`. This closes the cached WebGPU runtime gap left by the [earlier failure/retry check](browser-runtime-smoke-2026-10-22.md); it does not establish filtering quality.

## Setup and observed behavior

- Isolated checkout with no private feed captures or labels. Only the four unchanged invented smoke posts embedded in `app.mjs` were used.
- Public tokenizer and q8f16 assets already existed in the browser cache at the historical loopback origin. The test checked only their known hash keys. A test-server `connect-src 'self'` policy blocked external downloads throughout the actual load/run. No model download was required.
- Unmodified main inference UI and runtime modules; `@opendecider/web@0.9.0`, explicit **webgpu / q8f16**, revision `53da62af62275ff5076e29b962dd965f38107c50`. The loaded model metadata reported this same provider/dtype/revision, with no CPU substitution.
- Chromium 155 on the Mac, 10 logical cores, cross-origin isolation true. Model load (including cache read/integrity checks and session construction) took **2,074.32 ms**. This is not a cold download measurement.
- One click of “Run current instruction once” produced exactly four finite keep probabilities and a successful local JSON save. The default state template and instruction were unchanged; threshold stayed at 0.50.

| Case | Keep probability | Call duration (ms) |
|---|---:|---:|
| smoke-1 | 0.5044554485 | 184.835 |
| smoke-2 | 0.4672102137 | 129.685 |
| smoke-3 | 0.4670279001 | 89.625 |
| smoke-4 | 0.4963989880 | 82.015 |

These were **four sequential single-post calls**, not one four-item batch. No browser error/warning or model warning was observed. The capture passed independent checks for cardinality, IDs, finite probability bounds, actual provider/dtype/revision, condition, template and batch size. [Machine-readable evidence](../../measurements/browser-q8f16-runtime-2026-10-22.json) retains those measurements and a hash of the local synthetic raw capture.

The Free model control confirmed “Model released”; the disposable tab and test server were closed. AV's heavy-compute slot is released.

## Limits and next bounded step

Four familiar invented posts without independent acceptance labels support a runtime contract check only. Scores near the threshold are not calibrated confidence or an accuracy result. This is not a representative latency benchmark, sustained load test, or memory measurement. The run does not validate a cold download, cache writing, a fresh-origin model load, WASM, Laya, other dtypes, or packaged-extension behavior.

The next useful bounded runtime check is a separately requested cold-asset acquisition/cache-write test or a four-item batch cardinality check, if those paths are needed. Neither warrants a model sweep or changing thresholds. Product quality still requires a frozen independent acceptance set under explicit user rule semantics.
