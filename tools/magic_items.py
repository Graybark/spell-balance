"""Static 2024 magic item reader. Network-free normal builds."""
from bs4 import BeautifulSoup
from html import escape
from urllib.parse import urlsplit,unquote
import hashlib,json,re
def esc(value):return escape(str(value),quote=True)
def source_key(url):return unquote(urlsplit(url).path).split('/dnd5e/')[-1].casefold()
def render_items(data,link_conditions,spells):
    assert data['edition']=='2024'
    entries=data['entries']; descriptions=data['descriptions']; coverage=data['coverage']
    assert len(entries)==coverage['entry_count']
    paths={r['key']:r['id'] for r in entries}
    spell_paths={re.sub(r'[^a-z0-9]','',s['name'].casefold()):s['id'] for s in spells}
    condition_names={'blinded','charmed','deafened','exhaustion','frightened','grappled','incapacitated','invisible','paralyzed','petrified','poisoned','prone','restrained','stunned','unconscious'}
    bodies={}
    for key,d in descriptions.items():
        assert hashlib.sha256(d['html'].encode()).hexdigest()==d['sha256'],'Item source body changed'
        soup=BeautifulSoup('<div class="item-body spell-text">'+d['html']+'</div>','html.parser')
        for a in list(soup.select('a[href]')):
            if not a.get_text().strip():a.unwrap();continue
            if a.get_text().strip().casefold() in condition_names:
                a.unwrap();continue
            target=source_key(a['href'])
            if target in paths:a['href']='#'+paths[target]
            elif target.startswith('spells:'):
                name=re.sub(r'[^a-z0-9]','',target.split(':',1)[1])
                if name in spell_paths:a['href']='#'+spell_paths[name]
        for table in soup.select('table'):
            table['class']='item-table'
            if table.thead:
                for th in table.thead.select('th'):th['scope']='col'
            wrap=soup.new_tag('div',attrs={'class':'item-table-wrap','tabindex':'0','aria-label':'Magic item table'})
            table.wrap(wrap)
        bodies[key]=link_conditions(str(soup),'2024')
    def select(id,label,options):
        return '<div class="control"><label for="'+id+'">'+esc(label)+'</label><select id="'+id+'" disabled>'+''.join('<option value="'+esc(v)+'">'+esc(label)+'</option>' for v,label in options)+'</select></div>'
    controls='<div class="control"><label for="item-search">Search magic items</label><input id="item-search" type="search" placeholder="Item name or description" autocomplete="off" disabled></div>'
    types=sorted({r['type'] for r in entries})
    rarities=[v for v in ('Common','Uncommon','Rare','Very Rare','Legendary','Artifact','Varies','Not listed') if any(r['rarity']==v for r in entries)]
    controls+=select('item-type','Type',[('','All types')]+[(t,t) for t in types])
    controls+=select('item-rarity','Rarity',[('','All rarities')]+[(r,r) for r in rarities])
    controls+=select('item-attunement','Attunement',[('','Any'),('yes','Required'),('no','Not required'),('unknown','Not listed')])
    controls+=select('item-jump','Jump to item',[('','Choose an item')]+[(r['id'],r['name']) for r in entries])
    controls+='<div class="item-results"><span id="item-count" role="status" aria-live="polite">'+str(len(entries))+' entries</span><button id="item-clear" type="button" disabled>Clear filters</button></div>'
    cards=[]; links=[]
    for r in entries:
        attune='unknown' if r['attunement'] is None else ('yes' if r['attunement'] else 'no')
        attrs=' id="'+esc(r['id'])+'" data-type="'+esc(r['type'])+'" data-rarity="'+esc(r['rarity'])+'" data-attunement="'+attune+'"'
        card='<article class="magic-item-card"'+attrs+'><header class="item-heading"><div><p class="item-eyebrow">2024 Magic Item'+(' · Template' if r['is_template'] else '')+'</p><h3 tabindex="-1">'+esc(r['name'])+'</h3></div><span class="tag">'+esc(r['rarity'])+'</span></header>'
        card+='<dl class="item-meta">'+''.join('<div><dt>'+label+'</dt><dd>'+esc(value)+'</dd></div>' for label,value in [('Type',r['type']),('Rarity',r['rarity']),('Attunement',r['attunement_text'])])+'</dl>'
        if r.get('subtitle'):card+='<p class="item-subtitle">'+esc(r['subtitle'])+'</p>'
        if r['description_key']:
            if r['description_kind']=='family':
                parent=next(e for e in entries if e['key']==r['description_key'])
                card+='<p class="item-variant">Variant of <a href="#'+esc(parent['id'])+'">'+esc(parent['name'])+'</a>. The family’s rules are shown below; the item name identifies this variant.</p>'
            card+=bodies[r['description_key']]
        else:
            card+='<div class="item-reference"><p>This entry is listed in the 2024 Dungeon Master’s Guide. Its full description is available through Roll20.</p></div>'
        card+='<footer class="item-footer"><span>'+esc(r['source'])+'</span><a href="'+esc(r['url'])+'" rel="noopener noreferrer" target="_blank">Roll20 entry</a></footer></article>'
        cards.append(card)
        links.append('<li data-item="'+esc(r['id'])+'"><a class="item-link" href="#'+esc(r['id'])+'"><strong>'+esc(r['name'])+'</strong><small>'+esc(r['type']+' · '+r['rarity'])+'</small></a></li>')
    count=str(len(entries))
    intro='<header class="item-section-heading"><h2 id="magic-items-heading" tabindex="-1">Magic Items</h2><p>2024 rules · '+count+' items, variants, and templates</p><a href="#spells">Back to spells</a></header>'
    return '<section id="magic-items" class="magic-items-section" aria-labelledby="magic-items-heading">'+intro+'<nav class="item-controls" aria-label="Find magic items">'+controls+'</nav><div class="item-reader"><div class="item-detail"><div id="item-empty" hidden><p>No magic items match these filters.</p><button id="item-reset" type="button">Clear filters</button></div>'+''.join(cards)+'</div><aside class="item-list-panel" aria-label="Magic item navigation"><details id="item-menu" open><summary>Magic items <span id="item-sidebar-count">('+count+')</span></summary><nav aria-label="Magic item list"><ul>'+''.join(links)+'</ul></nav></details></aside></div></section>'
