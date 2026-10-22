import {validateLabelCases, validateLabelSnapshot} from './label-state.mjs';
import {createAutosaver} from './autosave.mjs';

export async function startLabeling({document, fetch}) {
  const $ = id => document.getElementById(id);
  const controls = ['keep','hide','uncertain','back','skip','save','goto','jump'];
  controls.forEach(id => { $(id).disabled = true; });
  let cases, index = 0;
  function render() {
    const c = cases[index];
    $('progress').textContent = `Case ${index+1} of ${cases.length} · ${cases.filter(c => c.reviewed).length} reviewed`;
    $('kind').textContent = c.kind || ''; $('rule').textContent = c.instruction;
    $('text').textContent = c.text || '[No readable post text]'; $('note').textContent = c.hasShowMore ? 'This is the feed preview; the original has more text behind “Show more”.' : '';
    let source = ''; try { const u = new URL(c.source); if (['http:', 'https:'].includes(u.protocol)) source = u.href; } catch {}
    $('source').href = source;
    $('selection').textContent = c.reviewed ? 'Your label: ' + c.label : 'Not labeled'; $('goto').value = index+1;
  }
  try {
    const response = await fetch('/local-results/labeling-cases.json');
    if (!response.ok) throw new Error('Could not load source cases (HTTP ' + response.status + ').');
    cases = validateLabelCases(await response.json());
    render();
    const previous = await fetch('/local-results/latest-labels.json');
    if (previous.ok) {
      const saved = validateLabelSnapshot(await previous.json(), cases);
      cases = saved.cases; index = saved.index;
    } else if (previous.status !== 404) throw new Error('Could not load saved progress (HTTP ' + previous.status + ').');
  } catch (error) {
    $('status').textContent = 'Loading failed; editing disabled to preserve saved progress: ' + error.message;
    return;
  }
  const saver = createAutosaver({
    status: message => { $('status').textContent = message; },
    persist: async snapshot => {
      validateLabelSnapshot(snapshot);
      const response = await fetch('/labels', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(snapshot)});
      if (!response.ok) throw new Error('HTTP ' + response.status);
    },
  });
  const save = () => saver.enqueue({type:'human-labels', cases, index, at:new Date().toISOString()});
  function label(value) {
    cases[index].label = value; cases[index].reviewed = true;
    if (index < cases.length-1) index++;
    render(); return save();
  }
  $('keep').onclick = () => label('keep'); $('hide').onclick = () => label('hide'); $('uncertain').onclick = () => label('uncertain');
  $('back').onclick = () => { index = Math.max(0,index-1); render(); };
  $('skip').onclick = () => { index = Math.min(cases.length-1,index+1); render(); };
  $('save').onclick = save;
  $('jump').onclick = () => { const n = Number($('goto').value); if (Number.isInteger(n)) { index = Math.min(cases.length-1,Math.max(0,n-1)); render(); } };
  document.onkeydown = event => {
    if (event.target.tagName === 'INPUT') return;
    const value = {k:'keep',h:'hide',u:'uncertain'}[event.key.toLowerCase()]; if (value) label(value);
  };
  controls.forEach(id => { $(id).disabled = false; }); render();
  $('status').textContent = 'Ready. No model scores have been shown.';
  return {save, flush: saver.flush};
}

if (typeof document !== 'undefined') startLabeling({document, fetch:globalThis.fetch.bind(globalThis)});
