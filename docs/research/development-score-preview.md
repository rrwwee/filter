# Local recorded-score product preview

This evolves the pending-post A/B interaction prototype from commit `75b6828a89976d411a48f91152a12134fd95579b`: the same show-while-checking versus wait-until-checked layout now accepts versioned, actual single-post development captures instead of invented scores. It is a local research preview, not an extension, deployed feed or live inference path.

Open `/prototypes/model-evaluation/pending-posts.html` on the existing loopback evaluation server. The preview expects `local-results/development-score-replay.json`. That private file is deliberately not committed. Its exporter accepts only reviewed development labels, complete single-post actual-rule populations and the explicitly implemented `minimal-prefix` format. It checks case text, source, instruction, label, score polarity and model identity. Separate revisions, devices, dtypes and capture files remain separate selectable recordings. No model runs while moving the slider.

Build locally using existing development-only labels and saved captures:

```sh
python3 tools/build_score_replay.py --labels local-results/development-labeled.json \
  --source local-results/recorded-capture.json \
  --output local-results/development-score-replay.json
npm start
```

Use the existing blind-label UI at `/prototypes/model-evaluation/label.html`; do not create another labeling interface. In a disposable preview worktree, place the development-only label list at `local-results/labeling-cases.json`, with the same list in a valid `latest-labels.json` snapshot. Do not point this review preview at the held-out labeling pool. Labels in a replay stay frozen until explicitly rebuilt, avoiding silent changes while reviewing thresholds.

## Interaction contract

- The recorded instruction is copied verbatim. Draft text and recording selection do not affect current posts until Apply.
- No matching capture means readable posts and a clear error. It never recycles old scores under a new instruction. Retry re-applies the selected local recording; it does not imply live inference.
- Higher keep thresholds monotonically expand hidden sets over fixed scores. The initial 0.50 is a developer-selected preview value, not a chosen default or release criterion.
- Pause and failure restore every loaded post. Pending A/B behavior uses cached results with explicitly labeled simulated timing. Historical call durations are not live latency measurements.
- Recorded-duration mode resolves one post at a time in displayed order, waiting that post's historical call duration before revealing its result. The withheld lane reveals qualifying posts as they resolve; the visible-pending lane removes rejected posts individually. Pause freezes the remaining simulated delay, and Resume continues it. Threshold changes and loading more posts do not restart the active delay. Apply and Retry start a fresh replay and invalidate old callbacks; failure cancels pending callbacks. Instant mode and Finish replay now remain available.
- The table retains hidden posts for inspection and compares them with prior keep/hide/insufficient-evidence labels. Labels do not influence visibility, and insufficient-evidence labels do not force visibility at every threshold.
- There are no default false-hide/retention gates. Previous numerical targets remain provisional; this preview helps the user assess actual tradeoffs.

No private captures, texts, source identifiers, labels, screenshots or individual scores should be committed or uploaded. Public CI uses synthetic inputs. The server adds only the named preview assets and one named local replay JSON to its existing allowlist. No authentication, trust settings, model weights or network exposure changes are introduced.

## Validation and limits

The local build used 20 previously reviewed development cases and three recorded model/dtype identities; each instruction has five cases. The hidden pool was not imported or scored. Existing labels were reused, and no new human labels were fabricated. Recordings retain source-file hashes, a frozen label-snapshot hash and a content-derived replay version. Source captures predate current integrity gates, so this validation cannot retroactively prove their complete historical execution or weight provenance.

Synthetic browser verification covers threshold changes, the visible wanted-hidden/unwanted-removed counts, Pause restoration, draft-only edits, missing-recording errors and Retry. Deterministic tests cover monotonicity, fixed scores, label independence, stale completion, invalid populations, data alignment and the narrow route allowlist. These are interaction and replay-integrity checks, not model-quality evaluation.
