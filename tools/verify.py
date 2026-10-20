"""Content/structure checks. No network required."""
from pathlib import Path
from bs4 import BeautifulSoup
from collections import Counter
import hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[1]
def normalized(html):
    return re.sub(r'\s+',' ',BeautifulSoup(html,'html.parser').get_text()).strip()
def main():
    filename=sys.argv[1] if len(sys.argv)>1 else 'index.html'
    raw=(ROOT/filename).read_text(encoding='utf-8'); page=BeautifulSoup(raw,'html.parser')
    data=json.loads((ROOT/'data/catalog.json').read_text()); tables=json.loads((ROOT/'data/classes.json').read_text())
    # Match Abjuration: real path-only SVG assets, never embedded raster images.
    import xml.etree.ElementTree as ET
    school_files={s['school']:s['school'].lower()+'.svg' for s in data}
    for school,file in school_files.items():
        vector=ET.fromstring((ROOT/file).read_text())
        assert vector.attrib['aria-label']==school
        assert {e.tag.rsplit('}',1)[-1] for e in vector.iter()}=={'svg','title','path'}
        assert not any(k.endswith('href') for e in vector.iter() for k in e.attrib)
    for card in page.select('.spell-card'):
        want=school_files[card['data-school']]
        assert card.select_one('.school-emblem')['src']==want
        assert page.select_one(f'.sidebar a[href="#{card["id"]}"] img')['src']==want
    assert len(page.select('.spell-card'))==len(data)==391
    assert not page.select('.permalink'), 'Spell-card permalink controls must remain removed.'
    assert not page.select('details#spell-slots, #spell-slots > summary')
    assert page.select_one('section#spell-slots[aria-labelledby=spell-slots-heading]')
    assert page.select_one('.section-nav a[href="#spell-slots"]')
    assert page.select_one('#spell-slots .back-to-spells[href="#spells"]')
    for record in data:
        assert page.find(id=record['id']) is not None
        assert page.select_one(f'.sidebar a[href="#{record["id"]}"]') is not None
    ids=[x['id'] for x in page.select('[id]')]
    assert len(set(ids))==len(ids), [x for x,n in Counter(ids).items() if n>1]
    assert page.select_one('.site-header .brand h1').get_text()=='Spellwright'
    assert page.select_one('.site-header .brand small').get_text()=='D&D Spell Reference & House Rules'
    assert page.title.get_text()=='Spellwright — D&D Spell Reference & House Rules'
    assert not page.select('.hero,.notice,.reader-source-store')
    assert 'Every spell is open on this page' not in raw
    scripts=page.select('script[src]'); assert len(scripts)==1 and scripts[0].has_attr('defer') and scripts[0].parent==page.head
    assert len(page.select('link[rel=stylesheet]'))==1
    assert all(name not in raw for name in ['house-rules.js','rules-core.js','spell-reader.js','reader-ready'])
    for link in page.select('link[href],img[src],script[src]'):
        path=link.get('href',link.get('src')).split('?')[0]
        assert (ROOT/path).is_file(),path
    for s in data:
        card=page.find(id=s['id']); assert card is not None
        assert card.h2.get_text()==s['name']
        assert card.select_one('.school-emblem')['alt']==s['school']
        for year,v in s['versions'].items():
            assert hashlib.sha256(v['body'].encode()).hexdigest()==v['body_sha256']
            pane=card.select_one(f'[data-panel="{year}"] .original-version')
            original=pane.select_one('.original-body') if not v['absent'] else pane
            assert normalized(str(original))==normalized(v['body']),f'{s["id"]} {year}: rules text changed'
            for a in BeautifulSoup(v['body'],'html.parser').select('a[href]'):
                assert original.find('a',href=a['href']),f'Missing source link {a["href"]}'
        for note in s['notes']+s['discussion']:
            n=BeautifulSoup(note,'html.parser')
            assert normalized(note) in normalized(str(card)),f'Missing annotation on {s["id"]}'
            for a in n.select('a[href]'): assert card.find('a',href=a['href'])
    for c in tables['classes']:
        rows=page.select(f'table[data-caster="{c["id"]}"] tbody tr');assert len(rows)==20
        for i,row in enumerate(rows):
            want=[str(i+1),'+'+str(2+i//4),c['features'][i]]+([str(c['values'][i])] if c.get('resource') else [])+[str(c['cantrips'][i]),str(c['prepared'][i])]+[str(x or '–') for x in tables['slots'][i]]
            got=[cell.get_text() for cell in row.find_all(['th','td'],recursive=False)]
            assert got==want,f'{c["id"]} row {i+1}'
    for id,level in [('fireball','3'),('forcecage','9'),('melf-s-acid-arrow','1'),('wall-of-force','5'),('lightning-bolt','3')]:
        assert page.find(id='spell-'+id)['data-level-house']==level
    f=page.find(id='spell-fireball')
    assert 'taking 6d6 Fire damage' in f.select_one('[data-panel=spell] [data-mode=house]').get_text()
    assert 'taking 8d6 Fire damage' in f.select_one('[data-panel="2024"]').get_text()
    assert len(page.select('.balance-note'))==17
    from house_rules_test import check_rule_content
    check_rule_content(page, data, json.loads((ROOT/'data/house-rules.json').read_text()))
    # User-supplied PHB 2014 screenshot confirms additive, not asterisk, bonuses.
    elemental=page.find(id='spell-elemental-weapon').select_one('[data-panel="2014"] .original-body').get_text()
    for phrase in ['has a +1 bonus to attack rolls','attack rolls increases to +2','the bonus increases to +3']:
        assert phrase in elemental, 'Elemental Weapon 2014 attack bonus regression: '+phrase
    assert '*1' not in elemental and '*2' not in elemental
    # The supplied 2024 Teleport reference must remain a semantic table, not a list.
    teleport=page.find(id='spell-teleport')
    outcome_tables=teleport.select('.teleport-outcome-table')
    assert len(outcome_tables)==2, 'Teleport table must exist in Spell and Compare 2024.'
    expected_rows=[
        ['Permanent circle','–','–','–','01–00'],
        ['Linked object','–','–','–','01–00'],
        ['Very familiar','01–05','06–13','14–24','25–00'],
        ['Seen casually','01–33','34–43','44–53','54–00'],
        ['Viewed once or described','01–43','44–53','54–73','74–00'],
        ['False destination','01–50','51–00','–','–'],
    ]
    for table in outcome_tables:
        assert table.caption.get_text()=='Teleportation Outcome'
        assert [c.get_text() for c in table.select('thead th[scope=col]')]==['Familiarity','Mishap','Similar Area','Off Target','On Target']
        assert [[c.get_text() for c in row.find_all(['th','td'],recursive=False)] for row in table.select('tbody tr')]==expected_rows
        assert len(table.select('tbody th[scope=row]'))==6
    assert not teleport.select('[data-panel="2014"] .teleport-outcome-table')
    print(json.dumps({'result':'PASS','original_edition_records':782,'spell_cards':391,'discussion_notes':17,'class_rows':100,'static_header':True,'static_tables':True,'unique_ids':len(ids),'one_deferred_script':True}))
if __name__=='__main__':main()
