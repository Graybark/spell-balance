"""Import the public 2024 indexes; retain full text only from Free Basic Rules (SRD).
Usage: python tools/import_magic_items.py
Normal builds and browsing use the resulting local data without network access.
"""
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlsplit, unquote, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup, SoupStrainer
import hashlib, json, re, time
from datetime import date
ROOT=Path(__file__).resolve().parents[1]
INDEX='https://roll20.net/compendium/dnd5e/Rules:Magic%20Items?expansion='
RARITIES=('Very Rare','Uncommon','Common','Rare','Legendary','Artifact','Varies')
def key(url):
    return unquote(urlsplit(url).path).split('/dnd5e/')[-1].casefold()
def identifier(url):
    part=unquote(urlsplit(url).path).split('/dnd5e/')[-1]
    kind,_,name=part.partition(':')
    return 'item-'+('template-' if kind.lower()=='templates' else '')+re.sub(r'[^a-z0-9]+','-',name.casefold()).strip('-')
def fetch(url):
    error=None
    for attempt in range(3):
        try:
            return urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=40).read()
        except Exception as e:
            error=e
            time.sleep(attempt+1)
    raise RuntimeError(str(error)+' '+url)
def index(expansion):
    url=INDEX+expansion
    soup=BeautifulSoup(fetch(url),'html.parser',parse_only=SoupStrainer('div',class_=lambda c:c and 'page' in c.split()))
    heading=next((h for h in soup.find_all(['h2','h3']) if h.get_text(' ',strip=True)=='Magic Items A–Z'),None)
    assert heading is not None,'Missing 2024 A–Z index'
    ul=heading.find_next('ul')
    records=[]
    for a in ul.select('a[href]'):
        href=urljoin(url,a['href'])
        if not any(p in href for p in ('/Items:','/Templates:')):continue
        li=a.find_parent('li')
        family=a
        parent_ul=li.find_parent('ul')
        while parent_ul is not ul:
            # Roll20 places child ULs beside the owning LI, rather than inside it.
            owner=parent_ul.parent if parent_ul.parent.name=='li' else parent_ul.find_previous_sibling('li')
            if owner:
                owner_link=owner.find('a',href=True)
                if owner_link:family=owner_link
            parent_ul=parent_ul.find_parent('ul')
            assert parent_ul is not None,'Unowned variant list'
        records.append({'name':re.sub(r'\s*\(Template\)$','',a.get_text()),
                        'key':key(href),'url':href,'family_key':key(urljoin(url,family['href'])),
                        'is_template':'/Templates:' in href,'id':identifier(href)})
    assert len(records)>300,(url,len(records))
    assert len({r['key'] for r in records})==len(records),'Duplicate source paths'
    return records
def metadata(body):
    p=None;label=''
    for candidate in body.find_all(['p','em','i']) if body else []:
        value=candidate.get_text(' ',strip=True)
        if len(value)<400 and re.match(r'^(Armor|Potion|Ring|Rod|Scroll|Staff|Wand|Weapon|Wondrous Item)\b',value,re.I) and re.search(r'\b('+('|'.join(RARITIES))+r')\b',value,re.I):
            p=candidate;label=value;break
    found=re.search(r'\b('+('|'.join(RARITIES))+r')\b',label,re.I)
    if not found:return {'type':'Not listed','rarity':'Not listed','attunement':None,'attunement_text':'Not listed','subtitle':''},None
    rarity=next(v for v in RARITIES if v.casefold()==found.group().casefold())
    category=label.split('(')[0].split(',')[0].strip()
    if category not in ('Armor','Potion','Ring','Rod','Scroll','Staff','Wand','Weapon','Wondrous Item'):category='Not listed'
    attune=re.search(r'Requires Attunement[^)]*',label,re.I)
    return {'type':category,'rarity':rarity,'attunement':bool(attune),
            'attunement_text':attune.group() if attune else 'Not required','subtitle':label},p
def item(record,full):
    html=fetch(record['url'])
    soup=BeautifulSoup(html,'html.parser',parse_only=SoupStrainer('div',class_=lambda c:c and 'page' in c.split()))
    title=soup.select_one('.page__title')
    assert title and re.sub(r'[^a-z0-9]','',title.get_text(' ',strip=True).casefold())==re.sub(r'[^a-z0-9]','',record['name'].casefold()),('Wrong item edition/title',record['name'])
    selected=soup.select_one('#expansion-select option[selected]')
    if selected:assert '(2024)' in selected.get_text(),('Wrong edition',record['name'])
    body=soup.select_one('.page__body')
    meta,header=metadata(body)
    result={'metadata':meta,'metadata_source':record['url']}
    if not full:return result
    assert body and header is not None,('Missing public item text',record['name'])
    header.decompose()
    for el in list(body.select('script,style,img,picture,figure,iframe,svg,button,.clearfix')):
        el.decompose()
    before=re.sub(r'\s+',' ',body.get_text())
    original_paragraphs=len(body.select('p'))
    original_tables=len(body.select('table'))
    for el in list(body.find_all(True)):
        if el.name in ('div','span'):el.unwrap();continue
        if el.name in ('h1','h2','h3'):el.name='h4'
        allowed={}
        if el.name=='a':
            href=urljoin(record['url'],el.get('href',''))
            if urlsplit(href).scheme not in ('http','https'):el.unwrap();continue
            allowed={'href':href}
        elif el.name in ('th','td'):
            allowed={k:v for k,v in el.attrs.items() if k in ('colspan','rowspan','scope')}
        el.attrs=allowed
    clean=body.decode_contents()
    after=re.sub(r'\s+',' ',BeautifulSoup(clean,'html.parser').get_text())
    assert before==after,('Source text changed in sanitization',record['name'])
    assert original_paragraphs==len(BeautifulSoup(clean,'html.parser').select('p'))
    result['description']={'html':clean,'sha256':hashlib.sha256(clean.encode()).hexdigest(),
                           'source_url':record['url'],'paragraphs':original_paragraphs,'tables':original_tables}
    return result
def main():
    free=index('33335'); dmg=index('33359')
    free_by={r['key']:r for r in free}
    records={r['key']:dict(r) for r in dmg}
    for r in free:records[r['key']]=dict(r)
    print('INDEX_COUNTS',len(free),len(dmg),len(records),flush=True)
    # Fetch every public SRD entry. For other families, retain factual metadata only.
    tasks={r['key']:(r,True) for r in free}
    for r in dmg:
        if r['key']==r['family_key'] and r['key'] not in tasks:tasks[r['key']]=(r,False)
    cache=ROOT/'data/magic-items-import-cache.json'
    fetched=json.loads(cache.read_text(encoding='utf-8')) if cache.exists() else {}
    tasks={k:v for k,v in tasks.items() if k not in fetched or fetched[k]['metadata']['type']=='Not listed'}
    print('SOURCE_TASKS',len(tasks),'CACHED',len(fetched),flush=True)
    errors=[]
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures={pool.submit(item,r,full):(k,r,full) for k,(r,full) in tasks.items()}
        for i,f in enumerate(as_completed(futures),1):
            k,r,full=futures[f]
            try:fetched[k]=f.result()
            except Exception as e:
                if full:errors.append([r['name'],str(e)])
                else:fetched[k]={'metadata':{'type':'Not listed','rarity':'Not listed','attunement':None,'attunement_text':'Not listed','subtitle':''},'metadata_source':r['url'],'metadata_error':str(e)}
            if i%25==0 or i==len(futures):
                cache.write_text(json.dumps(fetched,ensure_ascii=False),encoding='utf-8')
                print('FETCHED',i,'/',len(futures),'ERRORS',len(errors),flush=True)
    cache.write_text(json.dumps(fetched,ensure_ascii=False),encoding='utf-8')
    assert not errors,errors
    descriptions={k:v['description'] for k,v in fetched.items() if 'description' in v}
    entries=[]
    for k,r in records.items():
        origin=k if k in fetched else r['family_key']
        f=fetched.get(origin)
        assert f is not None,('Missing family metadata',r)
        r.update(f['metadata'])
        r['metadata_source']=f['metadata_source']
        r['description_key']=k if k in descriptions else (r['family_key'] if r['family_key'] in descriptions else None)
        r['description_kind']='direct' if k in descriptions else ('family' if r['description_key'] else 'reference')
        r['source']='Free Basic Rules (2024)' if r['description_key'] else 'Dungeon Master’s Guide (2024)'
        entries.append(r)
    entries.sort(key=lambda r:(r['name'].casefold(),r['key']))
    assert len({r['id'] for r in entries})==len(entries),'ID collision'
    coverage={'free_index_count':len(free),'dmg_index_count':len(dmg),'entry_count':len(entries),
              'full_description_count':sum(bool(r['description_key']) for r in entries),
              'reference_only_count':sum(not r['description_key'] for r in entries),
              'template_count':sum(r['is_template'] for r in entries),
              'metadata_unknown_count':sum(r['type']=='Not listed' for r in entries),
              'free_index_keys':sorted(free_by),'dmg_index_keys':sorted(r['key'] for r in dmg)}
    output={'edition':'2024','checked_on':date.today().isoformat(),'index_sources':[INDEX+'33335',INDEX+'33359'],
            'coverage':coverage,'descriptions':descriptions,'entries':entries}
    (ROOT/'data/magic-items.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('COVERAGE',json.dumps({k:v for k,v in coverage.items() if not k.endswith('_keys')}),flush=True)
if __name__=='__main__':main()
