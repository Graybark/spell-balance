from pathlib import Path
from html import escape
from bs4 import BeautifulSoup
import copy,hashlib,json

def blob(b):
    return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()

expected={'data/catalog.json':'cc0f7db23d6f491518e1ea78291d28a6d63fe8a4','src/app.css':'aa489d921c52b35449adc540d8c3f5c957091f5a','tools/verify.py':'b52852168687a1a8d321fd6f8112b684743cb72c'}
for name,sha in expected.items():
    assert blob(Path(name).read_bytes())==sha, 'Source changed: '+name
rows=[
    ['Permanent circle','–','–','–','01–00'],
    ['Linked object','–','–','–','01–00'],
    ['Very familiar','01–05','06–13','14–24','25–00'],
    ['Seen casually','01–33','34–43','44–53','54–00'],
    ['Viewed once or described','01–43','44–53','54–73','74–00'],
    ['False destination','01–50','51–00','–','–'],
]
headers=['Familiarity','Mishap','Similar Area','Off Target','On Target']
p=Path('data/catalog.json');original=json.loads(p.read_text(encoding='utf-8'));data=copy.deepcopy(original)
spell=next(s for s in data if s['id']=='spell-teleport');v=spell['versions']['2024'];body=v['body']
start=body.index('<p>TELEPORTATION OUTCOME (d100)</p>');end=body.index('</ul>',start)+len('</ul>')
old=body[start:end]
# The screenshot is the display reference; verify every existing outcome before reformatting it.
expected_items=[r[0]+' — '+('; '.join(h+': '+('—' if value=='–' else value) for h,value in zip(headers[1:],r[1:])))+'.' for r in rows]
assert [li.get_text() for li in BeautifulSoup(old,'html.parser').select('li')]==expected_items
new='<div class="spell-data-wrap" tabindex="0" role="region" aria-label="Teleportation Outcome"><table class="spell-data-table teleport-outcome-table"><caption>Teleportation Outcome</caption><colgroup><col class="familiarity-col"><col span="4"></colgroup><thead><tr>'
new+=''.join('<th scope="col">'+escape(h)+'</th>' for h in headers)+'</tr></thead><tbody>'
for r in rows:
    new+='<tr><th scope="row">'+escape(r[0])+'</th>'+''.join('<td>'+escape(x)+'</td>' for x in r[1:])+'</tr>'
new+='</tbody></table></div>'
v['body']=body[:start]+new+body[end:];v['body_sha256']=hashlib.sha256(v['body'].encode()).hexdigest()
assert v['body'].replace(new,old)==body
for before,after in zip(original,data):
    if before['id']!='spell-teleport':assert before==after
    else:
        assert before['versions']['2014']==after['versions']['2014']
        assert {k:x for k,x in before.items() if k!='versions'}=={k:x for k,x in after.items() if k!='versions'}
        assert {k:x for k,x in before['versions']['2024'].items() if k not in ('body','body_sha256')}=={k:x for k,x in v.items() if k not in ('body','body_sha256')}
p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
css='''
/* Teleport 2024: match the user-supplied Teleportation Outcome table only. */
.spell-data-wrap .teleport-outcome-table{table-layout:fixed;color:#222;font-size:14px;line-height:1.45}
.teleport-outcome-table .familiarity-col{width:32%}
.teleport-outcome-table caption{color:#111;font-size:16px;font-weight:700;margin-bottom:14px}
.teleport-outcome-table th,.teleport-outcome-table td{padding:10px 15px;border:1px solid #edeae8;text-align:center;vertical-align:middle}
.teleport-outcome-table thead{background:#fdfdfd}
.teleport-outcome-table thead th{border-bottom:2px solid #d0cac5;white-space:nowrap}
.teleport-outcome-table th:first-child{text-align:left}
.teleport-outcome-table tbody th{font-weight:400}
.teleport-outcome-table tbody tr:nth-child(odd){background:#d7e8ee}
.teleport-outcome-table tbody tr:nth-child(even){background:#f1f7f9}
@media (hover:hover){.teleport-outcome-table tbody tr:hover{background:#cde2ea}}
'''
p=Path('src/app.css');p.write_text(p.read_text(encoding='utf-8')+css,encoding='utf-8')
p=Path('tools/verify.py');s=p.read_text(encoding='utf-8')
marker="    assert len(page.select('.balance-note'))==17\n"
assert s.count(marker)==1
checks='''    # The supplied 2024 Teleport reference must remain a semantic table, not a list.
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
'''
p.write_text(s.replace(marker,marker+checks),encoding='utf-8')
print('Only Teleport 2024 list markup, scoped table styles and regression assertions changed.')
