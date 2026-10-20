# Local promotion-filter fine-tuning experiment

This is a disposable experiment, not a production training pipeline. All examples, outputs, logs, dependencies, and model checkpoints remain in ignored `local-results/finetune-promotions/` and `local-results/training-env/`. Do not publish these files.

The fixed instruction is the user's original `Hide promotions or ads` bullet, followed by `Should this post be hidden?`. True means hide. The initial checkpoint is `convaiinnovations/laya-multilingual` at revision `052592a15d198d9ad47da779604259b10b47b7aa`, matching the earlier browser evaluation. Runtime: Laya 0.4.12.

The independent split manifest is `plan.json`: 16 deliberately memorized examples (8 keep / 8 hide); a broader 60-example training set including those 16; 10 validation examples; 16 real-feed test examples. The test has 10 keep / 6 hide labels and contains commercial brands held out of training, including both retained Starlink variants. Labels are the earlier assistant judgments, not newly generated training-time labels or user-confirmed truth.

The script uses the upstream `train_model` implementation with supervised cross-entropy and a frozen encoder. It trains about 15 million decision-head parameters, not LoRA adapters. The overfit stage stops after 100% training accuracy and cross-entropy below 0.03, checked every five epochs, with a maximum of 100 epochs. The broader stage runs up to 40 epochs and selects by validation cross-entropy, not test results. No temperature calibration is fitted on these small sets. Full checkpoints are saved, and the final checkpoint is reloaded to check that saved predictions agree.

With the private datasets and base checkpoint already present, run from the worktree root:

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
  local-results/training-env/bin/python -u prototypes/model-finetuning/promotions_experiment.py
```

On macOS, the process needs access to MPS; a sandbox can hide the device. The experiment also supports CPU, but CPU timing is not comparable. Training does not require or use a hosted inference API.

A successful memorization test establishes that the model, loss, labels, gradients, optimizer and saved artifact work together. It does not establish useful feed filtering, calibration, or generalization to arbitrary filtering instructions. Inspect the held-out per-class counts and the saved per-post logits/probabilities rather than relying on aggregate accuracy alone.

`promotions_full_control.py` compares a full-weight fine-tune starting from the original base on exactly the same broad train/validation/test split. It was added after the head-only validation loss worsened, before inspecting its final test result. It uses 20 epochs maximum, micro-batch 1, gradient accumulation 4, encoder learning rate 1e-5, head learning rate 5e-5, and gradient checkpointing. The lowest validation cross-entropy checkpoint is saved; five unsuccessful validation checks after at least ten epochs stop the run. This control updates about 322M parameters and does not use LoRA.

Run `python3 prototypes/model-finetuning/report.py` to generate the private Markdown report from the saved JSON outputs. Raw logits and probabilities are retained for all evaluated splits. Neither training path fits calibration temperatures on these tiny datasets.
