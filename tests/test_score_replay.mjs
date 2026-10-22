import test from 'node:test';
import assert from 'node:assert/strict';
import {validateReplay,initialReplay,reduceReplay,selectRows,decision,visible,metrics} from '../prototypes/model-evaluation/score-replay.mjs';
const catalog=()=>({schema:1,kind:'development-score-replay',version:'synthetic-v1',cases:[
{id:'wanted',text:'Synthetic wanted technical post.',instruction:'Keep tech.',split:'development',label:'keep',reviewed:true},
{id:'unwanted',text:'Synthetic unwanted dating post.',instruction:'Keep tech.',split:'development',label:'hide',reviewed:true},
{id:'uncertain',text:'Synthetic unclear post.',instruction:'Keep tech.',split:'development',label:'uncertain',reviewed:true}],
captures:[{id:'capture',sourceSha256:'synthetic',identity:{revision:'fixture'},rows:[{id:'wanted',instruction:'Keep tech.',pKeep:.6,callMs:3},{id:'unwanted',instruction:'Keep tech.',pKeep:.2,callMs:4},{id:'uncertain',instruction:'Keep tech.',pKeep:.4,callMs:5}]}]});
const ready=c=>{let s=reduceReplay(initialReplay(),{type:'APPLY',captureId:'capture',rule:'Keep tech.'},c);return reduceReplay(s,{type:'FINISH',version:s.version},c);};
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
