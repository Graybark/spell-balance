"""Apply the approved mobile-navigation change to freshly verified sources."""
from pathlib import Path
import hashlib
root=Path.cwd()
expected={'src/app.js':'5907fa04d9e73e053264597a18499feb384afaf1','src/app.css':'5848e5a092198ca32dcd8f31a0e559b0d326ff4a','tools/build.py':'a57420a05ff162d07f52442e2f593060f47c8e6b','tools/browser_test.py':'55c323067b25b080c1f459e124dc9ebab09275a5'}
for name,sha in expected.items():
    b=(root/name).read_bytes()
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==sha, 'Source changed: '+name

def replace_once(text,before,after):
    assert text.count(before)==1, 'Ambiguous patch: '+before[:100]
    return text.replace(before,after,1)

p=root/'src/app.js';s=p.read_text(encoding='utf-8')
state="""  // Keep the phone list's explicit disclosure preference across navigation and reloads.
  // Track the applied layout separately: native toggle events can arrive after a resize.
  const menuStorageKey = 'spellwright.mobileSpellMenu';
  let menuIsMobile = mobile.matches;
  let mobileMenuOpen = false, desktopMenuOpen = menu.open;
  try {
    const saved = localStorage.getItem(menuStorageKey);
    if (saved === 'open' || saved === 'closed') mobileMenuOpen = saved === 'open';
  } catch (_) { /* Storage can be blocked; the in-memory preference still works. */ }
  function rememberMenuState() {
    if (menuIsMobile) {
      if (menu.open === mobileMenuOpen) return;
      mobileMenuOpen = menu.open;
      try { localStorage.setItem(menuStorageKey, mobileMenuOpen ? 'open' : 'closed'); }
      catch (_) { /* Keep the user's state for this page even when persistence fails. */ }
    } else {
      desktopMenuOpen = menu.open;
    }
  }
  menu.open = menuIsMobile ? mobileMenuOpen : desktopMenuOpen;
  menu.addEventListener('toggle', rememberMenuState);
  mobile.addEventListener('change', () => {
    // Save the old layout's actual disclosure state, including a pending user toggle.
    rememberMenuState();
    menuIsMobile = mobile.matches;
    menu.open = menuIsMobile ? mobileMenuOpen : desktopMenuOpen;
  });
"""
s=replace_once(s,"  const mobile = matchMedia('(max-width:800px)');\n","  const mobile = matchMedia('(max-width:800px)');\n"+state)
s=replace_once(s,'      if (mobile.matches) menu.open=false;\n','')
s=replace_once(s,"  mobile.addEventListener('change',()=>{menu.open=!mobile.matches;});\n",'')
s=replace_once(s,'  if(mobile.matches)menu.open=false;\n','')
p.write_text(s,encoding='utf-8')

p=root/'src/app.css';s=p.read_text(encoding='utf-8')
s=replace_once(s,'.reader-layout{display:grid;grid-template-columns:236px minmax(0,1fr);','.reader-layout{display:grid;grid-template-columns:236px minmax(0,1fr);grid-template-areas:"list detail";')
s=replace_once(s,'.sidebar{position:sticky;','.sidebar{grid-area:list;position:sticky;')
s=replace_once(s,'.reader-detail{min-width:0}', '.reader-detail{grid-area:detail;min-width:0}')
s=replace_once(s,'background:#f1f6fb;margin-bottom:12px;padding:0}.sidebar summary','background:#f1f6fb;margin:12px 0 0;padding:0}.sidebar summary')
p.write_text(s,encoding='utf-8')

p=root/'tools/build.py';s=p.read_text(encoding='utf-8')
old=next(line for line in s.splitlines() if "page+='<div class=\"reader-layout\"" in line)
start=old.index('<aside class="sidebar"');end=old.index('</aside>')+len('</aside>')
nav=old[start:end]
replacement="    # Content-first DOM matches phone reading/tab order; desktop CSS places the list left.\n"
replacement+="    navigation='"+nav+"'\n"
replacement+=old[:start]+old[end:]
replacement=replace_once(replacement,"+''.join(cards)+'</div></div></main>'","+''.join(cards)+'</div>'+navigation+'</div></main>'")
s=replace_once(s,old,replacement)
p.write_text(s,encoding='utf-8')

p=root/'tools/browser_test.py';s=p.read_text(encoding='utf-8')
extra=(root/'.github/mobile-menu-regression.txt').read_text(encoding='utf-8')
s=replace_once(s,'async def run(filename):\n',extra+'\nasync def run(filename):\n')
s=replace_once(s,'        await browser.close()\n','        await check_mobile_menu(browser,url)\n        await browser.close()\n')
s=replace_once(s,"'school_icons':391,'class_rows':100", "'mobile_menu_below_spell':True,'mobile_menu_preference_persists':True,'desktop_sidebar_preserved':True,'school_icons':391,'class_rows':100")
p.write_text(s,encoding='utf-8')
print('Patched only layout order, disclosure persistence and regression coverage.')
