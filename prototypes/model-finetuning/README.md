# Local promotion-filter fine-tuning experiment

This is a disposable experiment, not a production training pipeline. All examples, outputs, logs, dependencies, and model checkpoints remain in ignored `local-results/finetune-promotions/` and `local-results/training-env/`. Do not publish these files.

The fixed instruction is the user's original `Hide promotions or ads` bullet, followed by `Should this post be hidden?`. True means hide. The initial checkpoint is `convaiinnovations/laya-multilingual` at revision `052592a15d198d9ad47da779604259b10b47b7aa`, matching the earlier browser evaluation. Runtime: Laya 0.4.12.

The independent split manifest is `plan.json`: 16 deliberately memorized examples (8 keep / 8 hide); a broader 60-example training set including those 16; 10 validation examples; 16 real-feed test examples. The test has 10 keep / 6 hide labels and contains commercial brands held out of training, including both retained Starlink variants. Labels are the earlier assistant judgments, not newly generated training-time labels or user-confirmed truth.

The script uses the upstream `train_model` implementation with supervised cross-entropy and a frozen encoder. It trains about 15 million decision-head parameters, not LoRA adapters. The overfit stage stops after 100% training accuracy and cross-entropy below 0.03, checked every five epochs, with a maximum of 100 epochs. The broader stage restarts from the original base checkpoint with a fresh optimizer; it does not continue the deliberately overfitted weights. It runs up to 40 epochs and selects by validation cross-entropy, not test results. No temperature calibration is fitted on these small sets. Full checkpoints are saved, and the final checkpoint is reloaded to check that saved predictions agree.

With the private datasets and base checkpoint already present, run from the worktree root:

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
  local-results/training-env/bin/python -u prototypes/model-finetuning/promotions_experiment.py
```

On macOS, the process needs access to MPS; a sandbox can hide the device. The experiment also supports CPU, but CPU timing is not comparable. Training does not require or use a hosted inference API.

A successful memorization test establishes that the model, loss, labels, gradients, optimizer and saved artifact work together. It does not establish useful feed filtering, calibration, or generalization to arbitrary filtering instructions. Inspect the held-out per-class counts and the saved per-post logits/probabilities rather than relying on aggregate accuracy alone.

`promotions_full_control.py` compares a full-weight fine-tune starting from the original base on exactly the same broad train/validation/test split. It was added after the head-only validation loss worsened, before inspecting its final test result. It uses 20 epochs maximum, micro-batch 1, gradient accumulation 4, encoder learning rate 1e-5, head learning rate 5e-5, and gradient checkpointing. The lowest validation cross-entropy checkpoint is saved; five unsuccessful validation checks after at least ten epochs stop the run. This control updates about 322M parameters and does not use LoRA.

Run `python3 prototypes/model-finetuning/report.py` to generate the private Markdown report from the saved JSON outputs. Raw logits and probabilities are retained for all evaluated splits. Neither training path fits calibration temperatures on these tiny datasets.

## Broad instruction experiment

`build_broad_dataset.py` creates a new local dataset using existing four-rule feed annotations and explicitly authored synthetic scenarios. It expands instructions across criteria, keep-only vs hide semantics, combinations, bullets, paragraphs, and numbered lists. Posts are split before expansion; ambiguous or unannotated real-feed decisions are excluded. Prior promotion test posts remain held out. Test suites add unseen phrasing, unseen combinations, entirely untrained politics/sports criteria, and opposing-instruction pairs. Counts of expanded rows must not be treated as independent post counts.

`broad_experiment.py` starts from the original pinned base, freezes the encoder, trains the decision head, and selects by validation cross-entropy including the base as epoch zero. It saves raw outputs and reload-checks the selected checkpoint. `broad_report.py` reports per-suite and real/synthetic metrics plus paired formatting and instruction checks.

```sh
python3 prototypes/model-finetuning/build_broad_dataset.py
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
  local-results/training-env/bin/python -u prototypes/model-finetuning/broad_experiment.py
python3 prototypes/model-finetuning/broad_report.py
```

All broad experiment data and artifacts stay in ignored `local-results/finetune-broad/`. Synthetic examples and source code are distinct from captured feed text.

The first broader head-only run collapsed toward keeping everything. `broad_full_control.py` is a corrective experiment: balance keep/hide labels, add opposite-instruction pairs using training posts only, restart the original base, and train all parameters. It selects by validation loss averaged equally over the two classes. Because this changes sampling and trainable parameters together, it is not a controlled ablation. The reused test is diagnostic, not an untouched final benchmark.

## Compositional follow-up with fresh holdout

`build_compositional.py` creates the next independent split in `local-results/finetune-compositional/`. It may use prior experiment posts for training. All validation and test posts are new; test includes freshly captured For You posts, with exact and near-overlaps against the old feed removed, plus explicitly authored edge cases. Rules cover opposite instructions, any/all logic, exceptions, overriding exclusions, the original four-rule instruction, and no filtering. Individual policies are sampled across both labels where the data permits, and explicit same-post opposite pairs are included. The manifest records hashes and sampling availability.

`compositional_experiment.py` starts from the original pinned base and trains all parameters. It uses 0.05 label smoothing. Validation selection equally weights macro family-balanced accuracy and both-correct opposite-pair accuracy, with log loss as tie breaker. Test inference is deferred until the checkpoint is selected, then runs the new, original, and previous full checkpoints on exactly the same inputs. A gentle operating threshold is selected from validation only. No automatic prompt translation or strictness-dependent prompting is introduced.

```sh
python3 prototypes/model-finetuning/build_compositional.py
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
  local-results/training-env/bin/python -u prototypes/model-finetuning/compositional_experiment.py
python3 prototypes/model-finetuning/compositional_report.py
```

Do not rebuild the dataset during or after a run being compared: its hashes are part of the experiment. Captured feed snapshots and annotations, all datasets, checkpoints, outputs, reports, and error examples remain local and ignored. `compositional_report.py` generates the comparison report and a local error-inspection document.

### Crossed-format correction

The first compositional run exposed a design confound: each training wording variant always used one layout. Its fresh test is preserved as a failed diagnostic. `build_format_robust.py` fixes this by crossing wording with bullet and paragraph layouts, including explicit if/otherwise instructions. It uses a second newly captured/authored final holdout, checked against both the old training corpus and the first fresh test. The latter never enters this training set.

Run the shared trainer with `--directory finetune-format-robust --epochs 3 --micro-batch 4 --seed 20261023`, and the shared reporter with `--directory finetune-format-robust`. Both runs start from the original base. The data, final model, outputs, and reports remain under ignored local-results directories.

## Public evidence check (no weights or private data required)

From a fresh checkout, using Python 3's standard library only:

```sh
python3 prototypes/model-finetuning/audit_public_evidence.py
python3 -m unittest discover -s tests -v
```

The first command prints a deterministic JSON audit of the committed
`measurements/fine-tuning-aggregate.json`. It checks count bounds, per-model slice
population consistency, accuracy, and the unwanted fraction of visible pairs.
It exits nonzero for inconsistent arithmetic or invalid input. Empty slices are
warnings, not silently omitted or scored as successful. Rates with absent class
denominators are reported as null. The `records` output lists expanded pairs
and distinct posts separately; slices overlap and must not be summed.

On the committed final aggregate, 33 populated model/slice records pass these
arithmetic checks, but `New combinations` is empty. Therefore the final aggregate
does not support a novel-combinations result. The overall final set has 1,755
expanded pairs from only 47 posts, including 15 real-feed posts. Neither pair
counts nor distinct-post counts alone establish independent sampling. The
paraphrased-instruction slice uses a wording family present during training;
it is not an unseen-wording evaluation.

`tests/fixtures/synthetic-evidence.json` contains invented counts solely to test
the audit software. It is not a new dataset, model run, or replication of the
published experiment. The committed aggregate regression test protects the
current evidence interpretation; intentionally changing the published results
requires reviewing and updating those expectations.

This check does not reproduce AUC, raw predictions, uncertainty estimates,
split separation, label validity, model provenance, or training. Those require
private artifacts not included here. It does not choose a model or production
threshold. A passing audit means internally consistent published counts, not a
successful filter or an independently reproduced experiment.
