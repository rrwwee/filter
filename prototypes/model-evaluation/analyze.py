"""Summarize local labeled results; does not tune on held-out rows."""
import argparse,json,math,statistics
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('results');p.add_argument('--labels');p.add_argument('--threshold',type=float);a=p.parse_args()
d=json.loads(Path(a.results).read_text());labels={c['id']:c for c in json.loads(Path(a.labels).read_text()).get('cases',[])} if a.labels else {}
rows=[dict(r,label=labels.get(r['id'],{}).get('label',r.get('label')),split=labels.get(r['id'],{}).get('split',r.get('split'))) for r in d.get('rows',[])]
groups={}
for r in rows:groups.setdefault((r.get('candidate','opendecider'),r['dtype'],r['condition']),[]).append(r)
for key,rs in groups.items():
 calls={r['callStarted']:r for r in rs};times=[r['callMs'] for r in calls.values()]
 print(key, 'rows',len(rs),'calls',len(times),'median_call_ms',round(statistics.median(times),2),'actual_batch_sizes',sorted(set(r['batchSize'] for r in rs)))
 # Use one result per case for quality; timing repeats must not inflate the sample.
 unique={r['id']:r for r in rs};valid=[r for r in unique.values() if r['label'] in ('keep','hide')]
 if not valid:continue
 development=[r for r in valid if r['split']=='development'];threshold=a.threshold
 if threshold is None and development:
  positive=[r for r in development if r['label']=='keep'];negative=[r for r in development if r['label']=='hide']
  if positive and negative:
   options=sorted(set([0.0,1.0]+[r['pKeep'] for r in development]))
   eligible=[t for t in options if sum(r['pKeep']>=t for r in positive)/len(positive)>=.95]
   threshold=max(eligible);print('development_selected_threshold',threshold)
 if threshold is not None:
  for split in sorted(set(r['split'] for r in valid)):
   subset=[r for r in valid if r['split']==split];keep=[r for r in subset if r['label']=='keep'];hide=[r for r in subset if r['label']=='hide']
   brier=sum((r['pKeep']-(r['label']=='keep'))**2 for r in subset)/len(subset)
   print(split,'wanted_kept',f'{sum(r["pKeep"]>=threshold for r in keep)}/{len(keep)}','unwanted_hidden',f'{sum(r["pKeep"]<threshold for r in hide)}/{len(hide)}','brier',round(brier,4))
