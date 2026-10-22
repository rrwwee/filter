"""Build local instruction-following data; synthetic posts are explicitly authored fixtures."""
import hashlib, itertools, json, pathlib, random

ROOT = pathlib.Path(__file__).resolve().parents[2] / 'local-results'
OUT = ROOT / 'finetune-broad'
OUT.mkdir(exist_ok=True)
RNG = random.Random(20261020)

# Each group has distinct post scenarios, not substitutions into one text template.
# Tags describe visible content, not what the model should decide independently of instructions.
GROUPS = {
'tech': [
 'A hash map gives average constant-time lookups, but collisions can make individual lookups slower.',
 'Our database migration failed because the new index locked writes. Building it concurrently fixed the outage.',
 'I measured the compiler change: peak memory fell by 18%, with no change in the generated machine code.',
 'The neural network gets confident predictions wrong when the camera lighting changes. We need a separate evaluation set.',
 'This patch fixes a race between the cache eviction worker and concurrent readers. The lock now covers both operations.',
 'The browser extension can classify each new post locally using a small model and WebGPU. No server request is needed.'
],
'ad,tech': [
 'Launch offer: get 40% off CloudCrate database hosting. Start your paid plan at cloudcrate.example today.',
 'Sponsored by PixelDock: our new USB hub has six ports. Shop now using code DESK for a discount.',
 'We just launched TraceBee, a paid error-monitoring service. Sign up for a free trial and upgrade your team.',
 'Introducing our premium AI coding assistant. Subscribe this week to get three months for the price of one.',
 'Limited-time sale on CircuitLeaf mechanical keyboards. Order yours now before the offer ends.',
 'Paid partnership: TaskHarbor automates your team reports. Book a sales demo through the link in my profile.'
],
'dating': [
 'My first date brought a handwritten list of questions about our future wedding. We had only met an hour earlier.',
 'After six months on dating apps, I met my partner at a pottery class. We are going on our fourth date tonight.',
 'He spent our entire dinner describing his ex. I declined a second date.',
 'I asked her out after we kept meeting at the library. Our first date was a walk by the river.',
 'My boyfriend and I disagree about moving in together. We have been dating for a year.',
 'The person I matched with cancelled our date three times. I finally stopped rearranging my weekends.'
],
'clickbait,tech': [
 'One secret setting is destroying your laptop battery. Click through to find out which setting it is.',
 'I discovered a programming trick that changes everything. The actual trick is only in the linked article.',
 'This startup made a mistake that cost millions. Open the link to learn what the mistake was.',
 'You will never guess which browser feature is leaking your data. I reveal it after the jump.',
 'There is a reason your SQL queries are slow, but I am saving the explanation for my linked newsletter.',
 'The best tool for developers is not what you think. Click my profile link for the name.'
],
'funny': [
 'My cat has scheduled another meeting that could have been a nap.',
 'I bought a standing desk for my plants. They are the only ones showing professional growth.',
 'The sourdough starter has more demanding dietary requirements than anyone else in this household.',
 'My dog heard the word budget and immediately buried another asset in the garden.',
 'I joined a procrastination club. Our first meeting has been postponed indefinitely.',
 'The washing machine ate one sock and left the other as a warning.'
],
'art': [
 'I sketched the station using charcoal, leaving the paper bare for the bright windows.',
 'A limited palette of ultramarine and burnt sienna makes convincing shadows in this portrait.',
 'The exhibition pairs woven textiles with ceramics. The repeated curves connect the two materials.',
 'I used a dry brush to give the sea foam an uneven texture in this landscape painting.',
 'Here is my figure drawing process: establish the gesture first, then add the larger shadow shapes.',
 'For this collage I layered translucent paper over a photograph, then cut holes to expose the original image.'
],
'diet': [
 'I am counting calories every day to lose weight before summer and tracking the number on the scale.',
 'My weight-loss meal plan restricts carbohydrates and aims for a daily calorie deficit.',
 'I weigh all my food because portion control is the core of my current diet.',
 'This is my weekly fat-loss update: lower calorie intake and daily weigh-ins.',
 'I want to lose ten pounds, so I am replacing dessert with a low-calorie shake.',
 'My diet coach adjusted my macros to keep me in a calorie deficit while losing body fat.'
],
'spoilers': [
 'Spoiler for The Glass Harbor finale: the missing captain was the narrator all along.',
 'The ending of Moon Orchard reveals that the two sisters are the same person at different ages.',
 'Major plot reveal: in The Last Lantern, the detective kills his own brother in the final scene.',
 'I finished the game Ash Corridor. The final boss is your childhood friend, who betrays you in chapter nine.',
 'Spoilers for season two of Hollow Street: Mara dies in the final episode and the mayor escapes.',
 'The twist at the end of Silver Ferry is that the passengers have already died before boarding.'
],
'jobs,ad,tech': [
 'We are hiring a backend engineer to build payment services. Apply with your CV at careers.example.',
 'Open role: frontend developer, remote, full time. Send your portfolio to our recruiting team.',
 'Our robotics team needs a controls engineer. The job description and application form are linked here.',
 'Hiring a security researcher to audit our cloud platform. Applications close on Friday.',
 'Join our data infrastructure team as a staff engineer. Apply through our careers page.',
 'Recruiting mobile developers for a six-month contract. Message us to apply.'
],
'profanity': [
 'The train was cancelled again. This is fucking ridiculous.',
 'I spilled coffee over the clean laundry. Shit, that was the last thing I needed.',
 'What an asshole. He blocked the entire pavement with his car.',
 'This fucking queue has not moved in an hour.',
 'The parcel was delivered to the wrong street again. Such bullshit.',
 'That was a shitty way to treat the waiter.'
],
'politics': [
 'The candidates debated immigration policy and the proposed changes to election funding.',
 'Parliament votes tomorrow on the coalition government’s tax bill.',
 'The mayor is campaigning for reelection on a promise to change housing regulations.',
 'The opposition party announced its manifesto ahead of the national election.',
 'Senators disagreed over the proposed constitutional amendment during today’s debate.',
 'The council election results leave no party with an overall majority.'
],
'sports': [
 'The basketball team won in overtime after a three-pointer at the buzzer.',
 'The goalkeeper saved two penalties and kept a clean sheet in the cup final.',
 'The tennis match went to five sets before the defending champion won.',
 'The cycling stage ended with a sprint finish and a new leader in the overall standings.',
 'The baseball pitcher struck out twelve batters in seven innings.',
 'The marathon winner broke the course record by forty seconds.'
],
'neutral': [
 'I watered the balcony plants this morning and repotted the basil into a larger container.',
 'The soup needs another ten minutes on low heat before adding the parsley.',
 'The train leaves from platform six at half past three.',
 'We walked along the coast and watched the tide go out before heading home.',
 'The library is extending its opening hours during the exam period.',
 'I repaired the loose drawer handle with a longer screw and a washer.'
],
'tech,funny': [
 'My code works on my machine, which is why we are shipping my machine to every customer.',
 'The database and I have an agreement: I pretend to understand its query plan and it pretends to use my index.',
 'I named the server Titanic because the monitoring dashboard promised it was unsinkable.',
 'My rubber duck requested a transfer after hearing the latest architecture proposal.',
 'The build is green because we commented out the red part.',
 'I asked the cache to forget something and it said it would get back to me eventually.'
],
}
TAGS = ['ad','dating','clickbait','tech','funny','art','diet','spoilers','jobs','profanity','politics','sports']
PHRASES = {'ad':'promotions or ads','dating':'dating stories','clickbait':'posts that withhold their point until I click','tech':'technology-related posts','funny':'funny posts','art':'art posts','diet':'dieting and weight-loss content','spoilers':'plot spoilers','jobs':'job advertisements','profanity':'posts containing profanity','politics':'political posts','sports':'sports posts'}
ALT = {'ad':'sales pitches and sponsored content','dating':'stories about romantic dates and relationships','clickbait':'teasers that make me open a link to learn the actual point','tech':'content about computing, software, or technology','funny':'jokes and humorous observations','art':'drawing, painting, and other visual art','diet':'calorie restriction and attempts to lose weight','spoilers':'revelations about story endings or major plot twists','jobs':'recruitment and hiring announcements','profanity':'swearing','politics':'elections, political parties, or government policy','sports':'competitive sport and match results'}

def policy(kind, tags): return {'kind':kind,'tags':list(tags),'id':kind+':'+','.join(tags)}
policies = [policy('hide',[t]) for t in TAGS if t not in ('politics','sports')]
policies += [policy('only',[t]) for t in ['ad','dating','tech','art','funny']]
policies += [policy('hide',['ad','dating']),policy('hide',['clickbait','diet']),policy('hide',['spoilers','profanity']),policy('tech_funny',[]),policy('all',[])]
unseen = [policy('hide',['ad','dating','clickbait']),policy('hide',['diet','spoilers']),policy('hide',['jobs','profanity']),policy('art_except_diet',[]),policy('tech_funny_no_ads',[]),policy('original_four',[])]
novel = [policy('hide',[t]) for t in ['politics','sports']]

def clauses(p, alt=False):
 words=ALT if alt else PHRASES
 if p['kind']=='all':return ['Keep every post visible; do not filter anything']
 if p['kind']=='hide':return ['Hide '+words[t] for t in p['tags']]
 if p['kind']=='only':return ['Keep only '+words[p['tags'][0]]+'; hide everything else']
 if p['kind']=='tech_funny':return ['Keep technology-related posts and anything funny; hide the rest']
 if p['kind']=='original_four':return ['Hide promotions or ads','Hide dating stories','Hide posts that withhold their point until I click','Hide things unrelated to tech unless they are funny']
 if p['kind']=='tech_funny_no_ads':return ['Keep technology-related posts or funny posts','Hide promotions or ads even when they are funny or about tech']
 return ['Keep art posts','Hide everything else, including any dieting content even if it mentions art']

def render(p,style):
 c=clauses(p,style in ['conversational','checklist'])
 if style=='bullets':return '\n'.join('- '+x for x in c)
 if style=='paragraph':return '. '.join(c)+'.'
 if style=='numbered':return '\n'.join(f'{i+1}. {x}' for i,x in enumerate(c))
 if style=='conversational':return 'Please tailor my feed to these preferences: '+('; '.join(c))+'. Thanks.'
 return 'My feed preferences:\n'+'\n'.join('[ ] '+x for x in c)

def label(post,p):
 f=post['flags'];k=p['kind'];ts=p['tags']
 if k=='all':return False
 if k=='hide':
  vals=[f.get(t) for t in ts]
  return True if True in vals else (None if None in vals else False)
 if k=='only':return None if f.get(ts[0]) is None else not f[ts[0]]
 if k=='original_four':
  v=[f.get('ad'),f.get('dating'),f.get('clickbait'),post['original_flags'][3] if post['origin']=='real-feed' else not(f['tech'] or f['funny'])]
  return True if any(x==True for x in v) else None if None in v else False
 if post['origin']=='real-feed':
  # The fourth original annotation already combines technology and the humor exception.
  if k=='tech_funny':return post['original_flags'][3]
  if k=='tech_funny_no_ads':
   a,b=f['ad'],post['original_flags'][3]
   return True if a is True or b==1 else None if a is None or b is None else False
  return None
 if k=='tech_funny':return not(f['tech'] or f['funny'])
 if k=='tech_funny_no_ads':return f['ad'] or not(f['tech'] or f['funny'])
 return not f['art'] or f['diet']


def row(post,p,style,suite):
 y=label(post,p)
 if y is None:return None
 instruction=render(p,style)
 return {'id':f'{suite}|{post["id"]}|{p["id"]}|{style}','post_id':post['id'],'policy_id':p['id'],'style':style,'suite':suite,'origin':post['origin'],'state':post['text'],'instruction':instruction,'questions':{'hide':{'type':'noul','instructions':'Filtering rules:\n'+instruction+'\n\nShould this post be hidden?','criteria':{'true':'Hide the post.','false':'Keep the post visible.'}}},'expected':{'hide':bool(y)}}

def build():
 posts=[]

 for group,texts in GROUPS.items():
  for i,text in enumerate(texts):
   tags=set(group.split(',')); flags={t:t in tags for t in TAGS}
   split='test' if group in ['politics','sports'] or i>=4 else 'validation' if i==3 else 'train'
   posts.append({'id':f'authored-{group.replace(",","-")}-{i}','text':text,'flags':flags,'origin':'authored-synthetic','split':split,'scenario_group':group})
 oldplan=json.loads((ROOT/'finetune-promotions/plan.json').read_text())
 original=json.loads((ROOT/'bullet-judgments.json').read_text())['posts']
 for p in original:
  if p['origin']!='real-feed':continue
  pid=p['postId']; fs=p['flags']; split='test' if pid in oldplan['split_ids']['test'] else 'validation' if pid in oldplan['split_ids']['validation'] else 'train'
  posts.append({'id':pid,'text':p['text'],'flags':dict(zip(['ad','dating','clickbait'],[None if v is None else bool(v) for v in fs[:3]])),'original_flags':fs,'origin':'real-feed','split':split,'scenario_group':pid})

 data={k:[] for k in ['train','validation','test']}
 for post in posts:
  split=post['split']
  if split in ['train','validation']:
   valid=[p for p in policies if label(post,p) is not None]
   chosen=RNG.sample(valid,min(12 if split=='train' else 8,len(valid)))
   for i,p in enumerate(chosen):
    r=row(post,p,['bullets','paragraph','numbered'][i%3],split);data[split].append(r)
  else:
   valid=[p for p in policies if label(post,p) is not None]
   chosen=RNG.sample(valid,min(8,len(valid)))
   for p in chosen:
    for style,suite in [('bullets','heldout_posts'),('paragraph','format_pair'),('conversational','unseen_wording'),('checklist','unseen_wording')]:
     data['test'].append(row(post,p,style,suite))
   for p in unseen+novel:
    r=row(post,p,'conversational','unseen_criteria' if p in novel else 'unseen_combinations')
    if r:data['test'].append(r)

 # Counterfactuals are paired by post: hide a topic vs keep only that topic.
 # Evaluate on held-out authored posts, never on training posts.
 for post in posts:
  if post['split']=='test' and post['origin']=='authored-synthetic':
   active=next((t for t in ['ad','dating','tech','art','funny','diet','spoilers','jobs','profanity','politics','sports'] if post['flags'][t]),None)
   if active:
    for kind in ['hide','only']:data['test'].append(row(post,policy(kind,[active]),'paragraph','counterfactual'))

 for s,rows in data.items():
  RNG.shuffle(rows)
  (OUT/(s+'.jsonl')).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
 assert all({p['id'] for p in posts if p['split']==a}.isdisjoint({p['id'] for p in posts if p['split']==b}) for a,b in itertools.combinations(data,2))
 assert all({r['state'] for r in data[a]}.isdisjoint({r['state'] for r in data[b]}) for a,b in itertools.combinations(data,2))
 (OUT/'posts.json').write_text(json.dumps(posts,ensure_ascii=False,indent=2))
 manifest={'seed':20261020,'labels':'Authored synthetic content tags and existing assistant real-feed judgments; not user-confirmed. Missing labels are excluded.','split':'By post before instruction expansion; original 16-post promotion test remains held out. Authored scenarios have distinct prose but share topic families across splits.','train_policies':policies,'heldout_combinations':unseen,'untrained_criteria':novel,'training_styles':['bullets','paragraph','numbered'],'unseen_styles':['conversational with alternate phrases','checklist with alternate phrases'],'counts':{s:{'rows':len(rs),'posts':len({r['post_id'] for r in rs}),'hide':sum(r['expected']['hide'] for r in rs)} for s,rs in data.items()},'dataset_sha256':{s:hashlib.sha256((OUT/(s+'.jsonl')).read_bytes()).hexdigest() for s in data}}
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
 print(json.dumps(manifest['counts'],indent=2))

if __name__ == "__main__":
 build()
