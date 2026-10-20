"""Regression checks for the explicitly approved Lightning Bolt / Wall of Force rules."""
import re

WALL_TEXT = "An Invisible wall of force springs into existence at a point you choose within range. The wall appears in any orientation you choose, as a horizontal or vertical barrier or at an angle. It can be free floating or resting on a solid surface. You can form it into a hemispherical dome or a globe with a radius of up to 10 feet, or you can shape a flat surface made up of ten 10-foot-by-10-foot panels. Each panel must be contiguous with another panel. In any form, the wall is 1/4 inch thick and lasts for the duration. If the wall cuts through a creature's space when it appears, the creature is pushed to one side of the wall (you choose which side). If a creature would be surrounded on all sides by the wall (or the wall and another solid surface), that creature can make a Dexterity saving throw. On a success, it can use its Reaction to move up to its Speed so that it is no longer enclosed by the wall. Nothing can physically pass through the wall. It is immune to all damage and can't be dispelled by Dispel Magic. A Disintegrate spell destroys the wall instantly, however."
HOUSE_IDS={'spell-fireball','spell-forcecage','spell-melf-s-acid-arrow','spell-wall-of-force','spell-lightning-bolt'}
def clean(text): return re.sub(r'\s+',' ',text).strip()

def check_rule_content(page, catalog, house):
    assert set(house)==HOUSE_IDS
    assert {c['id'] for c in page.select('.spell-card') if 'house-rule' in c['data-categories'].split()}==HOUSE_IDS
    wall=page.find(id='spell-wall-of-force')
    lightning=page.find(id='spell-lightning-bolt')
    assert wall['data-level-house']==wall['data-level-official']=='5'
    assert lightning['data-level-house']==lightning['data-level-official']=='3'
    w=wall.select_one('[data-panel=spell] [data-mode=house] .spell-text')
    assert clean(w.get_text(' '))==WALL_TEXT
    assert 'Dexterity saving throw' in w.select_one('mark.house-change').get_text()
    assert 'Reaction' in w.select_one('mark.house-change').get_text()
    assert 'Dexterity save' in wall.select_one('[data-mode=house] .spell-meta').get_text()
    assert 'Ethereal Plane' not in w.get_text()
    assert '5 → 7' not in wall.select_one('.why').get_text()
    l=lightning.select_one('[data-panel=spell] [data-mode=house] .spell-text')
    assert 'taking 6d6 Lightning damage' in l.get_text()
    assert l.select_one('mark.house-change').get_text()=='6d6'
    assert lightning.select_one('[data-mode=house] .spell-meta mark.house-change').get_text()=='6d6'
    assert 'The damage increases by 1d6 for each spell slot level above 3.' in l.get_text()
    assert '8d6 Lightning' not in l.get_text()
    for card in (wall,lightning):
        assert card.select_one('.tag-house')
        assert card.select_one('.why')
        for year in ('2014','2024'):
            original=card.select_one(f'[data-panel="{year}"] .original-body')
            assert not original.select('.house-change')
            if card is wall:
                assert 'ethereal' in original.get_text().lower()
                assert 'Dexterity saving throw' not in original.get_text()
            else:
                assert '8d6' in original.get_text()

async def check_rule_browser(browser,url,report):
    errors=[]
    for width in (1280,390):
        context=await browser.new_context(viewport={'width':width,'height':1000})
        p=await context.new_page()
        p.on('pageerror',lambda e:errors.append(str(e)))
        await p.goto(url+'?label=house-rule#spell-lightning-bolt')
        await p.wait_for_selector('html.enhanced')
        # Count matching entries even when the phone disclosure is closed.
        assert await p.locator('.sidebar li:not([hidden])').count()==5
        assert await p.locator('.spell-card:visible h2').inner_text()=='Lightning Bolt'
        assert 'taking 6d6 Lightning damage' in await p.locator('#spell-lightning-bolt [data-panel=spell] [data-mode=house]').inner_text()
        assert await p.locator('#spell-lightning-bolt .spell-body mark.house-change:visible').inner_text()=='6d6'
        await p.locator('#spell-lightning-bolt').screenshot(path=str(report/f'lightning-house-{width}.png'))
        await p.locator('label[for="spell-lightning-bolt-info-compare"]').click()
        for year in ('2024','2014'):
            await p.locator(f'label[for="spell-lightning-bolt-editions-{year}"]').click()
            assert '8d6' in await p.locator(f'#spell-lightning-bolt [data-panel="{year}"] .original-body').inner_text()
        await p.select_option('#jump','spell-wall-of-force')
        # Jump intentionally clears filters; restore the category for this filter test.
        await p.select_option('#label','house-rule')
        walltext=await p.locator('#spell-wall-of-force [data-panel=spell] [data-mode=house] .spell-text').inner_text()
        assert clean(walltext)==WALL_TEXT
        assert 'Dexterity save' in await p.locator('#spell-wall-of-force [data-mode=house] .spell-meta').inner_text()
        await p.select_option('#level','5')
        assert await p.locator('.sidebar li:not([hidden])').count()==1
        assert await p.locator('.spell-card:visible h2').inner_text()=='Wall of Force'
        await p.reload();await p.wait_for_selector('html.enhanced')
        assert clean(await p.locator('#spell-wall-of-force [data-panel=spell] [data-mode=house] .spell-text').inner_text())==WALL_TEXT
        await p.locator('#spell-wall-of-force').screenshot(path=str(report/f'wall-house-{width}.png'))
        size=await p.evaluate('[document.documentElement.clientWidth,document.documentElement.scrollWidth]')
        assert size[1]<=size[0]+1,(width,size)
        await p.uncheck('#house-rules-toggle')
        official=await p.locator('#spell-wall-of-force [data-panel=spell] [data-mode=official]').inner_text()
        assert 'Ethereal Plane' in official and 'Dexterity saving throw' not in official
        assert await p.locator('.spell-card:visible h2').inner_text()=='Wall of Force'
        await p.check('#house-rules-toggle');await p.select_option('#level','7')
        assert await p.locator('#empty').is_visible()
        await p.select_option('#level','');await p.select_option('#spell-class','sorcerer')
        assert set(await p.locator('.sidebar li:not([hidden]) strong').all_text_contents())=={'Fireball','Lightning Bolt'}
        await context.close()
    context=await browser.new_context(java_script_enabled=False,viewport={'width':390,'height':1000})
    p=await context.new_page()
    for key in ('lightning-bolt','wall-of-force'):
        await p.goto(url+'#spell-'+key)
        house=await p.locator(f'#spell-{key} [data-panel=spell] [data-mode=house] .spell-text').inner_text()
        assert (clean(house)==WALL_TEXT) if key=='wall-of-force' else ('6d6 Lightning damage' in house)
        await p.locator(f'label[for="spell-{key}-info-compare"]').click()
        assert await p.locator(f'#spell-{key} [data-panel="2024"] .original-body').is_visible()
    await context.close()
    assert not errors,errors
