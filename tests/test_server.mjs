import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import {once} from 'node:events';
import {createEvaluationServer,serializedWrites} from '../prototypes/model-evaluation/server.mjs';
import {startLabeling} from '../prototypes/model-evaluation/labeling.mjs';

const fixtureCases=[{id:'one',text:'Synthetic example.',instruction:'Keep useful posts.',split:'development'}];
const snapshot=()=>({type:'human-labels',cases:structuredClone(fixtureCases),index:0,at:'2026-10-22T00:00:00Z'});
async function fixture(t) {
  const root=await fs.mkdtemp(path.join(os.tmpdir(),'filter-server-'));
  await fs.mkdir(path.join(root,'local-results'));await fs.mkdir(path.join(root,'prototypes/model-evaluation'),{recursive:true});
  await fs.writeFile(path.join(root,'prototypes/model-evaluation/index.html'),'<title>Fixture</title>');
  await fs.mkdir(path.join(root,'.git'));await fs.writeFile(path.join(root,'.git/config'),'PRIVATE_SENTINEL');
  for(const name of ['labeling-cases.json','bullet-cases.json'])await fs.writeFile(path.join(root,'local-results',name),JSON.stringify(fixtureCases));
  const server=createEvaluationServer({root,maxBodyBytes:1024});server.listen(0,'127.0.0.1');await once(server,'listening');
  const port=server.address().port,url='http://127.0.0.1:'+port;
  t.after(async()=>{server.closeAllConnections();await new Promise(resolve=>server.close(resolve));await fs.rm(root,{recursive:true,force:true});});
  const post=(body,headers={})=>new Promise((resolve,reject)=>{
    const bytes=JSON.stringify(body);
    const request=http.request(url+'/labels',{method:'POST',headers:{'Content-Type':'application/json','Content-Length':Buffer.byteLength(bytes),...headers}},response=>{
      response.resume();response.on('end',()=>resolve({status:response.statusCode}));
    });
    request.on('error',reject);request.end(bytes);
  });
  return {root,server,port,url,post};
}

test('normal labeling reads and atomic complete saves remain usable',async t=>{
  const f=await fixture(t);
  assert.equal((await fetch(f.url+'/')).status,200);
  assert.deepEqual(await(await fetch(f.url+'/local-results/labeling-cases.json')).json(),fixtureCases);
  assert.equal((await fetch(f.url+'/local-results/bullet-cases.json')).status,200);
  const body=snapshot();body.cases[0].label='keep';body.cases[0].reviewed=true;
  assert.equal((await f.post(body,{'Origin':f.url})).status,200);
  assert.deepEqual(await(await fetch(f.url+'/local-results/latest-labels.json')).json(),body);
  assert.deepEqual((await fs.readdir(path.join(f.root,'local-results'))).sort(),['bullet-cases.json','labeling-cases.json','latest-labels.json']);
});

test('labeling UI saves through the actual server contract',async t=>{
  const f=await fixture(t),elements=new Map();
  const get=id=>{if(!elements.has(id))elements.set(id,{textContent:'',value:1,disabled:false});return elements.get(id);};
  await startLabeling({document:{getElementById:get},fetch:(url,init)=>fetch(f.url+url,init)});
  await get('hide').onclick();
  assert.equal(get('status').textContent,'Saved locally.');
  const saved=await(await fetch(f.url+'/local-results/latest-labels.json')).json();
  assert.equal(saved.cases[0].label,'hide');assert.equal(saved.cases[0].reviewed,true);
});

test('run snapshots get distinct atomic files and invalid snapshots do not write',async t=>{
  const f=await fixture(t),payload={schema:1,cases:fixtureCases,rows:[]};
  const save=body=>fetch(f.url+'/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const a=await(await save(payload)).json(),b=await(await save(payload)).json();
  assert.notEqual(a.name,b.name);
  assert.deepEqual(JSON.parse(await fs.readFile(path.join(f.root,'local-results',a.name),'utf8')),payload);
  assert.equal((await save({})).status,400);
  assert.equal((await fs.readdir(path.join(f.root,'local-results'))).filter(x=>x.startsWith('run-')).length,2);
});

test('cross-origin and non-loopback writes fail without disk changes',async t=>{
  const f=await fixture(t);const before=await fs.readdir(path.join(f.root,'local-results'));
  for(const headers of [{'Origin':'https://evil.example'},{'Host':'evil.example:'+f.port},{'Origin':'null'},{'Sec-Fetch-Site':'cross-site'}]){
    assert.equal((await f.post(snapshot(),headers)).status,403,JSON.stringify(headers));
    assert.deepEqual(await fs.readdir(path.join(f.root,'local-results')),before);
  }
});

test('oversized fixed-length and chunked bodies fail before writing',async t=>{
  const f=await fixture(t);
  assert.equal((await f.post({padding:'x'.repeat(2048)})).status,413);
  const status=await new Promise((resolve,reject)=>{
    const request=http.request(f.url+'/labels',{method:'POST',headers:{'Content-Type':'application/json'}},response=>{response.resume();resolve(response.statusCode)});
    request.on('error',reject);request.write('x'.repeat(800));request.end('x'.repeat(800));
  });
  assert.equal(status,413);assert.equal((await fetch(f.url+'/local-results/latest-labels.json')).status,404);
});

test('private paths, nonallowlisted files and symlink escapes are blocked',async t=>{
  const f=await fixture(t);
  for(const route of ['/.git/config','/package.json','/local-results/private.json','/%2e%2e/.git/config','/prototypes/model-evaluation/%2e%2e/%2e%2e/.git/config']){
    assert.equal((await fetch(f.url+route)).status,404);
  }
  await fs.symlink(path.join(f.root,'.git/config'),path.join(f.root,'prototypes/model-evaluation/app.mjs'));
  assert.equal((await fetch(f.url+'/prototypes/model-evaluation/app.mjs')).status,404);
  await fs.symlink(path.join(f.root,'.git/config'),path.join(f.root,'local-results/latest-labels.json'));
  assert.equal((await fetch(f.url+'/local-results/latest-labels.json')).status,404);
  assert.equal((await f.post(snapshot())).status,400);
  assert.equal(await fs.readFile(path.join(f.root,'.git/config'),'utf8'),'PRIVATE_SENTINEL');
  const dist=path.join(f.root,'node_modules/@opendecider/web/dist');await fs.mkdir(dist,{recursive:true});
  await fs.writeFile(path.join(dist,'index.js'),'export const fixture=true;');
  assert.equal((await fetch(f.url+'/node_modules/@opendecider/web/dist/index.js')).status,200);
  await fs.symlink(path.join(f.root,'.git/config'),path.join(dist,'secret.js'));
  assert.equal((await fetch(f.url+'/node_modules/@opendecider/web/dist/secret.js')).status,404);
});

test('malformed or changed labels cannot overwrite the last valid snapshot',async t=>{
  const f=await fixture(t),valid=snapshot();assert.equal((await f.post(valid)).status,200);
  for(const bad of [{}, {...snapshot(),cases:[]}, {...snapshot(),cases:[{...fixtureCases[0],text:'different'}]}]){
    assert.equal((await f.post(bad)).status,400);
    assert.deepEqual(JSON.parse(await fs.readFile(path.join(f.root,'local-results/latest-labels.json'),'utf8')),valid);
  }
});

test('write queue preserves arrival order across delays and failures',async()=>{
  const enqueue=serializedWrites(),calls=[];let release;
  const first=enqueue(async()=>{calls.push(1);await new Promise(resolve=>{release=resolve;});throw Error('synthetic failure')});
  const second=enqueue(async()=>{calls.push(2);});
  await new Promise(resolve=>setImmediate(resolve));assert.deepEqual(calls,[1]);release();
  await assert.rejects(first);await second;assert.deepEqual(calls,[1,2]);
});

test('recorded preview exposes only its named local catalog and assets',async t=>{
  const f=await fixture(t);
  await fs.writeFile(path.join(f.root,'local-results/development-score-replay.json'),JSON.stringify({kind:'synthetic-replay'}));
  await fs.writeFile(path.join(f.root,'local-results/unrelated-private.json'),'PRIVATE');
  await fs.writeFile(path.join(f.root,'prototypes/model-evaluation/pending-posts.html'),'<title>Replay</title>');
  assert.equal((await fetch(f.url+'/prototypes/model-evaluation/pending-posts.html')).status,200);
  assert.deepEqual(await(await fetch(f.url+'/local-results/development-score-replay.json')).json(),{kind:'synthetic-replay'});
  assert.equal((await fetch(f.url+'/local-results/unrelated-private.json')).status,404);
});
