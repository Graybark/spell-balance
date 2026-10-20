"""Community discussion is distinct from spell rules and adopted house rules."""
TARGETS={'spell-clone':('Clone',8), 'spell-simulacrum':('Simulacrum',7)}
SOURCES={
    'spell-clone':[
        'https://www.dndbeyond.com/spells/2618973-clone',
        'https://rpg.stackexchange.com/questions/50541/does-the-clone-spell-make-someone-effectively-immortal',
        'https://www.torontodnd.com/communityupdate/2024-06-14',
    ],
    'spell-simulacrum':[
        'https://www.dndbeyond.com/forums/dungeons-dragons-discussion/streams-video/202653-treantmonk-2024-phb-rebalanced-spells',
        'https://roll20.net/compendium/dnd5e/Spells:Simulacrum?expansion=32231',
    ],
}
def check_discussion_content(page,data,house):
    lightning=next(s for s in data if s['id']=='spell-lightning-bolt')
    assert lightning['categories'].count('nerf')==1
    assert sum(t['class']=='tag tag-nerf' for t in lightning['tags'])==1
    card=page.find(id='spell-lightning-bolt')
    pane=card.select_one('[data-panel="discussion"]')
    assert pane and len(pane.select('.balance-note'))==1
    assert 'Several replies defend Lightning Bolt' in pane.get_text()
    assert '2020' in pane.get_text() and '2014 rules' in pane.get_text()
    assert 'campaign decision' in pane.get_text()
    assert len(pane.select('a[href]'))==2
    assert card.select_one('[data-panel="why"]')
    assert house['spell-lightning-bolt']['replacements']==[['taking 8d6 Lightning damage','taking 6d6 Lightning damage']]
    assert len(house)==5
    for id,(name,level) in TARGETS.items():
        records=[record for record in data if record['id']==id]
        assert len(records)==1
        record=records[0]
        assert record['categories'].count('nerf')==1
        assert 'material-cost' in record['categories']
        if id=='spell-simulacrum': assert 'revised' in record['categories']
        assert sum(tag['class']=='tag tag-nerf' for tag in record['tags'])==1
        card=page.find(id=id)
        assert len(card.select('.balance-note'))==1
        pane=card.select_one('[data-panel="discussion"]')
        assert pane is not None
        for url in SOURCES[id]: assert pane.find('a',href=url),url
        assert id not in house, 'A Nerf discussion is not an adopted mechanical override.'
        assert card['data-level-official']==card['data-level-house']==str(level)
        assert not card.select('.tag-house, .why')
    assert 'campaign-dependent' in page.find(id='spell-clone').select_one('.balance-note').get_text()
    assert 'before the revised PHB' in page.find(id='spell-clone').select_one('[data-panel="discussion"]').get_text()
    assert 'already cannot cast Simulacrum' in page.find(id='spell-simulacrum').select_one('[data-panel="discussion"]').get_text()

async def check_discussion_browser(browser,url,report):
    errors=[]
    for width in (1280,390):
        context=await browser.new_context(viewport={'width':width,'height':1000})
        p=await context.new_page()
        p.on('pageerror',lambda error:errors.append(str(error)))
        await p.goto(url+'?label=nerf#spell-simulacrum')
        await p.wait_for_selector('html.enhanced')
        assert await p.locator('#label').input_value()=='nerf'
        assert await p.locator('#visible-count').inner_text()=='11 spells'
        assert await p.locator('.sidebar li:not([hidden])').count()==11
        if width<=800:
            await p.locator('#spell-menu > summary').click()
            await p.wait_for_function('document.getElementById("spell-menu").open')
        for id,(name,level) in TARGETS.items():
            await p.locator(f'.sidebar a[href="#{id}"]').click()
            assert await p.locator('.spell-card:visible h2').inner_text()==name
            assert await p.locator('#label').input_value()=='nerf'
            assert await p.locator(f'#{id} .tag-nerf').inner_text()=='Nerf'
            await p.locator(f'label[for="{id}-info-discussion"]').click()
            pane=p.locator(f'#{id} [data-panel="discussion"]')
            assert await pane.is_visible()
            assert await pane.locator('.balance-note').count()==1
            for source in SOURCES[id]:
                assert await pane.locator('a').evaluate_all('(links,url)=>links.some(a=>a.getAttribute("href")===url)',source)
            await p.locator(f'#{id}').screenshot(path=str(report/f'{id}-discussion-{width}.png'))
            await p.locator(f'label[for="{id}-info-compare"]').click()
            for year in ('2024','2014'):
                await p.locator(f'label[for="{id}-editions-{year}"]').click()
                assert await p.locator(f'#{id} [data-panel="{year}"] .original-body').is_visible()
            size=await p.evaluate('[document.documentElement.clientWidth,document.documentElement.scrollWidth]')
            assert size[1]<=size[0]+1,(width,size)
        # Both additions remain ordinary Wizard spells with no adopted house-rule tag.
        await p.select_option('#spell-class','wizard')
        for level,id in [('7','spell-simulacrum'),('8','spell-clone')]:
            await p.select_option('#level',level)
            assert await p.locator(f'.sidebar li[data-spell="{id}"]').evaluate('(e)=>!e.hidden')
        await p.select_option('#level','')
        await p.select_option('#spell-class','')
        await p.select_option('#label','house-rule')
        assert await p.locator('#visible-count').inner_text()=='5 spells'
        for id in TARGETS: assert await p.locator(f'.sidebar li[data-spell="{id}"]').evaluate('(e)=>e.hidden')
        await context.close()
    await check_lightning_discussion_browser(browser,url,report)
    plain=await browser.new_context(java_script_enabled=False,viewport={'width':390,'height':1000})
    p=await plain.new_page()
    for id in TARGETS:
        await p.goto(url+'#'+id)
        await p.locator(f'label[for="{id}-info-discussion"]').click()
        assert await p.locator(f'#{id} .balance-note').is_visible()
    await plain.close()
    assert not errors,errors

async def check_lightning_discussion_browser(browser,url,report):
    from playwright.async_api import expect
    sources=[
        'https://www.dndbeyond.com/forums/dungeons-dragons-discussion/dungeon-masters-only/75512-fireball-and-lightning-bolt',
        'https://roll20.net/compendium/dnd5e/Spells:Lightning%20Bolt?expansion=32231',
    ]
    errors=[]
    for width in (1280,390):
        for javascript in (True,False):
            context=await browser.new_context(viewport={'width':width,'height':1000},java_script_enabled=javascript)
            p=await context.new_page()
            p.on('pageerror',lambda e:errors.append(str(e)))
            await p.goto(url+'?label=nerf#spell-lightning-bolt')
            if javascript:
                await p.wait_for_selector('html.enhanced')
                await expect(p.locator('#visible-count')).to_have_text('11 spells')
                assert await p.locator('.sidebar li[data-spell="spell-lightning-bolt"]').evaluate('(e)=>!e.hidden')
            card=p.locator('#spell-lightning-bolt')
            await expect(card).to_be_visible()
            await expect(card.locator('.tag-house')).to_be_visible()
            await expect(card.locator('.tag-nerf')).to_be_visible()
            house=card.locator('[data-panel="spell"] [data-mode="house"]')
            assert 'taking 6d6 Lightning damage' in await house.inner_text()
            await p.locator('label[for="spell-lightning-bolt-info-discussion"]').click()
            pane=card.locator('[data-panel="discussion"]')
            await expect(pane).to_be_visible()
            assert await pane.locator('.balance-note').count()==1
            for source in sources:
                assert await pane.locator('a').evaluate_all('(links,u)=>links.some(a=>a.getAttribute("href")===u)',source)
            assert 'Several replies defend Lightning Bolt' in await pane.inner_text()
            if javascript: await card.screenshot(path=str(report/f'lightning-discussion-{width}.png'))
            size=await p.evaluate('[document.documentElement.clientWidth,document.documentElement.scrollWidth]')
            assert size[1]<=size[0]+1,(width,size)
            await p.locator('label[for="spell-lightning-bolt-info-why"]').click()
            assert '8d6 → 6d6' in await card.locator('.why').inner_text()
            await p.locator('label[for="spell-lightning-bolt-info-compare"]').click()
            for year in ('2024','2014'):
                await p.locator(f'label[for="spell-lightning-bolt-editions-{year}"]').click()
                assert '8d6' in await card.locator(f'[data-panel="{year}"] .original-body').inner_text()
            if javascript:
                await p.select_option('#label','house-rule')
                await expect(p.locator('#visible-count')).to_have_text('5 spells')
                assert await p.locator('.sidebar li[data-spell="spell-lightning-bolt"]').evaluate('(e)=>!e.hidden')
            await context.close()
    assert not errors,errors
