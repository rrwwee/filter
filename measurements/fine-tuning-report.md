# Local fine-tuning checkpoint

This report records prototype evidence, not a production model selection. Source: the scripts in `prototypes/model-finetuning/`. Private captures, labels, individual outputs, dependencies, and checkpoints remain in ignored `local-results/`. The accompanying `fine-tuning-aggregate.json` contains only aggregate metrics.

## Method and corrections

- Original base: `convaiinnovations/laya-multilingual`, revision `052592a15d198d9ad47da779604259b10b47b7aa`; Laya 0.4.12, PyTorch 2.14.1, Apple M4 / 16 GB, MPS.
- A 16-example promotion-only memorization check reached 16/16. This verifies the training path, not generalization.
- The first broader head-only experiment incorrectly continued the memorized checkpoint. It was superseded. The corrected head-only run restarted the base and scored 14/16 on the promotion test, versus base 13/16. Full training from base also scored 13/16. Small samples do not establish a winner.
- Broader criteria training exposed a keep-everything collapse in head-only training. A corrective full-weight run improved the reused diagnostic test, but changed both sampling and trainable parameters, so it is not a controlled comparison.
- A subsequent fresh compositional evaluation exposed wording/layout confounding. The final run crosses wording families with bullet and paragraph layouts and adds if/otherwise forms. Every broader run restarts the original base; none starts from the memorization checkpoint.
- The final run used 1,706 training pairs / 195 posts, 512 validation pairs / 20 posts, and a new 1,755-pair holdout / 47 posts. Of those holdout posts, 15 are fresh real-feed posts and 32 are authored edge cases. Labels are assistant judgments, not user-confirmed truth. Repeated instructions on the same post are correlated.
- The final full-weight run selected epoch 2 of 3 on validation, taking about 23.3 minutes. Saved predictions were reproduced after checkpoint reload. This is not a browser-exported model.

## Final holdout at the default threshold

| Checkpoint | Accuracy | Wanted kept | Unwanted hidden | AUC |
| --- | ---: | ---: | ---: | ---: |
| Original base | 53.3% | 674/999 | 261/756 | .527 |
| Previous broader full tune | 67.2% | 571/999 | 608/756 | .759 |
| New crossed-format tune | 66.6% | 812/999 | 357/756 | .697 |

The new model is gentler but not universally better. It gets both opposing instructions correct on 41/45 pairs, versus 1/45 for the previous tune and 11/45 for base. On the 15 fresh real posts, the new model keeps 259/337 wanted pairs and hides 80/202 unwanted pairs. The original four-rule instruction remains weak: across three formats it keeps 54/54 wanted pairs but hides only 4/78 unwanted pairs.

Validation-selected operating points also transfer imperfectly. The 95%-validation-retention setting keeps 957/999 wanted test pairs while hiding 110/756 unwanted pairs. The 85% setting keeps 683/999 and hides 460/756. These are diagnostic tradeoffs, not recommended universal thresholds; scores are not established calibrated probabilities.

## Independent-rule diagnostic

The literal four bullets were tested separately and together on the same 47 posts. Among 44 labelable posts (18 wanted, 26 unwanted), the combined instruction kept all 18 wanted and hid 1 unwanted. OR across four independent checks hid all 44. That improves removal by destroying retention, so decomposition is not yet a solution with this checkpoint.

Input truncation was excluded: the rule input occupied 74 of 256 available head tokens, with at most 136 state tokens. Reversing/rotating rule order changed only 2/47 decisions. These controls do not establish the internal cause of the composition failure. Rewording two rules with training-like phrases still hid too many wanted posts; it remains diagnostic only, not automatic translation of user input.

Warm local Python/MPS timing (36 calls per method, tokenization plus inference, excluding model load):

| Method | Median | p95 |
| --- | ---: | ---: |
| One combined check | 26.8 ms | 41.2 ms |
| Four serial checks | 96.1 ms | 135.6 ms |
| Four checks in one batch | 56.2 ms | 92.8 ms |

These are not browser/WebGPU timings. Batched rules still repeat encoder computation; they do not share an encoded-post cache.

## Product and decision status

The user accepts some missed unwanted posts and some false hides. The earlier 95% retention / 80% removal figures remain provisional reference points, not settled launch gates. No replacement numeric target has been agreed. Strictness changes only the threshold; user instructions remain verbatim.

The evaluation decision stays open: choose a useful quality/retention tradeoff and model strategy, then validate the selected artifact in the browser. Live reversible X filtering and final architecture also remain unresolved. Raw outputs are saved locally for further diagnostics; this report publishes no individual posts, URLs, or labels.
