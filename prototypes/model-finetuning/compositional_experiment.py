"""Train on compositional policies, select on validation, unlock fresh test only afterward."""
import argparse,collections,gc,hashlib,json,pathlib,time
from importlib.metadata import version, PackageNotFoundError
from evaluation_contract import read_dataset, prediction_rows, validate_predictions, checkpoint_identity, require
import numpy as np
import torch
from laya.train import load_checkpoint,items_from_rows,TrainConfig,train_model,calibration_records,save_checkpoint

ROOT=pathlib.Path(__file__).resolve().parents[2]/'local-results'
parser=argparse.ArgumentParser()
parser.add_argument('--directory',default='finetune-compositional')
parser.add_argument('--epochs',type=int,default=5)
parser.add_argument('--micro-batch',type=int,default=2)
parser.add_argument('--seed',type=int,default=20261022)
args=parser.parse_args()
require(args.epochs > 0 and args.micro_batch > 0, 'epochs and micro-batch must be positive')
OUT=ROOT/args.directory
torch.set_num_threads(4);torch.manual_seed(args.seed)
DEVICE=torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
manifest,checked_data=read_dataset(OUT)
src={s:checked_data[s] for s in ['train','validation']}
del checked_data
base_identity=checkpoint_identity(ROOT/'finetune-promotions/base')
model,tok,cfg=load_checkpoint(str(ROOT/'finetune-promotions/base'));model.to(DEVICE)
items={}
for s,rs in src.items():
 items[s],skipped=items_from_rows(tok,rs,cfg['max_len'],cfg['head_max_len'],label_smoothing=.05 if s=='train' else 0)
 require(not skipped and len(items[s])==len(rs), f'{s}: tokenizer skipped input rows')

def evaluate(rows,its):
 start=time.perf_counter();rec=calibration_records(model,tok,its,DEVICE,cfg['max_len'],cfg['head_max_len'],batch_size=2);out=[]
 out=prediction_rows(rows,rec)
 validate_predictions(rows,out)
 return {'rows':out,'metrics':summarize(out),'seconds':time.perf_counter()-start}

def summarize(rs):
 by=collections.defaultdict(list);pairs=collections.defaultdict(list)
 for r in rs:
  by[r['family']].append(r)
  if r['pair_id']:pairs[r['pair_id']].append(r)
 acc=[];ce=[]
 for group in by.values():
  a=[];c=[]
  for y in [False,True]:
   cls=[r for r in group if r['expected_hide']==y]
   if not cls:continue
   a.append(np.mean([(r['p_hide']>=.5)==y for r in cls]));c.append(np.mean([-np.log(max(1e-12,r['p_hide'] if y else r['p_keep'])) for r in cls]))
  acc.append(np.mean(a));ce.append(np.mean(c))
 pair_acc=float(np.mean([len(v)==2 and all((r['p_hide']>=.5)==r['expected_hide'] for r in v) for v in pairs.values()])) if pairs else 0
 macro=float(np.mean(acc))
 return {'accuracy':float(np.mean([(r['p_hide']>=.5)==r['expected_hide'] for r in rs])),'macro_balanced_accuracy':macro,'macro_loss':float(np.mean(ce)),'pair_accuracy':pair_acc,'pair_count':len(pairs),'selection_score':.5*macro+.5*pair_acc}

base_val=evaluate(src['validation'],items['validation'])
best={'score':base_val['metrics']['selection_score'],'loss':base_val['metrics']['macro_loss'],'epoch':0,'validation':base_val};history=[];stale=0
save_cfg=dict(cfg,temperature=[1,1,1],temperature_by_options={},fine_tuned=True)
save_checkpoint(model,tok,save_cfg,str(OUT/'checkpoint'))
config=TrainConfig(epochs=args.epochs,micro_batch=args.micro_batch,grad_accum=max(1,4//args.micro_batch),encoder_lr=1e-5,head_lr=5e-5,min_lr=1e-6,weight_decay=.01,loss='soft-ce',freeze_encoder=False,gradient_checkpointing=True,amp=False,calib_frac=0,calib_max=0,seed=args.seed,label_smoothing=.05,log_every=100)
plan={'initialization':'original pinned base, never a prior fine-tune','config':{k:getattr(config,k) for k in ['epochs','micro_batch','grad_accum','encoder_lr','head_lr','min_lr','weight_decay','loss','seed','label_smoothing']},'dataset_hashes':manifest['hashes'],'selection':'maximize 0.5*macro family-balanced accuracy + 0.5*opposite-pair both-correct accuracy on validation; ties minimize macro log loss. Patience 2 after at least 3 epochs.','test_policy':'Test stays unscored until final checkpoint is selected. Test never controls training, thresholds, or calibration.'}
plan['base_checkpoint_identity']=base_identity
plan['runtime_versions']={}
for package in ['laya','torch','numpy','transformers','tokenizers']:
 try:plan['runtime_versions'][package]=version(package)
 except PackageNotFoundError:plan['runtime_versions'][package]='not installed'
(OUT/'training-plan.json').write_text(json.dumps(plan,indent=2));print('DEVICE',DEVICE,'PLAN',plan,flush=True)
class Done(Exception):pass
def callback(epoch,loss):
 global stale
 ev=evaluate(src['validation'],items['validation']);m=ev['metrics'];history.append({'epoch':epoch+1,'training_loss':loss,'validation':m})
 print('VALIDATION',epoch+1,loss,m,flush=True)
 if m['selection_score']>best['score']+1e-8 or (abs(m['selection_score']-best['score'])<=1e-8 and m['macro_loss']<best['loss']-1e-5):
  best.update(score=m['selection_score'],loss=m['macro_loss'],epoch=epoch+1,validation=ev);stale=0
  save_checkpoint(model,tok,save_cfg,str(OUT/'checkpoint'))
 else:stale+=1
 (OUT/'training-history.json').write_text(json.dumps({'best_epoch':best['epoch'],'history':history},indent=2))
 model.train()
 if epoch+1>=3 and stale>=2:raise Done()
start=time.perf_counter()
try:train_model(model,tok,items['train'],config,DEVICE,cfg['max_len'],cfg['head_max_len'],on_epoch_end=callback)
except Done:print('Validation stopping rule reached.',flush=True)
duration=time.perf_counter()-start
del model;gc.collect()
if DEVICE.type=='mps':torch.mps.empty_cache()
selected_identity=checkpoint_identity(OUT/'checkpoint')
model,tok,cfg=load_checkpoint(str(OUT/'checkpoint'));model.to(DEVICE);model.eval()
# Re-encode after loading: checkpoint tokenizer/config may differ.
items['validation'],skipped=items_from_rows(tok,src['validation'],cfg['max_len'],cfg['head_max_len'])
require(not skipped and len(items['validation'])==len(src['validation']), 'reloaded tokenizer skipped validation rows')
new_val=evaluate(src['validation'],items['validation'])
delta=max(abs(a['p_hide']-b['p_hide']) for a,b in zip(best['validation']['rows'],new_val['rows']))
require(all((a['p_hide']>=.5)==(b['p_hide']>=.5) for a,b in zip(best['validation']['rows'],new_val['rows'])), 'reloaded checkpoint changed validation decisions')
# Fixed gentle threshold chosen solely using validation, never test.
def gentle_threshold(rows):
 wanted=[r['p_hide'] for r in rows if not r['expected_hide']]
 candidates=sorted(set([0.,1.000001]+[float(np.nextafter(x,np.inf)) for x in wanted]))
 return next(t for t in candidates if np.mean([x<t for x in wanted])>=.95)
result={'plan':plan,'training_seconds':duration,'selected_epoch':best['epoch'],'epochs_run':len(history),'history':history,'reload_validation_max_delta':delta,'base_validation':base_val,'validation':new_val,'gentle_p_hide_threshold':gentle_threshold(new_val['rows']),'test_unlocked_after_training':True,'stages':{}}
require(hashlib.sha256((OUT/'test.jsonl').read_bytes()).hexdigest()==manifest['hashes']['test'], 'test data changed during training')
test_src=[json.loads(l) for l in (OUT/'test.jsonl').read_text().splitlines()]
test_items,skipped=items_from_rows(tok,test_src,cfg['max_len'],cfg['head_max_len']);require(not skipped and len(test_items)==len(test_src), 'tokenizer skipped test rows')
result['checkpoint_identities']={'new':selected_identity}
result['stages']['new']=evaluate(test_src,test_items)
print('NEW TEST',result['stages']['new']['metrics'],flush=True)
(OUT/'results.json').write_text(json.dumps(result,indent=2))
for name,path in [('base',ROOT/'finetune-promotions/base'),('previous',ROOT/'finetune-broad/full-checkpoint')]:
 del model;gc.collect()
 if DEVICE.type=='mps':torch.mps.empty_cache()
 result['checkpoint_identities'][name]=checkpoint_identity(path)
 if name=='base':require(result['checkpoint_identities'][name]==base_identity, 'base checkpoint changed during training')
 model,tok,cfg=load_checkpoint(str(path));model.to(DEVICE);model.eval()
 test_items,skipped=items_from_rows(tok,test_src,cfg['max_len'],cfg['head_max_len'])
 require(not skipped and len(test_items)==len(test_src), 'tokenizer skipped test rows')
 result['stages'][name]=evaluate(test_src,test_items)
 (OUT/'results.json').write_text(json.dumps(result,indent=2));print(name,'TEST',result['stages'][name]['metrics'],flush=True)
(OUT/'model-outputs.jsonl').write_text(''.join(json.dumps(dict(model=stage,**r))+'\n' for stage,ev in result['stages'].items() for r in ev['rows']))
print('COMPLETE',result['selected_epoch'],duration,flush=True)
