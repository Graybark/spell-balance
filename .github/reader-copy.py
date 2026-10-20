"""Apply reader-facing editorial copy; do not change spell mechanics or sources."""
from pathlib import Path
from html import escape
from bs4 import BeautifulSoup
import copy, hashlib, json, re
EXPECTED={
 'data/catalog.json':'bb7ddaef3ab168f2582c7bf506116e3c7e4546e1',
 'data/house-rules.json':'e5d786d41f9ef08e279974597ad03c7339694c9f',
 'tools/build.py':'89d2287dfc918539ddd62553637cb9b40aaee9f4',
 'tools/nerf_discussions_test.py':'0c0540fb3a7df564686a8ffbd54780ec0db1bb7f',
 'tools/verify.py':'f6fc74c4ec3ebbee3795011c672e086f39d1c996',
 'tools/browser_test.py':'90e8e939690889ad917dec1f402f784e9d472941',
}
ABSENT_OLD='This spell appears in the 2024 handbook but has no entry in the 2014 Player’s Handbook supplied for this comparison.'
ABSENT_NEW='No 2014 Player’s Handbook version is available for comparison.'
WALL_SUMMARY='Wall of Force remains a level-5 spell. A creature that would be enclosed by the wall, including against another solid surface, can make a Dexterity saving throw. On a success, it can use its Reaction to move up to its Speed out of the enclosure. The standard 2024 clause blocking ethereal travel is omitted. Casting time, range, components, and duration are unchanged.'
DISCUSSIONS={
 'spell-lightning-bolt':[
  ('Balance discussion:', 'Players debate Lightning Bolt’s damage and targeting relative to Fireball. Some favour adjustments, while others argue that its narrow line already makes hitting multiple enemies difficult.'),
  ('Edition context:', 'The linked discussion concerns the 2014 rules. The standard 2024 spell retains the same base damage and area.'),
  ('House-rule version:', 'Lightning Bolt deals 6d6 base Lightning damage, matching Fireball’s house-rule damage. The damage increases by 1d6 for each spell-slot level above 3.'),
 ],
 'spell-fireball': [('Balance discussion:', 'The standard 2024 spell deals 8d6 damage over a large area for a level-3 slot. Proposed nerfs include reducing its damage or radius.')],
 'spell-forcecage': [('Balance discussion:', 'Even after its 2024 changes, the standard spell’s strong confinement effect remains a subject of proposed nerfs.')],
 'spell-melf-s-acid-arrow': [('Balance discussion:', 'Players question whether the standard 2024 spell’s delayed damage justifies a level-2 slot. Proposed buffs include increasing the damage or extending the ongoing effect.')],
 'spell-wall-of-force': [('Balance discussion:', 'The standard 2024 spell can confine creatures without an initial saving throw. Proposed nerfs include making the wall breakable.')],
}
CLONE=('Campaign example:', 'TorontoDnD banned Clone in June 2024, before the revised Player’s Handbook. Other discussions argue that its long preparation time limits its practical impact. Spellwright retains the standard 2024 version.')
SIMULACRUM=('2024 rules:', 'A simulacrum cannot cast Simulacrum or take Short or Long Rests. The suggested restrictions on spellcasting and shapechanging would go beyond those limits. Spellwright retains the standard 2024 version.')
ERRATA={
 'spell-animal-shapes':'Temporary Hit Points come from the first form, vanish when the spell ends, and losing them does not end the transformation.',
 'spell-conjure-elemental':'The damage increases by 1d8 for each spell-slot level above 5.',
 'spell-conjure-fey':'The damage increases by 1d12 for each spell-slot level above 6.',
 'spell-conjure-minor-elementals':'The extra damage increases by 1d8 for each spell-slot level above 4.',
 'spell-conjure-woodland-beings':'The damage increases for each spell-slot level above 4.',
 'spell-giant-insect':'The summoned insect’s Hit Points equal 30 + 10 for each spell-slot level above 4.',
 'spell-polymorph':'Any remaining Temporary Hit Points vanish when the spell ends.',
 'spell-shapechange':'Temporary Hit Points come from the first form, vanish when the spell ends, and losing them does not end the spell.',
 'spell-true-polymorph':'For Creature into Creature, any remaining Temporary Hit Points vanish when the spell ends. Losing those Temporary Hit Points does not end the spell.',
}
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def text(s):return BeautifulSoup(s,'html.parser').get_text(' ',strip=True)
def urls(s):return [a['href'] for a in BeautifulSoup(s,'html.parser').select('a[href]')]
def once(s,a,b):
 assert s.count(a)==1,('Ambiguous text replacement',a[:100])
 return s.replace(a,b,1)
def paragraph(old,label,content):
 soup=BeautifulSoup(old,'html.parser');p=soup.find('p');assert p
 links=[str(a) for a in p.select('a[href]')]
 attrs=' class="'+escape(' '.join(p['class']),quote=True)+'"' if p.get('class') else ''
 return '<p'+attrs+'><strong>'+escape(label)+'</strong> '+escape(content,quote=False)+(' '+' '.join(links) if links else '')+'</p>'
def normal(s):
 s=re.sub(r'\s+',' ',s).strip().lower()
 return re.sub(r'^1 (action|bonus action|reaction)\b',r'\1',s)
def field_note(record,note):
 """Use current paired fields, not obsolete text embedded in old review prompts.
 Only previously annotated fields are considered. Presentation-only differences are omitted.
 """
 old=record['versions']['2014'];new=record['versions']['2024'];id=record['id']
 assert not old['absent'] and not new['absent']
 body=text(note);assert body.startswith('Fields to check:')
 bits=body[len('Fields to check:'):].strip().split('; ')
 sentences=[]
 for bit in bits:
  if bit.startswith('Renamed from '):
   if id=='spell-befuddlement':
    if not any('Renamed from Feeblemind' in text(n) for n in record['notes'] if 'field-signals' not in n):sentences.append('Renamed from Feeblemind.')
   elif id=='spell-shining-smite':sentences.append('Renamed from Branding Smite.')
   continue
  key=bit.partition(':')[0].lower();a=old['metadata'].get(key,'');b=new['metadata'].get(key,'')
  if key=='school':
   a=old['type'].split('·')[-1].strip();b=new['type'].split('·')[-1].strip()
   if a!=b:sentences.append(f'The school changes from {a} to {b}.')
  elif key=='casting time':
   # Header presentation alone is not evidence of new ritual access or casting duration.
   if normal(a)==normal(b.replace(' or Ritual','')):continue
   if id in ('spell-antipathy-sympathy','spell-plant-growth','spell-hellish-rebuke','spell-shield'):continue
   if id in ('spell-armor-of-agathys','spell-feather-fall'):continue
   if id=='spell-counterspell':sentences.append('The Reaction trigger explicitly specifies a spell with Verbal, Somatic, or Material components.')
   elif b.startswith('Bonus Action, which you take '):sentences.append('The Bonus Action is taken '+b.split('which you take ',1)[1]+'.')
   else:
    aa={'1 action':'an Action','1 bonus action':'a Bonus Action'}.get(a,a)
    bb={'Action':'an Action','Bonus Action':'a Bonus Action'}.get(b,b)
    sentences.append(f'Casting time changes from {aa} to {bb}.')
  elif key=='range':
   if normal(a)==normal(b):continue
   if a.startswith('Self (') and b=='Self':continue
   sentences.append(f'The range changes from {a} to {b}.')
  elif key=='duration':
   if normal(a)==normal(b):continue
   prefix='Concentration, up to '
   if a.startswith(prefix) and b==a[len(prefix):]:sentences.append(f'The spell lasts {b} without Concentration.')
   elif a.startswith(prefix) and b.startswith(prefix):sentences.append(f'The maximum Concentration duration changes from {a[len(prefix):]} to {b[len(prefix):]}.')
   elif b.startswith(prefix):sentences.append(f'The spell now requires Concentration, for up to {b[len(prefix):]}.')
   elif a.startswith(prefix) and b=='Instantaneous':sentences.append('Concentration is no longer required; the listed duration is Instantaneous.')
   else:sentences.append(f'The listed duration changes from {a} to {b}.')
  elif key=='components':
   aa=set(re.findall(r'\b[VSM]\b',a.split('(')[0]));bb=set(re.findall(r'\b[VSM]\b',b.split('(')[0]))
   if id=='spell-message':continue
   for char,label in [('V','Verbal'),('S','Somatic'),('M','Material')]:
    if char in aa-bb:sentences.append(f'The {label} component is removed.')
    if char in bb-aa:sentences.append(f'A {label} component is added.')
  else:raise AssertionError(('Unexpected field',key))
 return '<p class="field-signals"><strong>2024 changes:</strong> '+escape(' '.join(sentences),quote=False)+'</p>' if sentences else None

def revise_catalog(original):
 data=copy.deepcopy(original);stats={'field_notes_reviewed':0,'field_notes_rewritten':0,'field_notes_removed':0,'revision_labels':0,'errata_notes':0,'absent_placeholders':0,'discussion_entries':0};log=[]
 for s in data:
  id=s['id'];notes=[]
  for n in s['notes']:
   new=n
   if 'field-signals' in n:
    stats['field_notes_reviewed']+=1;new=field_note(s,n)
    stats['field_notes_rewritten' if new else 'field_notes_removed']+=1
   elif 'Revision identified:' in n:new=n.replace('Revision identified:','2024 changes:');stats['revision_labels']+=1
   elif 'Official errata applied:' in n:
    assert id in ERRATA;new=paragraph(n,'Official errata:',ERRATA[id]);stats['errata_notes']+=1
   if new!=n:log.append({'spell':s['name'],'field':'comparison note','before':text(n),'after':text(new) if new else None})
   if new:notes.append(new)
  s['notes']=notes
  old_disc=list(s['discussion'])
  if id in DISCUSSIONS:
   spec=DISCUSSIONS[id];assert len(spec)==len(s['discussion'])
   s['discussion']=[paragraph(n,label,body) for n,(label,body) in zip(s['discussion'],spec)]
  elif id=='spell-clone':
   assert len(s['discussion'])==2;s['discussion'][1]=paragraph(s['discussion'][1],*CLONE)
  elif id=='spell-simulacrum':
   assert len(s['discussion'])==2;s['discussion'][1]=paragraph(s['discussion'][1],*SIMULACRUM)
  elif id=='spell-mordenkainen-s-sword':
   s['discussion']=[once(n,'; these are community suggestions, not official changes.','.') for n in s['discussion']]
  if s['discussion']!=old_disc:
   stats['discussion_entries']+=1;log.append({'spell':s['name'],'field':'discussion','before':text(' '.join(old_disc)),'after':text(' '.join(s['discussion']))})
  assert urls(''.join(old_disc))==urls(''.join(s['discussion'])),id
  for year,v in s['versions'].items():
   if not v['absent']:continue
   assert year=='2014' and ABSENT_OLD in v['body'],id
   v['body']=once(v['body'],ABSENT_OLD,ABSENT_NEW)
   v['body_sha256']=hashlib.sha256(v['body'].encode()).hexdigest();stats['absent_placeholders']+=1
  before=next(r for r in original if r['id']==id)
  for k in before:
   if k not in ('notes','discussion','versions'):assert before[k]==s[k],(id,k)
  for year,v in s['versions'].items():
   if not before['versions'][year]['absent']:assert before['versions'][year]==v,(id,year)
   else:
    assert {k:z for k,z in before['versions'][year].items() if k not in ('body','body_sha256')}=={k:z for k,z in v.items() if k not in ('body','body_sha256')}
  assert urls(''.join(before['notes']))==urls(''.join(s['notes'])),id
 assert stats['field_notes_reviewed']==147 and stats['revision_labels']==8 and stats['errata_notes']==9 and stats['absent_placeholders']==30
 assert sum(bool(s['discussion']) for s in data)==20
 return data,stats,log

def apply(root):
 for name,sha in EXPECTED.items():assert blob((root/name).read_bytes())==sha,('Source changed',name)
 catalog=root/'data/catalog.json';original=json.loads(catalog.read_text(encoding='utf-8'))
 data,stats,log=revise_catalog(original)
 catalog.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 p=root/'data/house-rules.json';h=json.loads(p.read_text());old=copy.deepcopy(h)
 h['spell-wall-of-force']['summary']=WALL_SUMMARY
 for id in h:
  assert {k:v for k,v in h[id].items() if k!='summary'}=={k:v for k,v in old[id].items() if k!='summary'},id
 p.write_text(json.dumps(h,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 p=root/'tools/build.py';b=p.read_text()
 b=once(b,"('why','Why this version?'","('why','House-rule changes'")
 b=once(b,'<h3>House-rule change</h3>','<h3>House-rule changes</h3>')
 b=once(b,'This is the recorded change to the 2024 version. The original editions remain available in Compare versions.','See <strong>Compare versions</strong> for the standard 2024 spell and its 2014 counterpart.')
 b=once(b,'disabled>House-rule spells</label>','disabled>Use house-rule versions</label>')
 p.write_text(b,encoding='utf-8')
 p=root/'tools/nerf_discussions_test.py';b=p.read_text()
 b=b.replace('Several replies defend Lightning Bolt','others argue that its narrow line')
 b=once(b,"assert 'campaign decision' in pane.get_text()", "assert 'House-rule version:' in pane.get_text() and '6d6 base Lightning damage' in pane.get_text()")
 b=once(b,"'before the revised PHB'", "'before the revised Player’s Handbook'")
 b=once(b,"'already cannot cast Simulacrum'", "'A simulacrum cannot cast Simulacrum'")
 p.write_text(b,encoding='utf-8')
 p=root/'tools/verify.py';b=p.read_text()
 b=once(b,'    from house_rules_test import check_rule_content\n','    from reader_copy_test import check_reader_copy\n    check_reader_copy(page)\n    from house_rules_test import check_rule_content\n')
 p.write_text(b,encoding='utf-8')
 p=root/'tools/browser_test.py';b=p.read_text()
 b=once(b,'        await browser.close()\n','        from reader_copy_test import check_reader_copy_browser\n        await check_reader_copy_browser(browser,url,REPORT)\n        await browser.close()\n')
 p.write_text(b,encoding='utf-8')
 out=Path('/tmp/spellwright-reader-copy');out.mkdir(exist_ok=True)
 (out/'copy-summary.json').write_text(json.dumps(stats,indent=2))
 (out/'copy-changes.json').write_text(json.dumps(log,ensure_ascii=False,indent=2))
 print(json.dumps(stats))
if __name__=='__main__':apply(Path.cwd())
