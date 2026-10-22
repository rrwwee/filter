# Browser batch contract — 2026-10-22

The installed OpenDecider API performs true multi-item inference and preserves the tested input order, but batched probabilities were not numerically equivalent to the matching sequential calls within the predeclared 0.001 tolerance. No runtime behavior or tolerance was changed to make this pass.

## API and bounded test

`@opendecider/web@0.9.0` returns the client `OpenDecider` API. `systemOneBatch` flattens each state's questions into `NanoBackend.decideMany`. The backend sorts by token length, packs padded inputs within a default 4,096-token budget, runs ONNX, and writes probabilities back to the original item indices. Large inputs may span multiple forward passes; an API batch does not always mean one GPU pass.

One fixed test on main `88da9a11c9488296ebcf6d5c0fc30b7c8624e18b` reordered the existing invented smoke content as clickbait, technical post, duplicate clickbait, dating post. It ran one four-item API call, then four matching single-item API calls. The state question and rule matched the prior default harness smoke; the numerical tolerance 0.001 was fixed before inference. No classification threshold was tuned.

Actual runtime was **WebGPU / q8f16**, revision `53da62af62275ff5076e29b962dd965f38107c50`, in Chromium 155. Cached official assets were reused with external connections blocked. Competing owned jobs were checked first: no Python experiment process was running, the small-model thread was idle, and AV reported CPU-only verifier work.

A diagnostic-only wrapper recorded ONNX input tensor dimensions and SHA-256 fingerprints of unpadded token rows, then delegated the original `session.run` unchanged. This is an internal observation hook, not a new supported API or a production batching layer.

## Results

- Exactly **one `[4,103]` forward pass** occurred for the four-item batch. Sequential comparison produced `[1,96]`, `[1,103]`, `[1,96]`, `[1,101]` passes.
- The batch internally sorted rows into the two equivalent 96-token clickbait rows, the 101-token dating row, then the 103-token technical row. Returned token counts were restored to input order: `[96,103,96,101]`.
- All four outputs were present and finite. The two duplicate inputs produced identical batched scores. Token-count order and corresponding scores support correct mapping for these cases; identical duplicate rows cannot have distinct fingerprints.

| Input | Batched keep score | Sequential keep score | Absolute difference |
|---|---:|---:|---:|
| clickbait | 0.464719373 | 0.467027900 | 0.002308527 |
| technical | 0.504455448 | 0.504455448 | 0 |
| duplicate clickbait | 0.464719373 | 0.467027900 | 0.002308527 |
| dating | 0.467210214 | 0.467210214 | 0 |

**Numerical parity failed** the predeclared 0.001 check on both duplicate rows. The original failure capture was retained. [Evidence](../../measurements/browser-batch-contract-2026-10-22.json) summarizes all comparisons offline from the preserved raw arrays, including the failed check; the browser driver itself stops its summary map at the first parity failure. Padding/shape-dependent reduced-precision computation is one hypothesis, not an established cause.

At the unchanged 0.50 threshold, the four batch/sequential decisions happened to agree. This does not establish equivalence near other thresholds or on other content. No quality, calibration, throughput, or representative latency claim follows from this test.

The model was released in the driver's finally block, and the browser tab/server were closed. No second inference permutation or dtype sweep was run.

## Reproduction and product consequence

The [frozen diagnostic](../../tests/fixtures/browser-batch-contract.html) is a manual test fixture. In an isolated disposable checkout with dependencies and cached weights, copy it over the allowlisted `prototypes/model-evaluation/report.html`, start the loopback server with external connections blocked, and click its single run button. Restore the report afterward. It is not served by default and is not run by CI; CI remains model-free.

The runtime contract for this small case is one result per input in original order, with token-budget splitting possible for larger API batches. Do not treat batching as a numerically transparent optimization. The open numerical issue is recorded in the [problem buffer](problem-buffer.md). Next product-relevant work should specify safe behavior for uncertain/near-threshold results under frozen user-rule semantics, rather than running more smoke permutations.
