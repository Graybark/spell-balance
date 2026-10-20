"""Add the missing Lightning Bolt discussion while preserving both editions and house rules."""
from pathlib import Path
from html import escape
import copy,hashlib,json
ROOT=Path.cwd()
def blob(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
expected={'data/catalog.json':'3ed34cef898579f8ab523f6aade12d25f1cdb3c3','data/overview.json':'98e3fcf48680878ed20edc189fb348afc94b0d9a','tools/nerf_discussions_test.py':'7d0282f462e08959aa1829e5d3cd9dc1c8ab9440','data/house-rules.json':'e5d786d41f9ef08e279974597ad03c7339694c9f'}
for name,sha in expected.items(): assert blob((ROOT/name).read_bytes())==sha, 'Source changed: '+name

def link(url,label): return '<a href="'+escape(url,quote=True)+'" rel="noopener noreferrer" target="_blank">'+escape(label)+'</a>'
forum='https://www.dndbeyond.com/forums/dungeons-dragons-discussion/dungeon-masters-only/75512-fireball-and-lightning-bolt'
rules='https://roll20.net/compendium/dnd5e/Spells:Lightning%20Bolt?expansion=32231'
p=ROOT/'data/catalog.json';before=json.loads(p.read_text(encoding='utf-8'));after=copy.deepcopy(before)
records=[s for s in after if s['id']=='spell-lightning-bolt'];assert len(records)==1
s=records[0];assert not s['discussion'], 'Merge existing discussion instead of replacing it.'
s['discussion']=[
 '<p class="balance-note"><strong>Balance discussion (disputed):</strong> A 2020 D&D Beyond thread questions Fireball and Lightning Bolt\'s damage relative to a level-3 slot and discusses changing Lightning Bolt\'s damage or targeting. Several replies defend Lightning Bolt: its narrow line makes catching multiple enemies difficult, unlike Fireball\'s wider area. The discussion does not establish agreement that Lightning Bolt needs a nerf. '+link(forum,'Community discussion: Fireball and Lightning Bolt (2020)')+'</p>',
 '<p><strong>Edition context:</strong> The linked discussion concerns the 2014 rules. The 2024 spell still deals 8d6 Lightning damage in a 100-foot-long, 5-foot-wide Line, with +1d6 per higher-level slot. Those shared features make the older discussion relevant to the damage comparison, but it is not a 2024-specific consensus. '+link(rules,'2024 spell reference')+'</p>',
 '<p><strong>Recorded house rule:</strong> This reference uses the approved 6d6 base damage, matching Fireball\'s reduction; the +1d6 increase per higher-level slot is unchanged. That exact reduction is a campaign decision, not a claim that the linked commenters agreed on it. See <em>Why this version?</em> for the recorded change.</p>'
]
if 'nerf' not in s['categories']: s['categories'].append('nerf')
if not any(t.get('class')=='tag tag-nerf' for t in s['tags']): s['tags'].append({'text':'Nerf','class':'tag tag-nerf'})
for old,new in zip(before,after):
 if old['id']!='spell-lightning-bolt': assert old==new
 else:
  for key in old:
   if key not in ('categories','tags','discussion'): assert old[key]==new[key],key
  assert all(t in new['tags'] for t in old['tags'])
  assert set(old['categories']).issubset(new['categories'])
 for v in new['versions'].values(): assert hashlib.sha256(v['body'].encode()).hexdigest()==v['body_sha256']
assert len(after)==391 and sum(bool(s['discussion']) for s in after)==20
assert sum('nerf' in s['categories'] for s in after)==11 and sum('buff' in s['categories'] for s in after)==9
p.write_text(json.dumps(after,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=ROOT/'data/overview.json';overview=json.loads(p.read_text())
assert overview.count('19 balance discussions')==1
overview[overview.index('19 balance discussions')]='20 balance discussions'
p.write_text(json.dumps(overview,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def once(s,a,b):
 assert s.count(a)==1,a
 return s.replace(a,b,1)
p=ROOT/'tools/nerf_discussions_test.py';test=p.read_text(encoding='utf-8')
test=once(test,"inner_text()=='10 spells'","inner_text()=='11 spells'")
test=once(test,".count()==10",".count()==11")
test=once(test,'def check_discussion_content(page,data,house):\n','''def check_discussion_content(page,data,house):
    lightning=next(s for s in data if s['id']=='spell-lightning-bolt')
    assert lightning['categories'].count('nerf')==1
    assert sum(t['class']=='tag tag-nerf' for t in lightning['tags'])==1
    card=page.find(id='spell-lightning-bolt')
    pane=card.select_one('[data-panel="discussion"]')
    assert pane and len(pane.select('.balance-note'))==1
    assert 'Several replies defend Lightning Bolt' in pane.get_text()
    assert '2020' in pane.get_text() and '2014 rules' in pane.get_text()
    assert 'campaign decision' in pane.get_text()
    assert len(pane.select('a[href]'))==2
    assert card.select_one('[data-panel="why"]')
    assert house['spell-lightning-bolt']['replacements']==[['taking 8d6 Lightning damage','taking 6d6 Lightning damage']]
    assert len(house)==5
''')
test=once(test,"    plain=await browser.new_context(java_script_enabled=False,viewport={'width':390,'height':1000})", "    await check_lightning_discussion_browser(browser,url,report)\n    plain=await browser.new_context(java_script_enabled=False,viewport={'width':390,'height':1000})")
test+='''
async def check_lightning_discussion_browser(browser,url,report):
    from playwright.async_api import expect
    sources=[
        'https://www.dndbeyond.com/forums/dungeons-dragons-discussion/dungeon-masters-only/75512-fireball-and-lightning-bolt',
        'https://roll20.net/compendium/dnd5e/Spells:Lightning%20Bolt?expansion=32231',
    ]
    errors=[]
    for width in (1280,390):
        for javascript in (True,False):
            context=await browser.new_context(viewport={'width':width,'height':1000},java_script_enabled=javascript)
            p=await context.new_page()
            p.on('pageerror',lambda e:errors.append(str(e)))
            await p.goto(url+'?label=nerf#spell-lightning-bolt')
            if javascript:
                await p.wait_for_selector('html.enhanced')
                await expect(p.locator('#visible-count')).to_have_text('11 spells')
                assert await p.locator('.sidebar li[data-spell="spell-lightning-bolt"]').evaluate('(e)=>!e.hidden')
            card=p.locator('#spell-lightning-bolt')
            await expect(card).to_be_visible()
            await expect(card.locator('.tag-house')).to_be_visible()
            await expect(card.locator('.tag-nerf')).to_be_visible()
            house=card.locator('[data-panel="spell"] [data-mode="house"]')
            assert 'taking 6d6 Lightning damage' in await house.inner_text()
            await p.locator('label[for="spell-lightning-bolt-info-discussion"]').click()
            pane=card.locator('[data-panel="discussion"]')
            await expect(pane).to_be_visible()
            assert await pane.locator('.balance-note').count()==1
            for source in sources:
                assert await pane.locator('a').evaluate_all('(links,u)=>links.some(a=>a.getAttribute("href")===u)',source)
            assert 'Several replies defend Lightning Bolt' in await pane.inner_text()
            if javascript: await card.screenshot(path=str(report/f'lightning-discussion-{width}.png'))
            size=await p.evaluate('[document.documentElement.clientWidth,document.documentElement.scrollWidth]')
            assert size[1]<=size[0]+1,(width,size)
            await p.locator('label[for="spell-lightning-bolt-info-why"]').click()
            assert '8d6 → 6d6' in await card.locator('.why').inner_text()
            await p.locator('label[for="spell-lightning-bolt-info-compare"]').click()
            for year in ('2024','2014'):
                await p.locator(f'label[for="spell-lightning-bolt-editions-{year}"]').click()
                assert '8d6' in await card.locator(f'[data-panel="{year}"] .original-body').inner_text()
            if javascript:
                await p.select_option('#label','house-rule')
                await expect(p.locator('#visible-count')).to_have_text('5 spells')
                assert await p.locator('.sidebar li[data-spell="spell-lightning-bolt"]').evaluate('(e)=>!e.hidden')
            await context.close()
    assert not errors,errors
'''
compile(test,str(p),'exec')
p.write_text(test,encoding='utf-8')
print('Lightning Bolt Discussion added with dissent and edition context. 20 discussions; 11 Nerf entries. All 391 spell texts, all five house rules and class data unchanged.')
