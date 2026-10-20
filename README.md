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
