"""Local-only, intentionally narrow fine-tuning experiment. No uploads or calibration."""
import copy,gc,json,pathlib,time,traceback
import numpy as np
import torch
from laya.train import load_checkpoint,read_data,items_from_rows,TrainConfig,train_model,calibration_records,evaluate_records,save_checkpoint
ROOT=pathlib.Path(__file__).resolve().parents[2]/'local-results/finetune-promotions'
torch.set_num_threads(4)
DEVICE=torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
print('Device:',DEVICE,flush=True)
model,tok,cfg=load_checkpoint(str(ROOT/'base'));model.to(DEVICE)
for p in model.encoder.parameters():p.requires_grad_(False)
print('Total/trainable parameters:',sum(p.numel() for p in model.parameters()),sum(p.numel() for p in model.parameters() if p.requires_grad),flush=True)
splits={};source={}
for name in ['overfit','train','validation','test']:
 source[name]=[json.loads(x) for x in (ROOT/(name+'.jsonl')).read_text().splitlines()]
 splits[name],skipped=items_from_rows(tok,source[name],cfg['max_len'],cfg['head_max_len'])
 assert len(splits[name])==len(source[name]) and not skipped,(name,skipped)
print('Splits:',{k:len(v) for k,v in splits.items()},flush=True)
results={'device':str(DEVICE),'model':'convaiinnovations/laya-multilingual','revision':'052592a15d198d9ad47da779604259b10b47b7aa','temperature':'Fixed at 1; probabilities not calibrated','stages':{}}
def evaluate(name):
 rec=calibration_records(model,tok,splits[name],DEVICE,cfg['max_len'],cfg['head_max_len'],batch_size=4)
 metrics=evaluate_records(rec,[1,1,1]);rows=[]
 for row,(_,logits,target,k) in zip(source[name],rec):
  z=np.asarray(logits,dtype=float);p=np.exp(z-z.max());p/=p.sum()
  rows.append({'id':row['id'],'expected_hide':row['expected']['hide'],'p_hide':float(p[1]),'p_keep':float(p[0]),'logits':z.tolist()})
 metrics['kept_wanted']=sum(not r['expected_hide'] and r['p_hide']<.5 for r in rows)
 metrics['wanted']=sum(not r['expected_hide'] for r in rows)
 metrics['hidden_unwanted']=sum(r['expected_hide'] and r['p_hide']>=.5 for r in rows)
 metrics['unwanted']=sum(r['expected_hide'] for r in rows)
 return {'metrics':metrics,'rows':rows}
def capture(stage):
 results['stages'][stage]={name:evaluate(name) for name in splits}
 (ROOT/'results.json').write_text(json.dumps(results,indent=2))
 print(stage,{name:{k:d['metrics'][k] for k in ['accuracy','loss','kept_wanted','wanted','hidden_unwanted','unwanted']} for name,d in results['stages'][stage].items()},flush=True)
def head_copy():return {k:v.detach().cpu().clone() for k,v in model.state_dict().items() if not k.startswith('encoder.')}
def restore(s):
 missing,unexpected=model.load_state_dict(s,strict=False)
 assert not unexpected and all(k.startswith('encoder.') for k in missing)
class Done(Exception):pass
capture('base')
# Checkpoint saving happens once per stage, not each epoch.
best={'loss':float('inf'),'state':None,'epoch':0};history=[]
def overfit_callback(epoch,loss):
 history.append(loss)
 if (epoch+1)%5:return
 m=evaluate('overfit')['metrics']
 print('OVERFIT_CHECK',epoch+1,m['accuracy'],m['loss'],flush=True)
 if m['loss']<best['loss']:best.update(loss=m['loss'],state=head_copy(),epoch=epoch+1)
 model.train();model.encoder.eval()
 if m['accuracy']==1 and m['loss']<.03:raise Done()
start=time.perf_counter()
try:
 train_model(model,tok,splits['overfit'],TrainConfig(epochs=100,micro_batch=4,grad_accum=1,head_lr=5e-4,min_lr=1e-5,weight_decay=0,loss='soft-ce',freeze_encoder=True,calib_frac=0,calib_max=0,seed=42,log_every=0),DEVICE,cfg['max_len'],cfg['head_max_len'],on_epoch_end=overfit_callback)
except Done:print('Overfit stopping condition reached.',flush=True)
if best['state'] is not None:restore(best['state'])
model.eval();results['overfit_training']={'epochs':best['epoch'],'seconds':time.perf_counter()-start,'epoch_loss':history}
capture('overfit')
save_cfg=dict(cfg,fine_tuned=True,temperature=[1,1,1],temperature_by_options={})
save_checkpoint(model,tok,save_cfg,str(ROOT/'overfit-checkpoint'))
(ROOT/'overfit-checkpoint/questions.json').write_text(json.dumps(source['overfit'][0]['questions'],indent=2))
if results['stages']['overfit']['overfit']['metrics']['accuracy']<1:
 print('Overfit did not memorize every example; stopping before broadening.',flush=True)
 raise RuntimeError('Head-only overfit failed to reach 100% on training examples.')
# The overfit stage checks the pipeline only. Start the broader experiment
# independently from the original checkpoint, with a fresh optimizer.
del model,best;gc.collect()
if DEVICE.type=='mps':torch.mps.empty_cache()
model,tok,cfg=load_checkpoint(str(ROOT/'base'));model.to(DEVICE)
for p in model.encoder.parameters():p.requires_grad_(False)
model.eval()
results['broader_initialization']='original base checkpoint; independent of overfit stage'
# Broader distribution: select on validation, never on the test split.
initial=evaluate('validation')['metrics'];best={'loss':initial['loss'],'state':head_copy(),'epoch':0};history=[];stale=0
def broad_callback(epoch,loss):
 global stale
 history.append(loss)
 if (epoch+1)%2:return
 m=evaluate('validation')['metrics']
 print('VALIDATION_CHECK',epoch+1,m['accuracy'],m['loss'],flush=True)
 if m['loss']<best['loss']-1e-5:best.update(loss=m['loss'],state=head_copy(),epoch=epoch+1);stale=0
 else:stale+=1
 model.train();model.encoder.eval()
 if epoch+1>=20 and stale>=10:raise Done()
start=time.perf_counter()
try:
 train_model(model,tok,splits['train'],TrainConfig(epochs=40,micro_batch=4,grad_accum=1,head_lr=1e-4,min_lr=1e-5,weight_decay=.01,loss='soft-ce',freeze_encoder=True,calib_frac=0,calib_max=0,seed=43,log_every=0),DEVICE,cfg['max_len'],cfg['head_max_len'],on_epoch_end=broad_callback)
except Done:print('Validation stopping condition reached.',flush=True)
restore(best['state']);model.eval();results['broader_training']={'selected_epoch':best['epoch'],'epochs_run':len(history),'seconds':time.perf_counter()-start,'epoch_loss':history}
capture('broader')
save_checkpoint(model,tok,save_cfg,str(ROOT/'broader-checkpoint'))
(ROOT/'broader-checkpoint/questions.json').write_text(json.dumps(source['train'][0]['questions'],indent=2))
# Verify the saved artifact, after releasing the training model.
reference=results['stages']['broader']['test']['rows']
del best,model;gc.collect()
if DEVICE.type=='mps':torch.mps.empty_cache()
model,tok,cfg=load_checkpoint(str(ROOT/'broader-checkpoint'));model.to(DEVICE);model.eval()
reloaded=evaluate('test');results['reloaded_test']=reloaded
results['reload_max_p_hide_delta']=max(abs(a['p_hide']-b['p_hide']) for a,b in zip(reference,reloaded['rows']))
assert [r['p_hide']>=.5 for r in reference]==[r['p_hide']>=.5 for r in reloaded['rows']]
(ROOT/'results.json').write_text(json.dumps(results,indent=2))
print('COMPLETE. Reload max probability delta:',results['reload_max_p_hide_delta'],flush=True)
