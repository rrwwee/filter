import {validateReplay,initialReplay,reduceReplay,createReplayScheduler,decision,visible,metrics} from './score-replay.mjs';
const $=id=>document.getElementById(id),escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let catalog,state=initialReplay();
const pending=()=>state.posts.filter(p=>p.pending);
const scheduler=createReplayScheduler({getState:()=>state,dispatch:act,getMode:()=>$('delay').value});
function render(){
  const applied=catalog?.captures.find(c=>c.id===state.captureId);
  $('appliedrule').textContent=state.phase==='error'?'No usable recording for the requested instruction.':applied?`Applied recording: ${applied.identity.candidate} / ${applied.identity.dtype} / ${applied.identity.template} / ${applied.identity.revision}. Instruction: ${state.rule}`:'No recording applied yet.';
  $('strictlabel').textContent=state.threshold.toFixed(2);$('pause').textContent=state.paused?'Resume filtering':'Pause filtering';$('event').textContent=state.message;
  $('editnote').textContent=state.phase==='error'?'Recording unavailable':$('instruction').value===state.rule&&$('capture').value===state.captureId?'Applied':'Draft only — Apply required';
  $('add').disabled=state.phase!=='ready'||state.posts.length===state.available?.length;
  for(const [side,mode] of [['A','show'],['B','wait']]){
    const posts=state.posts.filter(p=>visible(state,p,mode));
    $('feed'+side).innerHTML=posts.map(p=>`<article class="post"><b>Recorded post</b><p>${escape(p.text||'[No readable post text]')}</p></article>`).join('')||'<div class="empty">No visible posts at this point in the replay.</div>';
    $('status'+side).textContent=state.paused?'Paused · all loaded posts restored':state.phase!=='ready'?'Replay unavailable · loaded posts remain readable':pending().length?`Replaying ${pending().length} pending result(s)`:'Recorded results displayed';
  }
  const m=metrics(state);$('metrics').textContent=`Loaded ${m.loaded} · wanted posts hidden ${m.wantedHidden}/${m.wanted} · unwanted posts removed ${m.unwantedHidden}/${m.unwanted} · insufficient evidence ${m.uncertain}`;
  $('decisions').innerHTML=state.posts.map(p=>`<tr><td>${escape(p.text||'[No readable post text]')}</td><td>${escape(p.label)}</td><td>${pending().includes(p)?'Pending':p.pKeep.toFixed(6)}</td><td>${escape(decision(state,p))}</td><td>${p.callMs.toFixed(1)} ms (historical)</td></tr>`).join('');
}
function act(action){state=reduceReplay(state,action,catalog);render();scheduler.sync();}
function apply(){act({type:'APPLY',captureId:$('capture').value,rule:$('instruction').value});}
function chooseCapture(){const capture=catalog.captures.find(c=>c.id===$('capture').value),m=capture.identity;$('provenance').textContent=`Selected recording (Apply required): ${m.candidate} / ${m.device} / ${m.dtype} · ${m.template} · revision ${m.revision} · recorded ${capture.recordedAt} · capture ${capture.sourceSha256}`;
  const rules=[...new Set(capture.rows.map(r=>r.instruction))];$('recorded-rule').innerHTML=rules.map((r,i)=>`<option value="${i}">${escape(r)}</option>`).join('');$('recorded-rule').onchange=()=>{$('instruction').value=rules[Number($('recorded-rule').value)];render();};$('instruction').value=rules[0];render();}
$('apply').onclick=apply;$('instruction').oninput=render;$('pause').onclick=()=>act({type:'PAUSE'});$('strictness').oninput=e=>act({type:'THRESHOLD',value:Number(e.target.value)/100});$('add').onclick=()=>act({type:'ADD'});$('finish').onclick=()=>act({type:'FINISH',version:state.version});$('fail').onclick=()=>act({type:'FAIL'});$('retry').onclick=()=>catalog?apply():load();$('delay').onchange=()=>scheduler.sync();
async function load(){try{const response=await fetch('/local-results/development-score-replay.json');if(!response.ok)throw Error('Local recording not available (HTTP '+response.status+'). Build it locally, then Retry.');catalog=validateReplay(await response.json());$('capture').replaceChildren(...catalog.captures.map(c=>{const option=document.createElement('option');option.value=c.id;option.textContent=c.identity.candidate+' / '+c.identity.dtype+' / '+c.identity.template;return option;}));$('capture').onchange=chooseCapture;$('version').textContent=`Replay version ${catalog.version}. ${catalog.labelProvenance}`;chooseCapture();apply();}catch(e){act({type:'FAIL',message:e.message});}}
load();
