# Filter local integrity checkpoint — 2026-10-22

## Integration and validation

The cloud archive was materialized to the Mac and inspected before extraction.
Its SHA-256 is `1dd10f04830567f313c30b1956827427c90529d252db88333072b49f67efaf3a`.
The cumulative patch was applied exactly once to base
`a87449652de29e7985dd3e4bcf8406794d6f8169` on branch
`codex/filter-integrity-local-20261022`, in a separate task-local worktree.
The main checkout's untracked glossary/research/prototype edits and all existing
worktrees were preserved. No push, deployment, training, paid API, or settings
change was performed.

The cloud changes independently passed the actual local test commands: 12 Node
and 27 Python tests. After two local hardening changes, 12 Node and 28 Python
tests pass, plus Python compilation, Node syntax checks, and `git diff --check`.
The tests exercise real browser/trainer/report control flow using deterministic
fake models; they establish software behavior, not filtering quality.

Reviewed claims: incomplete prediction populations fail instead of zip truncation;
each comparator is re-tokenized after loading; unknown splits and ordinary-run
holdouts cannot reach browser inference; malformed batches append no rows;
source hashes, row metadata, labels, binary scores and opposite pairs are checked;
keep/hide and reversed A/B polarity are tested; empty report slices are named and
hardcoded improvement claims removed.

Two further issues were corrected locally:

- The installed Laya `items_from_rows` prioritizes `gold` over `expected`.
  The audit previously verified only `expected`, so a gold override could silently
  change training labels. The contract now rejects gold overrides, extra question
  targets and extra expected labels. A regression test exercises this boundary.
- The report still asserted initialization from a pinned upstream model.
  It now attributes initialization to the recorded plan and explicitly flags absent
  checkpoint fingerprints/runtime versions. A report-flow regression test covers
  old results without this provenance.

## Actual local artifact checks

The existing experiment is `local-results/finetune-format-robust` in the original
model-evaluation worktree. Its raw dataset and saved results both pass the final
`evaluation_contract.py` audit. No input was modified to achieve a pass.

| Split | Instruction/post rows | Distinct posts | Keep labels | Hide labels |
|---|---:|---:|---:|---:|
| Train | 1,706 | 195 | 864 | 842 |
| Validation | 512 | 20 | 258 | 254 |
| Test | 1,755 | 47 | 999 | 756 |

All three saved model populations contain the same 1,755 test rows. Dataset
hashes agree, probabilities match binary logits, and source metadata/labels agree.
The requested `--require-family novel_combination` check correctly fails:
`test: required family novel_combination is empty`.

The updated report was also executed against a private local copy of the actual
data and results. The source experiment was not overwritten. Only aggregate
statistics are included here; the generated individual-error report stays local.

## What the saved results say

These are recalculations of historical scores, not new model inference or proof
of generalization. At the unchanged 0.5 hide threshold:

| Recorded stage | Overall correct / 1,755 | Wanted retained / 999 | Unwanted hidden / 756 | Opposite pairs both correct / 45 |
|---|---:|---:|---:|---:|
| Base | 935 | 674 | 261 | 11 |
| Previous | 1,179 | 571 | 608 | 1 |
| New | 1,169 | 812 | 357 | 41 |

The new model trades more retention for less removal relative to the previous
model. On the original four-rule instruction it retains 54/54 wanted pairs but
hides only 4/78 unwanted pairs. That is not evidence of a broadly solved filter.
The natural-feed subset has only 15 distinct posts (539 correlated rows); all test
rows together cover 47 posts. No novel-combination result exists.

## Methodological blockers and next tranche

Base, previous and new checkpoint directories exist locally (about 647 MB each),
as does the Laya environment. However, the historical results contain neither
checkpoint fingerprints nor runtime versions. Local config identifies the
encoder architecture but does not prove the claimed upstream revision or which
weight bytes produced the saved scores. Fingerprinting current weights would
not retroactively establish that history.

Labels are earlier assistant judgments and authored-case logic, not independently
adjudicated user ground truth. The current integrity audit cannot prove semantic
label truth, near-duplicate separation, historical test freshness, or the recorded
training-before-test ordering. Prior test results have already informed development.
Consequently no fresh quality comparison was run: the requested prerequisites of
independent labels and verified provenance are not established. No GPU was used;
the completed checks are small CPU operations.

The highest-value next tranche is to verify current local checkpoint provenance,
freeze a small newly adjudicated post-level acceptance set with both classes and
nonempty novel-combination coverage, then perform one bounded offline CPU replay
of base/previous/new with recorded fingerprints, runtime versions and fixed
thresholds. Coordinate with the parent before sustained memory/GPU work. Keep all
raw posts, labels, identifiers, per-row scores and model weights local; export
only aggregate outcomes and methodological limitations.
