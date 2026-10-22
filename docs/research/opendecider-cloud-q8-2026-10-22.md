# OpenDecider cloud CPU q8 check — 2026-10-22

This records a cloud run of the official OpenDecider runtime with the browser
harness's default state wrapper. It is **CPU/WASM q8**, not the browser's
WebGPU q8f16 default. It is a small synthetic diagnostic, not real-feed quality.
No inference was rerun while validating or publishing this checkpoint.

## Recorded outcomes

The 24 assistant-authored cases contain 12 wanted and 12 unwanted posts. At the
frozen 0.5 keep threshold:

| Method | Wanted falsely hidden | Unwanted removed | Scored |
|---|---:|---:|---:|
| OpenDecider nano CPU q8 | 2/12 | 7/12 | 24/24 |
| Frozen domain-keyword baseline | 2/12 | 0/12 | 24/24 |
| Keep everything | 0/12 | 0/12 | 24/24 |

Thus 5/12 unwanted posts remain visible under the model, versus 12/12 for the
keyword and keep-everything baselines.

The model removes 3/4 personal-dating cases, 1/4 deliberately withheld-clickbait
cases, and 3/4 off-topic cases. It keeps 2/2 technical dating-app cases and 1/2
substantive linked previews. These tiny slices describe the authored set only.
The keyword baseline is deliberately simple, not the strongest possible rule
system. Equal false-hide counts do not mean the methods made identical errors.

The result motivates attention to the clickbait exclusion. It does not identify
whether errors arise from the model, policy composition, instruction placement,
or quantization, and does not justify changing the threshold on these cases.

## Scope and provenance

- Runtime: `@opendecider/web@0.9.0`, Node `v24.19.0`, WASM q8, two threads.
- Model revision: `53da62af62275ff5076e29b962dd965f38107c50`.
  Model SHA-256: `3920323e41bb107f28566be7b45e6cb55a2bdc1951b27a6e62625857e22542c4`.
  Tokenizer SHA-256: `fd4146f0082d98fd1fc03bf41349f4d1eed478987ce9a64addc1654dfcad14ee`.
- Input uses the app's fixed keep question and
  `{filtering_instruction, post_text}`. The policy is the contract's combined
  diagnostic question about technology, personal dating stories and withholding
  the substantive point. It is **not a saved user filtering instruction**.
- The supplied app snapshot matches the current prototype apart from a trailing
  blank line. Runtime/model metadata match the installed official 0.9.0 manifest.
- The source archive includes a recorded frozen plan, source hashes, independent
  post-run audit, raw responses and package lock. It does not independently
  substantiate that a separate second label review was blinded to outcomes.
  The app snapshot is hashed, but no source commit is pinned. Model weights are absent: the recorded
  cloud hash verification cannot be independently repeated from this archive.
  Recorded timestamps and hashes do not themselves prove historical isolation.

The cases are nonrandom synthetic assistant judgments, not human-confirmed
labels. Do not describe them as a representative, statistically independent
held-out feed benchmark, or infer q8f16 browser accuracy from this CPU run.

## Independent publication checks

Without loading models, the local publication pass verified all 24 source-ID
joins, input texts/policy/question, binary label logic, raw probabilities,
threshold decisions, complete coverage, and the keyword baseline. It recomputed
the category counts, total call time and even-count median. No warnings or
truncation were reported; the raw outputs omit these diagnostic fields, so their
absence does not prove that no truncation occurred. All six supplied
deterministic tests pass.

Archive SHA-256:
`109f97284cdb3021772a326a3e6dcf4b84a9e685ec35dae3444e84a92faa86af`.
Recorded cases SHA-256:
`860fe2b1a652d1840d423186d35c4f41107ce83cbd24be758e09d55f53f59d0a`.
Results SHA-256:
`d0cdf07a84cb6008643389d7936d8fca5c0591ae394e64ef3518c2419bb6c266`.

Only this report and the sanitized aggregate are published. Raw responses and
synthetic case files remain in the local source archive; no previous result or
runtime behavior is changed.

## Recorded cost and next decision

Twenty-four single-state calls took 74.773 seconds total, with a 3.094-second
median. Recorded model loading took 3.695 seconds; peak process RSS was about
2.31 GiB. Model and tokenizer bytes total 595,577,625. There were no warm-up or
repeated latency trials, so this is not a laptop or browser responsiveness claim.

Before any automatic real-feed hiding, choose an explicit wanted-post loss
budget and obtain fresh human-reviewed evidence. A later development comparison
can test explicit per-rule decisions, particularly clickbait, then freeze the
chosen setup before a new evaluation on the actual browser backend. No runtime
mitigation is implemented by this publication.
