# Filter problem buffer

## Open: batch-dependent q8f16 probabilities

Evidence: [fixed browser batch contract](browser-batch-contract-2026-10-22.md), using cached OpenDecider 0.9.0 / WebGPU / q8f16 / revision `53da62af62275ff5076e29b962dd965f38107c50`.

One repeated clickbait input scored 0.464719373 in a true four-row pass versus 0.467027900 in a single-row pass. The 0.002308527 difference exceeds the 0.001 tolerance fixed before inference. Cardinality, tested ordering, duplicate equality, and the four decisions at threshold 0.50 were preserved. Root cause and generality are unknown; do not relabel this as a quality result or relax the tolerance after observing it.

Product risk: switching between single-item and batched inference can change a keep/hide decision for thresholds lying between differing scores. No runtime fix is yet justified. Before product batching, specify how near-threshold uncertainty is handled and validate against a frozen independent acceptance set. Any later root-cause test should isolate shape/padding from reduced-precision effects under a separately bounded compute slot.
