"""Diagnostic only: identical held-out posts, literal rules, explicit OR aggregation."""
import collections,itertools,json,pathlib,random,time
import numpy as np
import torch
from laya.train import load_checkpoint,items_from_rows,calibration_records
from build_format_robust import FINAL
from build_compositional import TAGS,evaluate

ROOT=pathlib.Path(__file__).resolve().parents[2]/'local-results/finetune-format-robust'
OUT=ROOT/'rule-probe';OUT.mkdir(exist_ok=True)
RULES=['Hide promotions or ads','Hide dating stories','Hide clickbait (posts that require you to click before they get to the point)',"Hide things unrelated to tech unless they're funny"]
FLAG_KEYS=['ad','dating','clickbait','offtopic']
posts={}
for r in map(json.loads,(ROOT/'test.jsonl').read_text().splitlines()):posts.setdefault(r['post_id'],{'id':r['post_id'],'text':r['state'],'origin':r['origin']})
for i,line in enumerate(FINAL.strip().splitlines()):
 tags,_=line.split('|',1);f={t:t in tags.split() for t in TAGS};f['offtopic']=not(f['tech'] or f['funny'])
 if f'final-authored-{i:02}' in posts:posts[f'final-authored-{i:02}']['flags']=f
for p in json.loads((ROOT/'fresh-feed-labeled.json').read_text()):
 if p['id'] in posts:
  f=p['flags'];f['offtopic']=evaluate(['not',['or','tech','funny']],f);posts[p['id']]['flags']=f
assert all('flags' in p for p in posts.values())

torch.set_num_threads(4);device=torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
t=time.perf_counter();model,tok,cfg=load_checkpoint(str(ROOT/'checkpoint'));model.to(device);model.eval();load_seconds=time.perf_counter()-t
def row(p,rules):
 return {'state':p['text'],'questions':{'hide':{'type':'noul','instructions':'Filtering rules:\n'+'\n'.join('- '+x for x in rules)+'\n\nShould this post be hidden?','criteria':{'false':'Keep the post visible.','true':'Hide the post.'}}},'expected':{'hide':False}}
def infer(rows,batch_size=4):
 items,skipped=items_from_rows(tok,rows,cfg['max_len'],cfg['head_max_len']);assert not skipped
 records=calibration_records(model,tok,items,device,cfg['max_len'],cfg['head_max_len'],batch_size=batch_size)
 result=[]
 for _,z,_,_ in records:
  z=np.asarray(z,dtype=float);p=np.exp(z-z.max());p/=p.sum();result.append({'p_hide':float(p[1]),'logits':z.tolist()})
 return result
variants={f'mask-{mask:02d}':[RULES[i] for i in range(4) if mask&(1<<i)] for mask in range(1,16)}
variants['reverse']=list(reversed(RULES))
for shift in range(1,4):variants[f'rotate-{shift}']=RULES[shift:]+RULES[:shift]
jobs=[(p,name) for p in posts.values() for name in variants]
preds=infer([row(p,variants[name]) for p,name in jobs]);outputs=collections.defaultdict(dict)
for (p,name),v in zip(jobs,preds):outputs[p['id']][name]=v

def or_label(vals):return True if True in vals else None if None in vals else False
def summary(rows,score_key):
 rs=[r for r in rows if r['expected_hide'] is not None];w=[r for r in rs if not r['expected_hide']];u=[r for r in rs if r['expected_hide']]
 kept=sum(r[score_key]<.5 for r in w);hidden=sum(r[score_key]>=.5 for r in u);visible=kept+len(u)-hidden
 return {'posts':len(rs),'wanted':len(w),'kept_wanted':kept,'unwanted':len(u),'hidden_unwanted':hidden,'accuracy':(kept+hidden)/len(rs),'auc':sum((a[score_key]<b[score_key])+.5*(a[score_key]==b[score_key]) for a in w for b in u)/(len(w)*len(u)),'unwanted_share_visible':(len(u)-hidden)/visible if visible else None}
rows=[]
for p in posts.values():
 ps=outputs[p['id']];single=[ps[f'mask-{1<<i:02d}']['p_hide'] for i in range(4)];flags=[p['flags'].get(k) for k in FLAG_KEYS]
 rows.append(dict(p,rule_labels=flags,single_scores=single,expected_hide=or_label(flags),combined=ps['mask-15']['p_hide'],independent=max(single),variants=ps))
stats={slice:{'combined':summary([r for r in rows if pred(r)],'combined'),'independent_OR':summary([r for r in rows if pred(r)],'independent')} for slice,pred in [('all',lambda r:True),('real_feed',lambda r:r['origin']=='fresh-real-feed')]}
violations=[r['id'] for r in rows if max(r['single_scores'])>=.5 and r['combined']<.5]
order_flips=[r['id'] for r in rows if len({r['variants'][v]['p_hide']>=.5 for v in ['mask-15','reverse','rotate-1','rotate-2','rotate-3']})>1]
# Confirm this probe reproduces the previously saved literal four-rule predictions.
old=json.loads((ROOT/'results.json').read_text())['stages']['new']['rows'];parity=[]
for r in old:
 if r['policy_id']=='original_four' and r['style']=='bullets':parity.append(abs(r['p_hide']-outputs[r['post_id']]['mask-15']['p_hide']))

# Warm end-to-end timings, including tokenization; no model loading or downloading.
rng=random.Random(20261024);sample=rng.sample(list(posts.values()),12)
for p in sample[:3]:infer([row(p,RULES)],1);infer([row(p,[x]) for x in RULES],4)
times=collections.defaultdict(list)
for _ in range(3):
 for p in sample:
  methods=['combined','independent_serial','independent_batch4'];rng.shuffle(methods)
  for method in methods:
   if device.type=='mps':torch.mps.synchronize()
   start=time.perf_counter()
   if method=='combined':infer([row(p,RULES)],1)
   elif method=='independent_serial':
    for x in RULES:infer([row(p,[x])],1)
   else:infer([row(p,[x]) for x in RULES],4)
   if device.type=='mps':torch.mps.synchronize()
   times[method].append((time.perf_counter()-start)*1000)
timing={m:{'p50_ms':float(np.percentile(xs,50)),'p95_ms':float(np.percentile(xs,95)),'n':len(xs)} for m,xs in times.items()}
result={'rules':RULES,'model':'latest format-robust checkpoint','device':str(device),'load_seconds':load_seconds,'scores':'Uncalibrated P(hide); decisions use >=0.5. Independent OR is max of scores, not a calibrated probability of the union.','statistics':stats,'monotonicity_violations':violations,'rule_order_decision_flips':order_flips,'reproduction_max_delta':max(parity),'timings':timing,'rows':rows,'note':'Diagnostic reuse of the last test set, no new held-out performance claim. Timings are warm local Python/MPS measurements, not browser WebGPU benchmarks.'}
(OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2),flush=True)
