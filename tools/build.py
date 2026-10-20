"""Build the static reference from explicit data. No runtime rules migration.
Usage: python tools/build.py [--output 'Spell Balance.html'] [--check]
Dependencies: beautifulsoup4 (pinned in requirements-build.txt).
"""
from pathlib import Path
from bs4 import BeautifulSoup
from html import escape
import argparse, copy, hashlib, json, re
ROOT=Path(__file__).resolve().parents[1]
SCHOOLS={s:s.lower()+'.svg' for s in ['Abjuration','Conjuration','Divination','Enchantment','Evocation','Illusion','Necromancy','Transmutation']}
CLASS_NAMES=['Bard','Cleric','Druid','Paladin','Ranger','Sorcerer','Warlock','Wizard']
def esc(x): return escape(str(x),quote=True)
def load(name): return json.loads((ROOT/'data'/f'{name}.json').read_text(encoding='utf-8'))
def norm(name): return re.sub(r'\s+','',name.strip().lower()).replace('vvizard','wizard')
def text(html): return BeautifulSoup(html,'html.parser').get_text()
def tabs(prefix, label, definitions):
    parts=[f'<div class="tabs" role="group" aria-label="{esc(label)}">']
    for i,(key,title,_) in enumerate(definitions):
        parts.append(f'<input class="tab-radio" type="radio" name="{prefix}" id="{prefix}-{key}" value="{key}"'+(' checked' if i==0 else '')+f'><label class="tab-label" id="{prefix}-{key}-label" for="{prefix}-{key}">{esc(title)}</label>')
    for key,_,html in definitions:
        parts.append(f'<section class="tab-panel" data-panel="{key}" aria-labelledby="{prefix}-{key}-label">{html}</section>')
    return ''.join(parts)+'</div>'
def footer(v,house=False):
    badges=[]
    for name in v['classes'].split(',') if v['classes'] else []:
        key=norm(name); title=key.title() if key.title() in CLASS_NAMES else name.strip()
        # Real links work without JavaScript; the app enhances them into filters.
        badges.append(f'<a class="class-badge" href="?class={esc(key)}#spells" data-filter-class="{esc(key)}">{esc(title)}</a>')
    availability=('<div class="availability"><span>Available for:</span>'+''.join(badges)+'</div>') if badges else ''
    return '<footer class="spell-footer">'+availability+'<span class="source">'+('Based on ' if house else '')+esc(v['source'])+'</span></footer>'
def metadata(v,level,school,house=None,official_level=None):
    meta=v['metadata']; soup=BeautifulSoup(v['body'],'html.parser'); p=soup.select_one('.spell-text > p'); first=p.get_text() if p else soup.get_text()
    body=soup.get_text(); area=list(dict.fromkeys(re.findall(r'\b\d+-foot(?:-radius)?\s+(?:Sphere|Emanation|Cube|Cone|Line|Cylinder)\b',first)))
    saves=list(dict.fromkeys(x+' save' for x in re.findall(r'\b(?:make|makes|making|succeed on|succeeds on)\s+(?:a|an)\s+(Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma)\s+saving throw\b',body)))
    attacks=list(dict.fromkeys(re.findall(r'\b(?:ranged|melee) spell attack\b',body,re.I)))
    damages=list(dict.fromkeys(re.findall(r'\b(?:taking|takes|take|deals|deal)\s+(\d+d\d+(?:\s*[+−-]\s*\d+)?\s+(?:Acid|Bludgeoning|Cold|Fire|Force|Lightning|Necrotic|Piercing|Poison|Psychic|Radiant|Slashing|Thunder) damage)\b',first)))
    def field(label,value,html=False):
        return f'<div><dt>{label}</dt><dd>{value if html else esc(value)}</dd></div>' if value else ''
    lv='Cantrip' if level==0 else str(level)
    if house and level!=official_level: lv='<mark class="house-change">'+lv+'</mark>'
    out=field('Level',lv,True)+field('Casting Time',meta.get('casting time',''))
    r=esc(meta.get('range',''))
    if len(area)==1: r+='<small>'+esc(area[0])+'</small>'
    out+=field('Range / Area',r,True)
    comp=meta.get('components',''); before,sep,after=comp.partition(' (')
    out+=field('Components',esc(before)+('<small>('+esc(after)+'</small>' if sep else ''),True)
    out+=field('Duration',meta.get('duration',''))+field('School',school)+field('Attack / Save','; '.join(attacks+saves))
    if len(damages)==1:
        dmg=esc(damages[0]); dmg=dmg.replace('6d6','<mark class="house-change">6d6</mark>') if house and house.get('highlight')=='6d6' else dmg
        out+=field('Damage / Effect',dmg,True)
    return '<dl class="spell-meta">'+out+'</dl>'
def body(v,house=None):
    s=BeautifulSoup(v['body'],'html.parser')
    for p in s.select('.spell-text p'):
        h=p.select_one('.run-in')
        if h and re.search(r'Higher.Level|At Higher Levels',h.get_text(),re.I): p['class']=p.get('class',[])+['upcast']
    html=str(s)
    if house:
        if house.get('highlight')=='6d6': html=html.replace('taking 6d6 ','taking <mark class="house-change">6d6</mark> ')
        if house.get('highlight')=='1': html=html.replace('for each spell slot level above 1.','for each spell slot level above <mark class="house-change">1</mark>.')
        for phrase in house.get('highlight_phrases',[]):
            rendered=escape(phrase,quote=False)
            assert html.count(rendered)==1, 'Ambiguous house-rule highlight'
            html=html.replace(rendered,'<mark class="house-change">'+rendered+'</mark>')
    return '<div class="spell-body">'+html+'</div>'+footer(v,bool(house))
def version(v,year):
    if v['absent']: return '<div class="original-version">'+v['body']+'</div>'
    meta=''.join(f'<div><dt>{esc(k)}</dt><dd>{esc(val)}</dd></div>' for k,val in v['metadata'].items())
    return f'<div class="original-version" data-original="{year}"><p class="version-label">{year} · {esc(v["type"])}</p><dl class="original-meta">{meta}</dl><div class="original-body">{v["body"]}</div>{footer(v)}</div>'
def build(output, check=False):
    catalog=load('catalog'); cls=load('classes'); house=load('house-rules'); overview=load('overview')
    assert len(catalog)==391 and len({s['id'] for s in catalog})==len(catalog)
    for s in catalog:
        assert s['school'] in SCHOOLS
        for v in s['versions'].values():
            assert hashlib.sha256(v['body'].encode()).hexdigest()==v['body_sha256'], 'Original spell body changed; review and update its checksum deliberately.'
    assert len(cls['slots'])==20 and all(len(r)==9 for r in cls['slots'])
    assert sum(cls['slots'][-1])==17 and cls['classes'][0]['prepared'][-1]==22
    def current(s): return house.get(s['id'],{}).get('level',s['official_level'])
    def level_html(s):
        def cap(n): return 'Cantrip' if n==0 else f'Level {n}'
        official=cap(s['official_level']); custom=cap(current(s))
        return f'<span data-mode="house">{custom}</span><span data-mode="official">{official}</span>' if custom!=official else official
    sidebar=[]; cards=[]
    for s in catalog:
        id=s['id']; h=house.get(id); v=s['versions']['2024']; hv=copy.deepcopy(v)
        if h:
            # Full-effect overrides keep user-supplied wording separate from official editions.
            if 'body_override' in h:
                assert not h['replacements'], f'Use a full effect or substitutions, not both: {id}'
                assert isinstance(h['body_override'],str) and h['body_override'].strip()
                hv['body']=h['body_override']
            for before,after in h['replacements']:
                assert hv['body'].count(before)==1, f'Ambiguous override for {id}'
                hv['body']=hv['body'].replace(before,after)
        school=s['school']; icon=SCHOOLS[school]; cats=s['categories']+(['house-rule'] if h else [])
        member=' '.join(norm(c) for c in v['classes'].split(','))
        school_icon=f'<img src="{icon}" width="26" height="26" alt="" draggable="false" loading="lazy" decoding="async">'
        sidebar.append(f'<li data-spell="{id}"><a href="#{id}" class="spell-link">{school_icon}<span><strong>{esc(s["name"])}</strong><small>{level_html(s)} · {school}</small></span>'+('<span class="house-dot" title="House-rule version available"></span>' if h else '')+'</a></li>')
        tags=''.join(f'<span class="{esc(t["class"])}">{esc(t["text"])}</span>' for t in s['tags'])
        if h: tags='<span class="tag tag-house"><span data-mode="house">House Rule</span><span data-mode="official">House Rule available</span></span>'+tags
        if re.search(r'\bConcentration\b',v['metadata'].get('duration',''),re.I): tags+='<span class="tag">Concentration</span>'
        if re.search(r'\britual\b',v['metadata'].get('casting time',''),re.I): tags+='<span class="tag">Ritual</span>'
        head=f'<header class="spell-heading"><div class="title-main"><div class="title-line"><h2 tabindex="-1">{esc(s["name"])}</h2><div class="heading-tags">{tags}</div></div><p class="eyebrow">{level_html(s)} · {school}</p></div><div class="heading-aside"><img class="school-emblem" draggable="false" src="{icon}" width="82" height="78" alt="{school}" decoding="async" loading="lazy"></div></header>'
        meta=metadata(v,s['official_level'],school)
        primary=body(v)
        if h:
            meta='<div data-mode="house">'+metadata(hv,current(s),school,h,s['official_level'])+'</div><div data-mode="official">'+meta+'</div>'
            primary='<div data-mode="house">'+body(hv,h)+'</div><div data-mode="official">'+primary+'</div>'
        compare=tabs(id+'-editions','Original editions',[('2024','2024',version(v,'2024')),('2014','2014',version(s['versions']['2014'],'2014'))])+''.join(s['notes'])
        defs=[('spell','Spell',primary)]
        if h: defs.append(('why','Why this version?','<div class="why"><h3>House-rule change</h3><p>'+esc(h['summary'])+'</p><p>This is the recorded change to the 2024 version. The original editions remain available in Compare versions.</p></div>'))
        defs.append(('compare','Compare versions',compare))
        if s['discussion']: defs.append(('discussion','Discussion',''.join(s['discussion'])))
        cards.append(f'<article class="spell-card" id="{id}" data-name="{esc(s["name"].lower())}" data-school="{school}" data-level-official="{s["official_level"]}" data-level-house="{current(s)}" data-categories="{esc(" ".join(cats))}" data-classes="{esc(member)}">'+head+meta+tabs(id+'-info','Spell information',defs)+'</article>')
    class_defs=[]
    for c in cls['classes']:
        assert len(c['features'])==len(c['cantrips'])==len(c['prepared'])==20
        if c['id']!='wizard': assert c['prepared']==list(map(sum,cls['slots']))
        headings=['Level','Proficiency<br>Bonus','Class<br>Features']+([esc(c['resource']).replace(' ','<br>',1)] if c.get('resource') else [])+['Cantrips','Prepared<br>Spells']
        cols=['level','prof','features']+(['resource'] if c.get('resource') else [])+['cantrips','prepared']
        table=f'<div class="table-wrap" tabindex="0" aria-label="{c["name"]} class table"><table class="slot-table" data-caster="{c["id"]}"><caption>{c["name"]} Features</caption><colgroup>'+''.join(f'<col class="slot-{x}-col">' for x in cols)+'</colgroup><colgroup span="9" class="slot-number-col"></colgroup>'
        table+=f'<thead><tr><td colspan="{len(headings)}" aria-hidden="true"></td><th colspan="9" scope="colgroup">—Spell Slots per Spell Level—</th></tr><tr>'+''.join('<th scope="col">'+h+'</th>' for h in headings)+''.join(f'<th scope="col">{i}</th>' for i in range(1,10))+'</tr></thead><tbody>'
        for i in range(20):
            values=[i+1,'+'+str(2+i//4),c['features'][i]]+([c['values'][i]] if c.get('resource') else [])+[c['cantrips'][i],c['prepared'][i]]+[n or '–' for n in cls['slots'][i]]
            table+='<tr><th scope="row">'+str(i+1)+'</th>'+''.join('<td'+(' class="features"' if j==2 else '')+'>'+esc(value)+'</td>' for j,value in enumerate(values) if j>0)+'</tr>'
        table+='</tbody></table></div>'; class_defs.append((c['id'],c['name'],table))
    css=(ROOT/'src/app.css').read_bytes(); js=(ROOT/'src/app.js').read_bytes()
    assets=ROOT/'assets'; assets.mkdir(exist_ok=True)
    cssname='app.'+hashlib.sha256(css).hexdigest()[:12]+'.css'; jsname='app.'+hashlib.sha256(js).hexdigest()[:12]+'.js'
    if check:
        assert (assets/cssname).read_bytes()==css and (assets/jsname).read_bytes()==js, 'Generated assets are stale.'
    else:
        (assets/cssname).write_bytes(css); (assets/jsname).write_bytes(js)
    def select(id,label,options):
        return f'<div class="control"><label for="{id}">{label}</label><select id="{id}" disabled>'+''.join(f'<option value="{esc(v)}">{esc(t)}</option>' for v,t in options)+'</select></div>'
    toolbar='<div class="control search-control"><label for="search">Search</label><input id="search" type="search" placeholder="Spell name or text" autocomplete="off" disabled></div>'
    toolbar+=select('spell-class','Class',[('','All classes')]+[(c.lower(),c) for c in CLASS_NAMES])
    toolbar+=select('level','Level',[('','All levels')]+[(str(i),'Cantrip' if not i else f'Level {i}') for i in range(10)])
    toolbar+=select('label','Category',[('','All spells'),('house-rule','House Rule'),('new','New to PHB'),('redesigned','Redesigned'),('revised','Revised'),('buff','Buff'),('nerf','Nerf'),('material-cost','Material Cost')])
    toolbar+=select('jump','Jump to spell',[('','Choose a spell')]+[(s['id'],s['name']) for s in catalog])
    toolbar+='<div class="rules-controls"><label class="rules-label"><input id="house-rules-toggle" type="checkbox" checked disabled>House-rule spells</label><div class="results"><span id="visible-count" role="status" aria-live="polite">391 spells</span><button type="button" id="clear" disabled>Clear</button></div></div>'
    page='''<!doctype html>
<html lang="en" data-rules="house">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="description" content="Spellwright: 2014 and 2024 spell reference, house-rule versions, class filters and full-caster spell slots.">
<title>Spellwright — D&amp;D Spell Reference &amp; House Rules</title>
<link rel="icon" type="image/svg+xml" href="favicon.svg?v=d20-brand-1">
<!-- State only; the complete layout and rules are already static HTML. -->
<script>try{document.documentElement.dataset.rules=new URLSearchParams(location.search).get('rules')==='official'?'official':'house'}catch(e){}</script>
'''+f'<link rel="stylesheet" href="assets/{cssname}">\n<script defer src="assets/{jsname}"></script>\n</head>\n<body>\n'
    page+='<a class="skip-link" href="#spells">Skip to spells</a><header class="site-header"><div class="header-inner"><a class="brand" href="#spells"><img src="favicon.svg?v=d20-brand-1" width="52" height="52" alt=""><div><h1>Spellwright</h1><small>D&amp;D Spell Reference &amp; House Rules</small></div></a><nav class="section-nav" aria-label="Page sections"><a href="#spell-slots">Spell Slots</a><a href="#spells">Browse spells</a></nav><details class="overview"><summary>Overview</summary><div class="counts">'+''.join('<span>'+esc(x)+'</span>' for x in overview)+f'<span>{len(house)} house rules</span></div></details></div></header>'
    page+='<nav class="toolbar" aria-label="Find spells"><div class="toolbar-inner">'+toolbar+'</div></nav>'
    page+='<main class="content"><section id="spell-slots" class="slot-section" aria-labelledby="spell-slots-heading"><header class="slot-view-header"><h2 id="spell-slots-heading" tabindex="-1">Spell Slots (Full Casters)</h2><a class="back-to-spells" href="#spells">Back to spells</a></header>'+tabs('caster','Full caster class',class_defs)+'</section>'
    # Content-first DOM matches phone reading/tab order; desktop CSS places the list left.
    navigation='<aside class="sidebar" aria-label="Spell navigation"><details id="spell-menu" open><summary>Spells <span id="sidebar-count">(391)</span></summary><nav aria-label="Spell list"><ul>'+''.join(sidebar)+'</ul></nav></details></aside>'
    page+='<div class="reader-layout" id="spells"><div class="reader-detail"><div id="empty" hidden><p>No spells match these filters.</p><button id="reset" type="button">Clear filters</button></div>'+''.join(cards)+'</div>'+navigation+'</div></main>'
    page+='<footer class="site-footer">Spellwright · 2014 &amp; 2024 editions · House-rule versions are marked in purple.</footer></body></html>\n'
    return page
if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',default='index.html'); parser.add_argument('--check',action='store_true'); args=parser.parse_args()
    result=build(args.output,args.check)
    target=ROOT/args.output
    if args.check:
        if not target.exists() or target.read_text(encoding='utf-8')!=result: raise SystemExit('Generated HTML is out of date; run tools/build.py.')
        print('Build is deterministic and up to date.')
    else:
        target.write_text(result,encoding='utf-8'); print(f'Built {args.output}: {len(result.encode()):,} bytes; all content rendered before JavaScript.')
