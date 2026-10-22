"""Freeze independently reviewed local cases after overlap checks. No inference."""
import argparse,json,hashlib,re
from pathlib import Path
from acceptance_replay import fingerprint
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('directory',type=Path)
parser.add_argument('history',type=Path)
parser.add_argument('--base-checkpoint',type=Path,required=True)
parser.add_argument('--tuned-checkpoint',type=Path,required=True)
args=parser.parse_args()
out=args.directory.resolve();root=args.history.resolve()
if (out/'plan.json').exists():raise ValueError('plan already frozen; do not overwrite')
normalize=lambda s:re.sub(r'\W+',' ',s.casefold()).strip()
texts=set();instructions=set();ids=set();files=0;failed=[]
def collect(v):
 if isinstance(v,dict):
  for k,x in v.items():
   if k in ('text','state','post_text') and isinstance(x,str):texts.add(normalize(x))
   if k in ('id','post_id') and isinstance(x,str):ids.add(x)
   if k in ('instruction','instructions') and isinstance(x,str):instructions.add(normalize(x))
   collect(x)
 elif isinstance(v,list):
  for x in v:collect(x)
for p in root.rglob('*'):
 if out == p or out in p.parents:continue
 if p.suffix not in ('.json','.jsonl') or 'training-env' in p.parts or any(x in p.parts for x in ('base','checkpoint','full-checkpoint','tokenizer','encoder')):continue
 try:
  if p.suffix=='.jsonl':
   for line in p.read_text().splitlines():
    if line.strip():collect(json.loads(line))
  else:collect(json.loads(p.read_text()))
  files+=1
 except Exception as e:failed.append({'file':str(p.relative_to(root)),'error':type(e).__name__})
cases=json.loads((out/'author-labels.json').read_text())
shingles=lambda s:set(tuple(s.split()[i:i+5]) for i in range(max(0,len(s.split())-4)))
known=[shingles(t) for t in texts if t]
checks=[]
for r in cases:
 t=normalize(r['state']);g=shingles(t)
 overlap=max((len(g&h)/min(len(g),len(h)) for h in known if g and h),default=0)
 check={'id':r['id'],'exact_text':t in texts,'identifier':r['id'] in ids,'instruction_exact':normalize(r['instruction']) in instructions,'max_5gram_overlap_min_denominator':overlap}
 checks.append(check)
 if check['exact_text'] or check['identifier'] or overlap>=.7:raise ValueError('overlap found; freeze blocked')
print(json.dumps({'files':files,'distinct_normalized_texts':len(texts),'instructions':len(instructions),'failed':failed,'max_overlap':max(c['max_5gram_overlap_min_denominator'] for c in checks),'exact':sum(c['exact_text'] for c in checks),'same_instruction':sum(c['instruction_exact'] for c in checks)}))
(out/'overlap-audit.json').write_text(json.dumps({'files':files,'distinct_normalized_texts':len(texts),'failed':failed,'checks':checks,'limit':'Only supplied local JSON/JSONL text/state/post_text strings. No semantic duplicate, external corpus, training history, or original upstream pretraining guarantee.'},indent=2))
if failed:raise ValueError('unreadable source files')
review=json.loads((out/'independent-labels.json').read_text());rd={r['id']:r for r in review}
for r in cases:
 if type(rd[r['id']]['expected_hide']) is not bool or rd[r['id']]['expected_hide']!=r['expected_hide']:raise ValueError('label reviewer disagreement: '+r['id'])
(out/'frozen-cases.json').write_text(json.dumps(cases,indent=2))
hashfile=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan={'cases_sha256':hashfile(out/'frozen-cases.json'),'review_sha256':hashfile(out/'independent-labels.json'),'overlap_sha256':hashfile(out/'overlap-audit.json'),'thresholds':[.25,.5,.75],'primary_threshold':.5,'threshold_policy':'Fixed before inference: primary uncalibrated binary 0.5; sensitivity 0.25 and 0.75, no acceptance-based selection.','device':'cpu','threads':2,'models':['local-base','local-tuned'],'labels':'Author specified + separate assistant reviewer blinded to author labels and all model predictions; no human validation.','excluded_ambiguous':len(json.loads((out/'ambiguous.json').read_text())),'source':'new authored synthetic; does not estimate real-feed prevalence'}
plan['checkpoint_bindings']={'local-base':fingerprint(args.base_checkpoint)['sha256'], 'local-tuned':fingerprint(args.tuned_checkpoint)['sha256']}
if len(set(plan['checkpoint_bindings'].values())) != 2:raise ValueError('comparison requires two distinct checkpoints')
with (out/'plan.json').open('x') as stream:stream.write(json.dumps(plan,indent=2))
print('FROZEN',plan['cases_sha256'])
