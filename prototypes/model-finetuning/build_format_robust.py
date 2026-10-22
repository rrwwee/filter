"""Decouple wording from layout; reserve a second, genuinely new final set."""
import collections,hashlib,json,pathlib,random,re
import build_compositional as base

ROOT=base.ROOT;OLD=ROOT/'finetune-compositional';OUT=ROOT/'finetune-format-robust'
FINAL='''
ad tech opensource | We released the source of FrameCrate under Apache 2.0. Try the new screen recorder today and send us your feedback.
ad tech | Buy a FrameCrate Pro license this month and get six months of cloud storage included.
tech opensource | A patch to the public-source scheduler fixes a deadlock when a worker exits during shutdown.
dating funny | On our second date he asked whether we could split the bill proportionally to our phone battery percentages.
dating | My partner and I are deciding whether to move to the same city after two years of dating.
art diet | My photo series records the low-calorie meals and weekly weigh-ins from my weight-loss challenge.
art | I am building a sculpture from folded copper sheets and translucent resin.
tech funny | I renamed the error log success.log. The team has never been more productive.
ad tech funny | Buy our password manager: finally, something in your life that remembers what you told it yesterday.
ad tech funny opensource | Download our GPL-licensed timer app. It is free software, and its only paid employee is the snooze button.
tech clickbait | There is one config key that solves this proxy error. I only reveal its name after you open the article.
tech | Set proxy_read_timeout to 90 seconds to avoid this timeout. The linked article explains the limits of that workaround.
jobs ad art | A printmaking workshop needs an instructor. Apply with a portfolio and your availability.
jobs ad tech opensource | Join the paid maintainer team for our MIT-licensed CLI. Applications are open on the project website.
tech | A hiring manager asked me how garbage collection handles cycles. Here is the example I used, not a job opening.
politics art | My screen print criticizes the opposition party's voting-policy proposal using a pattern of crossed-out ballot boxes.
sports tech | The fencing club measures reaction time with a light sensor and a microcontroller connected to a laptop.
sports | The swimming relay ended with the visitors touching the wall a tenth of a second ahead.
spoilers | Spoiler for The Salt Archive: the archivist deliberately burns the last letter and betrays the expedition at the ending.
spoilers tech | Spoiler for the game Blue Circuit: the tutorial guide deletes the city and becomes the final opponent.
tech | Blue Circuit reduces shader compilation stutter by warming its pipeline cache before a level loads. No story events are described.
profanity funny | Shit, I alphabetized the spice rack and now dinner is delayed by a filing dispute.
diet | I am logging smaller portions and calories to lose weight over the next three months.
ad diet | Order our calorie-controlled weight-loss meal boxes and get a discount on your first week.
art dating | I carved a small wooden portrait of my boyfriend for the anniversary of our first date.
art sports | My watercolor shows the goalkeeper stretching toward the ball in the championship match.
tech | This accessibility article quotes an ad saying 'Subscribe now' to explain why the button label is misleading. It does not sell a subscription.
art | These cake paintings are studies in texture and reflected color, not advice about food intake or losing weight.
tech | The software calls a timestamp comparison a date match. This is about computer time values, not romantic relationships.
funny | My vacuum robot has spent twenty minutes contemplating a sock. Same, honestly.
clickbait funny | The penguin has a brilliant excuse for missing the meeting. You must follow the link to read the punchline.
ad art | Order a signed etching from my new collection before the weekend sale ends.
'''

def number(s):return int(hashlib.sha256(s.encode()).hexdigest()[:12],16)
def rewrite(r,version,style,pair_suffix):
 p=next(p for p in base.policies() if p['id']==r['policy_id'])
 clauses=p['texts'][version]
 instruction='\n'.join('- '+c for c in clauses) if style=='bullets' else '. '.join(clauses)+'.'
 x=dict(r,id=r['id']+'|cross-'+str(version)+'-'+style,style=style,instruction=instruction)
 x['questions']={'hide':dict(r['questions']['hide'],instructions='Filtering rules:\n'+instruction+'\n\nShould this post be hidden?')}
 if r['pair_id']:x['pair_id']=r['pair_id']+pair_suffix
 return x

def build():
 rng=random.Random(20261023);data={}
 for split in ['train','validation']:
  old=[json.loads(s) for s in (OLD/(split+'.jsonl')).read_text().splitlines()]
  chosen=[r for r in old if split=='validation' or r['pair_id'] or number(r['id'])%2==0]
  rows=[]
  for r in chosen:
   # All four wording families occur in both layouts, including if/otherwise forms.
   key=r['pair_id'] or r['id'];v=number(key+'wording')%4
   for style in ['bullets','paragraph']:rows.append(rewrite(r,v,style,'|'+style))
  rng.shuffle(rows);data[split]=rows
 # Every final post is unseen by training, validation and the first fresh diagnostic.
 posts=[]
 for i,line in enumerate(FINAL.strip().splitlines()):
  tags,text=line.split('|',1);ts=set(tags.split());f={t:t in ts for t in base.TAGS};f['offtopic']=not(f['tech'] or f['funny'])
  posts.append({'id':f'final-authored-{i:02}','text':text.strip(),'flags':f,'origin':'authored-synthetic'})
 previous=[]
 previous+=json.loads((ROOT/'finetune-broad/posts.json').read_text())
 previous+=sum(json.loads((OLD/'posts.json').read_text()).values(),[]) if (OLD/'posts.json').exists() else []
 previous += json.loads((OLD/'fresh-feed-labeled.json').read_text())
 # The original v2 builder does not save its authored post catalog separately.
 previous += sum((base.authored(s) for s in ['train','validation','test']),[])
 oldg=[base.grams(p['text']) for p in previous];excluded=[]
 for p in json.loads((OUT/'fresh-feed-labeled.json').read_text()):
  g=base.grams(p['text']);overlap=max(len(g&h)/max(1,min(len(g),len(h))) for h in oldg)
  seen_id=any(p['source'].rsplit('/',1)[-1] in x['id'] for x in previous)
  if overlap>=.7 or seen_id:excluded.append({'id':p['id'],'overlap':overlap});continue
  p['flags']['offtopic']=base.evaluate(['not',['or','tech','funny']],p['flags']);posts.append(p)
 ps=base.policies();test=[]
 for post in posts:
  available=[p for p in ps if base.evaluate(p['expr'],post['flags']) is not None]
  critical=[p for p in available if p['id'] in ['original_four','tech_or_funny','only_except:art:diet','unless:ad:opensource']]
  selected=critical+rng.sample([p for p in available if p not in critical],min(8,len(available)-len(critical)))
  for p in selected:
   for ver,style in [(0,'bullets'),(0,'paragraph'),(3,'casual')]:test.append(base.make_row(post,p,ver,style,p['family']))
  active=[t for t in base.WORDS if post['flags'].get(t) is True]
  if active:
   t=rng.choice(active)
   for k in ['hide','only']:
    p=next(p for p in ps if p['id']==k+':'+t)
    test.append(base.make_row(post,p,3,'paragraph','opposite_pair','final:'+post['id']+':'+t))
 data['test']=test
 for a,b in [('train','validation'),('train','test'),('validation','test')]:assert {base.norm(r['state']) for r in data[a]}.isdisjoint({base.norm(r['state']) for r in data[b]})
 for s,rows in data.items():
  assert len({r['id'] for r in rows})==len(rows)
  (OUT/(s+'.jsonl')).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
 manifest={'seed':20261023,'post_policy':'Train/validation use the prior run split. Final test posts are new and overlap checked against all earlier experiments including the failed first fresh test.','fresh_feed_exclusions':excluded,'hashes':{s:hashlib.sha256((OUT/(s+'.jsonl')).read_bytes()).hexdigest() for s in data},'counts':{s:{'rows':len(rows),'posts':len({r['post_id'] for r in rows}),'hide':sum(r['expected']['hide'] for r in rows)} for s,rows in data.items()},'correction':'Wording and layout independently crossed; the same criterion/post appears in both bullet and paragraph form. Includes explicit if/otherwise wording in training. The first fresh test revealed the design issue and is now diagnostic, not final.'}
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest['counts'],indent=2));print('Excluded prior posts',len(excluded))
if __name__=='__main__':build()
