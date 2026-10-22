import test from 'node:test';
import assert from 'node:assert/strict';
import {createAutosaver} from '../prototypes/model-evaluation/autosave.mjs';
import {startLabeling} from '../prototypes/model-evaluation/labeling.mjs';

const cases = () => [1,2].map(n=>({id:String(n),text:'Synthetic '+n,instruction:'Keep useful posts.',split:'development',source:'https://example.org/'+n}));
const tick = () => new Promise(resolve=>setImmediate(resolve));
async function harness({source=cases(), saved, persist=async()=>({ok:true})}={}) {
  const elements = new Map();
  const element = id => { if(!elements.has(id))elements.set(id,{textContent:'',value:1,disabled:false});return elements.get(id); };
  const fetch = async(url,options) => {
    if(url.endsWith('labeling-cases.json'))return {ok:true,json:async()=>source};
    if(url.endsWith('latest-labels.json'))return saved === undefined ? {ok:false,status:404} : {ok:true,json:async()=>structuredClone(saved)};
    assert.equal(url,'/labels');return persist(JSON.parse(options.body));
  };
  const app = await startLabeling({document:{getElementById:element},fetch});
  return {element,app};
}

test('HTTP 500 never displays Saved',async()=>{
  const h=await harness({persist:async()=>({ok:false,status:500})});
  await h.element('save').onclick();
  assert.match(h.element('status').textContent,/Save failed: HTTP 500/);
  assert.doesNotMatch(h.element('status').textContent,/Saved locally/);
});

test('delayed rapid labels serialize requests and coalesce to newest complete snapshot',async()=>{
  const requests=[];let disk,active=0,maxActive=0;
  const h=await harness({persist:snapshot=>new Promise(resolve=>{
    active++;maxActive=Math.max(maxActive,active);
    requests.push({snapshot,finish:()=>{disk=snapshot;active--;resolve({ok:true});}});
  })});
  h.element('keep').onclick();h.element('hide').onclick();h.element('uncertain').onclick();
  assert.equal(requests.length,1);assert.match(h.element('status').textContent,/Saving/);
  assert.equal(requests[0].snapshot.cases[1].reviewed,undefined); // Immutable earlier snapshot.
  requests[0].finish();await tick();
  assert.equal(requests.length,2);assert.equal(requests[1].snapshot.cases[1].label,'uncertain');
  assert.match(h.element('status').textContent,/Saving/);
  requests[1].finish();await h.app.flush();
  assert.equal(maxActive,1);assert.deepEqual(disk.cases.map(c=>c.label),['keep','uncertain']);
  assert.ok(disk.cases.every(c=>c.reviewed));assert.equal(h.element('status').textContent,'Saved locally.');
});

test('malformed or unrelated saved state cannot replace source cases or enable writes',async()=>{
  for(const saved of [{type:'human-labels'}, {type:'human-labels',cases:cases(),index:NaN}, {type:'human-labels',cases:cases().map(c=>({...c,text:'changed'})),index:0}]){
    let writes=0;const h=await harness({saved,persist:async()=>{writes++;return {ok:true}}});
    assert.equal(h.element('text').textContent,'Synthetic 1');
    assert.equal(h.element('save').disabled,true);assert.equal(h.element('save').onclick,undefined);
    assert.match(h.element('status').textContent,/editing disabled/);assert.equal(writes,0);
  }
});

test('valid saved labels restore and normal labeling remains usable',async()=>{
  const saved={type:'human-labels',cases:cases(),index:1};saved.cases[0].label='keep';saved.cases[0].reviewed=true;
  let disk;const h=await harness({saved,persist:async snapshot=>{disk=snapshot;return {ok:true}}});
  assert.equal(h.element('text').textContent,'Synthetic 2');assert.equal(h.element('keep').disabled,false);
  await h.element('hide').onclick();assert.deepEqual(disk.cases.map(c=>c.label),['keep','hide']);
});


test('enqueue during drain completion is persisted before flush resolves', async()=>{
  let resolve; const first = new Promise(r=>{resolve=r}); const calls=[];
  const saver=createAutosaver({persist:value=>{calls.push(value);return value==='first'?first:Promise.resolve();},status:()=>{}});
  saver.enqueue('first');first.then(()=>saver.enqueue('second'));resolve();
  await tick();await saver.flush();assert.deepEqual(calls,['first','second']);
});

test('unreadable posts retain the uncertain labeling flow',async()=>{
  for(const text of ['',undefined]){
    let disk;const h=await harness({source:[{...cases()[0],text}],persist:async snapshot=>{disk=snapshot;return {ok:true}}});
    assert.equal(h.element('text').textContent,'[No readable post text]');
    assert.equal(h.element('uncertain').disabled,false);await h.element('uncertain').onclick();
    assert.equal(disk.cases[0].label,'uncertain');
  }
});
