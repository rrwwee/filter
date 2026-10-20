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
| laya fp32-fp16-embeddings | minimal-ab | 16/16 | 0/2 | 84.2 ms |
| laya fp32-fp16-embeddings | minimal-ba | 16/16 | 0/2 | 93.0 ms |
| laya fp32-fp16-embeddings | minimal-choice | 16/16 | 0/2 | 87.2 ms |
| laya fp32-fp16-embeddings | minimal-prefix | 16/16 | 0/2 | 79.9 ms |
| laya fp32-fp16-embeddings | minimal-state | 16/16 | 0/2 | 92.9 ms |
| laya fp32-fp16-embeddings | minimal-suffix | 16/16 | 0/2 | 80.6 ms |
| laya fp32-fp16-embeddings | question | 16/16 | 0/2 | 80.0 ms |
| laya fp32-fp16-embeddings | state | 16/16 | 0/2 | 81.7 ms |
| opendecider fp16 | choice | 16/16 | 0/2 | 97.8 ms |
| opendecider fp16 | direct | 16/16 | 1/2 | 108.7 ms |
| opendecider fp16 | minimal-ab | 16/16 | 0/2 | 126.1 ms |
| opendecider fp16 | minimal-ba | 16/16 | 0/2 | 137.7 ms |
| opendecider fp16 | minimal-choice | 16/16 | 0/2 | 139.7 ms |
| opendecider fp16 | minimal-prefix | 16/16 | 0/2 | 110.7 ms |
| opendecider fp16 | minimal-state | 16/16 | 0/2 | 137.9 ms |
| opendecider fp16 | minimal-suffix | 16/16 | 0/2 | 135.9 ms |
| opendecider fp16 | question | 16/16 | 0/2 | 108.1 ms |
| opendecider fp16 | state | 16/16 | 0/2 | 112.6 ms |
| opendecider q8f16 | choice | 16/16 | 0/2 | 106.6 ms |
| opendecider q8f16 | direct | 16/16 | 1/2 | 100.2 ms |
| opendecider q8f16 | minimal-ab | 16/16 | 0/2 | 107.0 ms |
| opendecider q8f16 | minimal-ba | 16/16 | 0/2 | 104.4 ms |
| opendecider q8f16 | minimal-choice | 16/16 | 0/2 | 110.0 ms |
| opendecider q8f16 | minimal-prefix | 16/16 | 0/2 | 90.6 ms |
| opendecider q8f16 | minimal-state | 16/16 | 0/2 | 99.3 ms |
| opendecider q8f16 | minimal-suffix | 16/16 | 0/2 | 91.3 ms |
| opendecider q8f16 | question | 16/16 | 0/2 | 103.6 ms |
| opendecider q8f16 | state | 16/16 | 0/2 | 109.3 ms |

`choice` uses explicit keep/hide options with the original instruction. `state` puts the user instruction in the state JSON; `question` puts it in a fixed question wrapper. `direct` is a hand-written yes/no question for each known rule type, with polarity explicitly mapped to keep probability. Direct questions are a diagnostic of task formulation, not a demonstrated general plain-language-rule solution.

The six `minimal-` formats keep every user instruction verbatim. Prefix and suffix put a fixed question after or before it. State uses `{filter, post}` with a fixed question. Choice supplies named keep/hide options. AB and BA use neutral option keys with reversed keep/hide meanings. Every minimal format also runs empty-instruction and explicit keep-all controls.

## Interpretation

A monotonic threshold cannot repair incorrectly ordered wanted/unwanted scores. Calibration and the ability to separate classes must be assessed separately. The controls with an empty rule and an explicit keep-all rule record actual model behavior; their scores must not be treated as the intended production behavior before a user supplies preferences.

Held-back post/instruction cases have not been inferred or used to change these templates. The final 40-case balanced test still requires enough human labels. No model is selected from this pass.

## Runtime scope

Apple M4 / 16 GB, Chromium 155, WebGPU, standalone browser page. Models loaded one at a time. First-call and warm-call measurements remain distinct. Full process/GPU peak memory, sustained scrolling and packaged-extension measurements remain outstanding.
