import json,pathlib,math,statistics,html,collections
root=pathlib.Path(__file__).resolve().parents[2]
cases={c['id']:c for c in json.loads((root/'local-results/bullet-cases.json').read_text())}
rows={}
for p in sorted((root/'local-results').glob('run-*.json')):
 for r in json.loads(p.read_text()).get('rows',[]):
  if r.get('template')=='bullet-hide' and r['id'] in cases:
   rows[(r['candidate'],r['dtype'],r['id'])]=r
configs=sorted({k[:2] for k in rows})
def selected(config,mask=None,origin=None):
 return [r for k,r in rows.items() if k[:2]==config and (mask is None or cases[r['id']]['kind']==f'bullets-{mask:02d}') and (origin is None or cases[r['id']]['origin']==origin)]
def metric(rs,t=.5):
 pos=[r for r in rs if r['label']=='keep'];neg=[r for r in rs if r['label']=='hide']
 return {'wanted':len(pos),'unwanted':len(neg),'uncertain':sum(r['label']=='uncertain' for r in rs),'kept':sum(r['pKeep']>=t for r in pos),'hidden':sum(r['pKeep']<t for r in neg),'threshold':t,'median_ms':statistics.median([r['callMs'] for r in rs]) if rs else None}
def threshold95(rs):
 pos=sorted(r['pKeep'] for r in rs if r['label']=='keep')
 return pos[len(pos)-math.ceil(.95*len(pos))] if pos else .5
def ratio(n,d):return f'{n}/{d}' if d else 'n/a'
def cell(m):return ratio(m['kept'],m['wanted'])+' kept / '+ratio(m['hidden'],m['unwanted'])+' hidden'
summary=[]
for config in configs:
 for mask in range(1,16):
  real=selected(config,mask,'real-feed');syn=selected(config,mask,'synthetic')
  summary.append({'candidate':config[0],'dtype':config[1],'mask':mask,'real_at_0_5':metric(real),'synthetic_at_0_5':metric(syn),'real_at_95_retention':metric(real,threshold95(real))})
(root/'local-results/bullet-summary.json').write_text(json.dumps(summary,indent=2))
names={('opendecider','q8f16'):'OpenDecider q8f16',('opendecider','fp16'):'OpenDecider fp16',('laya','fp32-fp16-embeddings'):'Laya multilingual'}
configs.sort(key=lambda c:['OpenDecider q8f16','OpenDecider fp16','Laya multilingual'].index(names[c]))
parts=['<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bullet-rule diagnostic</title><style>body{font:15px/1.5 system-ui;color:#173329;background:#f4f5f1;max-width:1200px;margin:30px auto;padding:0 24px}.panel{background:white;border:1px solid #cdd9cf;border-radius:12px;margin:20px 0;padding:22px}table{border-collapse:collapse;width:100%}th,td{padding:9px;text-align:left;border-bottom:1px solid #e2e7de;vertical-align:top}h1{font-size:30px}h2{font-size:21px}.muted{color:#56695c}pre{white-space:pre-wrap;font:inherit}details{margin:14px 0}code{font-size:13px}</style><h1>Bullet-rule diagnostic</h1><p class="muted">83 distinct real-feed previews + 12 synthetic contrast cases · 15 combinations · assistant judgments</p>', '<div class="panel"><h2>What changed</h2><pre>- Hide promotions or ads\n- Hide dating stories\n- Hide clickbait (posts that require you to click before they get to the point)\n- Hide things unrelated to tech unless they\'re funny</pre><p>These exact lines are used in every applicable combination. Fixed question: <strong>Should this post be hidden?</strong> Yes means hide; keep score = 1 − P(yes). Threshold changes do not change model inputs.</p><p>Earlier human labels are not used. Judgments were recorded before inference. Real posts are text-only; uncertain cases are excluded from accuracy counts. Promotions include direct product marketing and invitations to buy, try, or apply. Humor can exempt a post only from the fourth rule.</p><p><strong>This is a diagnostic, not a held-out acceptance test.</strong> The real sample has no clear dating stories. Synthetic cases test that behavior separately.</p></div>']
rules_panel=parts.pop()
parts.append('<div class="panel"><h2>All four bullets — real feed</h2><p>None of the tested candidates meets both the 95% wanted-retention and 80% unwanted-removal targets in this diagnostic.</p><table><tr><th>Model</th><th>At threshold 0.5</th><th>At ≥95% wanted retention</th><th>Calls</th></tr>')
for cfg in configs:
 rs=selected(cfg,15,'real-feed');t=threshold95(rs)
 parts.append(f'<tr><td>{names[cfg]}</td><td>{cell(metric(rs))}</td><td>{cell(metric(rs,t))}<br>t = {t:.4f}</td><td>{len(rs)}/83</td></tr>')
parts.append('</table><p class="muted">The alternate threshold is selected on these same agent labels; it is a best-case diagnostic, not a validated product threshold. The real all-rule set contains 33 keep, 37 hide, and 13 uncertain judgments.</p></div>')
parts.append(rules_panel)
parts.append('<div class="panel"><h2>All 15 combinations — real feed at threshold 0.5</h2><p>A = promotions · D = dating · C = clickbait · T = non-tech unless funny. Cells show wanted kept / unwanted hidden.</p><table><tr><th>Rules</th>'+''.join(f'<th>{names[c]}</th>' for c in configs)+'</tr>')
for mask in range(1,16):
 label='+'.join(ch for i,ch in enumerate('ADCT') if mask&(1<<i))
 parts.append('<tr><td>'+label+'</td>'+''.join('<td>'+cell(metric(selected(c,mask,'real-feed')))+'</td>' for c in configs)+'</tr>')
parts.append('</table><p class="muted">Dating-only has no clear hide examples in this real sample; n/a is a coverage gap, not a passing result.</p></div>')
parts.append('<div class="panel"><h2>Threshold feasibility across combinations</h2><p>For each combination, choose the highest threshold retaining at least 95% of wanted real posts, then check whether at least 80% of unwanted posts are hidden. These are optimistic in-sample checks, not acceptance results.</p><table><tr><th>Model</th><th>Combinations meeting both targets</th></tr>')
for cfg in configs:
 eligible=passed=0
 for mask in range(1,16):
  rs=selected(cfg,mask,'real-feed');m=metric(rs,threshold95(rs))
  if m['wanted'] and m['unwanted']:
   eligible+=1;passed+=m['hidden']>=math.ceil(.8*m['unwanted'])
 parts.append(f'<tr><td>{names[cfg]}</td><td>{passed}/{eligible} measurable combinations</td></tr>')
parts.append('</table></div>')
parts.append('<div class="panel"><h2>Synthetic contrast cases — all four bullets</h2><table><tr><th>Model</th><th>At threshold 0.5</th></tr>')
for cfg in configs:parts.append(f'<tr><td>{names[cfg]}</td><td>{cell(metric(selected(cfg,15,"synthetic")))}</td></tr>')
parts.append('</table><p class="muted">Authored examples, not additional real-feed observations.</p></div>')
for cfg in configs:
 rs=[r for r in selected(cfg,15,'real-feed') if r['label'] in ['keep','hide'] and ((r['pKeep']>=.5)!=(r['label']=='keep'))]
 rs.sort(key=lambda r:abs(r['pKeep']-.5),reverse=True)
 parts.append(f'<div class="panel"><h2>{names[cfg]}: disagreements at 0.5</h2><p>{len(rs)} disagreements on clear real-feed cases. Strongest first.</p>')
 for r in rs[:10]:
  c=cases[r['id']]
  parts.append(f'<details><summary>Expected {r["label"]}, model {"keep" if r["pKeep"]>=.5 else "hide"} · keep score {r["pKeep"]:.4f}</summary><pre>{html.escape(c["text"])}</pre><p>{html.escape(c["judgmentNote"])}</p></details>')
 parts.append('</div>')
(root/'local-results/bullet-report.html').write_text('\n'.join(parts))
md=['# Bullet-rule diagnostic','','83 distinct saved real-feed previews and 12 synthetic contrast cases, each evaluated under all 15 nonempty subsets of the four rules. Labels are assistant judgments recorded before inference; previous human labels are unused. This is not a held-out acceptance test.','','## All four rules: real feed','','At keep-score threshold 0.5. The alternative threshold is selected on this same dataset to retain at least 95% of wanted posts.','','| Model | Default: wanted kept / unwanted hidden | At ≥95% retention |','|---|---|---|']
for cfg in configs:
 rs=selected(cfg,15,'real-feed')
 md.append(f'| {names[cfg]} | {cell(metric(rs))} | {cell(metric(rs,threshold95(rs)))} |')
md += ['','Full-rule judgments: 33 keep, 37 hide, 13 uncertain. Uncertain cases are excluded from counts.','','## All combinations: real feed at 0.5','','A = promotions/ads; D = dating; C = clickbait; T = unrelated to tech unless funny.','','| Rules | '+' | '.join(names[c] for c in configs)+' |','|---|'+'---|'*len(configs)]
for mask in range(1,16):
 label='+'.join(ch for i,ch in enumerate('ADCT') if mask&(1<<i))
 md.append('| '+label+' | '+' | '.join(cell(metric(selected(c,mask,'real-feed'))) for c in configs)+' |')
md += ['','The saved real feed has no clear dating stories. Dating recall is tested only by synthetic cases. There are three dating-positive synthetic examples, including one funny dating story whose humor does not override the separate dating rule.','','## Synthetic cases: all four rules at 0.5','','| Model | Wanted kept / unwanted hidden |','|---|---|']
for cfg in configs:md.append(f'| {names[cfg]} | {cell(metric(selected(cfg,15,"synthetic")))} |')
md += ['','## Input and limitations','','The exact applicable bullet lines are placed after `Filtering rules:` and followed by `Should this post be hidden?`. True means hide, false means keep; the keep score is one minus the true probability. Strictness changes only the downstream threshold.','','Promotions include direct product marketing and invitations to buy, try, or apply. Useful educational links and noncommercial project demonstrations are not automatically ads. Only the fourth rule has a humor exception. Missing-media and ambiguous cases remain uncertain.','','The text-only capture contains previews and available quoted text, not images or expanded links. This exploration has consumed the saved feed sample; future acceptance testing needs fresh examples. No model or product threshold is selected.']
(root/'local-results/bullet-report.md').write_text('\n'.join(md)+'\n')
for cfg in configs:
 rs=selected(cfg,15,'real-feed');print(names[cfg],len(selected(cfg)), 'full real',cell(metric(rs)), '95%',cell(metric(rs,threshold95(rs))), 'synthetic',cell(metric(selected(cfg,15,'synthetic'))))
