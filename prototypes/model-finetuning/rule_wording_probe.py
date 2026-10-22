"""Diagnostic wording control; not automatic rewriting of user instructions."""
import json,pathlib
import numpy as np
import torch
from laya.train import load_checkpoint,items_from_rows,calibration_records
ROOT=pathlib.Path(__file__).resolve().parents[2]/'local-results/finetune-format-robust'
p=json.loads((ROOT/'rule-probe/results.json').read_text());torch.set_num_threads(4)
device=torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
model,tok,cfg=load_checkpoint(str(ROOT/'checkpoint'));model.to(device);model.eval()
controls=['Hide posts that withhold the point until I click','Keep technology posts and funny posts; hide everything else']
rows=[{'state':r['text'],'questions':{'hide':{'type':'noul','instructions':'Filtering rules:\n- '+text+'\n\nShould this post be hidden?','criteria':{'false':'Keep the post visible.','true':'Hide the post.'}}},'expected':{'hide':False}} for r in p['rows'] for text in controls]
items,skipped=items_from_rows(tok,rows,cfg['max_len'],cfg['head_max_len']);assert not skipped
rec=calibration_records(model,tok,items,device,cfg['max_len'],cfg['head_max_len'],batch_size=4)
out=[]
for i,r in enumerate(p['rows']):
 vals=[]
 for _,z,_,_ in rec[i*2:i*2+2]:
  z=np.asarray(z);q=np.exp(z-z.max());q/=q.sum();vals.append(float(q[1]))
 out.append({'id':r['id'],'alternative_clickbait':vals[0],'alternative_tech_funny':vals[1],'alternative_OR':max(r['single_scores'][:2]+vals),'expected_hide':r['expected_hide']})
valid=[r for r in out if r['expected_hide'] is not None];w=[r for r in valid if not r['expected_hide']];u=[r for r in valid if r['expected_hide']]
result={'wordings':controls,'rows':out,'summary':{'wanted':len(w),'kept_wanted':sum(r['alternative_OR']<.5 for r in w),'unwanted':len(u),'hidden_unwanted':sum(r['alternative_OR']>=.5 for r in u)},'note':'Explicit diagnostic paraphrases from training; not applied to user inputs.'}
(ROOT/'rule-probe/wording-control.json').write_text(json.dumps(result,indent=2));print(result['summary'])
