# Local decision models and browser runtimes

Research for [Investigate local decision models and browser runtimes](https://github.com/rrwwee/filter/issues/3), under [Find the way to a local X feed filter](https://github.com/rrwwee/filter/issues/1). Reviewed 2026-10-19. This is a bounded source investigation, not a model selection or an implementation specification.

## Finding

There are credible entirely local paths. Evaluate OpenDecider nano as a purpose-built decision baseline, Laya as a second decision family, and a small instruction model as a different approach. No winner is established. Browser deployment is feasible in existing source, but useful X filtering, a reliable strictness ordering, and acceptable resource consumption on Rory's hardware remain unmeasured.

All speed, memory and quality numbers below are **upstream reports**, not measurements made in this investigation. I did not download weights, run inference, install an extension, or access Rory's feed. A weight-file size is neither runtime memory nor total installation size. Native Python measurements are not browser measurements.

## Bounded candidate set

### OpenDecider nano with `@opendecider/web`

The published ONNX model is approximately 400M parameters, Apache-2.0, based on the MIT-licensed Ettin encoder. It exposes choice, ordered-score and yes/no (`noul`) questions rather than generated prose. Browser-ready weights and a JavaScript package exist; local execution needs no inference account, API key or per-call service. This is the most directly relevant starting point to evaluate, not an endorsement of its accuracy. [Model card](https://huggingface.co/manjunathshiva/opendecider-nano-ONNX)

The browser guide reports these configurations on Chrome/Apple M4 Max:

| Build/backend | Download | Reported runtime memory with a 2,048-token question | Reported single-question latency |
| --- | --- | --- | --- |
| q8f16/WebGPU | 450 MiB | about 2.2 GiB | 47 ms |
| q8/WebAssembly | 569 MiB | about 2.8 GiB | 125 ms with eight threads; 830 ms with one |

The faster multi-question GPU configuration is fp16: 755 MiB download and 40 questions in 1.1 seconds, versus 7.4 seconds for q8f16. The guide warns against fp16 on WASM: about 4.8 GiB. Its input ceiling is 2,048 tokens; truncation is reported. Loading supports progress, cached files, pinned revisions and SHA-256 validation. These tradeoffs require measuring the actual input/batch shape, rather than extrapolating single-question speed to an entire feed. [Browser guide](https://manjunathshiva.github.io/opendecider/guides/browser/)

An existing local YouTube extension reports a 755 MiB GPU download or 569 MiB CPU download, roughly 3.3/3 GiB loaded memory, and 40 own-rule decisions in 0.3/5.5 seconds respectively on M4 Max. Its own-rule balanced accuracy of 0.934 comes from three topic rules on 400 held-out YouTube videos, not nuanced X posts or compound instructions. It uses title/channel text and hides pending tiles. These results establish a useful precedent, not transferable acceptance evidence. [Extension guide](https://manjunathshiva.github.io/opendecider/guides/chrome-extension/)

### Laya family with an ONNX browser port

The English general checkpoint uses 421M parameters with 512-token context. The English typed-decisions variant has 1,024-token context and is specialized to four synthetic business workflows. Its authors explicitly warn that confidence is uncalibrated until refitted on held-out data, and that performance outside those workflows may be worse than the general checkpoint. Include both only if the evaluation budget permits; do not silently assume the typed variant is the better X filter. [Official typed-decisions card](https://huggingface.co/convaiinnovations/laya-typed-decisions)

The independent Apache-2.0 `layaForWeb` port offers the English checkpoint as approximately 440 MB q8e8 and 290 MB q4e8, using ONNX Runtime Web. WASM is its reference backend; WebGPU is experimental and only the q4e8 path is supported. It reports 2–5 seconds for three questions on a two-core machine. Its small comparison found only 10/12 top answers matching PyTorch for the int4 build, with a largest probability difference of 0.274. These are serious reasons to check output drift, not just download size. A conversion recipe exists for typed-decisions; this investigation did not verify a deployed typed browser artifact. [Port and comparison](https://github.com/vishalmysore/layaForWeb)

The official Laya ONNX documentation independently warns that its dynamic INT8 path changes accuracy and should not be used where calibrated probabilities matter. This is a different quantization path from the browser port and should not be conflated with it. [Official ONNX documentation](https://github.com/NandhaKishorM/laya/blob/main/docs/reference/agent.md)

### Small instruction-model comparators

- **Qwen3-0.6B with WebLLM:** Apache-2.0, supports disabling thinking in its prompt setup. A useful small general instruction-following comparator, with no verified feed-filter quality here. [Official model card](https://huggingface.co/Qwen/Qwen3-0.6B)
- **SmolLM2-360M-Instruct with Transformers.js:** Apache-2.0. The publisher supplies a Transformers.js usage example and ONNX artifacts, including q4f16 at 273 MB, q4 at 388 MB, and fp16 at 725 MB. These are alternative graph files, not amounts to sum. Exact backend compatibility and peak memory still need testing. [Official artifacts](https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct/tree/main/onnx)

WebLLM's source contains a prebuilt Qwen3-0.6B q4f16 model record with `vram_required_MB: 1403.34` and 4,096-token configured context, and q4f32 at 1924.98 MB. Treat these as configuration estimates, not total Chrome process memory. The same source exposes logprobs and response-format options. A decoder must generate or score labels; a number it prints is not automatically a trustworthy probability. Its model library is a separate WASM artifact, which must be packaged correctly for an extension. [Runtime configuration](https://github.com/mlc-ai/web-llm/blob/main/src/config.ts)

Transformers.js runs ONNX in-browser, with WASM CPU execution and optional WebGPU. Backend availability does not imply every quantized graph has equivalent accuracy or supported GPU operators. [Transformers.js](https://huggingface.co/docs/transformers.js/en/index), [WebGPU guide](https://huggingface.co/docs/transformers.js/en/guides/webgpu)

## What can be reused from OpenDecider?

Inspected source revision: [`7873aa45dbed68ba75f419bf21d0dfd1f09ded5d`](https://github.com/manjunathshiva/opendecider/tree/7873aa45dbed68ba75f419bf21d0dfd1f09ded5d). The source is Apache-2.0; redistribution must retain applicable license/notices and identify modified files. The NOTICE identifies model bases separately. [License](https://github.com/manjunathshiva/opendecider/blob/7873aa45dbed68ba75f419bf21d0dfd1f09ded5d/LICENSE), [NOTICE](https://github.com/manjunathshiva/opendecider/blob/7873aa45dbed68ba75f419bf21d0dfd1f09ded5d/NOTICE)

Useful seams are the model loader, progress reporting, backend fallback and batching. Its offscreen page owns one cached model promise, loads bundled ONNX runtime assets, and returns typed answers through runtime messaging. That is a concrete execution pattern to study independently of the YouTube UI. [Offscreen source](https://github.com/manjunathshiva/opendecider/blob/7873aa45dbed68ba75f419bf21d0dfd1f09ded5d/extension/src/offscreen.ts)

Its existing rule adapter is **not** a general compound-instruction parser: unless text ends in a question mark, it wraps the rule as “Is this video about …?”. Its state is title plus channel. In hide mode, its numeric decision is `ruleProbability > 1 - strictness`; keep-only mode uses `ruleProbability < strictness`. Settings clamp strictness to 0.2–0.8 and limit the rule to 200 characters. Thus direct reuse would alter the semantics of Rory's examples and exclude longer instructions. [Question and threshold logic](https://github.com/manjunathshiva/opendecider/blob/7873aa45dbed68ba75f419bf21d0dfd1f09ded5d/extension/src/questions.ts), [Settings](https://github.com/manjunathshiva/opendecider/blob/7873aa45dbed68ba75f419bf21d0dfd1f09ded5d/extension/src/settings.ts)

The manifest targets YouTube and Chrome 124+, uses `offscreen`, storage, alarms and context menus, and permits bundled WASM plus model-host connections. X extraction and For You detection require a new adapter; unrelated guard/context-menu functions are not part of the agreed product. Source availability does not settle whether to fork the extension or depend on its model package. [Manifest](https://github.com/manjunathshiva/opendecider/blob/7873aa45dbed68ba75f419bf21d0dfd1f09ded5d/extension/static/manifest.json)

## Execution and setup constraints

Chrome normally terminates an extension service worker after 30 seconds idle, and globals disappear. Model ownership cannot assume a permanently resident service worker. [Chrome lifecycle](https://developer.chrome.com/docs/extensions/develop/concepts/service-workers/lifecycle)

An offscreen document is a bundled hidden page, supports only the extension runtime API, and has one active instance per normal profile. The WORKERS reason allows worker use; non-audio reasons do not impose the audio idle lifetime. This makes offscreen ownership a credible candidate, while requiring explicit creation, release and recovery logic. [Chrome offscreen API](https://developer.chrome.com/docs/extensions/reference/api/offscreen)

WebLLM also publishes a WebGPU service-worker extension example. That shows another feasible integration route, but does not erase the worker lifecycle constraints. [Official example](https://github.com/mlc-ai/web-llm/blob/main/examples/chrome-extension-webgpu-service-worker/README.md)

Manifest V3 requires executable JavaScript and WASM to ship with the extension; remote data is distinguished from remote code. The design must bundle all runtime/model-library executable artifacts and limit downloads to model data. Do not assume a standard CDN-loading demo is store-ready. [Chrome remote-code guidance](https://developer.chrome.com/docs/extensions/develop/migrate/remote-hosted-code)

## Strictness and remaining decisions

Inference from these sources: thresholding one stable keep/hide score gives mechanically nested hidden sets as strictness increases. That establishes monotonic UI behavior, not semantic reliability. Entropy-based confidence measures certainty in either answer; using certainty alone can hide confidently wanted posts. Prefer evaluating a score aligned with “this instruction asks to hide this post,” including negation, exceptions and combined requirements.

The next evidence gates are precise:

1. **Hardware envelope:** which laptop/browser is the baseline, and are 3–3.3 GiB peak memory and the stated downloads acceptable? Should CPU-only be supported or explicitly unavailable?
2. **Instruction fidelity:** on one held-out set of X posts, compare the same compound instructions across the bounded candidates; separate topic, tech relevance and withheld-point judgments. Include post-text instructions that try to override the user's filter.
3. **Score usefulness:** measure wanted-post loss and unwanted-post leakage at multiple thresholds, calibration and ranking, with paraphrased instructions and quantized/full-precision drift. Determine whether a continuous slider is justified or only a few tested presets.
4. **Runtime envelope:** measure cold download/load, warm first decision, batches, sustained scrolling, total CPU/GPU/process memory, idle release, worker termination, device loss, background-tab behavior and failed downloads in the packaged extension.
5. **Reuse boundary:** after fidelity and hardware evidence, choose model-package reuse, extension fork, or separate implementation. Check pinned artifact licenses and dependency notices at that point.

These are unresolved gates, not commitments to build more prototypes or select a particular model in this ticket. An existing local extension clears the feasibility question; it does not clear the X product-quality question.
