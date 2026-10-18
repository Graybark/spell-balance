"""Regression coverage for the header-only Spell Slots view."""
async def check_slots_view(browser, url, report):
    errors=[]
    for width in (1280,390,360):
        context=await browser.new_context(viewport={'width':width,'height':900})
        page=await context.new_page()
        page.on('pageerror',lambda error:errors.append(str(error)))
        await page.goto(url+'#spell-fireball')
        await page.wait_for_selector('html.enhanced')
        assert not await page.locator('#spell-slots').is_visible()
        assert await page.locator('details#spell-slots, #spell-slots > summary').count()==0
        assert await page.locator('.slot-table tbody tr').count()==100
        layout=await page.locator('.reader-layout').bounding_box()
        content=await page.locator('main.content').bounding_box()
        pad=await page.locator('main.content').evaluate('(e)=>parseFloat(getComputedStyle(e).paddingTop)')
        assert abs(layout['y']-content['y']-pad)<1, 'Empty section space remains above the reader.'
        await page.select_option('#spell-class','wizard')
        await page.select_option('#label','house-rule')
        await page.locator('label[for="spell-fireball-info-why"]').click()
        if width<=800:
            await page.locator('#spell-menu > summary').click()
            await page.wait_for_function('document.getElementById("spell-menu").open')
        await page.locator('.section-nav a[href="#spell-slots"]').click()
        assert page.url.endswith('#spell-slots')
        assert await page.locator('#spell-slots').is_visible()
        assert not await page.locator('#spells').is_visible()
        assert not await page.locator('.toolbar').is_visible()
        assert await page.locator('#spell-slots-heading').evaluate('(e)=>e===document.activeElement')
        for caster in ('wizard','bard','cleric','druid','sorcerer'):
            await page.locator(f'label[for="caster-{caster}"]').click()
            assert await page.locator(f'.slot-table[data-caster="{caster}"]').is_visible()
            assert await page.locator(f'.slot-table[data-caster="{caster}"] tbody tr').count()==20
        size=await page.evaluate('[document.documentElement.clientWidth,document.documentElement.scrollWidth]')
        assert size[1]<=size[0]+1,(width,size)
        await page.evaluate('scrollTo(0,0)')
        await page.screenshot(path=str(report/f'slots-view-{width}.png'))
        await page.locator('.back-to-spells').click()
        assert await page.locator('.spell-card:visible h2').inner_text()=='Fireball'
        assert not await page.locator('#spell-slots').is_visible()
        assert await page.locator('#spell-class').input_value()=='wizard'
        assert await page.locator('#label').input_value()=='house-rule'
        assert await page.locator('#spell-fireball-info-why').is_checked()
        if width<=800:
            assert await page.locator('#spell-menu').evaluate('(e)=>e.open')
            assert await page.evaluate('localStorage.getItem("spellwright.mobileSpellMenu")')=='open'
        # The header's Browse spells link and history also restore the reader.
        await page.locator('.section-nav a[href="#spell-slots"]').click()
        await page.locator('.section-nav a[href="#spells"]').click()
        assert await page.locator('.spell-card:visible h2').inner_text()=='Fireball'
        await page.go_back()
        assert await page.locator('#spell-slots').is_visible()
        await page.go_forward()
        assert await page.locator('.spell-card:visible h2').inner_text()=='Fireball'
        await page.locator('label[for="spell-fireball-info-spell"]').click()
        await page.evaluate('scrollTo(0,0)')
        await page.screenshot(path=str(report/f'spells-without-slot-section-{width}.png'))
        # Existing deep links and caster selection work when loaded directly.
        await page.goto(url+'?caster=bard#spell-slots')
        await page.wait_for_selector('html.enhanced')
        assert await page.locator('#spell-slots').is_visible()
        assert await page.locator('#caster-bard').is_checked()
        await page.reload();await page.wait_for_selector('html.enhanced')
        assert await page.locator('#spell-slots').is_visible()
        assert await page.locator('#caster-bard').is_checked()
        await page.emulate_media(media='print')
        assert await page.locator('table[data-caster="bard"]').is_visible()
        assert not await page.locator('#spells').is_visible()
        await page.emulate_media(media='screen')
        await page.locator('.back-to-spells').click()
        await page.emulate_media(media='print')
        assert not await page.locator('#spell-slots').is_visible()
        assert await page.locator('.spell-card:visible').count()==1
        await page.emulate_media(media='screen')
        # A no-result reader is still reachable from the table view.
        await page.goto(url+'?q=no-matching-spell-93282#spell-slots')
        await page.wait_for_selector('html.enhanced')
        await page.locator('.back-to-spells').click()
        assert await page.locator('#empty').is_visible()
        await context.close()
    for width in (1280,390):
        for disabled in (True,False):
            context=await browser.new_context(java_script_enabled=not disabled,viewport={'width':width,'height':900})
            page=await context.new_page()
            if not disabled:
                await page.route('**/assets/app.*.js',lambda route:route.abort())
            await page.goto(url+'#spell-fireball')
            assert not await page.locator('#spell-slots').is_visible()
            await page.locator('.section-nav a[href="#spell-slots"]').click()
            assert await page.locator('#spell-slots').is_visible()
            assert not await page.locator('#spells').is_visible()
            await page.locator('label[for="caster-cleric"]').click()
            assert await page.locator('table[data-caster="cleric"]').is_visible()
            await page.locator('.back-to-spells').click()
            assert not await page.locator('#spell-slots').is_visible()
            assert await page.locator('.spell-card:visible').count()==1
            await page.goto(url+'#spell-slots')
            assert await page.locator('#spell-slots').is_visible()
            await context.close()
    assert not errors,errors
