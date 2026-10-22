"""Corrective balanced full-model experiment; test is now a reused diagnostic set."""
import collections,gc,json,pathlib,random,time
import numpy as np
import torch
from laya.train import load_checkpoint,items_from_rows,TrainConfig,train_model,calibration_records,evaluate_records,save_checkpoint
from build_broad_dataset import row,policy

ROOT=pathlib.Path(__file__).resolve().parents[2]/'local-results'
OUT=ROOT/'finetune-broad'
rng=random.Random(20261021)
train=[json.loads(l) for l in (OUT/'train.jsonl').read_text().splitlines()]
posts=json.loads((OUT/'posts.json').read_text())
paired=[]
for p in posts:
 if p['split']!='train':continue
 for tag,value in p['flags'].items():
  if value is True:
   for kind in ['hide','only']:
    paired.append(row(p,policy(kind,[tag]),'paragraph','train_opposites'))
pool=list({r['id']:r for r in train+paired}.values())
by_label={y:[r for r in pool if r['expected']['hide']==y] for y in [False,True]}
n=min(map(len,by_label.values()))
balanced=[]
for y,rs in by_label.items():
 fixed=[r for r in rs if r['suite']=='train_opposites']
 other=[r for r in rs if r['suite']!='train_opposites']
 balanced+=fixed+rng.sample(other,n-len(fixed))
rng.shuffle(balanced)
(OUT/'balanced-train.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in balanced))
torch.set_num_threads(4);torch.manual_seed(20261021)
device=torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
model,tok,cfg=load_checkpoint(str(ROOT/'finetune-promotions/base'));model.to(device)
src={'train':balanced}|{s:[json.loads(l) for l in (OUT/(s+'.jsonl')).read_text().splitlines()] for s in ['validation','test']}
items={}
for s,rs in src.items():
 items[s],skipped=items_from_rows(tok,rs,cfg['max_len'],cfg['head_max_len']);assert not skipped
print('FULL DEVICE',device,'ROWS',{s:len(rs) for s,rs in src.items()},flush=True)
def evaluate(s):
 rec=calibration_records(model,tok,items[s],device,cfg['max_len'],cfg['head_max_len'],batch_size=2)
 metrics=evaluate_records(rec,[1,1,1]);rows=[]
 for r,(_,z,_,_) in zip(src[s],rec):
  z=np.asarray(z,dtype=float);p=np.exp(z-z.max());p/=p.sum()
  rows.append({k:r[k] for k in ['id','post_id','policy_id','style','suite','origin']}|{'expected_hide':r['expected']['hide'],'p_hide':float(p[1]),'p_keep':float(p[0]),'logits':z.tolist()})
 losses={y:[-np.log(max(1e-12,x['p_hide'] if y else x['p_keep'])) for x in rows if x['expected_hide']==y] for y in [False,True]}
 metrics['balanced_loss']=float(np.mean([np.mean(ls) for ls in losses.values()]))
 return {'metrics':metrics,'rows':rows}
config=TrainConfig(epochs=4,micro_batch=1,grad_accum=4,encoder_lr=1e-5,head_lr=5e-5,min_lr=1e-6,weight_decay=.01,loss='soft-ce',freeze_encoder=False,gradient_checkpointing=True,amp=False,calib_frac=0,calib_max=0,seed=20261021,log_every=150)
best={'loss':evaluate('validation')['metrics']['balanced_loss'],'epoch':0};hist=[];stale=0
save_cfg=dict(cfg,fine_tuned=True,temperature=[1,1,1],temperature_by_options={})
save_checkpoint(model,tok,save_cfg,str(OUT/'full-checkpoint'))
class Done(Exception):pass
def callback(epoch,loss):
 global stale
 m=evaluate('validation')['metrics'];hist.append({'epoch':epoch+1,'training_loss':loss,'validation':m})
 print('FULL_VALIDATION',epoch+1,loss,m,flush=True)
 if m['balanced_loss']<best['loss']-1e-5:
  best.update(loss=m['balanced_loss'],epoch=epoch+1);stale=0
  save_checkpoint(model,tok,save_cfg,str(OUT/'full-checkpoint'))
 else:stale+=1
 model.train()
 if epoch+1>=3 and stale>=2:raise Done()
start=time.perf_counter()
try:train_model(model,tok,items['train'],config,device,cfg['max_len'],cfg['head_max_len'],on_epoch_end=callback)
except Done:print('Stopped on balanced validation loss.',flush=True)
seconds=time.perf_counter()-start
del model;gc.collect()
if device.type=='mps':torch.mps.empty_cache()
model,tok,cfg=load_checkpoint(str(OUT/'full-checkpoint'));model.to(device);model.eval()
result={'initialization':'original pinned base','selection':'balanced validation cross-entropy; base included as epoch zero','test_note':'Reused diagnostic test set; the failed head-only test motivated this corrective run. Not an untouched final benchmark.','training_config':{k:getattr(config,k) for k in ['epochs','micro_batch','grad_accum','encoder_lr','head_lr','seed']},'training_rows':len(balanced),'training_class_counts':{str(y):n for y in by_label},'training':{'selected_epoch':best['epoch'],'epochs_run':len(hist),'seconds':seconds,'history':hist},'stages':{s:evaluate(s) for s in src}}
(OUT/'full-results.json').write_text(json.dumps(result,indent=2))
print('FULL COMPLETE',result['training'],flush=True)
