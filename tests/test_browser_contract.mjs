import test from 'node:test';
import assert from 'node:assert/strict';
import {validateCases, runnableCases, directQuestion, decodeBatch} from '../prototypes/model-evaluation/contracts.mjs';
const c = (id, split) => ({id, split, text: 'Invented test post.'});
const yes = p => ({answers: {keep: {noul: p}}});
const choices = probabilities => ({answers: {keep: {probabilities}}});

test('ordinary calls allow only smoke/development and exclude both known holdouts', () => {
  const data = [c('s', 'smoke'), c('d', 'development'), c('h', 'heldout'), c('p', 'heldout-pool')];
  assert.deepEqual(runnableCases(data).map(x => x.id), ['s', 'd']);
  assert.throws(() => runnableCases([c('h', 'heldout')]));
});
test('unknown/missing splits fail rather than leaking into model calls', () => {
  for (const split of [undefined, null, 'test', 'held-out', '']) assert.throws(() => runnableCases([c('x', split)]));
});
test('diagnostic data requires the explicit bullet mode', () => {
  const data = [c('x', 'agent-diagnostic')];
  assert.throws(() => runnableCases(data));
  assert.equal(runnableCases(data, 'bullet').length, 1);
  assert.throws(() => runnableCases([c('s', 'smoke')], 'bullet'));
  assert.throws(() => runnableCases([c('h', 'heldout')], 'bullet'));
});
test('invalid case shapes/duplicate IDs cannot enter a run', () => {
  for (const data of [{}, [null], [{...c('x', 'smoke'), text: ''}], [c('x', 'smoke'), c('x', 'development')], [{...c('x', 'smoke'), instruction: {}}]]) assert.throws(() => validateCases(data));
});
test('unsupported direct questions fail, supported polarity is explicit', () => {
  assert.throws(() => directQuestion('ad'));
  assert.throws(() => directQuestion('__proto__'));
  assert.equal(directQuestion('tech')[1], true);
  assert.equal(directQuestion('dating')[1], false);
});
test('keep and hide question polarities remain distinct', () => {
  assert.equal(decodeBatch([yes(.8)], 1, {template:'state'})[0].pKeep, .8);
  assert.ok(Math.abs(decodeBatch([yes(.8)], 1, {template:'bullet-hide',yesMeansKeep:false})[0].pKeep-.2)<1e-12);
});
test('named and reversed neutral choices preserve keep meaning', () => {
  assert.equal(decodeBatch([choices({keep:.8,hide:.2})], 1, {template:'choice',isChoice:true})[0].pKeep,.8);
  assert.equal(decodeBatch([choices({A:.8,B:.2})], 1, {template:'minimal-ab',isChoice:true})[0].pKeep,.8);
  assert.equal(decodeBatch([choices({A:.2,B:.8})], 1, {template:'minimal-ba',isChoice:true})[0].pKeep,.8);
});
test('incomplete and overfull batches cannot be published as complete', () => {
  for (const outputs of [[], [yes(.1),yes(.2)], null]) assert.throws(() => decodeBatch(outputs,1,{template:'state'}));
});
test('bad probability anywhere rejects whole batch before append', () => {
  const rows = [];
  for (const p of [NaN, Infinity, -.1, 1.1, '.5', undefined]) {
    assert.throws(() => rows.push(...decodeBatch([yes(.5),yes(p)],2,{template:'state'})));
    assert.equal(rows.length,0);
  }
  assert.throws(() => decodeBatch([{}],1,{template:'state'}));
});
test('choice outputs require both finite normalized options', () => {
  for (const p of [{keep:.5}, {keep:.8,hide:.8}, {keep:NaN,hide:.5}, {keep:.5,hide:.5,unknown:0}]) assert.throws(() => decodeBatch([choices(p)],1,{template:'choice',isChoice:true}));
});

import {readFile} from 'node:fs/promises';
async function harness(outputs) {
  const elements = new Map();
  const defaults = {template:'state',candidate:'opendecider',device:'wasm',dtype:'q8',threshold:'50',rule:'Keep technology posts.'};
  const element = id => {
    if (!elements.has(id)) elements.set(id,{value:defaults[id]??'',textContent:'',innerHTML:'',disabled:false,scrollTop:0,scrollHeight:0});
    return elements.get(id);
  };
  let calls=0, saved;
  const model={backend:{device:'wasm',dtype:'q8',dispose:async()=>{}},meta:{stub:true},systemOneBatch:async()=>{calls++;return outputs;}};
  const args={document:{getElementById:element},navigator:{userAgent:'test',hardwareConcurrency:1},performance,crossOriginIsolated:true,
    loadNano:async()=>model,loadLaya:async()=>{throw Error('Not used');},noul:()=>({}),choice:()=>({}),REVISION:'stub',MODELS:{},
    validateCases,runnableCases,directQuestion,decodeBatch,
    fetch:async(url,options)=>{if(url!=='/save')throw Error('Unexpected network');saved=JSON.parse(options.body);return {json:async()=>({name:'stub-run.json'})};}};
  const source=(await readFile(new URL('../prototypes/model-evaluation/app.mjs',import.meta.url),'utf8')).replace(/^import .*;\n/gm,'');
  const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
  await new AsyncFunction(...Object.keys(args),source)(...Object.values(args));
  await element('load').onclick();
  return {element, calls:()=>calls, saved:()=>saved};
}
test('browser wiring excludes heldout data before inference and preserves valid polarity',async()=>{
  const h=await harness([yes(.8)]);
  const data=[c('dev','development'),c('secret','heldout-pool')];
  await h.element('file').onchange({target:{files:[{text:async()=>JSON.stringify(data)}]}});
  await h.element('actual').onclick();
  assert.equal(h.calls(),1);
  assert.equal(h.saved().rows.length,1);
  assert.equal(h.saved().rows[0].id,'dev');
  assert.equal(h.saved().rows[0].pKeep,.8);
});
test('browser wiring does not append partial bad batches',async()=>{
  const h=await harness([yes(.8),yes(NaN)]);
  await h.element('actual').onclick(); // first one-item call returns an invalid two-item batch
  assert.equal(h.calls(),1);
  await h.element('save').onclick();
  assert.equal(h.saved().rows.length,0);
  assert.match(h.element('log').textContent,/cardinality/);
});
