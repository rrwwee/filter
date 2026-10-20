import json, pathlib, statistics, math
root=pathlib.Path(__file__).resolve().parents[2]
rows={}
for p in sorted((root/'local-results').glob('run-*.json')):
 d=json.loads(p.read_text())
 for r in d.get('rows',[]):
  if r.get('split')!='development':continue
  key=(r.get('candidate','opendecider'),r.get('dtype'),r.get('template','legacy'),r['condition'],r['id'])
  rows[key]=r
configs=sorted(set(k[:3] for k in rows));summary=[]
for config in configs:
 actual=[r for k,r in rows.items() if k[:3]==config and k[3]=='actual'];pos=[r for r in actual if r.get('label')=='keep'];neg=[r for r in actual if r.get('label')=='hide'];unc=[r for r in actual if r.get('label')=='uncertain']
 if not pos or not neg:continue
 threshold=min(r['pKeep'] for r in pos)
 auc=sum((p['pKeep']>n['pKeep'])+.5*(p['pKeep']==n['pKeep']) for p in pos for n in neg)/(len(pos)*len(neg))
 score={'candidate':config[0],'dtype':config[1],'template':config[2],'clear':len(pos)+len(neg),'wanted':len(pos),'unwanted':len(neg),'uncertain':len(unc),'threshold_retaining_all_wanted':threshold,'kept_at_threshold':sum(r['pKeep']>=threshold for r in pos),'hidden_at_threshold':sum(r['pKeep']<threshold for r in neg),'kept_at_0_5':sum(r['pKeep']>=.5 for r in pos),'hidden_at_0_5':sum(r['pKeep']<.5 for r in neg),'pairwise_auc':auc,'brier_clear':sum((r['pKeep']-(r['label']=='keep'))**2 for r in pos+neg)/len(pos+neg),'median_actual_call_ms':statistics.median(r['callMs'] for r in actual),'kept_if_hiding_both':sum(r['pKeep']>max(n['pKeep'] for n in neg) for r in pos),'uncertain_p_keep':[r['pKeep'] for r in unc]}
 for cond in ['empty','keep-all']:
  vals=[r['pKeep'] for k,r in rows.items() if k[:3]==config and k[3]==cond]
  if vals:score[cond]={'n':len(vals),'min':min(vals),'max':max(vals),'mean':statistics.mean(vals)}
 summary.append(score)
print(json.dumps(summary,indent=2))
(root/'local-results/development-summary.json').write_text(json.dumps(summary,indent=2))
