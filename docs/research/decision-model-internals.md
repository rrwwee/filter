# How the evaluated decision models work

Source review: 2026-10-19. This is an explanation of existing implementations, not a model-selection decision. The browser evaluation uses `@opendecider/web@0.9.0` and `@r4ai/laya-web@0.2.0`; its Laya checkpoint is **multilingual**, not the separate English model.

## JSON is a transport and text format

The SDK validates the question schema in ordinary code. It turns each question into a token sequence and serializes a non-string state to JSON text. The network receives token IDs and an attention mask, not a JavaScript object or a JSON parser. Field names, punctuation, and field order therefore become textual evidence. This is visible in the installed SDKs' serializers and prompt builders: [OpenDecider prompt source](https://github.com/manjunathshiva/opendecider/blob/main/web/src/prompt.ts), [Laya Web core](https://github.com/r4ai/laya-web/blob/main/src/core.ts).

OpenDecider's effective layout is:

```text
[CLS] question: <instructions> [SEP]
[MASK] yes: <true-description> [MASK] no: <false-description> [SEP]
input: <post string or serialized state JSON> [SEP]
```

This is the actual installed OpenDecider `noul` path: `@opendecider/client@0.9.0` maps API criteria `true`/`false` to model option names `yes`/`no`, in that order, defaulting descriptions to `Yes`/`No`. It maps the resulting `yes` probability back to `noul` and response key `true`. Current Python source uses the same mapping and documents it as the training/evaluation format; this is a supported path, not evidence of a checkpoint mismatch. The inspected browser package pins model revision `53da62af62275ff5076e29b962dd965f38107c50`. [Python option mapping](https://github.com/manjunathshiva/opendecider/blob/main/opendecider/questions.py)

The question and options survive the 2,048-token budget; state text is shortened first. The browser then runs an ONNX forward pass, extracts logits at the option-marker positions, and normalizes over those options. There is no generated JSON to parse. [Browser implementation](https://github.com/manjunathshiva/opendecider/blob/main/web/src/nano.ts)

Laya Web uses a similar layout, beginning with `<question type> question:` and without OpenDecider's `input:` prefix. Its `noul` options actually are `false` then `true`, unlike OpenDecider. It allocates a separate head budget, records each marker's position, and truncates the question/options and state to fit. Moving the unchanged instruction between the question and a state field consequently changes the token arrangement even though it is not semantic rewriting. [Laya Web core](https://github.com/r4ai/laya-web/blob/main/src/core.ts)

## Architectures actually involved

**OpenDecider nano** uses the bidirectional Ettin-encoder-400m. At each option's marker, its contextual hidden vector passes through an MLP: Linear → GELU → LayerNorm → Linear, producing one scalar logit. A softmax across the options produces the distribution. The same scorer handles newly supplied option descriptions, rather than having a permanent output neuron for every possible category. [Model implementation](https://github.com/manjunathshiva/opendecider/blob/main/opendecider/nano.py), [architecture description](https://github.com/manjunathshiva/opendecider#architecture)

**The tested Laya multilingual** is an ONNX export of `convaiinnovations/laya-multilingual`, source revision `052592a15d198d9ad47da779604259b10b47b7aa`, as recorded by the local evaluation loader and installed package's `docs/development.md`. Its author describes mmBERT-base (bidirectional, 22 layers, hidden size 768) plus two transformer decision layers, an option-marker scorer, and an act/escalate head; total 322M parameters. The separate English Laya uses ModernBERT-large, totaling 421M. Neither evaluated candidate is decoder-only. [Multilingual architecture](https://huggingface.co/convaiinnovations/laya-multilingual#architecture)

Bidirectional means a marker can use evidence elsewhere on both sides of the sequence in the same pass. It does not sequentially write an answer token by token. All supplied options compete within the same distribution, so their wording and order are part of the input.

## Probabilities, calibration, and the strictness threshold

For logits `z_i`, normalization is `p_i = exp(z_i / T) / sum_j exp(z_j / T)`. With `T=1`, this is ordinary softmax. It guarantees nonnegative numbers summing to one; it does **not** guarantee that predictions assigned 0.8 are correct 80% of the time. Calibration is that latter empirical property. Temperature fitting adjusts `T` on held-out labeled data; it changes confidence without changing the winning class. [Guo et al., ICML 2017](https://proceedings.mlr.press/v70/guo17a.html)

Laya's published training method is RLCD: probability distributions are rewarded with proper scoring rules (log and spherical scores, plus a ranked score for ordinal outputs); noisy logits provide exploration, and updates use REINFORCE with a group-mean baseline. This describes the training incentive, not a guarantee for arbitrary deployment data. [Author's training description](https://huggingface.co/convaiinnovations/laya#training)

The multilingual checkpoint explicitly **ships uncalibrated**, with temperatures `[1,1,1]` and no option-count buckets. Its card reports overconfidence and improved calibration after held-out temperature fitting. It also warns of `noul` label bias and suggests checking an equivalent neutral-key two-option `choice`. Those claims are the author's measurements, not results from our feed. [Multilingual limitations](https://huggingface.co/convaiinnovations/laya-multilingual#limits)

The Laya browser SDK applies saved temperature by question type and option-count bucket before softmax. Its `noul` value is `P(true)`; its separate confidence field is not a keep probability. The installed OpenDecider browser backend applies plain softmax with no additional temperature fit. [Laya normalization code](https://github.com/r4ai/laya-web/blob/main/src/core.ts), [OpenDecider browser backend](https://github.com/manjunathshiva/opendecider/blob/main/web/src/nano.ts)

OpenDecider reports distilling distributions from two open teachers whose token scores were temperature-fitted on held-out gold labels before averaging; gold-only datasets use smoothed labels. Nano subsequently received typed-decisions training. These are the author's disclosed provenance claims. They do not establish calibration on our filtering instructions. [Training description](https://github.com/manjunathshiva/opendecider#training)

Our strictness slider remains downstream: `hide = pKeep < threshold`. Increasing the threshold hides more posts without changing model inputs. Calibration fitting is a separate model-output transformation, fixed during an evaluation. With binary output, a single positive temperature preserves ranking, so it cannot fix a wanted/unwanted ordering failure; it can only remap threshold values. The 20 development examples are inadequate to establish reliable empirical calibration.

## The shared API does not imply one architecture

Within OpenDecider itself, **small** takes a different approach: a Qwen3-4B causal decoder with a LoRA adapter. Options are lettered, and the implementation reads their probabilities from the next-token distribution; for more than 26 options it scores option-name sequences. This uses a decoder's existing language-model output rather than an encoder's scalar option-marker head. It can still avoid free-form answer generation. Thus API-compatible open implementations need not reproduce Jev's internals. [OpenDecider architecture](https://github.com/manjunathshiva/opendecider#architecture)

Open-source training code, model cards, and inference code disclose different amounts of detail. No statement here establishes the architecture or proprietary training recipe of Jev or another closed model; those require their own primary-source disclosures.
