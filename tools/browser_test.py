"""Regression tests against real HTTP loading, including delayed/failed JS.
Run after build.py; requires Playwright Chromium. Artifacts go to /tmp.
"""
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from threading import Thread
import argparse,asyncio,base64,json,os
from playwright.async_api import async_playwright
from slots_view_test import check_slots_view
from nerf_discussions_test import check_discussion_browser
ROOT=Path(__file__).resolve().parents[1]
REPORT=Path(os.environ.get('REFERENCE_TEST_OUTPUT','/tmp/spell-balance-validation'))
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
async def check_mobile_menu(browser,url):
    """Phone list stays below the card and changes state only on user disclosure input."""
    errors=[]
    context=await browser.new_context(viewport={'width':390,'height':900})
    page=await context.new_page()
    page.on('pageerror',lambda e:errors.append(str(e)))
    await page.goto(url+'#spell-fireball');await page.wait_for_selector('html.enhanced')
    async def state(want):
        await page.wait_for_function('(want)=>document.getElementById("spell-menu").open===want',arg=want)
    async def below():
        card=await page.locator('.spell-card:visible').bounding_box()
        nav=await page.locator('.sidebar').bounding_box()
        assert nav['y']>=card['y']+card['height'],(card,nav)
        assert await page.evaluate('!!(document.querySelector(".reader-detail").compareDocumentPosition(document.querySelector(".sidebar")) & Node.DOCUMENT_POSITION_FOLLOWING)')
    await state(False);await below()
    await page.locator('#spell-menu > summary').click();await state(True)
    await page.wait_for_function('localStorage.getItem("spellwright.mobileSpellMenu")==="open"')
    await page.locator('.sidebar a[href="#spell-shield"]').click()
    assert await page.locator('.spell-card:visible h2').inner_text()=='Shield'
    await state(True);await below()
    await page.select_option('#jump','spell-fireball');await state(True)
    await page.go_back();await state(True)
    await page.go_forward();await state(True)
    await page.select_option('#spell-class','wizard');await state(True)
    await page.uncheck('#house-rules-toggle');await state(True)
    await page.check('#house-rules-toggle');await page.click('#clear');await state(True)
    await page.reload();await page.wait_for_selector('html.enhanced');await state(True)
    await page.locator('#spell-menu > summary').focus();await page.keyboard.press('Enter');await state(False)
    await page.wait_for_function('localStorage.getItem("spellwright.mobileSpellMenu")==="closed"')
    await page.select_option('#jump','spell-alarm');await state(False)
    await page.reload();await page.wait_for_selector('html.enhanced');await state(False)
    # Desktop stays on the left, without losing the phone preference.
    await page.set_viewport_size({'width':1280,'height':900});await state(True)
    await page.evaluate('scrollTo(0,0)')
    card=await page.locator('.spell-card:visible').bounding_box();nav=await page.locator('.sidebar').bounding_box()
    assert nav['x']+nav['width']<=card['x'] and abs(nav['y']-card['y'])<2,(nav,card)
    assert await page.evaluate('localStorage.getItem("spellwright.mobileSpellMenu")')=='closed'
    await page.set_viewport_size({'width':390,'height':900});await state(False);await below()
    await page.locator('#spell-menu > summary').click();await state(True)
    await page.set_viewport_size({'width':1280,'height':900});await state(True)
    await page.set_viewport_size({'width':768,'height':900});await state(True);await below()
    for width in (390,360):
        await page.set_viewport_size({'width':width,'height':900});await below()
        w=await page.evaluate('[document.documentElement.clientWidth,document.documentElement.scrollWidth]')
        assert w[1]<=w[0]+1,w
    await page.select_option('#jump','spell-fireball');await state(True)
    await page.locator('.reader-layout').screenshot(path=str(REPORT/'mobile-menu-open.png'))
    again=await context.new_page();await again.goto(url+'#spell-shield');await again.wait_for_selector('html.enhanced')
    assert await again.locator('#spell-menu').evaluate('(m)=>m.open')
    await context.close()
    # Denied storage still leaves a usable menu with in-memory state.
    blocked=await browser.new_context(viewport={'width':390,'height':900})
    await blocked.add_init_script('Object.defineProperty(window,"localStorage",{get(){throw new DOMException("Storage blocked","SecurityError")}})')
    p=await blocked.new_page();p.on('pageerror',lambda e:errors.append(str(e)))
    await p.goto(url+'#spell-fireball');await p.wait_for_selector('html.enhanced')
    await p.locator('#spell-menu > summary').click()
    await p.locator('.sidebar a[href="#spell-shield"]').click()
    assert await p.locator('#spell-menu').evaluate('(m)=>m.open')
    await blocked.close()
    # Content-first order and native behavior also work without scripts.
    plain=await browser.new_context(java_script_enabled=False,viewport={'width':390,'height':900})
    p=await plain.new_page();await p.goto(url+'#spell-fireball')
    card=await p.locator('.spell-card:visible').bounding_box();nav=await p.locator('.sidebar').bounding_box()
    assert nav['y']>=card['y']+card['height']
    await p.locator('.sidebar a[href="#spell-shield"]').click()
    assert await p.locator('#spell-menu').evaluate('(m)=>m.open')
    await plain.close()
    assert not errors,errors

async def run(filename):
    REPORT.mkdir(parents=True,exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)))
    Thread(target=server.serve_forever,daemon=True).start()
    url=f'http://127.0.0.1:{server.server_port}/{filename}'
    errors=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch()
        page=await browser.new_page(viewport={'width':1280,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)))
        gate=asyncio.Event()
        async def hold_script(route):
            await gate.wait(); await route.continue_()
        await page.route('**/assets/app.*.js',hold_script)
        await page.goto(url,wait_until='commit')
        await page.locator('.site-header').wait_for(state='visible')
        await page.wait_for_function('document.styleSheets.length > 0')
        await page.wait_for_timeout(1500)
        assert await page.locator('.hero,.notice').count()==0
        assert await page.locator('.site-header h1').inner_text()=='Spellwright'
        assert await page.locator('table.slot-table tbody tr').count()==100
        assert not await page.locator('html.enhanced').count()
        before=await page.locator('.site-header').bounding_box()
        await page.evaluate('window.testHeader=document.querySelector(".site-header")')
        # Capture first paint without waiting for document.fonts.ready while deferred JS is held.
        cdp=await page.context.new_cdp_session(page)
        shot=await cdp.send('Page.captureScreenshot',{'format':'png'})
        (REPORT/'before-javascript.png').write_bytes(base64.b64decode(shot['data']))
        await cdp.detach()
        gate.set();await page.wait_for_selector('html.enhanced')
        after=await page.locator('.site-header').bounding_box()
        assert before==after,{'before':before,'after':after}
        assert await page.evaluate('testHeader === document.querySelector(".site-header")')
        assert await page.locator('.hero,.notice').count()==0
        await page.screenshot(path=str(REPORT/'after-javascript.png'))
        await page.unroute('**/assets/app.*.js',hold_script)
        await page.select_option('#jump','spell-fireball')
        assert await page.locator('.spell-card:visible h2').inner_text()=='Fireball'
        assert '6d6' in await page.locator('#spell-fireball .spell-body:visible').inner_text()
        await page.locator('label[for="spell-fireball-info-compare"]').click()
        assert '8d6' in await page.locator('#spell-fireball [data-panel="2024"]:visible').inner_text()
        await page.locator('label[for="spell-fireball-editions-2014"]').click()
        assert 'pointing finger' in await page.locator('#spell-fireball [data-panel="2014"]:visible').inner_text()
        await page.locator('label[for="spell-fireball-info-spell"]').click()
        # Icons are static on every entry; the School metadata field is text only.
        expected={'Abjuration':'abjuration.svg','Conjuration':'conjuration.svg','Divination':'divination.svg','Enchantment':'enchantment.svg','Evocation':'evocation.svg','Illusion':'illusion.svg','Necromancy':'necromancy.svg','Transmutation':'transmutation.svg'}
        all_icons=await page.locator('.spell-card').evaluate_all('(cs)=>cs.map(c=>[c.dataset.school,c.querySelector(".school-emblem").getAttribute("src")])')
        assert len(all_icons)==391 and all(expected[s]==f for s,f in all_icons)
        # School artwork must remain vector-only, transparent, and non-interactive.
        await page.evaluate("""async files => {
          for (const file of files) {
            const image = new Image(); image.src=file; await image.decode();
            const canvas=document.createElement('canvas');canvas.width=128;canvas.height=128;
            const ctx=canvas.getContext('2d');ctx.drawImage(image,0,0,128,128);
            for (const [x,y] of [[0,0],[127,0],[0,127],[127,127]]) {
              if(ctx.getImageData(x,y,1,1).data[3]!==0) throw new Error(file+' has an opaque background');
            }
          }
        }""",list(expected.values()))
        assert await page.locator('.school-emblem,.spell-link > img').evaluate_all("es=>es.every(e=>getComputedStyle(e).pointerEvents==='none' && e.getAttribute('draggable')==='false')")
        badge=page.locator('#spell-fireball .school-emblem')
        box=await badge.bounding_box()
        await page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2)
        assert await page.evaluate("p=>document.elementFromPoint(p.x,p.y).tagName!=='IMG'",{'x':box['x']+box['width']/2,'y':box['y']+box['height']/2})
        assert await page.locator('.spell-meta img').count()==0
        assert 'favicon.svg' in await page.locator('.brand img').get_attribute('src')
        classes=json.loads((ROOT/'data/classes.json').read_text())
        for c in classes['classes']:
            values=await page.locator(f'table[data-caster="{c["id"]}"] tbody tr').evaluate_all('(rows)=>rows.map(r=>Number(r.cells[r.cells.length-10].textContent))')
            assert values==c['prepared']
        await page.select_option('#label','house-rule');assert await page.locator('.sidebar li:visible').count()==5
        await page.select_option('#spell-class','wizard');assert await page.locator('.sidebar li:visible').count()==5
        await page.select_option('#level','9');assert await page.locator('.sidebar li:visible').count()==1
        assert await page.locator('.spell-card:visible h2').inner_text()=='Forcecage'
        await page.uncheck('#house-rules-toggle');assert await page.locator('#empty').is_visible()
        await page.select_option('#level','7');assert await page.locator('.spell-card:visible h2').inner_text()=='Forcecage'
        await page.reload();await page.wait_for_selector('html.enhanced')
        assert await page.locator('#spell-class').input_value()=='wizard'
        assert await page.locator('#level').input_value()=='7'
        assert not await page.locator('#house-rules-toggle').is_checked()
        await page.click('#clear');await page.check('#house-rules-toggle')
        await page.fill('#search','no-such-spell-827321');await page.wait_for_timeout(180);assert await page.locator('#empty').is_visible()
        await page.click('#reset');assert await page.locator('.sidebar li:visible').count()==391
        await page.select_option('#jump','spell-shield');await page.select_option('#jump','spell-fireball')
        await page.go_back();assert await page.locator('.spell-card:visible h2').inner_text()=='Shield'
        await page.go_forward();assert await page.locator('.spell-card:visible h2').inner_text()=='Fireball'
        await page.locator('#spell-fireball .class-badge:visible').filter(has_text='Sorcerer').click()
        assert await page.locator('#spell-class').input_value()=='sorcerer'
        await page.click('#clear')
        for width in (1440,1280,768,390,360):
            await page.set_viewport_size({'width':width,'height':1000})
            await page.select_option('#jump','spell-fireball')
            await page.evaluate('scrollTo(0,0)')
            await page.wait_for_timeout(50)
            size=await page.evaluate('[document.documentElement.clientWidth,document.documentElement.scrollWidth]')
            assert size[1]<=size[0]+1,(width,size)
            await page.screenshot(path=str(REPORT/f'fireball-{width}.png'))
        await page.set_viewport_size({'width':1280,'height':1000})
        await page.goto(url+'?caster=bard#spell-slots');await page.wait_for_selector('html.enhanced')
        assert await page.locator('#spell-slots').is_visible()
        assert not await page.locator('#spells').is_visible()
        assert await page.locator('#caster-bard').is_checked()
        await page.locator('#caster-bard').focus();await page.keyboard.press('ArrowRight')
        assert await page.locator('#caster-cleric').is_checked()
        # No JS: the header, sidebar anchors, spell tabs and class tabs still work.
        context=await browser.new_context(java_script_enabled=False,viewport={'width':1280,'height':1000})
        nojs=await context.new_page();await nojs.goto(url+'#spell-fireball')
        assert await nojs.locator('.spell-card:visible h2').inner_text()=='Fireball'
        await nojs.locator('label[for="spell-fireball-info-compare"]').click()
        await nojs.locator('label[for="spell-fireball-editions-2014"]').click()
        assert 'pointing finger' in await nojs.locator('#spell-fireball [data-panel="2014"]:visible').inner_text()
        await nojs.locator('.sidebar a[href="#spell-shield"]').click()
        assert await nojs.locator('.spell-card:visible h2').inner_text()=='Shield'
        await nojs.locator('.section-nav a[href="#spell-slots"]').click()
        await nojs.locator('label[for="caster-bard"]').click()
        assert await nojs.locator('table[data-caster="bard"]').is_visible()
        await nojs.screenshot(path=str(REPORT/'no-javascript.png'));await context.close()
        # Script download failure must not reveal a legacy layout or blank the page.
        failed=await browser.new_page(viewport={'width':1280,'height':1000})
        await failed.route('**/assets/app.*.js',lambda route:route.abort())
        await failed.goto(url+'#spell-fireball')
        assert await failed.locator('.site-header h1').inner_text()=='Spellwright'
        assert await failed.locator('.hero,.notice').count()==0
        assert await failed.locator('.spell-card:visible h2').inner_text()=='Fireball'
        await failed.locator('label[for="spell-fireball-info-why"]').click()
        assert await failed.locator('#spell-fireball .why').is_visible()
        await failed.screenshot(path=str(REPORT/'failed-javascript.png'))
        from house_rules_test import check_rule_browser
        await check_rule_browser(browser,url,REPORT)
        await check_mobile_menu(browser,url)
        await check_slots_view(browser,url,REPORT)
        await check_discussion_browser(browser,url,REPORT)
        await browser.close()
    server.shutdown()
    assert not errors,errors
    report={'result':'PASS','transport':'real local HTTP in CI','delayed_script_header_unchanged':True,'script_delay_ms':1500,'no_legacy_header':True,'script_failure_readable':True,'no_javascript_navigation_and_tabs':True,'history_and_filter_restore':True,'responsive_widths':[1440,1280,768,390,360],'mobile_menu_below_spell':True,'mobile_menu_preference_persists':True,'desktop_sidebar_preserved':True,'header_only_spell_slots':True,'slot_view_native_fallback':True,'slot_view_preserves_reader_state':True,'school_icons':391,'class_rows':100,'javascript_errors':errors}
    (REPORT/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='index.html');args=parser.parse_args();asyncio.run(run(args.output))
