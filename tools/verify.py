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
    assert len(page.select('.spell-card'))==len(data)==391
    ids=[x['id'] for x in page.select('[id]')]
    assert len(set(ids))==len(ids), [x for x,n in Counter(ids).items() if n>1]
    assert page.select_one('.site-header .brand h1').get_text()=='Spell Balance'
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
    for id,level in [('fireball','3'),('forcecage','9'),('melf-s-acid-arrow','1'),('wall-of-force','7')]:
        assert page.find(id='spell-'+id)['data-level-house']==level
    f=page.find(id='spell-fireball')
    assert 'taking 6d6 Fire damage' in f.select_one('[data-panel=spell] [data-mode=house]').get_text()
    assert 'taking 8d6 Fire damage' in f.select_one('[data-panel="2024"]').get_text()
    assert len(page.select('.balance-note'))==17
    print(json.dumps({'result':'PASS','original_edition_records':782,'spell_cards':391,'discussion_notes':17,'class_rows':100,'static_header':True,'static_tables':True,'unique_ids':len(ids),'one_deferred_script':True}))
if __name__=='__main__':main()
