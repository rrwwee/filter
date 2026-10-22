# Frozen wording and content factorial — 2026-10-22

## Finding

The results do not support a single universal “answer yes” mechanism. Both models use post content in some settings, but their interpretation of that content is strongly dependent on question polarity, answer names and equivalent rule wording. No prompt, threshold or model was selected using this diagnostic.

## Prespecified design

Four new authored base posts cover two topics and two meanings (neutral description versus direct purchase request). Each is paired with an added instruction-like prefix, giving eight scored cases with four keep and four hide labels. A separate reviewer confirmed labels and rule equivalence before inference. The prefix is explicitly non-authoritative under both rules.

The complete crossing is two equivalent rule wordings × hide/keep question polarity × false/true or A/B answer names × forward/reversed physical answer order. All 16 conditions keep the same binary NOUL question type. Each condition scores the same eight cases and a genuinely empty, unlabeled post: 128 scored forwards plus 16 controls per model. These are four underlying posts, not 128 independent examples. The empty inputs are never counted as correct or incorrect.

The original 26-case acceptance results and the previous 96-variant-per-model diagnostic remain byte-for-byte unchanged. The new posts have no exact normalized-text matches in 169 historical local files plus the two earlier frozen corpora; this does not prove semantic novelty or absence from pretraining.

## Every condition at the frozen 0.5 threshold

`r0` and `r1` are independently reviewed equivalent rule paraphrases. “Neutral” changes only displayed false/true answer names to A/B. Table cells report correct / 8 and the raw P(true) for the empty post. Empty P(true) is not an accuracy score.

| Condition | Base correct | Tuned correct | Base empty P(true) | Tuned empty P(true) |
|---|---:|---:|---:|---:|
| r0-hide-boolean-forward | 7/8 | 6/8 | 0.966 | 0.080 |
| r0-hide-boolean-reverse | 8/8 | 7/8 | 0.883 | 0.071 |
| r0-hide-neutral-forward | 1/8 | 3/8 | 0.794 | 0.706 |
| r0-hide-neutral-reverse | 5/8 | 5/8 | 0.311 | 0.279 |
| r0-keep-boolean-forward | 1/8 | 3/8 | 0.965 | 0.947 |
| r0-keep-boolean-reverse | 0/8 | 3/8 | 0.861 | 0.637 |
| r0-keep-neutral-forward | 5/8 | 4/8 | 0.753 | 0.912 |
| r0-keep-neutral-reverse | 3/8 | 3/8 | 0.338 | 0.688 |
| r1-hide-boolean-forward | 4/8 | 4/8 | 0.960 | 0.794 |
| r1-hide-boolean-reverse | 5/8 | 4/8 | 0.770 | 0.973 |
| r1-hide-neutral-forward | 4/8 | 7/8 | 0.449 | 0.356 |
| r1-hide-neutral-reverse | 3/8 | 4/8 | 0.164 | 0.685 |
| r1-keep-boolean-forward | 3/8 | 2/8 | 0.971 | 0.822 |
| r1-keep-boolean-reverse | 2/8 | 3/8 | 0.803 | 0.961 |
| r1-keep-neutral-forward | 4/8 | 3/8 | 0.827 | 0.532 |
| r1-keep-neutral-reverse | 2/8 | 6/8 | 0.087 | 0.255 |

## Paired factor sensitivity

A flip compares the same post under one changed factor, averaging over the other factors. Each row has 64 correlated pairs per model.

| Changed factor | Base flips | Tuned flips | Base mean absolute ΔP(hide) | Tuned mean absolute ΔP(hide) |
|---|---:|---:|---:|---:|
| rule_index | 19/64 | 37/64 | 0.223 | 0.432 |
| polarity | 41/64 | 41/64 | 0.386 | 0.486 |
| labels | 27/64 | 33/64 | 0.322 | 0.482 |
| order | 19/64 | 15/64 | 0.118 | 0.122 |

The injected prefix flips 25/64 base comparisons and 15/64 tuned comparisons. Mean raw P(true) changes are +0.027 and +0.047, respectively; the means hide heterogeneous effects. This tests one prefix, not general prompt-injection resistance.

## Hypotheses and counterevidence

- **Unconditional affirmative bias:** insufficient as a sole account. Tuned empty P(true) ranges from 0.071 to 0.973 and base from 0.087 to 0.971. Both positive and negative raw-true logit margins occur. Bias clearly depends on the input format. Empty ablation also changes length and token positions, so it is not a pure model intercept.
- **No use of content:** contradicted in some settings. In r0/hide/boolean/reverse, the base distinguishes all four purchase/neutral matched pairs in the correct direction and scores 8/8. Its mean purchase-minus-neutral P(hide) is +0.913. The tuned model has +0.637 and 7/8 there. This demonstrates content discrimination in a narrow setting, not robust task understanding.
- **Weak binding between the rule/question and answer meaning:** consistent with the data. The same r0/boolean/reverse base model scores 0/8 when the question is changed to keep; purchase-minus-neutral semantic P(hide) becomes −0.857. Across all formats, both models flip 41/64 semantic decisions under polarity inversion, despite unchanged keep/hide ground truth. A polarity factor changes both question text and criterion meaning, so it does not isolate one token-level cause.
- **Wording and response-label shortcuts:** plausible, not localized. Equivalent rule wording flips 37/64 tuned decisions, while relabeling false/true to A/B flips 33/64. These manipulations change tokenization/context; the experiment does not identify a circuit, embedding direction or causal layer.
- **Physical slot bias:** contributes but is not sufficient. Physical order flips 19/64 base and 15/64 tuned decisions; other factors cause larger changes. A global output inversion would merely exchange error types and is not proposed as a fix.

## Implementation and evidence checks

The raw canonical true probability and the semantic hide probability are recorded separately, together with physical and canonical logits, marker positions and full token IDs. Inspection and tests verify that option permutations are undone exactly once. Inverting the question changes which canonical answer means hide. All inputs use a uniform target scaffold; true labels do not enter tokenization or the forward call. The 16 requested answer-name/order combinations were checked against decoded model heads before inference.

The runner independently reconstructs every input sequence, compares token IDs and marker positions, and rejects truncation. Actual sequences span 66–90 tokens, with zero truncations. Empty states have zero content tokens. Fixed cases, labels, rules, variants, render checks, code and checkpoint hashes are verified. The probability and logit records remain local; the published JSON contains aggregates only.

Base and tuned runs used CPU with two threads each, no training or paid services. Recorded process peaks were 1.51 and 1.68 GiB. Measured run times were 21.54 and 15.85 seconds; processes briefly overlapped, so these are not controlled latency measurements. Runtime: Laya 0.4.12, Torch 2.14.1, Transformers 5.20.2, Tokenizers 0.23.3.

## Limits and next step

This is a compact mechanism diagnostic with two closely templated topics, explicit wording and independent assistant labels, not human ground truth or a natural-feed sample. The full table is reported rather than selecting its best row. The evidence motivates a separate frozen intervention study on option-marker representations and question-versus-content sensitivity, with output mapping fixed. It does not justify training yet or promoting a new prompt as generally reliable.
