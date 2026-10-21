"""Locally authored contrastive instruction data and a newly sealed holdout."""
import collections,hashlib,json,pathlib,random,re

ROOT=pathlib.Path(__file__).resolve().parents[2]/'local-results'
OUT=ROOT/'finetune-compositional';OUT.mkdir(exist_ok=True)
TAGS=['ad','dating','clickbait','tech','funny','art','diet','spoilers','jobs','profanity','politics','sports','opensource','offtopic']
WORDS={'ad':'promotions or advertisements','dating':'dating stories','clickbait':'posts that withhold the point until I click','tech':'technology posts','funny':'jokes or funny posts','art':'art posts','diet':'dieting or weight-loss posts','spoilers':'plot spoilers','jobs':'job advertisements','profanity':'posts with profanity','politics':'politics','sports':'sports','opensource':'posts about open-source projects'}
ALT={'ad':'sales pitches and sponsored posts','dating':'romantic relationship anecdotes','clickbait':'click-through teasers that do not give the actual point','tech':'content about software, computing, or technology','funny':'humorous content','art':'drawing, painting, and visual art','diet':'calorie restriction or attempts to lose weight','spoilers':'major story or ending reveals','jobs':'recruitment announcements','profanity':'swearing','politics':'elections and political affairs','sports':'competitive sport','opensource':'projects with publicly available source code under an open-source license'}

# Distinct situations with deliberately overlapping attributes. These are synthetic.
CATALOG={
'train': '''
ad tech opensource | We launched OpenCanvas under the MIT license. Try our new drawing editor today; the full source is on our public repository.
ad tech | Our new closed-source drawing editor is available for $12 a month. Start your subscription today.
tech opensource | I fixed a memory leak in a GPL-licensed renderer. The bug was a reference cycle between two cache entries.
ad art | My print shop is open. Buy a signed linocut this weekend and get free shipping.
art | The wet edge matters more than brush size when blending these watercolor washes.
art diet | My sketchbook tracks a strict weight-loss diet: I draw every meal and write its calorie limit underneath.
art funny | I tried painting a graceful swan; my canvas now depicts a furious potato with a neck.
diet | I am cutting my daily calories to lose weight before the holiday.
tech diet | I wrote a spreadsheet macro that calculates my calorie deficit for my weight-loss plan.
ad diet | Join our paid fat-loss program and get a personalized calorie-restriction plan.
dating funny | My date asked for my star sign, then opened a spreadsheet of acceptable answers.
dating | We have been dating for eight months and are deciding whether to move in together.
tech dating | My partner and I met while debugging the same compiler bug. Our first date was coffee after the fix shipped.
ad dating | Subscribe to our matchmaking service to meet singles near you.
funny | My houseplant has filed a complaint about the inconsistent management of this household.
tech funny | The database promised eventual consistency. I would like an appointment with eventual.
ad tech funny | Our paid backup app remembers your files even when you forget why you saved them. Subscribe today.
tech | Using a monotonic clock prevents elapsed-time measurements from jumping when the system clock changes.
tech clickbait | One missing database setting is ruining your performance. Open my article to learn its name.
tech | The missing setting is synchronous_commit. Disabling it trades durability for latency; I explain the tradeoff in the linked article.
clickbait art | This one painting technique changes everything. The technique itself is revealed only in the link.
art | I start this portrait with a large value study before adding color. The linked video shows the brushwork.
jobs ad tech | Hiring a frontend engineer to build our accessibility tools. Send an application through our careers page.
tech | I interviewed a frontend candidate today and learned a useful way to test keyboard navigation.
jobs ad art | Our studio is recruiting a ceramic artist. Apply with three photographs of your work.
art | I finished my ceramic residency and displayed the bowls at the community gallery.
politics | The city council debated the voting district boundaries before next month's election.
politics tech | Parliament is debating a bill requiring audits of automated decision systems.
sports | The volleyball final went to five sets before the visitors won.
sports tech | Optical tracking measured the serve speed during the tennis final; the tracking camera runs a neural network.
spoilers | Spoiler for The Copper Stair: the missing sister is revealed to be the detective in the last chapter.
spoilers tech | Spoiler for the game Kernel Island: the friendly maintenance robot is the final boss.
tech | Kernel Island uses a custom renderer with clustered lighting; this post contains no story details.
profanity funny | Fuck, I spent ten minutes looking for the glasses I was wearing.
profanity tech | This fucking dependency silently changed its return type between patch versions.
ad opensource tech | Support our Apache-licensed database by buying a hosted plan. The self-hosted source remains available.
opensource tech | The Apache-licensed database can be self-hosted. Here is a walkthrough of its write-ahead log, with no sales offer.
ad tech | Our proprietary database service starts at $99 per month. Contact sales for a demo.
dating funny tech | We agreed to stop discussing programming on dates. Then we spent dessert arguing about null pointers.
art sports | I drew the goalkeeper's gloves in charcoal after the football match.
art politics | My mural depicts the candidates in the local election and their campaign slogans.
ad art opensource tech | Try our open-source animation tool. Its source is MIT-licensed, and you can download the app free today.
ad art tech | Purchase the new proprietary animation suite and get our premium brush pack.
diet funny | My calorie tracker thinks the birthday cake was a formatting error. Sadly it was not.
ad sports | Buy tickets for Saturday's rugby final at the stadium box office.
ad tech jobs | We are hiring a developer advocate for our open roles. Apply on the recruitment site.
tech opensource | This open-source parser handles quoted commas by tracking whether the cursor is inside a string.
tech funny opensource | The open-source linter found 83 problems. I closed the terminal, so now there are none.
ad tech funny opensource | Download our MIT-licensed linter today. It judges your code so your colleagues can take a lunch break.
politics funny | The candidate promised shorter meetings, then launched a three-hour speech explaining the policy.
tech clickbait ad | Subscribe to the newsletter to discover the secret command that fixes your terminal. I will not name it here.
tech ad | Our newsletter teaches shell scripting. This issue explains set -e and its pitfalls. Subscribe for future issues.
art dating | I painted a portrait of my girlfriend to mark our first anniversary together.
art | The portrait uses a cool shadow under the chin and a warm highlight on the cheekbone.
tech diet ad | Buy our nutrition app to track calorie deficits and hit your target weight.
tech sports funny | My running watch congratulated me on a personal best while I was riding the bus.
profanity dating | My date spent the whole evening insulting the waiter. What an asshole.
spoilers funny | Spoiler for Velvet Comet: the emperor is three raccoons in a coat. At least the costume budget explains itself.
clickbait | The reason everyone is leaving that city will shock you. You need to click to find out what it is.
 | The library has added quiet study desks on the second floor.
 | I repotted the fern into a clay pot and moved it away from direct sunlight.
tech | This post quotes an advertisement as a bad example of API documentation. It is an analysis, not an offer to buy anything.
dating | We booked our second date for the museum. We have not discussed moving in together.
art diet | The exhibition is my illustrated diary of a weight-loss program, with calorie targets beside each photograph.
''',
'validation': '''
ad tech opensource | Announcing our BSD-licensed note app. Try it today; the complete source is available for everyone to modify.
ad tech | Sign up for the paid, closed-source note app. The annual plan is discounted this week.
tech opensource | I traced a crash in an open-source text editor to an invalid cursor offset.
dating funny | My date brought a compatibility quiz. We disagreed about the correct font before reaching question two.
dating | My girlfriend and I are planning a weekend away for our anniversary.
art diet | These drawings document my restrictive weight-loss meals and daily calorie allowance.
art | I carved the texture into a clay tile before applying the glaze.
tech funny | The test passed locally, so I am applying for local to become our production environment.
tech clickbait | There is a hidden shortcut that fixes this editor issue. Follow the link to discover the shortcut.
tech | The shortcut is Ctrl+Shift+P. It opens the command palette; the linked tutorial covers the less common commands.
jobs ad tech | Recruiting a firmware engineer for our device team. Apply by email this week.
politics tech | The legislature is considering new rules for biometric databases.
sports | The hockey match ended with a penalty shootout.
spoilers | Spoiler for Amber House: the guardian burns the diary and escapes in the final scene.
profanity funny | Shit, my attempt at a tidy desk has become a second, smaller untidy desk.
ad art | Order a signed poster from my exhibition before the sale closes.
''',
'test': '''
ad tech opensource | Meet PatchNest, our new LGPL-licensed code editor. Download it today; contributions to the public source repository are welcome.
ad tech | Reserve your seat for a sales demo of our proprietary code editor. Paid licenses start next week.
tech opensource | A contributor to an open-source audio codec removed an unnecessary allocation from the decoding loop.
dating funny | Our first date was going well until we discovered we had both brought a prepared exit excuse.
dating | My boyfriend asked whether we should keep separate apartments for another year.
art diet | My latest collage charts a month of weight-loss meals, including the daily calorie ceilings I followed.
art | I am layering indigo ink over torn paper to make a winter seascape.
tech funny | Our microservices are independent. They just need all the other services to agree before doing anything.
ad tech funny | Subscribe to our uptime monitor. It will wake you before your customers do, which is our very specific form of kindness.
ad tech funny opensource | Try our open-source deployment helper today. The MIT-licensed code is free, and the jokes in the error messages are complimentary.
tech clickbait | I found the single flag that stops these container crashes. Its name is in the linked post, not here.
tech | The flag is --init; it installs a tiny init process that reaps zombies. My link contains a reproducible example.
jobs ad art | A public gallery is hiring an exhibition designer. Submit a portfolio to apply.
art | I installed the exhibition lighting so the sculpture casts a shadow onto the far wall.
jobs ad tech | We need an embedded Rust developer for our sensor project. Applications are open on the company site.
tech | A recruiter asked me about Rust lifetimes. Here is the example I used to explain borrowing to them.
politics tech | The new campaign-finance proposal includes disclosure rules for AI-generated political adverts.
politics funny | The campaign's promise of complete transparency arrived in an unreadable PDF scan.
sports tech | The baseball broadcast estimated bat speed from two synchronized high-speed cameras.
sports | The badminton semifinal was decided by a long rally at match point.
spoilers | Spoiler for Paper Horizon: the courier destroys the map and becomes the new antagonist in the closing scene.
spoilers tech | Spoiler for the game Static Garden: your companion overwrites your save and becomes the final enemy.
tech | Static Garden's loading screen streams textures in smaller chunks to avoid memory spikes. No plot details here.
profanity funny | Fuck, I labelled the box miscellaneous and now every object I own qualifies.
diet | I have started weighing portions to maintain a calorie deficit during my weight-loss program.
ad diet | Purchase our meal-replacement plan for a lower-calorie approach to losing weight.
art dating | I made a lino print of the cafe where my partner and I went on our first date.
art sports | This sculpture captures the movement of a sprinter leaving the starting blocks.
tech opensource | This code review compares two free software licenses and explains why their linking rules differ.
tech | I am quoting the phrase 'Buy our backup service' to explain why marketing copy should not appear in an error message.
 | The footbridge is closed for repairs until Monday morning.
 | I cooked lentil soup for dinner and saved the leftovers for tomorrow.
art | Painting fruit does not mean dieting: this is a study of reflected light on a bowl of pears.
tech | Our database uses the term dating internally for assigning timestamps. This post is about timestamp ordering, not romance.
funny | My umbrella is excellent at identifying which direction I least want to walk.
ad art | Buy an original charcoal drawing from my studio sale this weekend.
'''}


CATALOG['train'] += """
clickbait funny | My toaster has a secret second career. Click the link to discover which profession has been stealing your breakfast.
politics art | My political cartoon shows the mayor juggling the promises from the election manifesto.
sports tech | The cycling team uses open telemetry software to measure power output during the race.
opensource tech jobs ad | We are hiring maintainers for our GPL-licensed editor. Apply to the open-source engineering team through our jobs page.
clickbait funny tech | The computer's favorite excuse for losing my homework will surprise you. I reveal the punchline only after you click.
art politics funny | I drew parliament as a flock of pigeons fighting over one chip. It is a political cartoon about the budget vote.
"""
CATALOG['validation'] += """
sports tech | A sensor on the racing bicycle estimates torque and transmits the readings to the coach's laptop.
politics art | I painted a mural criticizing the governing party's election promises.
clickbait funny | The squirrel has a ridiculous explanation for stealing the picnic. Open the link to read the punchline.
opensource tech jobs ad | The open-source robotics project is hiring a paid maintainer. Apply with a link to your contributions.
"""
CATALOG['test'] += """
politics art | My new woodcut is a protest against the government's voting bill, with ballot boxes forming the central image.
clickbait funny tech | My laptop says it has a hilarious reason for crashing. You'll have to visit the link to hear its excuse.
opensource tech jobs ad | Hiring a developer for our AGPL-licensed mapping platform. We publish all source code; send your application to the team.
"""

def authored(split):
 out=[]
 for i,line in enumerate(CATALOG[split].strip().splitlines()):
  if not line.strip():continue
  tags,text=line.split('|',1);ts=set(tags.split());flags={t:t in ts for t in TAGS};flags['offtopic']=not(flags['tech'] or flags['funny'])
  out.append({'id':f'v2-{split}-{i:03}','text':text.strip(),'flags':flags,'origin':'authored-synthetic','split':split})
 return out

def any3(xs):return True if True in xs else None if None in xs else False
def evaluate(e,f):
 if isinstance(e,str):return f.get(e)
 op,*parts=e;v=[evaluate(p,f) for p in parts]
 if op=='not':return None if v[0] is None else not v[0]
 if op=='or':return any3(v)
 return False if False in v else None if None in v else True

def policies():
 out=[]
 def add(id,family,e,texts):out.append({'id':id,'family':family,'expr':e,'texts':texts})
 for t in WORDS:
  a,b=WORDS[t],ALT[t]
  add('hide:'+t,'opposition',t,[[f'Hide {a}'],[f'Please remove {b}'],[f'I do not want to see {a}'],[f'Filter out {b}; keep other posts visible']])
  add('only:'+t,'opposition',['not',t],[[f'Keep only {a}; hide everything else'],[f'Only show me {b}'],[f'Hide anything that is not {a}'],[f'If it is {b}, leave it in my feed. Otherwise remove it']])
 for a,b in [('ad','dating'),('clickbait','diet'),('politics','sports'),('jobs','spoilers')]:
  add(f'either:{a}:{b}','combination',['or',a,b],[[f'Hide {WORDS[a]}',f'Hide {WORDS[b]}'],[f'Please remove both {ALT[a]} and {ALT[b]}'],[f'I want neither {WORDS[a]} nor {WORDS[b]} in my feed'],[f'Filter a post if it is {ALT[a]} or {ALT[b]}; matching either is enough']])
 for a,b in [('ad','tech'),('dating','funny'),('art','diet')]:
  add(f'both:{a}:{b}','conjunction',['and',a,b],[[f'Hide posts only when they are both {WORDS[a]} and {WORDS[b]}'],[f'Remove the overlap between {ALT[a]} and {ALT[b]}. Leave posts matching just one visible'],[f'Both conditions must apply before hiding: {WORDS[a]}; {WORDS[b]}'],[f'A post needs to be {ALT[a]} AND {ALT[b]} to be removed; either condition alone is fine']])
 for a,b in [('ad','opensource'),('dating','funny'),('sports','tech'),('politics','art'),('clickbait','funny')]:
  add(f'unless:{a}:{b}','exception',['and',a,['not',b]],[[f'Hide {WORDS[a]} unless they are also {WORDS[b]}'],[f'Remove {ALT[a]}, but make an exception for {ALT[b]}'],[f'Keep {WORDS[b]} even when they are {WORDS[a]}; hide other {WORDS[a]}'],[f'For {ALT[a]}, the only exception is {ALT[b]}. Other posts can stay']])
 for a,b in [('tech','ad'),('art','diet'),('funny','dating'),('opensource','jobs')]:
  add(f'only_except:{a}:{b}','override',['or',['not',a],b],[[f'Keep only {WORDS[a]}',f'Always hide {WORDS[b]}, even if they match'],[f'Only {ALT[a]} belong in this feed. Exclude any {ALT[b]} regardless'],[f'Hide everything outside {WORDS[a]}. Also hide {WORDS[b]}'],[f'I want {ALT[a]} without {ALT[b]}; nothing else should remain']])
 add('tech_or_funny','combination',['not',['or','tech','funny']],[[f'Keep technology posts and funny posts; hide everything else'],['Show me software, computing, or jokes. Either is enough to keep a post'],['Hide off-topic posts unless they are funny'],['My feed should contain tech OR humor; it need not contain both']])
 add('original_four','override',['or','ad','dating','clickbait','offtopic'],[['Hide promotions or ads','Hide dating stories','Hide clickbait (posts that require you to click before they get to the point)',"Hide things unrelated to tech unless they're funny"],['Keep tech or humor, but remove advertisements, romantic anecdotes, and posts that make me click to learn the point. Those exclusions apply even to funny tech posts.'],['No promotions, dating stories, or withholding teasers. Otherwise keep technology content and funny posts.'],['Show computing and comedy. Even within those topics, exclude sales pitches, dating stories, and click-through teasers. Hide the rest.']])
 add('no_filter','control',['and','ad',['not','ad']],[['Do not filter anything; keep every post'],['All posts should stay visible'],['No exclusions today'],['Leave the entire feed as it is']])
 return out

def norm(s):return re.sub(r'\W+',' ',s.lower()).strip()
def grams(s):
 w=norm(s).split();return {tuple(w[i:i+5]) for i in range(max(1,len(w)-4))}
def make_row(post,p,version,style,suite,pair_id=None):
 y=evaluate(p['expr'],post['flags'])
 if y is None:return None
 clauses=p['texts'][version]
 if style=='bullets':instruction='\n'.join('- '+c for c in clauses)
 elif style=='numbered':instruction='\n'.join(f'{i+1}. '+c for i,c in enumerate(clauses))
 elif style=='casual':instruction='Here is what I want from my feed: '+'. '.join(clauses)+'.'
 else:instruction='. '.join(clauses)+'.'
 return {'id':f'{suite}|{post["id"]}|{p["id"]}|{version}|{style}','post_id':post['id'],'policy_id':p['id'],'family':p['family'],'suite':suite,'pair_id':pair_id,'style':style,'origin':post['origin'],'state':post['text'],'instruction':instruction,'expected':{'hide':bool(y)},'questions':{'hide':{'type':'noul','instructions':'Filtering rules:\n'+instruction+'\n\nShould this post be hidden?','criteria':{'false':'Keep the post visible.','true':'Hide the post.'}}}}

def build():
 rng=random.Random(20261022)
 old=json.loads((ROOT/'finetune-broad/posts.json').read_text());fresh=json.loads((OUT/'fresh-feed-labeled.json').read_text())
 for p in old:
  p['split']='train';p['flags']['offtopic']=p.get('original_flags',[None]*4)[3] if p['origin']=='real-feed' else not(p['flags']['tech'] or p['flags']['funny'])
  p['flags'].setdefault('opensource',None)
 for p in fresh:
  p['split']='test';p['flags']['offtopic']=evaluate(['not',['or','tech','funny']],p['flags'])
 # Remove old text or near-duplicates from the fresh real-world holdout.
 oldg=[grams(p['text']) for p in old]; exclusions=[];kept=[]
 for p in fresh:
  g=grams(p['text']);similar=max((len(g&h)/max(1,min(len(g),len(h))) for h in oldg),default=0)
  same=any(p['source'].rsplit('/',1)[-1] in x['id'] for x in old)
  if same or similar>=.7:exclusions.append({'id':p['id'],'reason':'prior-feed overlap','overlap':similar})
  else:kept.append(p)
 posts={'train':old+authored('train'),'validation':authored('validation'),'test':authored('test')+kept}
 ps=policies();data={s:[] for s in posts};balances=[]
 for p in ps:
  for split in ['train','validation']:
   buckets={v:[x for x in posts[split] if evaluate(p['expr'],x['flags']) is v] for v in [False,True]}
   take=12 if split=='train' else 4
   n=min(take,*(len(v) for v in buckets.values()))
   if p['family']=='control':n=min(take,len(buckets[False]))
   for y,candidates in buckets.items():
    for i,post in enumerate(rng.sample(candidates,min(n,len(candidates)))):
     data[split].append(make_row(post,p,i%3,['bullets','paragraph','numbered'][i%3],p['family']))
   balances.append({'split':split,'policy':p['id'],'available':{str(k):len(v) for k,v in buckets.items()},'per_class':n})
 # Jointly require opposite decisions for the same content, not just aggregate balance.
 for split in ['train','validation','test']:
  for post in posts[split]:
   active=[t for t in WORDS if post['flags'].get(t) is True]
   if not active:continue
   tag=active[rng.randrange(len(active))];pair=f'{split}:{post["id"]}:{tag}'
   for kind in ['hide','only']:
    p=next(p for p in ps if p['id']==kind+':'+tag)
    data[split].append(make_row(post,p,3 if split=='test' else (1 if split=='validation' else 0),'paragraph','opposite_pair',pair))
 # Fresh test: shared post/policy combinations across all formats; withheld wording v3.
 for post in posts['test']:
  available=[p for p in ps if evaluate(p['expr'],post['flags']) is not None]
  critical=[p for p in available if p['id'] in ['original_four','tech_or_funny','only_except:art:diet','unless:ad:opensource']]
  selected=critical+rng.sample([p for p in available if p not in critical],min(8,len(available)-len(critical)))
  for p in selected:
   for style,ver in [('bullets',0),('paragraph',0),('casual',3)]:data['test'].append(make_row(post,p,ver,style,p['family']))
 # New compositions use known operations but tag combinations absent from training.
 novel=[{'id':'novel:ad:art','family':'novel_combination','expr':['and','ad',['not','art']],'texts':[['Hide promotions unless they are about visual art']]}, {'id':'novel:tech:sports','family':'novel_combination','expr':['or',['not','tech'],'sports'],'texts':[['Keep only technology content, but remove anything about sports even if it involves technology']]}, {'id':'novel:dating:diet:spoilers','family':'novel_combination','expr':['or','dating','diet','spoilers'],'texts':[['Hide dating stories, weight-loss content, and plot spoilers. Leave the rest visible']]}]
 for post in posts['test']:
  for p in novel:
   r=make_row(post,p,0,'paragraph','novel_combination')
   if r:data['test'].append(r)
 for s,rows in data.items():
  # Remove duplicated identical inputs and verify contradictory labels never occur.
  unique={}
  for r in rows:
   key=(r['state'],r['instruction'])
   if key in unique:assert unique[key]['expected']==r['expected']
   if key not in unique or r['pair_id']:unique[key]=r
  data[s]=list(unique.values());rng.shuffle(data[s])
 for a,b in [('train','validation'),('train','test'),('validation','test')]:
  assert {norm(p['text']) for p in posts[a]}.isdisjoint({norm(p['text']) for p in posts[b]})
 for s,rs in data.items():(OUT/(s+'.jsonl')).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rs))
 manifest={'seed':20261022,'labels':'Assistant-authored semantic labels; synthetic scenarios and captured feed separated. No outputs consulted.','counts':{s:{'rows':len(rs),'posts':len({r['post_id'] for r in rs}),'hide':sum(r['expected']['hide'] for r in rs)} for s,rs in data.items()},'policy_balance':balances,'policies':ps,'novel_policies':novel,'fresh_feed_exclusions':exclusions,'hashes':{s:hashlib.sha256((OUT/(s+'.jsonl')).read_bytes()).hexdigest() for s in data},'evaluation_rule':'No test inference before final checkpoint selection; compare original base, previous full model, new full model on the same fresh set. Validation macro loss balances behavior families and labels.','post_policy':'All previous data may train; every validation and test post is newly authored or freshly captured. No exact text overlap, and near-duplicate prior-feed posts excluded from fresh test.'}
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));(OUT/'posts.json').write_text(json.dumps(posts,ensure_ascii=False,indent=2))
 print(json.dumps(manifest['counts'],indent=2));print('Excluded fresh feed overlap:',len(exclusions))

if __name__=='__main__':build()
