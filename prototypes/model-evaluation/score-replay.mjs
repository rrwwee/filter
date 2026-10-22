// Threshold-only recorded replay. Labels never influence a filtering decision.
export function validateReplay(data) {
  if (data?.schema !== 1 || data.kind !== 'development-score-replay' || typeof data.version !== 'string' || !data.version || !Array.isArray(data.cases) || !data.cases.length || !Array.isArray(data.captures) || !data.captures.length) throw Error('Invalid replay catalog');
  const cases = new Map();
  for (const c of data.cases) {
    if (!c || typeof c.id !== 'string' || cases.has(c.id) || c.split !== 'development' || c.reviewed !== true || !['keep','hide','uncertain'].includes(c.label) || typeof c.text !== 'string' || typeof c.instruction !== 'string') throw Error('Invalid development case');
    cases.set(c.id,c);
  }
  const captures = new Set();
  for (const capture of data.captures) {
    if (typeof capture.id !== 'string' || !/^[A-Za-z0-9_-]{1,128}$/.test(capture.id) || captures.has(capture.id) || !capture.sourceSha256 || !capture.identity?.revision || !Array.isArray(capture.rows) || capture.rows.length !== cases.size) throw Error('Invalid capture identity or population');
    captures.add(capture.id); const seen = new Set();
    for (const row of capture.rows) {
      const c=cases.get(row.id);
      if (!c || seen.has(row.id) || c.instruction !== row.instruction || typeof row.pKeep !== 'number' || !Number.isFinite(row.pKeep) || row.pKeep < 0 || row.pKeep > 1 || !Number.isFinite(row.callMs) || row.callMs < 0) throw Error('Invalid captured score');
      seen.add(row.id);
    }
  }
  return data;
}
export const initialReplay = () => ({phase:'loading',paused:false,threshold:0.5,version:0,posts:[],captureId:null,rule:'',message:'Loading local recorded results…'});
export function selectRows(catalog,captureId,rule) {
  const capture=catalog.captures.find(c=>c.id===captureId);
  if(!capture)throw Error('Choose an available recording');
  const rows=new Map(capture.rows.filter(r=>r.instruction===rule).map(r=>[r.id,r]));
  const posts=catalog.cases.filter(c=>c.instruction===rule).map(c=>({...c,pKeep:rows.get(c.id)?.pKeep,callMs:rows.get(c.id)?.callMs,question:rows.get(c.id)?.question,pending:true}));
  if(!posts.length || posts.some(p=>!rows.has(p.id)))throw Error('No recorded scores for this exact instruction. Choose a recorded instruction and Apply.');
  return posts;
}
export function reduceReplay(state,action,catalog) {
  if(action.type==='THRESHOLD') {
    if(!Number.isFinite(action.value)||action.value<0||action.value>1)throw Error('Invalid threshold');
    return {...state,threshold:action.value,message:'Threshold changed; recorded scores and model inputs are unchanged.'};
  }
  if(action.type==='PAUSE')return {...state,paused:!state.paused,message:state.paused?'Filtering resumed.':'Paused; every loaded post is readable.'};
  if(action.type==='FAIL')return {...state,phase:'error',message:action.message||'Replay unavailable. Loaded posts remain readable; Retry is available.'};
  if(action.type==='APPLY') {
    try {
      const available=selectRows(catalog,action.captureId,action.rule);
      return {...state,phase:'ready',captureId:action.captureId,rule:action.rule,version:state.version+1,available,posts:available.slice(0,3),message:'Applied exact recorded instruction; replaying cached scores.'};
    }catch(error){return {...state,phase:'error',rule:action.rule,version:state.version+1,posts:state.posts.map(p=>({...p,pending:true})),message:error.message};}
  }
  if(action.type==='ADD'&&state.phase==='ready')return {...state,posts:state.available.slice(0,Math.min(state.posts.length+3,state.available.length)).map(p=>state.posts.find(x=>x.id===p.id)||p),message:'Loaded the next recorded posts.'};
  if(action.type==='RESOLVE'&&state.phase==='ready'&&!state.paused&&action.version===state.version&&state.posts.find(p=>p.pending)?.id===action.id){
    const posts=state.posts.map(p=>p.id===action.id?{...p,pending:false}:p);
    return {...state,posts,message:posts.some(p=>p.pending)?'Next recorded result displayed; sequential timing is simulated.':'Recorded results displayed. No live model inference occurred.'};
  }
  if(action.type==='FINISH'&&state.phase==='ready'&&!state.paused&&action.version===state.version)return {...state,posts:state.posts.map(p=>({...p,pending:false})),message:'Recorded results displayed. No live model inference occurred.'};
  return state;
}

// One simulated call at a time. Pausing freezes its remaining delay; unrelated
// renders and loading more posts must not restart an already scheduled call.
export function createReplayScheduler({getState,dispatch,getMode,now=()=>performance.now(),setTimer=setTimeout,clearTimer=clearTimeout}) {
  let timer=null,active=null,generation=0;
  function stop(preserve=false){
    if(timer!==null){
      clearTimer(timer);timer=null;generation++;
      if(preserve&&active)active.remaining=Math.max(0,active.remaining-(now()-active.started));
    }
    if(!preserve)active=null;
  }
  function sync(){
    const state=getState(),next=state.posts.find(p=>p.pending),mode=getMode();
    if(state.phase!=='ready'||!next){stop();return;}
    if(!active||active.version!==state.version||active.id!==next.id||active.mode!==mode){
      stop();active={version:state.version,id:next.id,mode,remaining:mode==='recorded'?next.callMs:0};
    }
    if(state.paused){stop(true);return;}
    if(timer!==null)return;
    const job=active,token=++generation;
    job.started=now();
    timer=setTimer(()=>{
      if(token!==generation)return;
      timer=null;active=null;
      const current=getState();
      if(current.phase==='ready'&&!current.paused&&current.version===job.version&&current.posts.find(p=>p.pending)?.id===job.id){
        dispatch({type:'RESOLVE',id:job.id,version:job.version});
      }
      sync();
    },job.remaining);
  }
  return {sync,cancel:()=>stop()};
}
export const decision=(state,p)=>state.paused||state.phase!=='ready'?'readable':p.pending?'pending':p.pKeep>=state.threshold?'keep':'hide';
export const visible=(state,p,mode)=>decision(state,p)==='readable'||(p.pending?mode==='show':decision(state,p)!=='hide');
export function metrics(state) {
  const judged=state.posts.filter(p=>['keep','hide'].includes(p.label));
  return {loaded:state.posts.length,wanted:judged.filter(p=>p.label==='keep').length,
    wantedHidden:judged.filter(p=>p.label==='keep'&&decision(state,p)==='hide').length,
    unwanted:judged.filter(p=>p.label==='hide').length,
    unwantedHidden:judged.filter(p=>p.label==='hide'&&decision(state,p)==='hide').length,
    uncertain:state.posts.filter(p=>p.label==='uncertain').length};
}
