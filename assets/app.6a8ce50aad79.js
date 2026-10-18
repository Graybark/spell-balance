/* Interaction only. Layout, editions, house rules, class rows and icons are static. */
(() => {
  'use strict';
  const doc = document;
  const controls = Object.fromEntries(['search','spell-class','level','label','jump','house-rules-toggle','clear','reset'].map(id => [id, doc.getElementById(id)]));
  const cards = [...doc.querySelectorAll('.spell-card')];
  const links = new Map([...doc.querySelectorAll('.sidebar li')].map(li => [li.dataset.spell, li]));
  const entries = cards.map(card => ({card, item: links.get(card.id),
    haystack: card.textContent.toLocaleLowerCase(),
    classes: new Set(card.dataset.classes.split(' ')), categories: new Set(card.dataset.categories.split(' '))}));
  const byId = new Map(entries.map(entry => [entry.card.id, entry]));
  const empty = doc.getElementById('empty'), menu = doc.getElementById('spell-menu'), slots = doc.getElementById('spell-slots');
  const mobile = matchMedia('(max-width:800px)');
  // Keep the phone list's explicit disclosure preference across navigation and reloads.
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
  let active = null, searchTimer;
  const isHouse = () => controls['house-rules-toggle'].checked;
  // Class tables are a separate in-page view reached from the header, not a disclosure.
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
  function setURL(push = false, hash) {
    const url = new URL(location.href);
    for (const [key,id] of [['q','search'],['class','spell-class'],['level','level'],['label','label']]) {
      const value = controls[id].value.trim();
      if (value) url.searchParams.set(key,value); else url.searchParams.delete(key);
    }
    if (isHouse()) url.searchParams.delete('rules'); else url.searchParams.set('rules','official');
    const caster = doc.querySelector('input[name="caster"]:checked').value;
    if (caster === 'wizard') url.searchParams.delete('caster'); else url.searchParams.set('caster',caster);
    if (hash !== undefined) url.hash = hash;
    try { if (push) history.pushState(null,'',url); else history.replaceState(null,'',url); }
    catch (_) { /* Plain file URLs may not permit history rewriting. */ }
    syncView();
  }
  function choose(entry, navigate = false) {
    if (active) {active.card.classList.remove('is-active'); active.item.querySelector('a').removeAttribute('aria-current');}
    active=entry;
    if (!active) return;
    active.card.classList.add('is-active'); active.item.querySelector('a').setAttribute('aria-current','true');
    if (navigate && location.hash !== '#spell-slots') {
      active.card.querySelector('h2').focus({preventScroll:true});
      active.card.scrollIntoView({block:'start'});
    }
    if (!mobile.matches && location.hash !== '#spell-slots') requestAnimationFrame(() => {
      if (!active) return;
      const nav=menu.querySelector('nav'), r=active.item.getBoundingClientRect(), n=nav.getBoundingClientRect();
      if(r.top<n.top || r.bottom>n.bottom) nav.scrollTop+=r.top-n.top-60;
    });
  }
  function filter(preferHash = false, navigate = false) {
    doc.documentElement.dataset.rules = isHouse() ? 'house':'official';
    const q=controls.search.value.trim().toLocaleLowerCase(), cl=controls['spell-class'].value, lv=controls.level.value, cat=controls.label.value;
    const matches=[];
    for (const entry of entries) {
      const {card}=entry;
      const level = isHouse() ? card.dataset.levelHouse:card.dataset.levelOfficial;
      const match=(!q || entry.haystack.includes(q)) && (!cl || entry.classes.has(cl)) && (!lv || lv===level) && (!cat || entry.categories.has(cat));
      entry.item.hidden=!match; if(match) matches.push(entry);
    }
    const requested=byId.get(location.hash.slice(1));
    const selected=preferHash && matches.includes(requested) ? requested : matches.includes(active) ? active : matches[0] || null;
    empty.hidden=matches.length>0;
    doc.getElementById('visible-count').textContent=matches.length+' spells';
    doc.getElementById('sidebar-count').textContent='('+matches.length+')';
    choose(selected,navigate);
    if(requested && active && requested!==active) setURL(false,active.card.id);
  }
  function restore(navigate=false) {
    clearTimeout(searchTimer);
    const p=new URLSearchParams(location.search);
    controls.search.value=p.get('q')||'';
    for(const [key,id] of [['class','spell-class'],['level','level'],['label','label']]) {
      const c=controls[id], wanted=(p.get(key)||'').toLowerCase();
      c.value=[...c.options].some(o=>o.value===wanted)?wanted:'';
    }
    controls['house-rules-toggle'].checked=p.get('rules')!=='official';
    const caster=p.get('caster')||'wizard';
    const selected=[...doc.querySelectorAll('input[name="caster"]')].find(i=>i.value===caster)||doc.getElementById('caster-wizard');
    selected.checked=true;
    filter(true,navigate);
    syncView(navigate);
  }
  function clear() {
    clearTimeout(searchTimer);
    ['search','spell-class','level','label'].forEach(id=>controls[id].value='');
    setURL();filter();
  }
  controls.search.addEventListener('input',()=>{
    clearTimeout(searchTimer); searchTimer=setTimeout(()=>{setURL();filter();},100);
  });
  ['spell-class','level','label','house-rules-toggle'].forEach(id=>controls[id].addEventListener('change',()=>{clearTimeout(searchTimer);setURL();filter();}));
  controls.clear.addEventListener('click',clear);controls.reset.addEventListener('click',clear);
  controls.jump.addEventListener('change',()=>{
    const entry=byId.get(controls.jump.value);if(!entry)return;
    ['search','spell-class','level','label'].forEach(id=>controls[id].value='');
    setURL(true,entry.card.id);filter(true,true);controls.jump.value='';
  });
  doc.addEventListener('click',event=>{
    const a=event.target.closest('a');
    if(!a || event.button!==0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey)return;
    if(a.dataset.filterClass){
      event.preventDefault();controls['spell-class'].value=a.dataset.filterClass;setURL();filter();return;
    }
    const href=a.getAttribute('href');
    if(href==='#spell-slots') {
      event.preventDefault();clearTimeout(searchTimer);setURL(true,'spell-slots');syncView(true);return;
    }
    if(href==='#spells' && location.hash==='#spell-slots') {
      event.preventDefault();setURL(true,active ? active.card.id : 'spells');
      if(active)choose(active,true);else doc.getElementById('spells').scrollIntoView({block:'start'});
      return;
    }
    if(!href?.startsWith('#spell-'))return;
    const entry=byId.get(href.slice(1));if(!entry)return;
    event.preventDefault();
    if(entry.item.hidden){['search','spell-class','level','label'].forEach(id=>controls[id].value='');filter();}
    setURL(true,entry.card.id);choose(entry,true);
  });
  doc.querySelectorAll('input[name="caster"]').forEach(input=>input.addEventListener('change',()=>setURL()));
  window.addEventListener('popstate',()=>restore(true));
  window.addEventListener('hashchange',()=>{syncView(true);if(location.hash!=='#spell-slots')filter(true,true);});
  function setOffsets(){const toolbar=doc.querySelector('.toolbar');const h=matchMedia('(max-width:700px)').matches?0:toolbar.getBoundingClientRect().height;doc.documentElement.style.setProperty('--top',Math.ceil(h+12)+'px');}
  setOffsets();if('ResizeObserver'in window)new ResizeObserver(setOffsets).observe(doc.querySelector('.toolbar'));else window.addEventListener('resize',setOffsets);
  // Restore state and select the existing card before enabling interactions.
  restore();doc.documentElement.classList.add('enhanced');
  doc.querySelectorAll('.toolbar [disabled]').forEach(control=>{control.disabled=false;});
})();
