"""Condition term decoration must not change any spell rules text."""
from bs4 import BeautifulSoup
from build import CONDITION_NAMES, condition_url
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
    assert page.select_one('#condition-tooltip[role="tooltip"]')
    links=page.select('.condition-link')
    assert len(links)>400,('Insufficient condition references',len(links))
    assert {'2014','2024'}=={link['data-edition'] for link in links}
    for link in links:
        assert link.find_parent(class_='spell-text')
        assert link['data-condition'] in CONDITION_NAMES
        assert link['href']==condition_url(link['data-condition'],link['data-edition'])
        assert link.get_text().lower()==link['data-condition']
        assert link.get('aria-label')
        assert not link.find_parent('a')
    for record in data:
        card=page.find(id=record['id'])
        for edition,v in record['versions'].items():
            pane=card.select_one('[data-panel="'+edition+'"] .original-body .spell-text')
            if v['absent']:continue
            assert pane,record['id']+' '+edition
            assert normalized(str(pane))==normalized(v['body']),('Spell text changed',record['id'],edition)
            assert all(link['data-edition']==edition for link in pane.select('.condition-link'))
    for id,name in [('spell-hold-person','paralyzed'),('spell-fear','frightened'),('spell-invisibility','invisible'),('spell-hypnotic-pattern','charmed')]:
        card=page.find(id=id)
        for year in ('2014','2024'):
            assert card.select_one('[data-panel="'+year+'"] .condition-link[data-condition="'+name+'"]')
    for year in ('2014','2024'):
        card=page.find(id='spell-wall-of-force')
        assert not card.select_one('[data-panel="'+year+'"] .condition-link[data-condition="invisible"]'),year
    assert not page.find(id='spell-wall-of-force').select_one('[data-panel="spell"] .condition-link[data-condition="invisible"]')

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
    assert '2024 rules' in await tip.inner_text()
    assert 'Strength and Dexterity' in await tip.inner_text()
    assert await tip.locator('.condition-source').count()==0
    await trigger.click()
    modal=p.locator('#condition-dialog')
    await expect(modal).to_be_visible()
    assert await modal.evaluate('(el)=>el.open')
    assert 'Paralyzed' == await p.locator('#condition-dialog-title').inner_text()
    assert '2024 rules' in await modal.inner_text()
    assert await modal.locator('.condition-source').get_attribute('href')=='https://roll20.net/compendium/dnd5e/Rules:Rules%20Definitions?expansion=33335#Paralyzed%20%5BCondition%5D'
    assert len(new_pages)==0
    await p.keyboard.press('Escape')
    await expect(modal).not_to_be_visible()
    assert await trigger.evaluate('(el)=>document.activeElement===el')
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
    assert '2014 rules' in await modal.inner_text()
    assert '/Conditions#Paralyzed' in await modal.locator('.condition-source').get_attribute('href')
    await p.locator('#condition-dialog-close').click()
    await p.locator('#condition-tooltip').screenshot(path=str(report/'conditions-desktop-hover.png')) if await tip.is_visible() else None
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
