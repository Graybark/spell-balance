"""Recover paragraph breaks only where they match the corresponding Roll20 entry.
Never edit spell wording, edition metadata, or house-rule overrides.
"""
import json, re, time, requests, hashlib, unicodedata
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import quote
from difflib import SequenceMatcher

catalog=Path('data/catalog.json')
data=json.loads(catalog.read_text(encoding='utf-8'))
session=requests.Session()
session.headers.update({'User-Agent':'Mozilla/5.0 (compatible; SpellwrightParagraphAudit/1.0)'})
results=[]
def plain(x):
    return unicodedata.normalize('NFKD',x).replace('’',"'").replace('—','-').replace('–','-')
def tokens(x):
    return re.findall(r"[a-z0-9]+",plain(x).lower())
def source_paragraphs(name,year):
    if year=='2024': url='https://roll20.net/compendium/dnd5e/Spells%3A'+quote(name,safe='')+'?expansion=32231'
    else: url='https://roll20.net/compendium/dnd5e/'+quote(name,safe='')
    res=session.get(url,timeout=18)
    if res.status_code!=200: return [],'http-'+str(res.status_code)
    soup=BeautifulSoup(res.text,'html.parser')
    # 2024 page__body; 2014 spell description paragraphs are in the document body.
    pp=soup.select('.page__body p') if year=='2024' else soup.select('p')
    return [p for p in pp if len(tokens(p.get_text(' ',strip=True)))>5],None

def find_paras(source,target):
    tt=tokens(target)
    # Start with the paragraph whose first 7 tokens match the stored text.
    starts=[]
    for i,p in enumerate(source):
        st=tokens(p.get_text(' ',strip=True))
        if len(st)>=7 and st[:7]==tt[:7]: starts.append(i)
    if not starts: return None,'no-matching-source-start'
    start=starts[0]
    ps=[]
    for p in source[start:start+25]:
        ps.append(p.get_text(' ',strip=True))
        combined=tokens(' '.join(ps))
        if len(combined)>len(tt)*1.5:break
        if len(combined)>=len(tt)*.7 and combined[-6:]==tt[-6:]: break
    st=tokens(' '.join(ps))
    sim=SequenceMatcher(None,st,tt,autojunk=False).ratio()
    if sim < .78: return None,'low-source-similarity-'+str(round(sim,2))
    return ps,None

def update_one(body,paras):
    # Only plain-text, single-paragraph spell descriptions are touched.
    m=re.fullmatch(r'(<div class="spell-text spell-text-(?:2014|2024)"><p>)([^<]+)(</p></div>)',body,flags=re.S)
    if not m: return None,'complex-markup'
    raw=m.group(2)
    breaks=[]
    left=0
    for p in paras[:-1]:
        t=tokens(p)
        if len(t)<8: continue
        # Match the last 8 Roll20 words in the unchanged local text.
        words=re.findall(r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?",plain(p))
        anchor=' '.join(words[-8:])
        # Search on a normalized shadow string, with a character map back to original.
        shadow=plain(raw)
        pattern=r'\b'+r'\W+'.join(map(re.escape,words[-8:]))+r'\b'
        matches=list(re.finditer(pattern,shadow,re.I))
        matches=[a for a in matches if a.end()>left]
        if len(matches)!=1: return None,'ambiguous-boundary'
        # Move past source terminal punctuation if present (e.g. comma/period).
        end=matches[0].end()
        while end<len(raw) and raw[end] in '.!?:;”"\' ':end+=1
        if end>=len(raw) or end<=left: return None,'bad-boundary'
        breaks.append(end)
        left=end
    if not breaks: return None,'no-source-breaks'
    rebuilt=m.group(1)+('</p><p>'.join(raw[a:b].strip() for a,b in zip([0]+breaks,breaks+[len(raw)])))+m.group(3)
    if BeautifulSoup(rebuilt,'html.parser').get_text(' ',strip=True)!=BeautifulSoup(body,'html.parser').get_text(' ',strip=True):
        return None,'text-changed'
    return rebuilt,None

for i,s in enumerate(data):
    for year,v in s['versions'].items():
        if v.get('absent'):continue
        count=len(re.findall(r'<p(?:\s|>)',v['body']))
        wordcount=len(tokens(BeautifulSoup(v['body'],'html.parser').get_text(' ',strip=True)))
        if count!=1 or wordcount<90:continue
        record={'spell':s['name'],'edition':year,'words':wordcount}
        try:
            ps,error=source_paragraphs(s['name'],year)
            if error: record['result']=error
            else:
                matched,error=find_paras(ps,BeautifulSoup(v['body'],'html.parser').get_text(' ',strip=True))
                if error:record['result']=error
                else:
                    changed,error=update_one(v['body'],matched)
                    if error:record['result']=error
                    else:
                        v['body']=changed
                        v['body_sha256']=hashlib.sha256(changed.encode('utf-8')).hexdigest()
                        record['result']='updated';record['paragraphs']=len(matched)
        except Exception as e:
            record['result']='error-'+type(e).__name__
        results.append(record)
        print(record,flush=True)
        time.sleep(.12)
catalog.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
Path('/tmp/roll20-paragraph-audit.json').write_text(json.dumps(results,indent=2))
print('SUMMARY',len(results),'updated',sum(x['result']=='updated' for x in results),flush=True)
