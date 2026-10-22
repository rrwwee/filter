# Filter: bounded offline acceptance replay — 2026-10-22

## Measured result

This is new local CPU inference, not a replay of historical scores or a deterministic model stub. At the prespecified 0.5 hide threshold, the local base answered 17/26 correctly and the locally fine-tuned checkpoint 16/26. The tuned model showed no overall improvement on this tiny authored set. Neither model establishes product readiness.

| Slice | Cases | Base correct | Tuned correct | Base wanted retained | Tuned wanted retained | Base unwanted hidden | Tuned unwanted hidden |
|---|---:|---:|---:|---:|---:|---:|---:|
| easy | 8 | 7/8 | 6/8 | 3/4 | 2/4 | 4/4 | 4/4 |
| adversarial | 8 | 4/8 | 3/8 | 0/4 | 0/4 | 4/4 | 3/4 |
| novel_combination | 10 | 6/10 | 7/10 | 4/5 | 2/5 | 2/5 | 5/5 |
| all | 26 | 17/26 | 16/26 | 7/13 | 4/13 | 10/13 | 12/13 |

At the primary threshold, both models incorrectly hide all four wanted adversarial examples. The tuned model hides more unwanted novel-combination cases but also loses more wanted cases. This is a retention/removal tradeoff, not a demonstrated overall gain.

## Threshold sensitivity, fixed before inference

Hide when uncalibrated P(hide) is greater than or equal to the threshold. Primary threshold 0.5; secondary thresholds 0.25 and 0.75 were recorded before either run. None was selected using these outcomes. No fitted temperature calibration was applied.

| Threshold | Base correct | Tuned correct | Base retained / 13 | Tuned retained / 13 | Base hidden / 13 | Tuned hidden / 13 |
|---|---:|---:|---:|---:|---:|---:|
| 0.25 | 14/26 | 14/26 | 2 | 2 | 12 | 12 |
| 0.5 | 17/26 | 16/26 | 7 | 4 | 10 | 12 |
| 0.75 | 18/26 | 16/26 | 10 | 5 | 8 | 11 |

## Uncertainty and label independence

All 26 scored posts are newly authored synthetic cases with explicit question semantics: direct purchase solicitation, adversarial/quoted instructions, and two composed topic/measurement/exception rules. The novel-combination label means new authored rules with no exact instruction match in the inspected corpus; it does not prove an unseen logical structure in model pretraining. There are 13 keep and 13 hide labels. Two borderline purchase-invitation cases were excluded before inference.

A separate assistant reviewer saw only the instructions/posts, not author labels or model outputs. Reviewer critique led to stronger prerequisite/exception coverage before freezing. Final labels agree on every scored case. This is independent assistant review, not human adjudication or independent population sampling. No labels, cases, thresholds or checkpoints were selected after seeing predictions. The test is now exposed and must remain diagnostic for future work.

Illustrative binomial Wilson 95% intervals at 0.5 are base 46.2–80.6%, tuned 42.5–77.6%. These assume independent Bernoulli samples, which authored rule clusters do not satisfy; they are scale illustrations, not calibrated population-confidence claims. Paired outcomes: 13 correct for both, 4 base-only, 3 tuned-only, 6 wrong for both. Slice sizes are only 8, 8 and 10.

## Frozen inputs and overlap limits

The corpus extractor inspected 169 available local JSON/JSONL files, finding 762 distinct normalized text/state/post_text strings and 729 instruction strings. There were zero parse failures, zero exact text matches, zero ID matches, zero exact instruction matches, and zero shared five-word shingles between acceptance posts and extracted historical text. The comparison covers only these fields/files; it does not prove semantic independence, absence from inaccessible files, media, or upstream pretraining. No private historical text is included in this report.

Acceptance SHA-256: `88ba89619bf569f1379c14f19751f18783306f46cd3d60b4de73da4f3b235740`. Plan SHA-256: `ae19ff210341b42a2361b6a8d33c1111cb10e0e2cb0c1b3a3c94e6c3cc20da27`. Both runs used the same frozen hashes. Reviewer judgments and detailed per-row model outputs remain local.

## Current checkpoint provenance

Base weights, encoder config, agent config and tokenizer JSON match the local cached manifest for revision `052592a15d198d9ad47da779604259b10b47b7aa`. The tokenizer configuration file does not match that cached manifest. The cache itself was not authenticated against a remote authority during this task. Therefore the results identify current local files, not an unqualified pristine upstream checkpoint. No original checkpoint was modified. Historical training provenance remains unknown.

| Alias | Current model.safetensors SHA-256 | Load-and-score seconds | Peak process RSS |
|---|---|---:|---:|
| local-base | `9d628fd971b700382ac6f65920a86f149777b2e748e0c955fb3b19695aa8f204` | 4.53 | 2.19 GiB |
| local-tuned | `ad66fb14dfea45a33e4dc940073d356d0f6d71cbd671d80e89a7214df01b7158` | 3.95 | 2.53 GiB |

Each model ran in its own sequential process on CPU with two intra-operation threads, batch size one, no training, no network/model download, and no GPU. Current checkpoint fingerprints were checked again after inference. The external timing wrapper failed its macOS clock-rate query after the successful base run; the completed results and in-process timing/RSS are used above.

Independent review verified polarity and metric arithmetic. A separate label-flip check changed every expected label for each tokenizer: all 26 encoded model inputs stayed identical apart from the target field. Inspection of the installed forward call confirmed that target/label fields are not passed to the model.

The completed plan froze aliases but did not pre-register checkpoint hashes. Actual commands supplied the intended base and tuned directories; the resulting identities were separately verified against those files. The reusable scripts now require pre-frozen alias-to-hash bindings and recheck the plan, review, overlap audit and case hashes before and after scoring. These hardening changes do not retroactively strengthen the original plan. Its original bytes and results remain unchanged.

Runtime: laya 0.4.12, torch 2.14.1, transformers 5.20.2, tokenizers 0.23.3, numpy 2.5.4, safetensors 0.8.0.

## Next useful experiment

Keep this frozen set as regression evidence. A higher-value next diagnostic is a separate blinded, counterbalanced set that swaps equivalent keep/hide question polarity and option order, then measures per-post score changes and attention/representation sensitivity without retraining. The adversarial wanted-post failures are the clearest target. Before any real-feed quality claim, add human-reviewed natural posts and a genuinely unexposed post-level acceptance set. Resolve or explicitly retain the tokenizer-config provenance difference. Do not tune thresholds on this now-observed acceptance set.
