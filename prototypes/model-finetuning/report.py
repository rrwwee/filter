import json,pathlib
root=pathlib.Path(__file__).resolve().parents[2]/'local-results/finetune-promotions'
r=json.load(open(root/'results.json'))
full=json.load(open(root/'full-results.json')) if (root/'full-results.json').exists() else None
stages=[('Base checkpoint',r['stages']['base']),('16-example overfit',r['stages']['overfit']),('Broader, head only',r['stages']['broader'])]
if full:stages.append(('Broader, full model',full['stages']))
def correct(x):
 m=x['metrics'];return f"{round(m['accuracy']*m['items'])}/{m['items']}"
def purity(x):
 m=x['metrics']; unwanted=m['unwanted']-m['hidden_unwanted'];kept=m['kept_wanted']+unwanted
 return f'{unwanted}/{kept} ({unwanted/kept:.1%})' if kept else 'undefined (no posts kept)'
def auc(x):
 rows=x['rows'];wanted=[r['p_keep'] for r in rows if not r['expected_hide']];unwanted=[r['p_keep'] for r in rows if r['expected_hide']]
 return sum((a>b)+.5*(a==b) for a in wanted for b in unwanted)/(len(wanted)*len(unwanted))
lines=['# Promotion-filter fine-tuning experiment','','Local experiment on the exact instruction `Hide promotions or ads`. Prompt, checkpoint architecture, and label meanings were kept fixed. The initial model is Laya multilingual, revision `052592a15d198d9ad47da779604259b10b47b7aa`; runtime Laya 0.4.12 on Apple MPS.','','## Deliberate memorization','','The model trained only its approximately 15M decision-head parameters on 16 balanced examples; the approximately 307M encoder parameters stayed frozen.','','| Checkpoint | Correct on the same 16 training examples | Cross-entropy |','|---|---:|---:|']
for name,sets in stages[:3]:
 x=sets['overfit'];lines.append(f"| {name} | {correct(x)} | {x['metrics']['loss']:.4f} |")
lines+=['',f"The overfit stage selected epoch {r['overfit_training']['epochs']} and took {r['overfit_training']['seconds']:.1f} seconds of training. It is a memorization check, not evidence of generalization.",'','## Broader distribution','','60 training examples, 10 validation examples, and 16 real-feed test examples. The tiny overfit examples are a subset of the broader training data. The test set has 10 keep / 6 hide judgments and was excluded from training and checkpoint selection. Checkpoints were selected by validation cross-entropy; test results did not control training. All labels are prior assistant judgments, not user-confirmed ground truth.','','| Checkpoint | Broad train | Validation | Test | Test wanted retained | Test unwanted hidden | Unwanted share of visible test posts | Test ranking AUC |','|---|---:|---:|---:|---:|---:|---:|---:|']
for name,sets in stages:
 m=sets['test']['metrics'];lines.append(f"| {name} | {correct(sets['train'])} | {correct(sets['validation'])} | {correct(sets['test'])} | {m['kept_wanted']}/{m['wanted']} | {m['hidden_unwanted']}/{m['unwanted']} | {purity(sets['test'])} | {auc(sets['test']):.3f} |")
lines+=['','All decisions use the default 0.5 probability boundary. Temperatures remain 1; no calibration was fitted. This small test is for comparing this experiment, not production acceptance or arbitrary instruction following.','','## Artifact verification','',f"The head-only saved checkpoint was reloaded; its test decisions were unchanged. Maximum probability change from fp16 serialization: {r['reload_max_p_hide_delta']:.6f}. The starting Python and browser models agree on all 86 distinct cases, with maximum probability difference about 0.00005."]
if full:lines += ['',f"Full-model control selected epoch {full['selected_epoch']} from {full['epochs_run']} epochs and took {full['seconds']:.1f} seconds of training. Its reported results are from reloading the saved checkpoint."]
lines+=['','## Result','','The memorization check passed. The small broader-data experiment did not show an improvement on the fixed test split: head-only training worsened its accuracy and ranking, while full-weight training matched the base accuracy and AUC with a different keep/hide tradeoff. This does not establish that larger, better-covered training data would fail, nor that the model generalizes to other filtering instructions.','','Laya 0.4.12 documents full fine-tuning by default and an optional frozen-encoder head-only path; its built-in training configuration does not expose LoRA. See https://github.com/NandhaKishorM/laya/blob/main/docs/finetune.md and https://github.com/NandhaKishorM/laya/blob/main/laya/train.py.','','Saved locally: `results.json`, `full-results.json`, `model-outputs.jsonl`, `training.log`, `full-training.log`, `plan.json`, `requirements.lock`, and the `overfit-checkpoint/`, `broader-checkpoint/`, `full-checkpoint/` directories. Nothing was uploaded.']
(root/'report.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
