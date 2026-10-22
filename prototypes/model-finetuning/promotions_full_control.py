"""Full-weight control for the same fixed local promotion-filter split."""
import gc,json,pathlib,time
import numpy as np
import torch
from laya.train import load_checkpoint,items_from_rows,TrainConfig,train_model,calibration_records,evaluate_records,save_checkpoint
ROOT=pathlib.Path(__file__).resolve().parents[2]/'local-results/finetune-promotions'
torch.set_num_threads(4);DEVICE=torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
print('Full fine-tune device:',DEVICE,flush=True)
model,tok,cfg=load_checkpoint(str(ROOT/'base'));model.to(DEVICE)
print('Trainable parameters:',sum(p.numel() for p in model.parameters() if p.requires_grad),flush=True)
src={s:[json.loads(l) for l in (ROOT/(s+'.jsonl')).read_text().splitlines()] for s in ['train','validation','test']}
items={}
for s,rows in src.items():
 items[s],skipped=items_from_rows(tok,rows,cfg['max_len'],cfg['head_max_len']);assert not skipped

def evaluate(s):
 records=calibration_records(model,tok,items[s],DEVICE,cfg['max_len'],cfg['head_max_len'],batch_size=2)
 m=evaluate_records(records,[1,1,1]);rows=[]
 for r,(_,z,_,_) in zip(src[s],records):
  z=np.asarray(z,dtype=float);p=np.exp(z-z.max());p/=p.sum()
  rows.append({'id':r['id'],'expected_hide':r['expected']['hide'],'p_hide':float(p[1]),'p_keep':float(p[0]),'logits':z.tolist()})
 m.update(wanted=sum(not r['expected_hide'] for r in rows),kept_wanted=sum(not r['expected_hide'] and r['p_hide']<.5 for r in rows),unwanted=sum(r['expected_hide'] for r in rows),hidden_unwanted=sum(r['expected_hide'] and r['p_hide']>=.5 for r in rows))
 return {'metrics':m,'rows':rows}
class Done(Exception):pass
best={'loss':float('inf'),'epoch':0};hist=[];stale=0
# Save only the best validation checkpoint; don't retain a second full model in RAM.
def callback(epoch,loss):
 global stale
 hist.append(loss)
 if (epoch+1)%2:return
 e=evaluate('validation');m=e['metrics'];print('FULL_VALIDATION',epoch+1,m['accuracy'],m['loss'],flush=True)
 if m['loss']<best['loss']-1e-5:
  best.update(loss=m['loss'],epoch=epoch+1);stale=0
  save_checkpoint(model,tok,dict(cfg,temperature=[1,1,1],temperature_by_options={},fine_tuned=True),str(ROOT/'full-checkpoint'))
 else:stale+=1
 model.train()
 if epoch+1>=10 and stale>=5:raise Done()
start=time.perf_counter()
try:
 train_model(model,tok,items['train'],TrainConfig(epochs=20,micro_batch=1,grad_accum=4,encoder_lr=1e-5,head_lr=5e-5,min_lr=1e-6,weight_decay=.01,loss='soft-ce',freeze_encoder=False,gradient_checkpointing=True,amp=False,seed=44,log_every=0),DEVICE,cfg['max_len'],cfg['head_max_len'],on_epoch_end=callback)
except Done:print('Full control stopped on validation.',flush=True)
seconds=time.perf_counter()-start
del model;gc.collect()
if DEVICE.type=='mps':torch.mps.empty_cache()
model,tok,cfg=load_checkpoint(str(ROOT/'full-checkpoint'));model.to(DEVICE);model.eval()
r={'device':str(DEVICE),'selected_epoch':best['epoch'],'epochs_run':len(hist),'seconds':seconds,'epoch_loss':hist,'stages':{s:evaluate(s) for s in items},'calibration':'not fitted; T=1'}
(ROOT/'full-results.json').write_text(json.dumps(r,indent=2))
(ROOT/'full-checkpoint/questions.json').write_text(json.dumps(src['train'][0]['questions'],indent=2))
print('FULL COMPLETE', {s:d['metrics'] for s,d in r['stages'].items()},flush=True)
