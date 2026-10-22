# Filter evaluation integrity: October 22, 2026

## What changed

The browser now permits only declared smoke/development cases in ordinary runs,
with separate admission for assistant-labeled bullet diagnostics. Unknown splits
fail closed. A complete returned batch must have finite valid probabilities before
any of its rows are appended. Keep/hide and reversed A/B polarity are tested;
unsupported hand-written direct-question kinds are rejected.

The compositional trainer no longer silently truncates source rows to the number
of returned predictions. It checks binary logits and complete populations, records
actual local checkpoint fingerprints/runtime package versions, and re-tokenizes
for each loaded comparator. A different comparator tokenizer must not receive
encodings made for the newly trained checkpoint.

Before reports are generated, raw data and all three model populations are checked
against source IDs, labels, metadata and dataset hashes. Exact normalized text and
post-ID leakage across splits, contradictory labels, count mismatches and invalid
probabilities fail. Empty report slices are called out rather than silently omitted.

## Run

`npm test` uses Node and Python standard libraries only; no dependency install,
model download, network request or private feed is needed. Tests include actual
browser and trainer/report control flow with deterministic fake models. Those
fixtures are software tests, not measured filtering performance.

With private experiment inputs already present locally:

```
python3 prototypes/model-finetuning/evaluation_contract.py local-results/finetune-format-robust
python3 prototypes/model-finetuning/evaluation_contract.py local-results/finetune-format-robust --results
```

For a prospective novel-combination claim, add `--require-family novel_combination`
to require nonempty coverage of both classes. The current final public aggregate
has no such slice. Do not re-label that existing result as new-combination evidence.

## Inputs available and missing

Available here: pinned source at a87449652de29e7985dd3e4bcf8406794d6f8169,
public aggregate reports, source builders/trainers, and synthetic software fixtures.

Not available in this cloud checkout: `local-results/finetune-format-robust/`
manifest/train/validation/test files and raw results; original base under
`local-results/finetune-promotions/base`; comparator under
`local-results/finetune-broad/full-checkpoint`; selected new checkpoint. Thus no
new real-model evaluation or training was performed. The documented original
model is Laya multilingual revision 052592a15d198d9ad47da779604259b10b47b7aa;
its identity has not been independently confirmed against absent local weights.

The public Python runtime is documented as Laya 0.4.12. Browser dependency pins
remain unchanged. Private raw posts/labels/checkpoints must stay local and ignored.

## Limits and next decision

Passing checks establish comparison integrity, not independent label truth, model
quality, semantic deduplication or genuine historical holdout isolation. Reading
split files for integrity does not score them, but exposes them to the training
process; this is a validation guard, not an enforced secrecy boundary. A recorded
“test unlocked after training” flag is not proof of execution history. Checkpoint
hashes identify bytes, not their upstream authorship. Rows expanded from a post
remain correlated.

Next: run this preflight where the private artifacts already reside, inspect
coverage and label provenance, and only then plan a frozen acceptance run. Fresh
independently judged posts are needed for a new generalization claim because
previous test outputs have already informed exploration.
