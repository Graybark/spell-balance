"""Coverage, source preservation and independent magic-item navigation checks."""
from pathlib import Path
from bs4 import BeautifulSoup
from collections import Counter
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
def normalized(s):return re.sub(r'\s+',' ',s.get_text()).strip()
def check_item_content(page):
    data=json.loads((ROOT/'data/magic-items.json').read_text(encoding='utf-8'))
    entries=data['entries']; coverage=data['coverage']; bodies=data['descriptions']
    assert data['edition']=='2024'
    assert {e['key'] for e in entries}==set(coverage['free_index_keys'])|set(coverage['dmg_index_keys'])
    assert len(entries)==coverage['entry_count']==len({e['id'] for e in entries})
    assert set(coverage['free_index_keys'])==set(bodies)
    assert coverage['full_description_count']+coverage['reference_only_count']==len(entries)
    assert len(entries)>1000 and len(bodies)>300
    assert page.select_one('.section-nav a[href="#magic-items"]')
    assert page.select_one('section#magic-items[aria-labelledby="magic-items-heading"]')
    cards={c['id']:c for c in page.select('.magic-item-card')}
    assert len(cards)==len(entries)
    assert len(page.select('#item-menu li'))==len(entries)
    expected={k:normalized(BeautifulSoup(d['html'],'html.parser')) for k,d in bodies.items()}
    for key,d in bodies.items():
        assert hashlib.sha256(d['html'].encode()).hexdigest()==d['sha256']
        assert 'expansion=33335' in d['source_url']
    for e in entries:
        card=cards[e['id']]
        assert card.h3.get_text()==e['name']
        assert card['data-type']==e['type'] and card['data-rarity']==e['rarity']
        assert card.select_one('.item-footer a')['href']==e['url']
        if e['description_key']:
            d=bodies[e['description_key']]; body=card.select_one('.item-body')
            assert body and normalized(body)==expected[e['description_key']],(e['name'],'item rules text changed')
            assert len(body.select('p'))==d['paragraphs']
            assert len(body.select('table'))==d['tables']
            for table in body.select('table'):assert table.parent.get('class')==['item-table-wrap']
            assert not card.select_one('.item-reference')
        else:
            assert card.select_one('.item-reference') and not card.select_one('.item-body')
            assert e['description_kind']=='reference'
    section=page.select_one('#magic-items')
    assert not section.select('script,iframe,img,style')
    assert 'Roll20 Note:' not in section.get_text()
    assert page.select_one('#item-staff-of-the-magi .item-body table')
    assert len(page.select('#item-bag-of-holding .item-body p'))>=3
    assert page.select_one('#item-ring-of-invisibility .condition-link[data-condition=invisible]')
    assert len(page.select('.spell-card'))==391

async def check_item_browser(browser,url,report):
    from playwright.async_api import expect
    errors=[]
    for width in (1280,390,320):
        context=await browser.new_context(viewport={'width':width,'height':900},has_touch=width<800,is_mobile=width<800)
        p=await context.new_page();p.on('pageerror',lambda e:errors.append(str(e)))
        await p.goto(url+'#item-bag-of-holding')
        await p.wait_for_selector('html.enhanced')
        assert await p.locator('html').get_attribute('data-view')=='items'
        assert await p.locator('.magic-item-card:visible h3').inner_text()=='Bag of Holding'
        assert not await p.locator('.toolbar').is_visible()
        assert not await p.locator('.reader-layout').is_visible()
        assert await p.locator('.section-nav a[href="#magic-items"]').get_attribute('aria-current')=='page'
        total=await p.locator('#item-menu li').count()
        assert total>1000
        assert await p.locator('#item-count').inner_text()==str(total)+' entries'
        await p.locator('#item-search').fill('invisibility')
        await p.wait_for_timeout(200)
        assert 0<await p.locator('#item-menu li:not([hidden])').count()<total
        await p.select_option('#item-type','Ring')
        assert await p.locator('.magic-item-card:visible').get_attribute('data-type')=='Ring'
        await p.select_option('#item-attunement','yes')
        assert await p.locator('.magic-item-card:visible').get_attribute('data-attunement')=='yes'
        await p.reload();await p.wait_for_selector('html.enhanced')
        assert await p.locator('#item-search').input_value()=='invisibility'
        assert await p.locator('#item-type').input_value()=='Ring'
        assert await p.locator('#item-attunement').input_value()=='yes'
        await p.locator('#item-clear').click()
        await p.select_option('#item-jump','item-ring-of-invisibility')
        condition=p.locator('#item-ring-of-invisibility .condition-link[data-condition=invisible]').first
        await condition.click()
        await expect(p.locator('#condition-dialog')).to_be_visible()
        assert await p.locator('#condition-dialog-title').inner_text()=='Invisible'
        await p.locator('#condition-dialog-close').click()
        await p.select_option('#item-jump','item-staff-of-the-magi')
        assert await p.locator('.magic-item-card:visible h3').inner_text()=='Staff of the Magi'
        assert await p.locator('#item-staff-of-the-magi .item-body table').count()>0
        assert await p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        await p.locator('.magic-item-card:visible').screenshot(path=str(report/('magic-item-'+str(width)+'.png')))
        await p.go_back()
        assert await p.locator('.magic-item-card:visible h3').inner_text()=='Ring of Invisibility'
        await p.go_forward()
        assert await p.locator('.magic-item-card:visible h3').inner_text()=='Staff of the Magi'
        await p.locator('#item-search').fill('no-such-item-qzx')
        await expect(p.locator('#item-empty')).to_be_visible()
        assert await p.locator('#item-count').inner_text()=='0 entries'
        await p.locator('#item-reset').click()
        await p.locator('.section-nav a[href="#spells"]').click()
        assert await p.locator('html').get_attribute('data-view')=='spells'
        await p.locator('#search').fill('Fireball')
        await p.wait_for_timeout(200)
        spell_count=await p.locator('#visible-count').inner_text()
        await p.locator('.section-nav a[href="#magic-items"]').click()
        assert await p.locator('html').get_attribute('data-view')=='items'
        await p.locator('.section-nav a[href="#spell-slots"]').click()
        assert await p.locator('#spell-slots').is_visible()
        assert not await p.locator('#magic-items').is_visible()
        await p.locator('.section-nav a[href="#spells"]').click()
        assert await p.locator('#search').input_value()=='Fireball'
        assert await p.locator('#visible-count').inner_text()==spell_count
        await context.close()
    nojs=await browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844})
    p=await nojs.new_page()
    await p.goto(url+'#item-bag-of-holding')
    assert await p.locator('#magic-items').is_visible()
    assert await p.locator('.magic-item-card:visible h3').inner_text()=='Bag of Holding'
    assert not await p.locator('.reader-layout').is_visible()
    await p.locator('.item-link[href="#item-staff-of-the-magi"]').click()
    assert await p.locator('.magic-item-card:visible h3').inner_text()=='Staff of the Magi'
    assert await p.locator('#item-staff-of-the-magi table').count()>0
    await p.locator('.section-nav a[href="#spells"]').click()
    assert await p.locator('.reader-layout').is_visible()
    assert not await p.locator('#magic-items').is_visible()
    await nojs.close()
    assert not errors,errors
