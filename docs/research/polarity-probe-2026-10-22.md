# Filter question-polarity and answer-order diagnostic — 2026-10-22

## Outcome

The tuned checkpoint is strongly sensitive to question polarity after outputs are mapped correctly into hide probability. At the fixed 0.5 threshold, switching the equivalent question from “hidden?” to “kept visible?” changes all 12 decoded decisions in forward answer order, and 11/12 in reversed order. Reversing only physical answer order under the hide question changes 0/12 decisions. This is not an unnoticed sign error in the decoder: the canonical mapping and slot permutation were reviewed and unit-tested, and the hide-forward baseline exactly reproduces all four original targeted scores.

The four previously failed wanted cases and their matched wanted controls remain similarly problematic under the hide question. The tuned mean hide probability is 0.976255 on the targets and 0.976068 on the controls. This does not support an explanation based only on the conspicuous quoted/instruction-like wording removed from controls. It points toward a broader response-label/question-semantics problem in this setup. It does not establish a unique internal mechanism.

## Prespecified paired design

The original 26-case acceptance set is unchanged. This separate diagnostic has 12 posts: the four previously failed wanted adversarial posts, four matched wanted controls, and four direct-purchase hide controls. The targets are intentionally selected after observing failures; this is not a fresh acceptance estimate. A separate assistant reviewer, blinded to author labels and predictions, confirmed all 12 labels. Labels remain assistant judgments, not human ground truth. One wanted control is a broader paraphrase, limiting causal attribution to a single phrase.

Eight variants were frozen before scoring: a 2×2 NOUL hide/keep question by forward/reversed physical order; named keep/hide choices in both physical orders; and A/B choices with swapped meaning assignments. The last pair changes label-to-meaning mapping and hide position together; it is not a pure order comparison. All results below use uncalibrated scores at the same fixed 0.5 threshold. No training, post-hoc threshold selection, or best-prompt deployment occurred.

## Correct decisions by condition

Each cell is wanted targets / wanted controls / hide controls, with four cases in each group. Rows are repeated observations of the same 12 posts, not new independent examples.

| Variant | Local base | Local tuned |
|---|---|---|
| noul-hide-forward | 0/4 / 0/4 / 4/4 | 0/4 / 0/4 / 3/4 |
| noul-hide-reverse | 1/4 / 0/4 / 3/4 | 0/4 / 0/4 / 3/4 |
| noul-keep-forward | 3/4 / 2/4 / 0/4 | 4/4 / 4/4 / 1/4 |
| noul-keep-reverse | 3/4 / 2/4 / 1/4 | 4/4 / 4/4 / 0/4 |
| choice-named-forward | 0/4 / 0/4 / 1/4 | 2/4 / 3/4 / 2/4 |
| choice-named-reverse | 0/4 / 1/4 / 1/4 | 2/4 / 1/4 / 3/4 |
| choice-neutral-A-keep | 2/4 / 0/4 / 0/4 | 1/4 / 1/4 / 1/4 |
| choice-neutral-A-hide | 1/4 / 1/4 / 2/4 | 0/4 / 0/4 / 4/4 |

## Paired invariance checks

| Comparison | Base decision flips / 12 | Tuned decision flips / 12 | Base mean absolute ΔP(hide) | Tuned mean absolute ΔP(hide) |
|---|---:|---:|---:|---:|
| noul-hide-forward / noul-hide-reverse | 2 | 0 | 0.0548 | 0.0024 |
| noul-keep-forward / noul-keep-reverse | 1 | 1 | 0.0723 | 0.0536 |
| choice-named-forward / choice-named-reverse | 1 | 5 | 0.1393 | 0.0796 |
| noul-hide-forward / noul-keep-forward | 9 | 12 | 0.5098 | 0.9351 |
| noul-hide-reverse / noul-keep-reverse | 10 | 11 | 0.4782 | 0.8889 |
| choice-neutral-A-keep / choice-neutral-A-hide | 6 | 5 | 0.2686 | 0.1208 |

In the forward NOUL comparison, all 12 tuned raw true/false decisions remain unchanged even though the question and option descriptions invert which answer means hide. On wanted posts, the model still tends to say “true” to either question. Switching to the keep question appears to rescue wanted posts, but correctly hides only 1/4 direct-purchase controls (0/4 with reversed order). Thus a global inversion or a selected prompt would exchange one failure for another. Named choices also remain order-sensitive: five of twelve tuned decisions change under physical reversal.

These outcomes are consistent with response-label/polarity sensitivity and task-following failures, rather than merely a hidden result-mapping bug. The experiment cannot isolate token-level lexical mechanisms, localize an internal circuit, or establish performance prevalence. Both models fail some simple semantic controls; neither is ready for an unqualified filtering-quality claim.

The base also shows substantial polarity sensitivity, so this is not shown to be a defect introduced by fine-tuning. Near-identical target/control scores show that the removed triggers are unnecessary for these failures, not that lexical effects are absent. No general order invariance is claimed: NOUL-keep has one tuned flip with a 0.605 probability change, and named choices have five flips.

## Tokenizer difference resolved for this runtime

The [pinned upstream tokenizer configuration](https://huggingface.co/convaiinnovations/laya-multilingual/blob/052592a15d198d9ad47da779604259b10b47b7aa/tokenizer/tokenizer_config.json) has Git blob hash `eea1ed61121530d74c1722dc2aab6ec917a75909`, matching the cached metadata. The only JSON field difference is `extra_special_tokens`: upstream stores a two-string list; the local file maps `extra_0` and `extra_1` to those same strings. The installed Laya compatibility helper explicitly performs that conversion. No original model file was changed in this investigation.

Both the raw upstream and local configurations load in the installed Transformers version. Their full vocabularies, special-token strings and IDs are equal. Their complete encoded inputs are equal for all 26 original cases, the 12 diagnostic posts, and all 96 rendered diagnostic variants. The normalized upstream config also equals the local JSON. Therefore this difference has no observed input effect in this runtime and corpus; it does not explain the measured failures. This is not a cross-version guarantee.

## Execution and evidence limits

Both models ran sequentially on CPU with two threads; 96 forward calls per model. Inputs use 77–94 tokens. Base scoring took 7.14 seconds with 1.51 GiB peak process RSS; tuned scoring took 6.79 seconds with 2.51 GiB peak RSS. The tokenizer comparison loaded only tokenizers and did not run inference. No GPU, training, paid service, or model download was used.

The run froze cases, reviewer labels, variants, rendered question definitions, tokenizer-effect evidence, runner code hash, and both checkpoint fingerprints. These hashes were checked at execution; original weights and the original 26-case file remain unchanged. Physical order was checked against installed Laya: the encoder renders options in the supplied permutation, the model scores marker positions in that physical order, and the helper returns those logits without restoring canonical order. The probe restores order exactly once before selecting hide probability.

Runtime: Laya 0.4.12; Torch 2.14.1; Transformers 5.20.2; Tokenizers 0.23.3. Existing recorded model weight hashes remain base `9d628fd971b700382ac6f65920a86f149777b2e748e0c955fb3b19695aa8f204` and tuned `ad66fb14dfea45a33e4dc940073d356d0f6d71cbd671d80e89a7214df01b7158`. Historical training provenance is not re-established by this diagnostic.

The corpus, rendered per-post inputs and raw outputs remain local. The report exports only aggregate results. With four posts per slice and deliberate failure selection, confidence intervals or model-ranking claims would be misleading.

## Next useful experiment

Use a separately frozen small truth-table diagnostic varying negation and affirmative wording while preserving post content, with keep/hide and A/B counterbalancing. Inspect per-option marker representations and pre-softmax logit differences to test whether the response bias tracks the answer label, question tokens, or content. Preserve the current diagnostics unchanged. Do not retrain or choose a production prompt based on the best row above.
