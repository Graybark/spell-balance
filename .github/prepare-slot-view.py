"""Prepare the requested navigation change without altering spell or class data."""
from pathlib import Path
import hashlib
ROOT=Path.cwd()
def blob(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
expected={'src/app.js':'289c077f96e2c69d7f525290b2ab01b22450bf05','src/app.css':'d23c8d6abcf0efaae94d51691e7f63359f162cd9','tools/build.py':'eb4e6aefd3dba953852a9247cf6be37c917ae5e8','tools/browser_test.py':'8721b542dc45b61606b5a9672fc29df098fb7e72','tools/verify.py':'d14f2eb40c871a6a3c763396778ed6d3bd6cf4af'}
for name,sha in expected.items(): assert blob((ROOT/name).read_bytes())==sha, 'Source changed: '+name

def once(s,before,after):
    assert s.count(before)==1, 'Ambiguous patch: '+before[:100]
    return s.replace(before,after,1)

p=ROOT/'tools/build.py';s=p.read_text(encoding='utf-8')
s=once(s,'<main class="content"><details id="spell-slots" class="slot-section"><summary>Spell Slots (Full Casters)</summary>', '<main class="content"><section id="spell-slots" class="slot-section" aria-labelledby="spell-slots-heading"><header class="slot-view-header"><h2 id="spell-slots-heading" tabindex="-1">Spell Slots (Full Casters)</h2><a class="back-to-spells" href="#spells">Back to spells</a></header>')
s=once(s,"+tabs('caster','Full caster class',class_defs)+'</details>'", "+tabs('caster','Full caster class',class_defs)+'</section>'")
p.write_text(s,encoding='utf-8')

p=ROOT/'src/app.css';s=p.read_text(encoding='utf-8')
s=once(s,'.slot-section{margin-bottom:18px;', '.slot-section{display:none;')
s=once(s,'.slot-section>summary{padding:10px 14px;font:700 18px/1.4 Georgia,serif;background:linear-gradient(120deg,#e0edf7,#f4f8fc);border-radius:8px}', '.slot-view-header{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px 18px;padding:14px;background:linear-gradient(120deg,#e0edf7,#f4f8fc);border-radius:8px 8px 0 0}.slot-view-header h2{margin:0;font:700 21px/1.4 Georgia,serif;color:#1b3b62}.back-to-spells{font-size:13px;white-space:nowrap;padding:5px 0}')
view_css='''/* The header link opens the class-table view; no duplicate disclosure in the spell reader.
   Native fragment navigation is the fallback when the interaction script is unavailable. */
html:not(.enhanced):has(#spell-slots:target) #spell-slots,
html.enhanced[data-view=slots] #spell-slots{display:block}
html:not(.enhanced):has(#spell-slots:target) .toolbar,
html:not(.enhanced):has(#spell-slots:target) .reader-layout,
html.enhanced[data-view=slots] .toolbar,
html.enhanced[data-view=slots] .reader-layout{display:none}
@media print{.back-to-spells{display:none}.slot-section{break-after:auto}}
'''
s+='\n'+view_css
p.write_text(s,encoding='utf-8')

p=ROOT/'src/app.js';s=p.read_text(encoding='utf-8')
view_js='''  // Class tables are a separate in-page view reached from the header, not a disclosure.
  // Keep the existing reader, filters and phone-menu preference intact when switching views.
  function syncView(navigate = false) {
    const showingSlots = location.hash === '#spell-slots';
    doc.documentElement.dataset.view = showingSlots ? 'slots' : 'spells';
    doc.querySelectorAll('.section-nav a').forEach(link => {
      const selected = (link.getAttribute('href') === '#spell-slots') === showingSlots;
      if (selected) link.setAttribute('aria-current','page'); else link.removeAttribute('aria-current');
    });
    setOffsets();
    if (navigate && showingSlots) {
      slots.querySelector('h2').focus({preventScroll:true});
      slots.scrollIntoView({block:'start'});
    }
  }
'''
s=once(s,'  function setURL(push = false, hash) {\n',view_js+'  function setURL(push = false, hash) {\n')
s=once(s,'    catch (_) { /* Plain file URLs may not permit history rewriting. */ }\n','    catch (_) { /* Plain file URLs may not permit history rewriting. */ }\n    syncView();\n')
s=once(s,'    if (navigate) {\n',"    if (navigate && location.hash !== '#spell-slots') {\n")
s=once(s,'    if (!mobile.matches) requestAnimationFrame(() => {\n',"    if (!mobile.matches && location.hash !== '#spell-slots') requestAnimationFrame(() => {\n")
s=once(s,"    if(location.hash==='#spell-slots') slots.open=true;",'    syncView(navigate);')
s=once(s,"    if(href==='#spell-slots')slots.open=true;",'''    if(href==='#spell-slots') {
      event.preventDefault();clearTimeout(searchTimer);setURL(true,'spell-slots');syncView(true);return;
    }
    if(href==='#spells' && location.hash==='#spell-slots') {
      event.preventDefault();setURL(true,active ? active.card.id : 'spells');
      if(active)choose(active,true);else doc.getElementById('spells').scrollIntoView({block:'start'});
      return;
    }''')
s=once(s,"  window.addEventListener('hashchange',()=>{if(location.hash==='#spell-slots')slots.open=true;else filter(true,true);});", "  window.addEventListener('hashchange',()=>{syncView(true);if(location.hash!=='#spell-slots')filter(true,true);});")
s=once(s,"  let printState;\n  window.addEventListener('beforeprint',()=>{printState=slots.open;slots.open=true;});\n  window.addEventListener('afterprint',()=>{if(typeof printState==='boolean')slots.open=printState;});\n",'')
assert 'slots.open' not in s
p.write_text(s,encoding='utf-8')

p=ROOT/'tools/browser_test.py';s=p.read_text(encoding='utf-8')
s=once(s,'from playwright.async_api import async_playwright\n','from playwright.async_api import async_playwright\nfrom slots_view_test import check_slots_view\n')
s=once(s,"        assert await page.locator('#spell-slots').get_attribute('open') is not None", "        assert await page.locator('#spell-slots').is_visible()\n        assert not await page.locator('#spells').is_visible()")
s=once(s,"        await nojs.locator('#spell-slots > summary').click()", "        await nojs.locator('.section-nav a[href=\"#spell-slots\"]').click()")
s=once(s,'        await check_mobile_menu(browser,url)\n','        await check_mobile_menu(browser,url)\n        await check_slots_view(browser,url,REPORT)\n')
s=once(s,"'school_icons':391,'class_rows':100", "'header_only_spell_slots':True,'slot_view_native_fallback':True,'slot_view_preserves_reader_state':True,'school_icons':391,'class_rows':100")
p.write_text(s,encoding='utf-8')

p=ROOT/'tools/verify.py';s=p.read_text(encoding='utf-8')
s=once(s,"    assert not page.select('.permalink'), 'Spell-card permalink controls must remain removed.'", "    assert not page.select('.permalink'), 'Spell-card permalink controls must remain removed.'\n    assert not page.select('details#spell-slots, #spell-slots > summary')\n    assert page.select_one('section#spell-slots[aria-labelledby=spell-slots-heading]')\n    assert page.select_one('.section-nav a[href=\"#spell-slots\"]')\n    assert page.select_one('#spell-slots .back-to-spells[href=\"#spells\"]')")
p.write_text(s,encoding='utf-8')
print('Prepared header-only class tables; all data files and school assets are untouched.')
