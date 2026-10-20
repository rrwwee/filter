# First labeled development comparison

This is a development result, not a held-out acceptance test. All personal post text, source URLs, labels, and full results remain in ignored local-results/. The counts below are aggregate findings.

## Sample

Rory labeled 20 real For You previews: 16 keep, 2 hide, and 2 insufficient-evidence cases. Both hide examples use the tech-only rule; there are no labeled hide examples for dating, withheld-point, or combined rules yet. With 16 wanted cases, the 95% retention target requires keeping all 16. With only two unwanted cases, these percentages are highly unstable.

## Comparison

Thresholds below are chosen on these development cases to preserve all 16 wanted posts. They must not be represented as frozen product thresholds or validated probabilities.

| Candidate | Template | Wanted kept | Unwanted hidden | Median actual-rule call |
|---|---|---:|---:|---:|
| laya fp32-fp16-embeddings | choice | 16/16 | 0/2 | 77.6 ms |
| laya fp32-fp16-embeddings | direct | 16/16 | 1/2 | 81.4 ms |
| laya fp32-fp16-embeddings | question | 16/16 | 0/2 | 80.0 ms |
| laya fp32-fp16-embeddings | state | 16/16 | 0/2 | 81.7 ms |
| opendecider fp16 | choice | 16/16 | 0/2 | 97.8 ms |
| opendecider fp16 | direct | 16/16 | 1/2 | 108.7 ms |
| opendecider fp16 | question | 16/16 | 0/2 | 108.1 ms |
| opendecider fp16 | state | 16/16 | 0/2 | 112.6 ms |
| opendecider q8f16 | choice | 16/16 | 0/2 | 106.6 ms |
| opendecider q8f16 | direct | 16/16 | 1/2 | 100.2 ms |
| opendecider q8f16 | question | 16/16 | 0/2 | 103.6 ms |
| opendecider q8f16 | state | 16/16 | 0/2 | 109.3 ms |

`choice` uses explicit keep/hide options with the original instruction. `state` puts the user instruction in the state JSON; `question` puts it in a fixed question wrapper. `direct` is a hand-written yes/no question for each known rule type, with polarity explicitly mapped to keep probability. Direct questions are a diagnostic of task formulation, not a demonstrated general plain-language-rule solution.

## Interpretation

A monotonic threshold cannot repair incorrectly ordered wanted/unwanted scores. Calibration and the ability to separate classes must be assessed separately. The controls with an empty rule and an explicit keep-all rule record actual model behavior; their scores must not be treated as the intended production behavior before a user supplies preferences.

Held-back post/instruction cases have not been inferred or used to change these templates. The final 40-case balanced test still requires enough human labels. No model is selected from this pass.

## Runtime scope

Apple M4 / 16 GB, Chromium 155, WebGPU, standalone browser page. Models loaded one at a time. First-call and warm-call measurements remain distinct. Full process/GPU peak memory, sustained scrolling and packaged-extension measurements remain outstanding.

## Main finding

Across all three builds, every generic format tested (rule in state, rule in question, and explicit keep/hide choice) hides 0/2 unwanted examples at thresholds preserving all 16 wanted examples. Hand-written direct questions improve ranking: 16/16 kept and 1/2 hidden; hiding both retains 15/16 wanted (93.75%). This is a formulation/ordering issue as well as a threshold issue; monotonically recalibrating the scores cannot fix an inverted wanted/unwanted pair.

The generic-to-direct change is a diagnostic result, not authorization to hard-code these four rules as the product. The next development question is how to preserve arbitrary user instructions when producing an effective model decision question.

## Batched model-call timings on the development posts

Three repetitions, standalone WebGPU page. q8f16 median one-post call: 118.7 ms; full four-post call: 440.4 ms; full eight-post call: 981.0 ms. Effective throughput across each requested batch configuration, including the last partial batch: 8.09, 7.93, 7.46 posts/s.

fp16 median one-post call: 134.9 ms; four-post: 500.1 ms; eight-post: 985.6 ms. Effective throughput: 7.30, 7.47, 7.31 posts/s. Mixed lengths introduce padding. These model-call numbers exclude the page's display work and do not establish extension latency or a general batching winner.

No held-out acceptance test was run, and no threshold or candidate is frozen for production. More negative coverage is needed, particularly for dating, withholding teasers, and combined instructions. The desired 95%/80% targets remain unchanged.
