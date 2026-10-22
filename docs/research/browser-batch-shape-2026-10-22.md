# Batch score discrepancy: sequence length and backend controls

Issue [#18](https://github.com/rrwwee/filter/issues/18) remains open. On the same cached q8f16 graph, extending one clickbait input from 96 to 103 tokens with correctly masked padding reproduced the entire previously observed WebGPU batch-score change. Increasing batch size at a fixed sequence length did not change that input's score. The same graph on explicit WASM showed no padding change. This narrows the observed failure to sequence-length-sensitive WebGPU execution; it does not identify a faulty kernel or prove quantization is the cause.

## Frozen design and provenance

The [plan](browser-batch-shape-plan-2026-10-22.md) was saved and independently reviewed before inference. The original four invented posts, rule, question, 0.001 numerical tolerance and 0.50 keep threshold were unchanged. The [original failure](browser-batch-contract-2026-10-22.md) is retained. There was one bounded run, 11 forwards per backend, no fitting or new labels. The technical and dating cases remain controls in the original API batch and sequential calls; targeted tensor interventions use the clickbait row only.

Actual runtime: Chromium 155, cross-origin isolated; OpenDecider web 0.9.0, ONNX Runtime Web 1.30.0; explicit WebGPU followed by explicit single-thread WASM, both **q8f16**, revision `53da62af62275ff5076e29b962dd965f38107c50`. Both loaded the same 469,218,222-byte graph with pinned SHA256 `80436dbed1a284548b5e6c3975bb26df81fb493fc4e64629e5a6ef490bf0e0ae` and the pinned tokenizer entirely from the existing browser cache. External model fetches were rejected; the isolated server restricted connections to its own origin. No new weights, private captures or user feed state were used.

The [manual driver](../../tests/fixtures/browser-batch-shape.html) intercepts the diagnostic session only, records actual tensors and all option logits, then delegates the original ONNX call. Its six direct interventions are not a new public batching API. Inputs/masks were int64; returned logits were float32, with values consistent with reduced precision. Reconstructed softmax matched API scores. Correct option order and token ID 50284 were checked against the installed dependency; padding ID 50283 matched captured feeds.

## Results

| Clickbait condition | Shape | WebGPU keep score | WASM keep score |
|---|---|---:|---:|
| Original single | 1 × 96 | 0.467027900 | 0.463687094 |
| Exact single repeat | 1 × 96 | 0.467027900 | 0.463687094 |
| Masked padding added | 1 × 103 | 0.464719373 | 0.463687094 |
| Masked padding IDs changed to zero | 1 × 103 | 0.464719373 | 0.463687094 |
| Two identical unpadded rows | 2 × 96 | 0.467027900 | 0.463687094 |
| Four identical padded rows | 4 × 103 | 0.464719373 | 0.463687094 |
| Original mixed batch (clickbait row) | 4 × 103 | 0.464719373 | 0.463687094 |

Within each backend, exact single and mixed-batch repeats were identical. Captured unmasked IDs stayed identical across padding interventions. Changing masked token content had no effect in this test, which supplies no evidence of mask leakage here. Padding alone was sufficient to reproduce the WebGPU difference; mixed-neighbor content and batch dimension were unnecessary for this observed case. WASM's invariance under the same graph and tensors provides a backend contrast. It does not distinguish attention implementation, fusion, rounding, position handling or another shape-dependent backend path.

WebGPU's maximum API batch/single difference was again **0.002308527**, exceeding the unchanged **0.001** tolerance; WASM's was zero. Same-graph cross-backend scores also differ, so WASM is not established as a numerically equivalent fallback or a quality reference.

## Product consequences and limits

At the fixed **keep if score ≥ 0.50** rule, there were **0/4 API decision flips within each backend** and **0/4 cross-backend API decision flips**. All targeted clickbait tensor controls also stayed below 0.50. This is a small stability observation, not evidence of acceptable false-hide rates or general decision parity.

For the observed WebGPU clickbait pair, thresholds in `(0.4647193728668166, 0.46702790013192075]` would produce different decisions (using score ≥ threshold). That is a descriptive interval, not a proposed or fitted operating threshold. The original tolerance failure remains a failure.

Wall-clock totals including load, hashing and recording were about 2.80 seconds for WebGPU and 34.58 seconds for WASM. These are not comparative throughput measurements. The browser was briefly unresponsive during CPU work; observed renderer RSS reached about 3.2 GB. Both sessions were disposed, the tab and loopback server closed. No further model run was performed.

[Raw synthetic capture](../../measurements/browser-batch-shape-2026-10-22.raw.json) and [summary with hashes](../../measurements/browser-batch-shape-2026-10-22.json) are preserved. CI verifies feed identity, masks, arithmetic, output mapping, recorded comparisons and the retained failure without loading a model.

Next bounded product task: retain sequential inference as the current behavioral reference, define the actual threshold/abstention policy independently of these four cases, then validate decision stability on a frozen acceptance set around that independently chosen policy. Do not introduce silent backend switching or declare batching transparent based on these controls.
