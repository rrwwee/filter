# Model evaluation prototype

Throwaway browser harness for the decision ticket **Evaluate candidate models against real filtering instructions**. This is not a production extension and does not establish X filtering quality.

Run from this directory:

```sh
npm ci --ignore-scripts && npm start
```

- Inference: http://127.0.0.1:8766/
- Human labeling: http://127.0.0.1:8766/prototypes/model-evaluation/label.html

The harness downloads model weights from their publisher. Post text is classified locally. Personal feed captures, human labels, and uncurated results live only in ignored `local-results/`; they are never committed. The public measurement file uses invented smoke cases only.

## Inputs and experimental separation

The pinned package versions are in package-lock.json. OpenDecider's package pins and hash-checks its weight revision. Laya uses the published r4ai model config, whose source revision and asset hashes are recorded by the publisher. Record the specific loaded metadata for every result. Laya multilingual is a distinct checkpoint, not the English model.

A fixed nonempty yes/no question judges a state containing `filtering_instruction` and `post_text`. Compare an empty filtering-instruction string, an explicit keep-all instruction, and actual instructions. Strictness changes only the threshold on the recorded keep probability.

The sample labels are not inferred by the agent. The real feed labeling set assigns one of four rule types per post, with 20 development cases and the remainder an untouched held-out pool. Human labels determine whether there are enough clear keep/hide and uncertain cases to construct the agreed evaluation. No held-out inference is available from the prototype's ordinary run buttons.

## Initial measurements

Apple M4 / 16 GB; in-app Chromium 155; WebGPU; standalone cross-origin-isolated page. OpenDecider 0.9.0, q8f16, revision `53da62af62275ff5076e29b962dd965f38107c50`.

- First download plus load: 14.26 s. This is not a cached-load measurement.
- Warm sequential single-post calls, 12 samples: median about 94.7 ms.
- Four-post calls, 3 samples: median about 274.8 ms for all four results.
- The requested batch-size-8 run contained only four available smoke posts. It does **not** measure an eight-post batch. Actual batch size is preserved in each result.
- The first call took 622 ms before later calls settled. Warm and first-inference numbers must remain separate.
- GPU/total process memory, sustained scrolling, and packaged-extension behavior have not yet been measured.

These short invented posts are not representative performance or quality acceptance tests. The keep-all control did not produce uniformly high keep probabilities with this first fixed template. The probabilities cluster near 0.5, so record the full distribution and investigate template sensitivity on development cases; do not assume 0.5 is a validated operating threshold. Never tune on held-out cases.

`measurements/opendecider-q8f16-smoke.json` holds the actual captured results. No winner or passing quality score has been established.

## Label review and analysis

The private capture is never bundled with this branch. The local labeling page reads `local-results/labeling-cases.json` and autosaves `local-results/latest-labels.json`. It does not expose model scores. K / H / U record keep / hide / insufficient evidence, respectively. The first 20 cases are development; the remaining pool must stay out of inference/tuning until the setup is frozen.

`python3 prototypes/model-evaluation/analyze.py local-results/run-....json --labels local-results/latest-labels.json` reports per-condition timing and, when labels exist, selects a threshold using development cases only. It keeps timing repeats from inflating the quality sample. An explicit `--threshold` can evaluate a previously frozen threshold. The script does not imply that class counts or coverage are adequate; inspect these before claiming the 95%/80% gates.

## Second candidate smoke run

Laya multilingual, `@r4ai/laya-web@0.2.0`, source revision `052592a15d198d9ad47da779604259b10b47b7aa`, loaded from the publisher's r4ai hosted export on WebGPU. Its manifest records fp32 weights and fp16 embedding storage. Initial download plus load was 42.49 s; first call 1071.5 ms; the four actual-instruction calls were 81.3, 82.2, 158.5, and 77.5 ms. This small sequence is not a stabilized latency benchmark. The runtime has no multi-state batch API exposed by this adapter; do not interpret sequential calls as a GPU batch.

The same invented cases and fixed question/state template were used. The keep-all control again did not yield uniformly high keep probabilities. Raw results are in `measurements/laya-multilingual-smoke.json`. This may reflect task/template sensitivity; no conclusion about real-feed accuracy or calibration is supported before labeled evaluation.

Capture limitation: this initial sample contains the rendered post/quote text and a Show-more flag. It does not yet provide structured link-card titles or image/video content. Labels apply to the displayed captured evidence; richer link-card extraction needs to be validated before treating results as full feed-context acceptance.

## OpenDecider fp16 smoke comparison

The fp16 build's first download/load took 19.50 s. On the same four short smoke inputs, 12 warm single-post calls had a median of 117.6 ms; three four-post calls had a median of 298.7 ms. The larger build was not faster in this small run on the base M4. This does not refute upstream large-batch results on different hardware and input shapes. Run order was sequential, sample counts are small, and there is no resource-controlled performance conclusion yet. Raw capture: `measurements/opendecider-fp16-smoke.json`.

## Labeled development run

The four recorded formulations are `state` (rule as a JSON state field), `question` (rule in a yes/no question wrapper), `choice` (explicit keep/hide options using the original rule), and `direct` (hand-written task questions for each of the four known instruction types). All retain fixed model inputs when strictness changes. Direct questions are diagnostic and do not demonstrate a general solution for arbitrary instructions.

Human labels are never included in the state sent to the model. The first 20 reviewed cases contain 16 keep, 2 hide, and 2 insufficient-evidence labels; both hide labels are for tech relevance. The held-out pool stays excluded by the run filter. At this sample size, preserving 95% of 16 wanted posts requires preserving all 16; do not interpret a development percentage as a stable generalization estimate.

Use `python3 prototypes/model-evaluation/summarize-development.py` to aggregate the local development captures, then `python3 prototypes/model-evaluation/write-development-report.py` to generate a text-free aggregate report. Raw real-post captures and labels stay ignored. The aggregate records counts, not identifiable post content.
