"""Repair only two 2014 attack-bonus signs confirmed by the user's screenshot."""
from pathlib import Path
import copy, hashlib, json, os

def blob(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()

expected={'data/catalog.json':'64dbbab3ce86fbdefcbdedf37798a0a58d419729','data/source-verification.json':'510b259efda619b35b16c9aff95e76ac9fbed5e6','tools/verify.py':'eabeee2efd447b1a11c8d4d07d88b7b1c22b1149'}
for path,sha in expected.items():
    assert blob(Path(path).read_bytes())==sha, 'Source changed; stop: '+path

path=Path('data/catalog.json')
original=json.loads(path.read_text(encoding='utf-8')); data=copy.deepcopy(original)
spell=next(s for s in data if s['id']=='spell-elemental-weapon')
version=spell['versions']['2014']; before=version['body']
assert hashlib.sha256(before.encode()).hexdigest()==version['body_sha256']=='788b9c323b0d337a32419393c264c0c498ac46c45b1ee7eed51bf17371127861'
after=before
for old,new in [('has a *1 bonus to attack rolls','has a +1 bonus to attack rolls'),('attack rolls increases to *2','attack rolls increases to +2')]:
    assert after.count(old)==1
    after=after.replace(old,new)
assert len(before)==len(after) and sum(a!=b for a,b in zip(before,after))==2
version['body']=after; version['body_sha256']=hashlib.sha256(after.encode()).hexdigest()
for old,new in zip(original,data):
    if old['id']!='spell-elemental-weapon': assert old==new
    else:
        assert old['versions']['2024']==new['versions']['2024']
        assert {k:v for k,v in old.items() if k!='versions'}=={k:v for k,v in new.items() if k!='versions'}
        assert {k:v for k,v in old['versions']['2014'].items() if k not in ('body','body_sha256')}=={k:v for k,v in new['versions']['2014'].items() if k not in ('body','body_sha256')}
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

html=Path(os.environ.get('REFERENCE_HTML','index.html')).read_text(encoding='utf-8')
assert html.count(before)==1, 'Expected exactly one original 2014 body in generated HTML.'
Path('/tmp/expected-elemental-weapon.html').write_text(html.replace(before,after),encoding='utf-8')

path=Path('data/source-verification.json'); audit=json.loads(path.read_text(encoding='utf-8'))
assert audit['resolved_groups']==90 and audit['remaining_groups']==1
assert len(audit['remaining'])==1 and audit['remaining'][0]['id']=='F128'
assert not any('F128' in e['resolved_audit_ids'] for e in audit['entries'])
audit['scope']='Remaining transcription audit: edition-matched Roll20 spell definitions and linked creature stat blocks, plus the user-supplied legacy Elemental Weapon screenshot (Player\'s Handbook, 2014, p. 237). Existing rules, errata and house-rule choices preserved. This closes the recorded audit findings; it is not a blanket certification of all 391 spells.'
audit['resolved_groups']=91; audit['remaining_groups']=0
audit['spells_changed']=76; audit['edition_records_changed']=82
audit['entries'].append({'spell':'Elemental Weapon','edition':'2014','resolved_audit_ids':['F128'],'fields':['body'],'sources':[], 'source_type':'user-supplied screenshot','source_details':"Elemental Weapon — Legacy; Player's Handbook (2014), p. 237. Screenshot supplied in this conversation on 2026-10-20.",'correction':'Changed *1 to +1 and *2 to +2 in attack bonuses. The +3 bonus, damage dice, casting details and all other wording are unchanged.'})
audit['remaining']=[]
path.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

path=Path('tools/verify.py'); source=path.read_text(encoding='utf-8')
marker="    # The supplied 2024 Teleport reference must remain a semantic table, not a list.\n"
assert source.count(marker)==1
check="""    # User-supplied PHB 2014 screenshot confirms additive, not asterisk, bonuses.
    elemental=page.find(id='spell-elemental-weapon').select_one('[data-panel="2014"] .original-body').get_text()
    for phrase in ['has a +1 bonus to attack rolls','attack rolls increases to +2','the bonus increases to +3']:
        assert phrase in elemental, 'Elemental Weapon 2014 attack bonus regression: '+phrase
    assert '*1' not in elemental and '*2' not in elemental
"""
path.write_text(source.replace(marker,check+marker),encoding='utf-8')
print('Only Elemental Weapon 2014: two asterisks replaced with plus signs; 2024 and all other rules unchanged.')
print('Audit F128 resolved using the supplied screenshot: 91 resolved groups; 0 remaining.')
