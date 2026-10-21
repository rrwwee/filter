"""Independent broad-instruction head-only fine-tune, with local raw outputs."""
import gc, json, pathlib, time
import numpy as np
import torch
from laya.train import load_checkpoint, items_from_rows, TrainConfig, train_model, calibration_records, evaluate_records, save_checkpoint

ROOT=pathlib.Path(__file__).resolve().parents[2]/'local-results'
OUT=ROOT/'finetune-broad'
torch.set_num_threads(4)
DEVICE=torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
torch.manual_seed(20261020)
model,tok,cfg=load_checkpoint(str(ROOT/'finetune-promotions/base'))
model.to(DEVICE)
for p in model.encoder.parameters():p.requires_grad_(False)
src={s:[json.loads(l) for l in (OUT/(s+'.jsonl')).read_text().splitlines()] for s in ['train','validation','test']}
items={}
for s,rows in src.items():
 items[s],skipped=items_from_rows(tok,rows,cfg['max_len'],cfg['head_max_len'])
 assert len(items[s])==len(rows) and not skipped,(s,skipped)
print('DEVICE',DEVICE,'ROWS',{s:len(r) for s,r in src.items()},flush=True)

def evaluate(s,with_rows=True):
 records=calibration_records(model,tok,items[s],DEVICE,cfg['max_len'],cfg['head_max_len'],batch_size=4)
 m=evaluate_records(records,[1,1,1]);rows=[]
 for r,(_,z,_,_) in zip(src[s],records):
  z=np.asarray(z,dtype=float);p=np.exp(z-z.max());p/=p.sum()
  rows.append({k:r[k] for k in ['id','post_id','policy_id','style','suite','origin']}|{'expected_hide':r['expected']['hide'],'p_hide':float(p[1]),'p_keep':float(p[0]),'logits':z.tolist()})
 return {'metrics':m,'rows':rows} if with_rows else m

result={'initialization':'Original pinned base; no prior fine-tune weights','device':str(DEVICE),'calibration':'T=1, not calibrated','stages':{}}
result['stages']['base']={s:evaluate(s) for s in src}
(OUT/'results.json').write_text(json.dumps(result,indent=2))
def head_copy():return {k:v.detach().cpu().clone() for k,v in model.state_dict().items() if not k.startswith('encoder.')}
best={'loss':result['stages']['base']['validation']['metrics']['loss'],'epoch':0,'state':head_copy()}
hist=[];stale=0
class Done(Exception):pass
def callback(epoch,loss):
 global stale
 m=evaluate('validation',False);hist.append({'epoch':epoch+1,'training_loss':loss,'validation':m})
 print('VALIDATION',epoch+1,loss,m['loss'],m['accuracy'],flush=True)
 if m['loss']<best['loss']-1e-5:best.update(loss=m['loss'],epoch=epoch+1,state=head_copy());stale=0
 else:stale+=1
 model.train();model.encoder.eval()
 if epoch+1>=4 and stale>=3:raise Done()
config=TrainConfig(epochs=12,micro_batch=4,grad_accum=1,head_lr=2e-5,min_lr=2e-6,weight_decay=.01,loss='soft-ce',freeze_encoder=True,calib_frac=0,calib_max=0,seed=20261020,log_every=0)
result['training_config']={k:getattr(config,k) for k in ['epochs','micro_batch','grad_accum','head_lr','min_lr','weight_decay','loss','freeze_encoder','seed']}
start=time.perf_counter()
try:train_model(model,tok,items['train'],config,DEVICE,cfg['max_len'],cfg['head_max_len'],on_epoch_end=callback)
except Done:print('Stopped on validation.',flush=True)
missing,unexpected=model.load_state_dict(best['state'],strict=False)
assert not unexpected and all(k.startswith('encoder.') for k in missing)
model.eval();result['training']={'selected_epoch':best['epoch'],'epochs_run':len(hist),'seconds':time.perf_counter()-start,'history':hist}
result['stages']['tuned']={s:evaluate(s) for s in src}
save_checkpoint(model,tok,dict(cfg,fine_tuned=True,temperature=[1,1,1],temperature_by_options={}),str(OUT/'checkpoint'))
reference=result['stages']['tuned']['test']['rows']
del best,model;gc.collect()
if DEVICE.type=='mps':torch.mps.empty_cache()
model,tok,cfg=load_checkpoint(str(OUT/'checkpoint'));model.to(DEVICE);model.eval()
reloaded=evaluate('test');result['reload_max_p_hide_delta']=max(abs(a['p_hide']-b['p_hide']) for a,b in zip(reference,reloaded['rows']))
assert all((a['p_hide']>=.5)==(b['p_hide']>=.5) for a,b in zip(reference,reloaded['rows']))
(OUT/'results.json').write_text(json.dumps(result,indent=2))
(OUT/'model-outputs.jsonl').write_text(''.join(json.dumps(dict(stage=stage,split=split,**row))+'\n' for stage,sets in result['stages'].items() for split,d in sets.items() for row in d['rows']))
print('COMPLETE',result['training']['selected_epoch'],'reload delta',result['reload_max_p_hide_delta'],flush=True)
