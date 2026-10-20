"""Add the two requested community Nerf discussions, not mechanical house rules."""
from pathlib import Path
from html import escape
import copy, hashlib, json, re
from bs4 import BeautifulSoup
ROOT=Path.cwd()
def blob(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
expected={'data/catalog.json':'18cd7f1814b5fd5b3c10ebfcea9570b814099cd8','data/overview.json':'31d7ad2f104756740f57e89208f5e5ff4c5ea696','tools/verify.py':'dcd227680fedf936f4bd7b744c732cf3cf640a45','tools/browser_test.py':'d7731362bb2907beefe85994a5a38f761e62315b'}
for path,sha in expected.items():
    assert blob((ROOT/path).read_bytes())==sha, 'Source changed; review before applying: '+path

def link(url,label):
    return '<a href="'+escape(url,quote=True)+'" rel="noopener noreferrer" target="_blank">'+escape(label)+'</a>'

notes={
'spell-simulacrum':[
    '<p class="balance-note"><strong>Balance discussion (2024):</strong> Critics still question the value of an additional creature with a copied character\'s actions and spellcasting. In a discussion of the revised PHB, a proposed further nerf is to prevent the simulacrum from casting spells or changing shape. Other commenters defend the spell and prefer encounter adjustments or narrative limits. '+link('https://www.dndbeyond.com/forums/dungeons-dragons-discussion/streams-video/202653-treantmonk-2024-phb-rebalanced-spells','2024 balance discussion and proposed restrictions')+'</p>',
    '<p><strong>Edition context:</strong> The 2024 simulacrum already cannot cast Simulacrum or take Short or Long Rests. Do not treat the old direct self-copying chain as an unrestricted 2024 option; claims involving Wish require separate rules interpretation. These are community proposals, not consensus or an adopted house rule. '+link('https://roll20.net/compendium/dnd5e/Spells:Simulacrum?expansion=32231','2024 spell text')+'</p>'
],
'spell-clone':[
    '<p class="balance-note"><strong>Balance discussion (campaign-dependent):</strong> The 2024 spell comments discuss maintaining younger replacement bodies and using Wish to avoid component costs. The balance concern is repeatable protection from permanent death and aging, rather than extra combat damage. This is not unconditional immortality: the clone needs 120 days to mature, its vessel must remain undisturbed for indefinite preservation, the soul must be free and willing, and equipment does not transfer. '+link('https://www.dndbeyond.com/spells/2618973-clone','2024 spell and community comments')+' '+link('https://rpg.stackexchange.com/questions/50541/does-the-clone-spell-make-someone-effectively-immortal','Legacy discussion: immortality and practical limits')+'</p>',
    '<p><strong>Restriction example, not consensus:</strong> TorontoDnD banned Clone in its June 2024 community update, before the revised PHB. This is a documented campaign restriction, not an official change or proof of a general 2024 consensus. The legacy discussion also argues that the long timescale often limits its impact during play. Added for Nerf consideration; no particular Clone house rule has been adopted here. '+link('https://www.torontodnd.com/communityupdate/2024-06-14','June 2024 campaign restriction')+'</p>'
]}
path=ROOT/'data/catalog.json';original=json.loads(path.read_text(encoding='utf-8'));data=copy.deepcopy(original)
assert len(data)==391
for spell in data:
    if spell['id'] not in notes: continue
    print('Before:',spell['name'],spell['categories'],'discussion sections:',len(spell['discussion']))
    assert not spell['discussion'], 'Discussion already exists; merge rather than duplicate: '+spell['id']
    if 'nerf' not in spell['categories']: spell['categories'].append('nerf')
    if not any(t.get('class')=='tag tag-nerf' for t in spell['tags']):
        spell['tags'].append({'text':'Nerf','class':'tag tag-nerf'})
    spell['discussion']=notes[spell['id']]
for before,after in zip(original,data):
    if before['id'] not in notes: assert before==after
    else:
        for key in before:
            if key not in ('categories','tags','discussion'): assert before[key]==after[key],key
        assert before['versions']==after['versions']
        assert set(before['categories']).issubset(after['categories'])
        assert all(t in after['tags'] for t in before['tags'])
    for version in after['versions'].values():
        assert hashlib.sha256(version['body'].encode()).hexdigest()==version['body_sha256']
assert sum('nerf' in s['categories'] for s in data)==10
assert sum('buff' in s['categories'] for s in data)==9
assert sum(bool(s['discussion']) for s in data)==19
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
overview=ROOT/'data/overview.json';items=json.loads(overview.read_text())
assert items.count('17 balance discussions')==1
items[items.index('17 balance discussions')]='19 balance discussions'
overview.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def once(s,a,b):
    assert s.count(a)==1,a
    return s.replace(a,b,1)
p=ROOT/'tools/verify.py';s=p.read_text(encoding='utf-8')
s=once(s,"    assert len(page.select('.balance-note'))==17", "    discussion_count=sum(bool(record['discussion']) for record in data)\n    assert len(page.select('.balance-note'))==discussion_count\n    assert f'{discussion_count} balance discussions' in json.loads((ROOT/'data/overview.json').read_text())\n    from nerf_discussions_test import check_discussion_content\n    check_discussion_content(page, data, json.loads((ROOT/'data/house-rules.json').read_text()))")
s=once(s,"'discussion_notes':17", "'discussion_notes':discussion_count")
p.write_text(s,encoding='utf-8')
p=ROOT/'tools/browser_test.py';s=p.read_text(encoding='utf-8')
s=once(s,'from slots_view_test import check_slots_view\n','from slots_view_test import check_slots_view\nfrom nerf_discussions_test import check_discussion_browser\n')
s=once(s,'        await browser.close()\n','        await check_discussion_browser(browser,url,REPORT)\n        await browser.close()\n')
p.write_text(s,encoding='utf-8')
print('Added Simulacrum and Clone once: 10 Nerf, 9 Buff, 19 discussions, 391 spells. Official texts, all five house rules, class data and other 389 records unchanged.')
