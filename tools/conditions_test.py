"""Condition term decoration must not change any spell rules text."""
from bs4 import BeautifulSoup
from build import CONDITION_NAMES, condition_url, link_conditions
from verify import normalized

def check_condition_content(page,data,house):
    library=page.select_one('#condition-definitions')
    assert library is not None
    template=BeautifulSoup(library.decode_contents(),'html.parser')
    assert len(template.select('[data-condition-entry]'))==30
    assert set(x['data-condition-entry'] for x in template.select('[data-condition-entry]'))==set(CONDITION_NAMES)
    for section in template.select('[data-condition-entry]'):
        name=section['data-condition-entry'];year=section['data-edition']
        link=section.select_one('.condition-source')
        assert link and link['href']==condition_url(name,year)
        assert section.select('li') and section.select_one('.condition-edition')
    assert page.select_one('#condition-dialog[aria-labelledby="condition-dialog-title"]')
    assert page.select_one('#condition-tooltip[role="dialog"][aria-modal="false"]')
    links=page.select('.condition-link')
    assert len(links)>400,('Insufficient condition references',len(links))
    assert {'2014','2024'}=={link['data-edition'] for link in links}
    for link in links:
        assert link.find_parent(class_='spell-text') or link.find_parent(class_='stat-block')
        assert link['data-condition'] in CONDITION_NAMES
        assert link['href']==condition_url(link['data-condition'],link['data-edition'])
        assert link.get_text().lower()==link['data-condition']
        assert link.get('aria-label')
        assert link.get('aria-haspopup')=='dialog'
        assert not link.find_parent('a')
    for record in data:
        card=page.find(id=record['id'])
        for edition,v in record['versions'].items():
            pane=card.select_one('[data-panel="'+edition+'"] .original-body')
            if v['absent']:continue
            assert pane and pane.select_one('.spell-text'),record['id']+' '+edition
            assert normalized(str(pane))==normalized(v['body']),('Spell text changed',record['id'],edition)
            assert all(link['data-edition']==edition for link in pane.select('.condition-link'))
            # Removing just the enhancement must recover every original element,
            # attribute, paragraph, emphasis mark, link, and text node exactly.
            restored=BeautifulSoup(pane.decode_contents(),'html.parser')
            for link in restored.select('.condition-link'):link.unwrap()
            assert str(restored)==str(BeautifulSoup(v['body'],'html.parser')),(record['id'],edition,'HTML changed')
        # Main descriptions and every house replacement receive the same treatment.
        v=record['versions']['2024']; expected=v['body']; rule=house.get(record['id'])
        if rule:
            expected=rule.get('body_override',expected)
            for before,after in rule['replacements']:expected=expected.replace(before,after)
            primary=card.select_one('[data-panel=spell] [data-mode=house] .spell-body')
        else:primary=card.select_one('[data-panel=spell] .spell-body')
        assert primary.get_text()==BeautifulSoup(expected,'html.parser').get_text(),record['id']+' main text changed'
    for id,name in [('spell-hold-person','paralyzed'),('spell-fear','frightened'),('spell-invisibility','invisible'),('spell-hypnotic-pattern','charmed')]:
        card=page.find(id=id)
        for year in ('2014','2024'):
            assert card.select_one('[data-panel="'+year+'"] .condition-link[data-condition="'+name+'"]')
    for year in ('2014','2024'):
        card=page.find(id='spell-wall-of-force')
        assert not card.select_one('[data-panel="'+year+'"] .condition-link[data-condition="invisible"]'),year
    assert not page.find(id='spell-wall-of-force').select_one('[data-panel="spell"] .condition-link[data-condition="invisible"]')
    assert page.select_one('#spell-animate-objects [data-panel=spell] .stat-block .condition-link[data-condition=poisoned]')
    assert page.select_one('#spell-summon-aberration [data-panel=spell] .stat-block .condition-link[data-condition=incapacitated]')
    assert not page.select_one('#spell-arcane-eye [data-panel=spell] .condition-link[data-condition=invisible]')
    sample='<div class="spell-text"><p data-test="Poisoned">BLINDED, <em>Prone</em>, unrestrained and unconsciousness. <a href="/unchanged">Charmed</a> <strong>Stunned</strong>.</p></div><p>Poisoned</p>'
    result=BeautifulSoup(link_conditions(sample,'2014'),'html.parser')
    assert [a.get_text() for a in result.select('.condition-link')]==['BLINDED','Prone','Stunned']
    assert result.select_one('p[data-test="Poisoned"]')
    assert result.select_one('a[href="/unchanged"]').get_text()=='Charmed'
    assert not page.select('[data-panel=discussion] .condition-link, .spell-meta .condition-link, .spell-heading .condition-link')
    for link in result.select('.condition-link'):link.unwrap()
    assert str(result)==str(BeautifulSoup(sample,'html.parser'))
    # Edition distinctions are visible in the offline summaries, not inferred from the spell.
    def definition(name,year):return template.select_one('[data-condition-entry="'+name+'"][data-edition="'+year+'"]').get_text()
    assert 'twice' in definition('exhaustion','2024') and 'halved' in definition('exhaustion','2014')
    assert 'Initiative' in definition('invisible','2024') and 'Initiative' not in definition('invisible','2014')
    assert 'disease' in definition('petrified','2014') and 'disease' not in definition('petrified','2024')
    assert "doesn't set Speed to 0" in definition('stunned','2024')

async def check_condition_browser(browser,url,report):
    from playwright.async_api import expect
    # Desktop mouse and keyboard: preview on hover/focus, click opens a native dialog.
    context=await browser.new_context(viewport={'width':1280,'height':950})
    p=await context.new_page()
    new_pages=[]
    context.on('page',lambda page:new_pages.append(page))
    errors=[]
    p.on('pageerror',lambda e: errors.append(str(e)))
    await p.goto(url+'#spell-hold-person')
    await p.wait_for_selector('html.enhanced')
    trigger=p.locator('#spell-hold-person [data-panel="spell"] .condition-link').first
    assert await trigger.inner_text()=='Paralyzed'
    await trigger.hover()
    tip=p.locator('#condition-tooltip')
    await expect(tip).to_be_visible()
    assert '2024 rules' in (await tip.inner_text()).lower()
    assert 'Strength and Dexterity' in await tip.inner_text()
    assert await tip.locator('.condition-source').count()==1
    before=await trigger.bounding_box()
    await tip.locator('.condition-source').hover()
    await p.wait_for_timeout(350)
    await expect(tip).to_be_visible()
    assert await trigger.bounding_box()==before,'Hover must not move spell text'
    await tip.screenshot(path=str(report/'conditions-desktop-hover.png'))
    await p.mouse.move(5,5)
    await expect(tip).not_to_be_visible()
    await trigger.focus()
    await expect(tip).to_be_visible()
    await p.keyboard.press('ArrowDown')
    assert await tip.locator('.condition-source').evaluate('(el)=>document.activeElement===el')
    await p.keyboard.press('Escape')
    await expect(tip).not_to_be_visible()
    assert await trigger.evaluate('(el)=>document.activeElement===el')
    await trigger.click()
    modal=p.locator('#condition-dialog')
    await expect(modal).to_be_visible()
    assert await modal.evaluate('(el)=>el.open')
    assert 'Paralyzed' == await p.locator('#condition-dialog-title').inner_text()
    assert '2024 rules' in (await modal.inner_text()).lower()
    assert await modal.locator('.condition-source').get_attribute('href')=='https://roll20.net/compendium/dnd5e/Rules:Rules%20Definitions?expansion=33335#Paralyzed%20%5BCondition%5D'
    assert len(new_pages)==0
    await p.keyboard.press('Escape')
    await expect(modal).not_to_be_visible()
    assert await trigger.evaluate('(el)=>document.activeElement===el')
    await p.locator('#search').focus()
    await trigger.focus()
    await expect(tip).to_be_visible()
    await p.keyboard.press('Enter')
    await expect(modal).to_be_visible()
    await p.locator('#condition-dialog-close').click()
    await expect(modal).not_to_be_visible()
    await p.locator('label[for="spell-hold-person-info-compare"]').click()
    await p.locator('label[for="spell-hold-person-editions-2014"]').click()
    old=p.locator('#spell-hold-person [data-panel="2014"] .condition-link').first
    await old.click()
    assert '2014 rules' in (await modal.inner_text()).lower()
    assert '/Conditions#Paralyzed' in await modal.locator('.condition-source').get_attribute('href')
    await p.locator('#condition-dialog-close').click()
    await p.locator('#condition-tooltip').screenshot(path=str(report/'conditions-desktop-hover.png')) if await tip.is_visible() else None
    # Edges and a short viewport: the entire preview stays inside the viewport,
    # and its contents can scroll without dismissing it.
    await p.goto(url+'#spell-flesh-to-stone')
    await p.wait_for_selector('html.enhanced')
    edge=p.locator('#spell-flesh-to-stone [data-panel=spell] .condition-link[data-condition=petrified]').first
    await p.set_viewport_size({'width':800,'height':260})
    await edge.evaluate("el=>{el.style.position='fixed';el.style.right='3px';el.style.bottom='3px';el.style.zIndex='80'}")
    await edge.hover()
    await expect(tip).to_be_visible()
    r=await tip.bounding_box()
    assert 0<=r['x'] and r['x']+r['width']<=800 and 0<=r['y'] and r['y']+r['height']<=260,r
    assert await tip.evaluate('(el)=>el.scrollHeight>el.clientHeight')
    await tip.hover()
    await tip.evaluate('(el)=>el.scrollTop=el.scrollHeight')
    await expect(tip).to_be_visible()
    await edge.evaluate("el=>el.removeAttribute('style')")
    await p.set_viewport_size({'width':1280,'height':950})
    await p.goto(url+'#spell-hold-person');await p.wait_for_selector('html.enhanced')
    trigger=p.locator('#spell-hold-person [data-panel=spell] .condition-link').first
    await trigger.hover()
    await p.select_option('#jump','spell-web')
    await expect(tip).not_to_be_visible()
    web=p.locator('#spell-web [data-panel=spell] .condition-link[data-condition=restrained]').first
    await web.click();await expect(modal).to_be_visible()
    # Programmatic navigation/history is possible even with a modal open.
    await p.evaluate("location.hash='spell-sleep'")
    await expect(modal).not_to_be_visible()
    assert not await p.locator('.condition-link[aria-expanded=true]').count()
    await p.locator('#spell-sleep [data-panel=spell] .condition-link').first.hover()
    await p.uncheck('#house-rules-toggle')
    await expect(tip).not_to_be_visible()
    assert await p.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+1')
    await context.close()
    # Actual touch emulation: no new window, in-page dialog, backdrop and close.
    phone=await browser.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True,device_scale_factor=1)
    mobile=await phone.new_page()
    opened=[]
    phone.on('page',lambda page:opened.append(page))
    mobile.on('pageerror',lambda e: errors.append(str(e)))
    await mobile.goto(url+'#spell-hold-person')
    await mobile.wait_for_selector('html.enhanced')
    mobile_trigger=mobile.locator('#spell-hold-person [data-panel="spell"] .condition-link').first
    address=mobile.url
    await mobile_trigger.tap()
    mobile_dialog=mobile.locator('#condition-dialog')
    await expect(mobile_dialog).to_be_visible()
    assert await mobile_dialog.evaluate('(d)=>d.open')
    assert mobile.url==address
    assert len(opened)==0
    assert not await mobile.locator('#condition-tooltip').is_visible()
    width=await mobile.evaluate('[document.documentElement.clientWidth,document.documentElement.scrollWidth]')
    assert width[1]<=width[0]+1,width
    await mobile.screenshot(path=str(report/'conditions-touch-overlay.png'))
    await mobile.locator('#condition-dialog-close').tap()
    await expect(mobile_dialog).not_to_be_visible()
    assert await mobile_trigger.evaluate('(el)=>document.activeElement===el')
    # Reopen, tap outside the sheet, then reopen once more and use Escape.
    await mobile_trigger.tap()
    await mobile.touchscreen.tap(8,8)
    await expect(mobile_dialog).not_to_be_visible()
    assert await mobile_trigger.evaluate('(el)=>document.activeElement===el')
    await mobile_trigger.tap()
    await mobile.keyboard.press('Tab')
    assert await mobile_dialog.evaluate('(el)=>el.contains(document.activeElement)')
    await mobile.keyboard.press('Tab')
    assert await mobile_dialog.evaluate('(el)=>el.contains(document.activeElement)')
    await mobile.keyboard.press('Escape')
    await expect(mobile_dialog).not_to_be_visible()
    for spell,conditions in [('blindness-deafness',['blinded','deafened']),('web',['restrained']),('sleep',['incapacitated','unconscious'])]:
        await mobile.select_option('#jump','spell-'+spell)
        for condition in conditions:
            term=mobile.locator('#spell-'+spell+' [data-panel=spell] .condition-link[data-condition='+condition+']').first
            await term.tap()
            await expect(mobile_dialog).to_be_visible()
            assert await mobile.locator('#condition-dialog-title').inner_text()==condition.title()
            await mobile.locator('#condition-dialog-close').tap()
    # A naturally long condition scrolls inside a narrow sheet; Close remains visible.
    await mobile.set_viewport_size({'width':320,'height':480})
    await mobile.locator('#spell-sleep [data-panel=spell] .condition-link[data-condition=unconscious]').first.tap()
    content=mobile.locator('#condition-dialog-content')
    assert await content.evaluate('(el)=>el.scrollHeight>el.clientHeight')
    await content.evaluate('(el)=>el.scrollTop=el.scrollHeight')
    await expect(mobile.locator('#condition-dialog-close')).to_be_in_viewport()
    assert await mobile.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth')
    await mobile.screenshot(path=str(report/'conditions-narrow-scroll.png'))
    # A tap on sheet padding is not an outside tap.
    box=await mobile_dialog.bounding_box()
    await mobile.touchscreen.tap(box['x']+4,box['y']+12)
    await expect(mobile_dialog).to_be_visible()
    await mobile.locator('#condition-dialog-close').tap()
    await mobile.locator('label[for="spell-sleep-info-compare"]').tap()
    await mobile.locator('label[for="spell-sleep-editions-2014"]').tap()
    await mobile.locator('#spell-sleep [data-panel="2014"] .condition-link[data-condition=unconscious]').first.tap()
    assert '2014 rules' in (await mobile_dialog.inner_text()).lower()
    await mobile.locator('#condition-dialog-close').tap()
    assert mobile.url.startswith(url) and not opened
    await phone.close()
    # JavaScript disabled: anchors still lead to Roll20.
    fallback=await browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844})
    nojs=await fallback.new_page()
    await nojs.goto(url+'#spell-hold-person')
    anchor=nojs.locator('#spell-hold-person [data-panel="spell"] .condition-link').first
    assert (await anchor.get_attribute('href')).startswith('https://roll20.net/')
    assert not await nojs.locator('#condition-dialog').is_visible()
    await fallback.close()
    assert not errors,errors

if __name__=='__main__':
    import argparse, asyncio, json
    from pathlib import Path
    from playwright.async_api import async_playwright
    parser=argparse.ArgumentParser(description='Check condition references on a published site.')
    parser.add_argument('--url',required=True)
    parser.add_argument('--report',default='/tmp/spell-balance-validation')
    args=parser.parse_args()
    async def live():
        report=Path(args.report);report.mkdir(parents=True,exist_ok=True)
        async with async_playwright() as pw:
            browser=await pw.chromium.launch()
            await check_condition_browser(browser,args.url,report)
            await browser.close()
        print(json.dumps({'result':'PASS','published_url':args.url,'conditions':15,'editions':[2014,2024],'desktop_hover':True,'keyboard':True,'touch_overlay':True,'navigation_cleanup':True}))
    asyncio.run(live())
