"""One-time import from the pre-rebuild document; not part of browser startup.
Run before build.py. Original rules, markup, citations and IDs are retained.
"""
from pathlib import Path
from bs4 import BeautifulSoup
import hashlib, json, re, sys
ROOT = Path(__file__).resolve().parents[1]
def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()
def main():
    dest = ROOT / 'data/catalog.json'
    if dest.exists():
        print('Already migrated; using data/catalog.json'); return
    source = ROOT / (sys.argv[1] if len(sys.argv)>1 else 'index.html')
    raw = source.read_text(encoding='utf-8')
    soup = BeautifulSoup(raw, 'html.parser')
    catalog = []
    for card in soup.select('.spell-card'):
        versions={}
        for year, selector in [('2024','.version-2024'),('2014','.version-2014,.version-absent')]:
            v = card.select_one(selector)
            assert v is not None
            metadata = {i.dt.get_text(strip=True).lower():i.dd.get_text() for i in v.select('.meta-item')}
            # Exclude only known title/metadata wrappers, never rules/stat blocks.
            body=''.join(str(c) for c in v.find_all(recursive=False) if not (c.name=='h3' or set(c.get('class',[])) & {'version-head','spell-type','classes','metadata'}))
            t=v.select_one('.spell-type'); cl=v.select_one('.classes'); note=v.select_one('.edition-note')
            versions[year]={'type':t.get_text() if t else '', 'classes':cl.get_text() if cl else '',
                'source':note.get_text() if note else '', 'metadata':metadata, 'body':body,
                'body_sha256':digest(body), 'absent':'version-absent' in v.get('class',[])}
        tags=[{'text':t.get_text(),'class':' '.join(t.get('class',[]))} for t in card.select('.heading-tags > .tag')]
        catalog.append({'id':card['id'],'name':card.h2.get_text(), 'official_level':int(card['data-level']),
                        'school':versions['2024']['type'].split('·')[-1].strip(),
                        'categories':card.get('data-categories','').split(), 'tags':tags,'versions':versions,
                        'notes':[str(n) for n in card.select('.review-note,.revised-note,.errata-note,.field-signals')],
                        'discussion':[str(n) for n in card.select('.balance-note')]})
    assert len(catalog)==391 and len({x['id'] for x in catalog})==391
    assert sum(bool(x['discussion']) for x in catalog)==17
    slots=json.loads(re.search(r'const slots = (\[.*?\]);',raw)[1])
    classes=json.loads(re.search(r'const classes = (\[.*?\]);',raw)[1])
    rules=(ROOT/'rules-core.js').read_text()
    wizard=json.loads(re.search(r'const wizardPrepared = (\[.*?\]);',rules)[1])
    for c in classes:
        c['prepared']=wizard if c['id']=='wizard' else list(map(sum,slots))
    assert wizard[-1]==22 and sum(slots[-1])==17
    house={
      'spell-fireball':{'level':3,'summary':'Base damage: 8d6 → 6d6. The +1d6 increase per higher-level slot is unchanged.', 'replacements':[['taking 8d6 Fire damage','taking 6d6 Fire damage']], 'highlight':'6d6'},
      'spell-forcecage':{'level':9,'summary':'Spell level: 7 → 9. All other effects and requirements are unchanged.', 'replacements':[]},
      'spell-melf-s-acid-arrow':{'level':1,'summary':'Spell level: 2 → 1. Base damage is unchanged; upcasting now scales from level 1.', 'replacements':[['for each spell slot level above 2.','for each spell slot level above 1.']], 'highlight':'1'},
      'spell-wall-of-force':{'level':7,'summary':'Spell level: 5 → 7. All other effects and requirements are unchanged.', 'replacements':[]}}
    counts=[c.get_text(' ',strip=True) for c in soup.select('.counts > .count')]
    for name,value in [('catalog',catalog),('classes',{'slots':slots,'classes':classes}),('house-rules',house),('overview',counts)]:
        path=ROOT/'data'/f'{name}.json'; path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Imported 391 spells, 782 original-edition records, 17 discussions and 100 class rows.')
if __name__=='__main__': main()
