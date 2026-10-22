import test from 'node:test';
import assert from 'node:assert/strict';
import {validateReplay,initialReplay,reduceReplay,createReplayScheduler,selectRows,decision,visible,metrics} from '../prototypes/model-evaluation/score-replay.mjs';
const catalog=()=>({schema:1,kind:'development-score-replay',version:'synthetic-v1',cases:[
{id:'wanted',text:'Synthetic wanted technical post.',instruction:'Keep tech.',split:'development',label:'keep',reviewed:true},
{id:'unwanted',text:'Synthetic unwanted dating post.',instruction:'Keep tech.',split:'development',label:'hide',reviewed:true},
{id:'uncertain',text:'Synthetic unclear post.',instruction:'Keep tech.',split:'development',label:'uncertain',reviewed:true}],
captures:[{id:'capture',sourceSha256:'synthetic',identity:{revision:'fixture'},rows:[{id:'wanted',instruction:'Keep tech.',pKeep:.6,callMs:3},{id:'unwanted',instruction:'Keep tech.',pKeep:.2,callMs:4},{id:'uncertain',instruction:'Keep tech.',pKeep:.4,callMs:5}]}]});
const ready=c=>{let s=reduceReplay(initialReplay(),{type:'APPLY',captureId:'capture',rule:'Keep tech.'},c);return reduceReplay(s,{type:'FINISH',version:s.version},c);};
test('individual completions reveal or remove only the next pending post',()=>{
 const c=validateReplay(catalog());let s=reduceReplay(initialReplay(),{type:'APPLY',captureId:'capture',rule:'Keep tech.'},c);
 const resolve=id=>{s=reduceReplay(s,{type:'RESOLVE',id,version:s.version},c);};
 resolve('unwanted');assert.ok(s.posts.every(p=>p.pending));
 resolve('wanted');assert.deepEqual(s.posts.map(p=>p.pending),[false,true,true]);
 assert.deepEqual(s.posts.filter(p=>visible(s,p,'wait')).map(p=>p.id),['wanted']);
 assert.deepEqual(s.posts.filter(p=>visible(s,p,'show')).map(p=>p.id),['wanted','unwanted','uncertain']);
 resolve('unwanted');assert.deepEqual(s.posts.map(p=>p.pending),[false,false,true]);
 assert.deepEqual(s.posts.filter(p=>visible(s,p,'show')).map(p=>p.id),['wanted','uncertain']);
 s=reduceReplay(s,{type:'THRESHOLD',value:.7},c);
 assert.deepEqual(s.posts.filter(p=>visible(s,p,'wait')).map(p=>p.id),[]);
 assert.equal(s.posts[2].pending,true);
});
test('stricter thresholds only expand hidden sets without changing scores or labels',()=>{
 const c=validateReplay(catalog());let s=ready(c),previous=[];
 const original=JSON.stringify(s.posts);
 for(const threshold of [0,.3,.5,.7,1]){s=reduceReplay(s,{type:'THRESHOLD',value:threshold},c);const hidden=s.posts.filter(p=>decision(s,p)==='hide').map(p=>p.id);assert.ok(previous.every(id=>hidden.includes(id)));previous=hidden;assert.equal(JSON.stringify(s.posts),original);}
 assert.equal(metrics(s).wantedHidden,1);assert.equal(metrics(s).unwantedHidden,1);
});
test('pending modes, pause, failure, unsupported applied instruction and stale completion stay readable correctly',()=>{
 const c=validateReplay(catalog());let s=reduceReplay(initialReplay(),{type:'APPLY',captureId:'capture',rule:'Keep tech.'},c);
 assert.ok(visible(s,s.posts[0],'show'));assert.ok(!visible(s,s.posts[0],'wait'));
 s=reduceReplay(s,{type:'FINISH',version:s.version},c);assert.equal(decision(s,s.posts[2]),'hide'); // uncertain is not forced visible
 for(const type of ['PAUSE','FAIL']){const inactive=reduceReplay(s,{type},c);assert.ok(inactive.posts.every(p=>visible(inactive,p,'wait')));}
 const changed=reduceReplay(s,{type:'APPLY',captureId:'capture',rule:'A different instruction'},c);
 assert.equal(changed.phase,'error');assert.ok(changed.posts.every(p=>visible(changed,p,'wait')));
 assert.deepEqual(reduceReplay(changed,{type:'FINISH',version:s.version},c),changed);
 assert.throws(()=>selectRows(c,'missing','Keep tech.'));
});
test('invalid or heldout data, duplicate scores and incomplete results are rejected',()=>{
 for(const mutate of [c=>c.cases[0].split='heldout',c=>c.captures[0].rows.pop(),c=>c.captures[0].rows[0].pKeep=NaN,c=>c.captures[0].rows[1].id='wanted']){const c=catalog();mutate(c);assert.throws(()=>validateReplay(c));}
});
test('score metadata cannot replace frozen case fields or inject option markup',()=>{
 const c=catalog();Object.assign(c.captures[0].rows[0],{text:'Changed',label:'hide',split:'heldout'});
 validateReplay(c);const selected=selectRows(c,'capture','Keep tech.')[0];
 assert.equal(selected.text,'Synthetic wanted technical post.');assert.equal(selected.label,'keep');assert.equal(selected.split,'development');
 c.captures[0].id='x" onmouseover="alert(1)';assert.throws(()=>validateReplay(c));
});

function simulation(c=validateReplay(catalog())) {
 let state=initialReplay(),time=0,serial=0,mode='recorded';const timers=new Map(),callbacks=[],resolved=[];
 const scheduler=createReplayScheduler({getState:()=>state,getMode:()=>mode,now:()=>time,
  dispatch:action=>{state=reduceReplay(state,action,c);resolved.push([time,action.id]);},
  setTimer:(callback,delay)=>{const id=++serial;timers.set(id,{callback,at:time+delay});callbacks.push(callback);return id;},
  clearTimer:id=>timers.delete(id)});
 const act=action=>{state=reduceReplay(state,action,c);scheduler.sync();};
 return {get state(){return state;},resolved,callbacks,act,
  apply:()=>act({type:'APPLY',captureId:'capture',rule:'Keep tech.'}),
  mode:value=>{mode=value;scheduler.sync();},
  advance:ms=>{const until=time+ms;
   while(timers.size){const [id,job]=[...timers].sort((a,b)=>a[1].at-b[1].at||a[0]-b[0])[0];if(job.at>until)break;
    timers.delete(id);time=job.at;job.callback();
   }time=until;
  }};
}
test('recorded replay resolves sequentially at individual durations and thresholds do not restart it',()=>{
 const f=simulation();f.apply();f.advance(2);assert.deepEqual(f.resolved,[]);
 f.advance(1);assert.deepEqual(f.resolved,[[3,'wanted']]);
 assert.deepEqual(f.state.posts.filter(p=>visible(f.state,p,'wait')).map(p=>p.id),['wanted']);
 f.advance(1);f.act({type:'THRESHOLD',value:.7});
 assert.equal(visible(f.state,f.state.posts[0],'wait'),false);
 f.advance(3);assert.deepEqual(f.resolved,[[3,'wanted'],[7,'unwanted']]);
 assert.equal(visible(f.state,f.state.posts[1],'show'),false);assert.equal(f.state.posts[2].pending,true);
 f.advance(5);assert.deepEqual(f.resolved,[[3,'wanted'],[7,'unwanted'],[12,'uncertain']]);
});
test('pause restores posts and resumes the remaining delay without accepting cancelled callbacks',()=>{
 const f=simulation();f.apply();f.advance(4);const stale=f.callbacks.at(-1);
 f.act({type:'PAUSE'});assert.ok(f.state.posts.every(p=>visible(f.state,p,'wait')));
 f.advance(100);stale();assert.deepEqual(f.resolved,[[3,'wanted']]);
 f.act({type:'PAUSE'});stale();f.advance(2);assert.deepEqual(f.resolved,[[3,'wanted']]);
 f.advance(1);assert.deepEqual(f.resolved,[[3,'wanted'],[107,'unwanted']]);
});
test('Apply, failure and Retry invalidate callbacks while preserving readable failure and fresh replay',()=>{
 const f=simulation();f.apply();f.advance(1);const beforeApply=f.callbacks.at(-1);
 f.apply();beforeApply();assert.deepEqual(f.resolved,[]);
 f.advance(3);assert.deepEqual(f.resolved,[[4,'wanted']]);const beforeFailure=f.callbacks.at(-1);
 f.act({type:'FAIL'});beforeFailure();f.advance(100);
 assert.ok(f.state.posts.every(p=>visible(f.state,p,'wait')));assert.deepEqual(f.resolved,[[4,'wanted']]);
 f.apply();beforeApply();beforeFailure();assert.ok(f.state.posts.every(p=>p.pending));
 f.advance(3);assert.deepEqual(f.resolved,[[4,'wanted'],[107,'wanted']]);
 const beforeUnsupported=f.callbacks.at(-1);
 f.act({type:'APPLY',captureId:'capture',rule:'Unavailable instruction'});beforeUnsupported();
 assert.equal(f.state.phase,'error');assert.ok(f.state.posts.every(p=>visible(f.state,p,'wait')));
});
test('loading more posts preserves the active timer and Finish cancels pending callbacks',()=>{
 const c=catalog();c.cases.push({...c.cases[0],id:'fourth'});c.captures[0].rows.push({...c.captures[0].rows[0],id:'fourth'});
 const f=simulation(validateReplay(c));f.apply();f.advance(2);f.act({type:'ADD'});
 assert.equal(f.state.posts.length,4);f.advance(1);assert.deepEqual(f.resolved,[[3,'wanted']]);
 const stale=f.callbacks.at(-1);f.act({type:'FINISH',version:f.state.version});stale();f.advance(20);
 assert.ok(f.state.posts.every(p=>!p.pending));assert.deepEqual(f.resolved,[[3,'wanted']]);
});
test('instant replay completes without simulated duration and timing changes replace old callbacks',()=>{
 const f=simulation();f.apply();f.advance(1);const stale=f.callbacks.at(-1);
 f.mode('instant');stale();f.advance(0);
 assert.deepEqual(f.resolved,[[1,'wanted'],[1,'unwanted'],[1,'uncertain']]);
});
