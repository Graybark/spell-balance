"""Regression checks for reader-facing copy rather than maintenance instructions."""
import re
HOUSE_IDS=('spell-fireball','spell-forcecage','spell-melf-s-acid-arrow','spell-lightning-bolt','spell-wall-of-force')
OLD_COPY=('Fields to check:','Revision identified:','Official errata applied:',
          'Why this version?','Recorded house rule:','approved 6d6',
          'supplied for this comparison','supplied replacement effect',
          'This is the recorded change','not consensus','adopted here')

def check_reader_copy(page):
    content=page.get_text(' ',strip=True)
    for old in OLD_COPY: assert old not in content,old
    assert page.select_one('.rules-label').get_text(' ',strip=True)=='Use house-rule versions'
    for id in HOUSE_IDS:
        card=page.find(id=id)
        assert card.find('label',attrs={'for':id+'-info-why'}).get_text()=='House-rule changes'
        assert card.select_one('.why h3').get_text()=='House-rule changes'
        assert 'See Compare versions for the standard 2024 spell and its 2014 counterpart.' in card.select_one('.why').get_text(' ',strip=True)
    assert len(page.select('.field-signals'))==78
    assert all(n.strong.get_text()=='2024 changes:' for n in page.select('.field-signals,.revised-note'))
    assert len(page.select('.errata-note'))==9
    assert all(n.strong.get_text()=='Official errata:' for n in page.select('.errata-note'))
    for id in ('spell-clairvoyance','spell-haste','spell-dominate-beast','spell-compulsion','spell-nystul-s-magic-aura','spell-tree-stride','spell-true-polymorph'):
        assert not page.find(id=id).select('.field-signals'),id
    assert 'The school changes from Conjuration to Evocation.' in page.find(id='spell-acid-splash').select_one('.field-signals').get_text()
    for note in page.select('.field-signals'):
        t=note.get_text()
        assert not any(bad in t for bad in ('V.}','immedi-','Components•','fect','Renamed from Nystuls','upto'))
    absent=page.select('[data-panel="2014"] .original-version:not([data-original])')
    assert len(absent)==30
    assert all(n.select_one('.absent-copy').get_text(' ',strip=True)=='No 2014 Player’s Handbook version is available for comparison.' for n in absent)
    assert all(n.select_one('.absent-title').get_text()=='No 2014 PHB entry' for n in absent)
    lightning=page.find(id='spell-lightning-bolt').select_one('[data-panel="discussion"]')
    t=lightning.get_text(' ',strip=True)
    assert 'House-rule version:' in t and 'matching Fireball’s house-rule damage' in t
    assert 'Some favour adjustments, while others argue' in t
    assert '2014 rules' in t and '2020' in t
    assert len(lightning.select('a[href]'))==2
    wall=page.find(id='spell-wall-of-force').select_one('.why').get_text()
    assert 'remains a level-5 spell' in wall and 'earlier level-7' not in wall
    for id in ('spell-clone','spell-simulacrum'):
        assert 'Spellwright retains the standard 2024 version.' in page.find(id=id).select_one('[data-panel="discussion"]').get_text()
    assert 'Campaign example:' in page.find(id='spell-clone').select_one('[data-panel="discussion"]').get_text()

async def check_reader_copy_browser(browser,url,report):
    from playwright.async_api import expect
    for width in (1440,1280,768,390,360):
        context=await browser.new_context(viewport={'width':width,'height':1000})
        p=await context.new_page()
        await p.goto(url+'#spell-lightning-bolt')
        await p.wait_for_selector('html.enhanced')
        toggle=p.get_by_label('Use house-rule versions',exact=True)
        await expect(toggle).to_be_checked()
        await p.locator('label[for="spell-lightning-bolt-info-discussion"]').click()
        await expect(p.locator('#spell-lightning-bolt [data-panel="discussion"]')).to_be_visible()
        assert 'approved' not in await p.locator('#spell-lightning-bolt [data-panel="discussion"]').inner_text()
        if width in (1280,390):await p.locator('#spell-lightning-bolt').screenshot(path=str(report/f'reader-copy-lightning-{width}.png'))
        for id in HOUSE_IDS:
            await p.select_option('#jump',id)
            card=p.locator('#'+id)
            await card.get_by_text('House-rule changes',exact=True).first.click()
            await expect(card.locator('.why')).to_be_visible()
            await expect(card.locator('.why h3')).to_have_text('House-rule changes')
        if width in (1280,390):await p.locator('#spell-wall-of-force').screenshot(path=str(report/f'reader-copy-wall-{width}.png'))
        await p.select_option('#jump','spell-lightning-bolt')
        await p.locator('label[for="spell-lightning-bolt-info-spell"]').click()
        await toggle.uncheck()
        assert 'taking 8d6 Lightning damage' in await p.locator('#spell-lightning-bolt [data-panel="spell"] [data-mode="official"]').inner_text()
        await toggle.check()
        assert 'taking 6d6 Lightning damage' in await p.locator('#spell-lightning-bolt [data-panel="spell"] [data-mode="house"]').inner_text()
        for id in ('spell-acid-splash','spell-clairvoyance','spell-arcane-vigor'):
            await p.select_option('#jump',id)
            await p.locator(f'label[for="{id}-info-compare"]').click()
            assert 'Fields to check:' not in await p.locator('#'+id).inner_text()
        await p.locator('label[for="spell-arcane-vigor-editions-2014"]').click()
        await expect(p.locator('#spell-arcane-vigor [data-panel="2014"]')).to_contain_text('No 2014 Player’s Handbook version is available for comparison.')
        size=await p.evaluate('[document.documentElement.clientWidth,document.documentElement.scrollWidth]')
        assert size[1]<=size[0]+1,(width,size)
        label=await p.locator('.rules-label').bounding_box();results=await p.locator('.rules-controls .results').bounding_box()
        if width<=600 and abs(label['y']-results['y'])<20:
            assert label['x']+label['width']<=results['x']+1,(width,label,results)
        await context.close()
    plain=await browser.new_context(java_script_enabled=False,viewport={'width':390,'height':1000})
    p=await plain.new_page();await p.goto(url+'#spell-wall-of-force')
    await p.locator('label[for="spell-wall-of-force-info-why"]').click()
    assert await p.locator('#spell-wall-of-force .why').is_visible()
    assert 'remains a level-5 spell' in await p.locator('#spell-wall-of-force .why').inner_text()
    await plain.close()
