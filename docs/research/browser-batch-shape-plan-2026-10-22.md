# Issue 18 predeclared tensor diagnostic

Frozen before inference on 2026-10-22. Preserve original four synthetic posts, rule, question, original 0.001 numerical tolerance, fixed keep threshold 0.50 and original failed evidence. No new label/quality claim, threshold fitting or model training.

Use existing cached official revision 53da62af62275ff5076e29b962dd965f38107c50, @opendecider/web 0.9.0, ONNX Runtime Web 1.30.0, q8f16 graph only. Cache miss ends the attempt, no download. Explicit WebGPU first then dispose; explicit WASM same graph second then dispose. No silent fallback. One pass per condition, with identical-feed repeat controls. Stop before another forward pass after 90 seconds per backend. No new dtype sweep.

Per backend: original four-item API batch and four sequential calls capture exact tensors and all option logits. Reconstruct probabilities from mask-position logits and check against API scores (1e-12). Then six direct ONNX controls:
1. Exact single-clickbait feed repeat: fixed shape/data numerical repeatability.
2. Single clickbait right-padded to original batch max length, using pad ID 50283 and attention mask 0: changes sequence length but not batch size/content.
3. Same padded single, masked token IDs changed to 0: same shape and mask, detects sensitivity to masked content.
4. Two duplicate unpadded clickbait rows: changes batch dimension with no padding.
5. Four duplicate padded clickbait rows: compare one versus four rows at fixed padded length; all rows identical, excludes mixed-neighbor content.
6. Exact original four-row feed repeat: repeatability and extraction control.

Compare raw logits and probabilities, not rounded display. Verify original unpadded token hashes/order and dtype/model hash; preserve padding/mask values and feed hashes. Compare each padded row's unmasked IDs to its source. Summarize fixed 0.50 decision flips separately from failures of original 0.001 tolerance. Report numerical threshold-crossing intervals descriptively, not as newly chosen operating thresholds.

Interpretation limits: stable identical-feed repeats with differences confined to shape changes implicate shape-sensitive execution but do not identify a kernel. Masked-ID sensitivity suggests mask leakage or numerical dependence, not proof of missing attention masking. Same-graph backend contrast can distinguish backend sensitivity; q8f16 on both backends cannot isolate all quantization effects. If WASM fails, record error, do not substitute q8 or claim precision attribution. No parity threshold relaxation.
