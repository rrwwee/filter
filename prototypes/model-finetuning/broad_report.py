import collections,json,pathlib
root=pathlib.Path(__file__).resolve().parents[2]/'local-results/finetune-broad'
r=json.loads((root/'results.json').read_text());r['stages']['head_only']=r['stages'].pop('tuned')
full=json.loads((root/'full-results.json').read_text()) if (root/'full-results.json').exists() else None
if full:r['stages']['full_balanced']=full['stages']
manifest=json.loads((root/'manifest.json').read_text())
def metrics(rows):
 n=len(rows);w=[x for x in rows if not x['expected_hide']];u=[x for x in rows if x['expected_hide']]
 correct=sum((x['p_hide']>=.5)==x['expected_hide'] for x in rows)
 auc=sum((a['p_hide']<b['p_hide'])+.5*(a['p_hide']==b['p_hide']) for a in w for b in u)/(len(w)*len(u)) if w and u else None
 return f'{correct}/{n} ({correct/n:.1%})',f'{sum(x["p_hide"]<.5 for x in w)}/{len(w)}',f'{sum(x["p_hide"]>=.5 for x in u)}/{len(u)}',f'{auc:.3f}' if auc is not None else 'n/a'
lines=['# Broad filtering-instruction experiment','','Fine-tuning of the original pinned Laya multilingual checkpoint: an initial head-only run and, when available, a corrective full-model run with balanced labels and opposing training instructions. Neither run uses a previous fine-tuned checkpoint. User instructions are rendered verbatim inside the fixed question wrapper.','','Labels are assistant-authored synthetic content annotations or previous assistant feed judgments, not user-confirmed ground truth. Repeated instruction variants are correlated observations, not independent posts. This is a diagnostic of broader instruction following, not production validation.','','## Dataset','']
for split,c in manifest['counts'].items():lines.append(f'- {split}: {c["rows"]} instruction/post pairs across {c["posts"]} posts; {c["hide"]} hide labels.')
lines+=['','Post text is disjoint across splits. The prior 16 real-feed test posts remain held out. Training uses bullets, paragraphs, and numbered instructions. Test adds conversational phrasing and checklists, unseen criterion combinations, and two criteria absent from training (politics and sports). Synthetic topic families occur across splits, so this is not an independent natural-feed sample.','','## Results at the unchanged 0.5 threshold','','| Slice | Model | Correct | Wanted retained | Unwanted hidden | AUC |','|---|---|---:|---:|---:|---:|']
for label,predicate in [('All test pairs',lambda x:True),('Real feed',lambda x:x['origin']=='real-feed'),('Authored synthetic',lambda x:x['origin']=='authored-synthetic')]+[(s,lambda x,s=s:x['suite']==s) for s in ['heldout_posts','format_pair','unseen_wording','unseen_combinations','unseen_criteria','counterfactual']]:
 for stage,sets in r['stages'].items():
  rows=[x for x in sets['test']['rows'] if predicate(x)]
  if rows:lines.append('| '+' | '.join([label,stage,*metrics(rows)])+' |')
test_rows=r['stages']['base']['test']['rows']
keep_baseline=sum(not x['expected_hide'] for x in test_rows)/len(test_rows)
lines+=['',f'Always keeping every test post yields {keep_baseline:.1%} accuracy. The head-only result is a collapse toward that baseline, not a useful filtering improvement; it hides zero unwanted test posts at 0.5.']
lines+=['','## Paired instruction checks','','| Model | Bullet/paragraph agreement | Bullet/unseen-wording agreement | Opposing instructions both correct |','|---|---:|---:|---:|']
for stage,sets in r['stages'].items():
 groups=collections.defaultdict(dict);counter=collections.defaultdict(list)
 for row in sets['test']['rows']:
  if row['suite']=='counterfactual':counter[row['post_id']].append(row)
  elif row['suite'] in ['heldout_posts','format_pair','unseen_wording']:groups[row['post_id'],row['policy_id']][row['style']]=row
 def agreement(styles):
  pairs=[(g['bullets'],g[s]) for g in groups.values() for s in styles if 'bullets'in g and s in g]
  return f'{sum((a["p_hide"]>=.5)==(b["p_hide"]>=.5) for a,b in pairs)}/{len(pairs)}'
 pairs=list(counter.values());ok=sum(len(p)==2 and all((x['p_hide']>=.5)==x['expected_hide'] for x in p) for p in pairs)
 lines.append(f'| {stage} | {agreement(["paragraph"])} | {agreement(["conversational","checklist"])} | {ok}/{len(pairs)} |')
lines+=['','## By filtering policy','','These rows combine wording variants, so observations are correlated.','','| Policy | Base accuracy | Latest trained model accuracy |','|---|---:|---:|']
base=r['stages']['base']['test']['rows'];tuned=r['stages']['full_balanced' if full else 'head_only']['test']['rows']
for policy in sorted({x['policy_id'] for x in base}):
 lines.append('| '+policy+' | '+metrics([x for x in base if x['policy_id']==policy])[0]+' | '+metrics([x for x in tuned if x['policy_id']==policy])[0]+' |')
lines+=['','Agreement alone is not correctness: two equivalent wordings can make the same wrong decision. The opposing-instruction metric requires both decisions to be correct.','','## Training and artifacts','',f'Selected epoch {r["training"]["selected_epoch"]} by lowest validation cross-entropy (including the original base as epoch zero), from {r["training"]["epochs_run"]} epochs. Training took {r["training"]["seconds"]:.1f} seconds. Temperatures remained 1; no calibration or threshold fitting. Saved-checkpoint reload preserved every test decision, maximum probability difference {r["reload_max_p_hide_delta"]:.6f}.','','The local directory contains the split JSONL files, manifest, authored and captured post metadata, raw logits and probabilities, training log, results, and checkpoint. No outputs or feed text were published.']
if full:
 lines+=['','## Corrective full-model run','',f'Balanced training: {full["training_rows"]} pairs, equal keep and hide counts, including paired opposite instructions. Selected epoch {full["training"]["selected_epoch"]} from {full["training"]["epochs_run"]}, using balanced validation cross-entropy. Training took {full["training"]["seconds"]:.1f} seconds. Metrics are from the reloaded selected checkpoint.','',full['test_note'],'','This changes both data sampling and trainable parameters, so it cannot isolate which change caused a performance difference.']
if full:
 lines+=['','## Interpretation','','The corrective run improves single-rule classification and robustness to wording on this diagnostic dataset. It does not establish reliable general instruction following: unseen combinations remain weak, and no opposing-instruction pair has both decisions correct. The original four-rule combined filter also remains below a useful acceptance level. Formatting agreement cannot compensate for these semantic failures.','','Next evaluation should use a fresh held-out set. The next training-data changes should emphasize matched positive/negative examples for keep-only instructions and varied combinations/exceptions, with balanced validation slices for these behaviors.']
(root/'report.md').write_text('\n'.join(lines)+'\n');print('\n'.join(lines))
