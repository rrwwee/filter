import argparse,collections,json,pathlib,math

parser=argparse.ArgumentParser();parser.add_argument('--directory',default='finetune-compositional');args=parser.parse_args()
ROOT=pathlib.Path(__file__).resolve().parents[2]/'local-results'/args.directory
r=json.loads((ROOT/'results.json').read_text());manifest=json.loads((ROOT/'manifest.json').read_text())
src={x['id']:x for x in map(json.loads,(ROOT/'test.jsonl').read_text().splitlines())}

def summary(rows,t=.5):
 w=[x for x in rows if not x['expected_hide']];u=[x for x in rows if x['expected_hide']]
 keep=sum(x['p_hide']<t for x in w);hide=sum(x['p_hide']>=t for x in u);n=len(rows)
 auc=sum((a['p_hide']<b['p_hide'])+.5*(a['p_hide']==b['p_hide']) for a in w for b in u)/(len(w)*len(u)) if w and u else None
 visible=keep+len(u)-hide
 return {'n':n,'posts':len({x['post_id'] for x in rows}),'accuracy':(keep+hide)/n,'wanted':len(w),'wanted_kept':keep,'unwanted':len(u),'unwanted_hidden':hide,'auc':auc,'unwanted_fraction_visible':(len(u)-hide)/visible if visible else None}

def pairs(rows):
 g=collections.defaultdict(list)
 for x in rows:
  if x['pair_id']:g[x['pair_id']].append(x)
 return {'correct':sum(len(xs)==2 and all((x['p_hide']>=.5)==x['expected_hide'] for x in xs) for xs in g.values()),'total':len(g),'ordered':sum(next(x['p_hide'] for x in xs if x['expected_hide'])>next(x['p_hide'] for x in xs if not x['expected_hide']) for xs in g.values())}

def agreement(rows,other):
 g=collections.defaultdict(dict)
 for x in rows:
  if x['suite']=='opposite_pair':continue
  g[x['post_id'],x['policy_id']][x['style']]=x
 ps=[(v['bullets'],v[other]) for v in g.values() if 'bullets' in v and other in v]
 return sum((a['p_hide']>=.5)==(b['p_hide']>=.5) for a,b in ps),len(ps)

names={'base':'Original','previous':'Previous full fine-tune','new':'New compositional fine-tune'}
slices={'All fresh test pairs':lambda x:True,'Fresh real feed':lambda x:x['origin']=='fresh-real-feed','Authored edge cases':lambda x:x['origin']=='authored-synthetic','Combinations':lambda x:x['family']=='combination','Both conditions required':lambda x:x['family']=='conjunction','Exceptions':lambda x:x['family']=='exception','Explicit overriding exclusions':lambda x:x['family']=='override','New combinations':lambda x:x['family']=='novel_combination','Original four-rule instruction':lambda x:x['policy_id']=='original_four','Bullet lists':lambda x:x['style']=='bullets','Paragraphs':lambda x:x['style']=='paragraph' and not x['pair_id'],'Paraphrased instructions':lambda x:x['style']=='casual'}
aggregate={};lines=['# Compositional filtering: fresh held-out evaluation','','The new full-model run starts from the original pinned Laya multilingual checkpoint. The previous fine-tune is only an evaluation comparator. Training emphasizes opposite instructions, combinations, conjunctions, exceptions, and exclusions that override an allowed topic.','','## Data and isolation','']
for split,c in manifest['counts'].items():lines.append(f'- {split}: {c["rows"]} instruction/post pairs across {c["posts"]} posts; {c["hide"]} hide labels.')
lines+=['','The fresh test includes newly authored cases and new For You feed captures. Overlapping posts from all earlier experiments were excluded; details are in the manifest. Earlier experiment posts may be used for training, but no validation or test post text occurs in training. All labels are assistant judgments, not user-confirmed ground truth. Media-only ambiguity is excluded for affected criteria. Synthetic results are not evidence of natural-feed prevalence. Repeated instructions per post are correlated observations.','','Dataset SHA-256 hashes are recorded in `manifest.json` and verified before and after training. No test inference occurred until checkpoint selection was complete. Neither model selection nor the gentle threshold uses the fresh test.','','## Results at the unchanged 0.5 hide-score threshold','','| Slice | Model | Accuracy | Wanted retained | Unwanted hidden | Ranking AUC |','|---|---|---:|---:|---:|---:|']
for slice_name,pred in slices.items():
 aggregate[slice_name]={}
 for model in ['base','previous','new']:
  selected=[x for x in r['stages'][model]['rows'] if pred(x)]
  if not selected:continue
  s=summary(selected);aggregate[slice_name][model]=s
  lines.append(f'| {slice_name} | {names[model]} | {s["accuracy"]:.1%} | {s["wanted_kept"]}/{s["wanted"]} | {s["unwanted_hidden"]}/{s["unwanted"]} | '+(f'{s["auc"]:.3f}' if s['auc'] is not None else 'n/a')+' |')
lines+=['','## Instruction and formatting checks','','Both decisions must be right for an opposite pair to pass. Score ordering is also reported so a threshold shift is distinguishable from failure to follow the instruction. Formatting agreement can include two matching wrong answers; interpret it alongside accuracy.','','| Model | Opposite pairs both correct | Opposite scores correctly ordered | Bullet/paragraph agreement | Bullet/new-wording agreement |','|---|---:|---:|---:|---:|']
pair_metrics={}
for model in ['base','previous','new']:
 rows=r['stages'][model]['rows'];p=pairs(rows);pair_metrics[model]=p;a,b=agreement(rows,'paragraph');c,d=agreement(rows,'casual')
 lines.append(f'| {names[model]} | {p["correct"]}/{p["total"]} | {p["ordered"]}/{p["total"]} | {a}/{b} | {c}/{d} |')
operating_points={"Default":.5}
wanted_validation=[x['p_hide'] for x in r['validation']['rows'] if not x['expected_hide']]
for target in [.95,.85,.70]:
 candidates=sorted(set([0.,1.000001]+[math.nextafter(x,math.inf) for x in wanted_validation]))
 operating_points[f"{target:.0%} validation retention"]=next(t for t in candidates if sum(x<t for x in wanted_validation)/len(wanted_validation)>=target)
operating_results={}
lines+=['','## Retention/removal tradeoffs','','These thresholds are chosen using validation only, targeting several retention levels. Neither complete blocking nor zero false positives is required. Actual fresh-test outcomes are reported below; validation targets are not guarantees. Strictness changes only the threshold, never model inputs. No temperature calibration is fitted.','','| Setting | Test slice | Keep threshold | Wanted retained | Unwanted hidden | Unwanted share of visible pairs |','|---|---|---:|---:|---:|---:|']
for setting,t in operating_points.items():
 operating_results[setting]={}
 for label,pred in [('All fresh test pairs',lambda x:True),('Fresh real feed',lambda x:x['origin']=='fresh-real-feed')]:
  s=summary([x for x in r['stages']['new']['rows'] if pred(x)],t);q=s['unwanted_fraction_visible'];operating_results[setting][label]=s
  lines.append(f'| {setting} | {label} | {1-t:.4f} | {s["wanted_kept"]}/{s["wanted"]} | {s["unwanted_hidden"]}/{s["unwanted"]} | '+(f'{q:.1%}' if q is not None else 'n/a')+' |')
lines+=['','## Training and limitations','',f'Selected epoch {r["selected_epoch"]} from {r["epochs_run"]}. Training time: {r["training_seconds"]:.1f} seconds. Selection gives equal weight to validation macro family-balanced accuracy and opposite-pair accuracy; ties prefer lower log loss. Label smoothing is 0.05. The reloaded checkpoint preserved every validation decision (max probability difference {r["reload_validation_max_delta"]:.6f}).','','Full history, settings, dataset hashes, uncalibrated raw logits/probabilities, and the checkpoint remain local. The change combines data, sampling, regularization, and model-selection changes; it does not isolate their individual effects. These are small post-level test sets, despite the larger number of instruction pairs.','']
a=aggregate['All fresh test pairs'];core=aggregate['Original four-rule instruction']['new']
lines+=['','## Interpretation','',f"Overall accuracy is {a['new']['accuracy']:.1%} for the new model versus {a['previous']['accuracy']:.1%} for the previous model; aggregate ranking AUC is {a['new']['auc']:.3f} versus {a['previous']['auc']:.3f}. The new model improves opposite-instruction behavior, but it is not an unqualified improvement in filtering quality.",'',f"The original four-rule combined instruction remains weak: the new model keeps {core['wanted_kept']}/{core['wanted']} wanted pairs but hides only {core['unwanted_hidden']}/{core['unwanted']} unwanted pairs at the default threshold. This should not be hidden by better single-rule results.",'','The retention/removal table shows useful imperfect operating choices. Counts expand a small set of posts under multiple instructions, so they should not be interpreted as independent natural-feed observations.']
(ROOT/'report.md').write_text('\n'.join(lines)+'\n')
(ROOT/'summary.json').write_text(json.dumps({'slices':aggregate,'pairs':pair_metrics,'selected_epoch':r['selected_epoch'],'gentle_keep_threshold':1-r['gentle_p_hide_threshold'],'operating_points':operating_results},indent=2))
# Local, inspectable failure cases; deliberately not published.
errors=[x for x in r['stages']['new']['rows'] if (x['p_hide']>=.5)!=x['expected_hide']]
errors.sort(key=lambda x: x['p_hide'] if not x['expected_hide'] else 1-x['p_hide'],reverse=True)
errlines=['# Selected errors from the new model','','Assistant labels may themselves be debatable; inspect the exact text and instruction.']
seen=set()
for x in errors:
 if x['post_id'] in seen:continue
 seen.add(x['post_id']);s=src[x['id']]
 errlines += ['',f'## {x["post_id"]} — {x["policy_id"]}','',f'Expected: {"hide" if x["expected_hide"] else "keep"}; P(hide): {x["p_hide"]:.4f}.','','Instruction:','','```text',s['instruction'],'```','','Post:','','```text',s['state'],'```']
 if len(seen)>=20:break
(ROOT/'errors.md').write_text('\n'.join(errlines)+'\n')
print(json.dumps({'slices':aggregate,'pairs':pair_metrics,'selected_epoch':r['selected_epoch']},indent=2))
