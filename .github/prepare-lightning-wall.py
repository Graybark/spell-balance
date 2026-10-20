"""Apply the two explicitly approved house-rule changes to verified source files."""
from pathlib import Path
from html import escape
import hashlib, json
ROOT=Path.cwd()
def blob(b):
    return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def replace_once(s,before,after):
    assert s.count(before)==1, 'Unexpected source: '+before[:100]
    return s.replace(before,after,1)
for path,sha in {
    'data/house-rules.json':'89b7d55a7275c6b3a65e3e194ab9b633dde196a6',
    'tools/build.py':'7ae83fbcc067c4ba7b6bb373d0f6414d18b2b64a',
    'tools/browser_test.py':'de510ee48effc733cf2c2c6035d32e5eac434851',
}.items():
    assert blob(Path(path).read_bytes())==sha, 'Source changed: '+path

intro="An Invisible wall of force springs into existence at a point you choose within range. The wall appears in any orientation you choose, as a horizontal or vertical barrier or at an angle. It can be free floating or resting on a solid surface. You can form it into a hemispherical dome or a globe with a radius of up to 10 feet, or you can shape a flat surface made up of ten 10-foot-by-10-foot panels. Each panel must be contiguous with another panel. In any form, the wall is 1/4 inch thick and lasts for the duration. If the wall cuts through a creature's space when it appears, the creature is pushed to one side of the wall (you choose which side)."
escape_rule="If a creature would be surrounded on all sides by the wall (or the wall and another solid surface), that creature can make a Dexterity saving throw. On a success, it can use its Reaction to move up to its Speed so that it is no longer enclosed by the wall."
barrier="Nothing can physically pass through the wall. It is immune to all damage and can't be dispelled by Dispel Magic. A Disintegrate spell destroys the wall instantly, however."
hpath=Path('data/house-rules.json');house=json.loads(hpath.read_text())
assert set(house)=={'spell-fireball','spell-forcecage','spell-melf-s-acid-arrow','spell-wall-of-force'}
house['spell-lightning-bolt']={
    'level':3,
    'summary':'Base damage: 8d6 → 6d6. The +1d6 increase per higher-level slot is unchanged.',
    'replacements':[['taking 8d6 Lightning damage','taking 6d6 Lightning damage']],
    'highlight':'6d6',
}
house['spell-wall-of-force']={
    'level':5,
    'summary':'Level 5, replacing the earlier level-7 house rule. Uses the supplied replacement effect: a creature enclosed by the wall (or the wall and another solid surface) can make a Dexterity saving throw and, on a success, use its Reaction to move up to its Speed out of the enclosure. The former Ethereal Plane restriction is not included. Casting details are unchanged.',
    'replacements':[],
    'body_override':'<div class="spell-text spell-text-2024">'+''.join('<p>'+escape(p,quote=False)+'</p>' for p in [intro,escape_rule,barrier])+'</div>',
    'highlight_phrases':[escape_rule],
}
hpath.write_text(json.dumps(house,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

p=Path('tools/build.py');s=p.read_text()
s=replace_once(s,"        if h:\n            for before,after in h['replacements']:\n", "        if h:\n            # Full-effect overrides keep user-supplied wording separate from official editions.\n            if 'body_override' in h:\n                assert not h['replacements'], f'Use a full effect or substitutions, not both: {id}'\n                assert isinstance(h['body_override'],str) and h['body_override'].strip()\n                hv['body']=h['body_override']\n            for before,after in h['replacements']:\n")
s=replace_once(s,"        if house.get('highlight')=='6d6': html=html.replace('taking 6d6 Fire damage','taking <mark class=\"house-change\">6d6</mark> Fire damage')", "        if house.get('highlight')=='6d6': html=html.replace('taking 6d6 ','taking <mark class=\"house-change\">6d6</mark> ')")
s=replace_once(s,"    return '<div class=\"spell-body\">'+html+'</div>'+footer(v,bool(house))", "        for phrase in house.get('highlight_phrases',[]):\n            rendered=escape(phrase,quote=False)\n            assert html.count(rendered)==1, 'Ambiguous house-rule highlight'\n            html=html.replace(rendered,'<mark class=\"house-change\">'+rendered+'</mark>')\n    return '<div class=\"spell-body\">'+html+'</div>'+footer(v,bool(house))")
p.write_text(s,encoding='utf-8')

p=Path('tools/verify.py');s=p.read_text()
s=replace_once(s,"('wall-of-force','7')", "('wall-of-force','5'),('lightning-bolt','3')")
s=replace_once(s,"    assert len(page.select('.balance-note'))==17", "    assert len(page.select('.balance-note'))==17\n    from house_rules_test import check_rule_content\n    check_rule_content(page, data, json.loads((ROOT/'data/house-rules.json').read_text()))")
p.write_text(s,encoding='utf-8')

p=Path('tools/browser_test.py');s=p.read_text()
for id in ('label','spell-class'):
    old=f"        await page.select_option('#{id}','"+('house-rule' if id=='label' else 'wizard')+"');assert await page.locator('.sidebar li:visible').count()==4"
    s=replace_once(s,old,old[:-1]+'5')
s=replace_once(s,'        await check_mobile_menu(browser,url)\n', '        from house_rules_test import check_rule_browser\n        await check_rule_browser(browser,url,REPORT)\n        await check_mobile_menu(browser,url)\n')
p.write_text(s,encoding='utf-8')
print('Updated only approved house rules, build-time support and regression coverage. Official catalog and class data untouched.')
