/* Sidebar reader and per-spell tabs. No new spell rules are defined here.
 * Original edition nodes and sourced discussion notes are kept, not replaced.
 * The Abjuration icon is traced from the user-supplied artwork in favicon.svg.
 */
(() => {
  'use strict';
  if (document.documentElement.dataset.spellReader) return;
  if (typeof cards === 'undefined' || typeof applyFilters !== 'function') throw new Error('Spell reader: core spell data is unavailable.');
  const coreFilter = applyFilters;
  const searchBox = document.getElementById('search');
  const classBox = document.getElementById('spell-class');
  const levelBox = document.getElementById('level');
  const categoryBox = document.getElementById('label');
  const rulesBox = document.getElementById('house-rules-toggle');
  const jumpBox = document.getElementById('jump');
  const toolbar = document.querySelector('.toolbar');
  const root = document.getElementById('spells');
  const emptyState = document.getElementById('empty');
  const icon = new URL('favicon.svg?v=abjuration-reader-1', document.currentScript.src).href;
  if (!root || !rulesBox || !classBox || !cards.length) throw new Error('Spell reader: missing page controls.');
  const make = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const normalizeClass = name => name.trim().toLowerCase().replace(/\s+/g,'').replace(/^vvizard$/,'wizard');
  const availableClasses = new Set([...classBox.options].map(option => option.value));
  const readMeta = source => new Map([...source.querySelectorAll(':scope > .metadata .meta-item')].map(item => [item.querySelector('dt').textContent.trim().toLowerCase(), item.querySelector('dd').textContent.trim()]));
  const getSchool = source => source.querySelector('.spell-type').textContent.split('·').pop().trim();
  const data = cards.map(card => {
    const official = card.querySelector('.version-2024');
    const old = card.querySelector('.version-2014, .version-absent');
    const custom = card.querySelector('.version-house');
    const heading = card.querySelector('.spell-heading');
    if (!official || !old || !heading || !official.querySelector('.metadata')) throw new Error('Spell reader: incomplete source for '+card.id);
    return { card, official, old, custom, heading, name:heading.querySelector('h2').textContent,
      school:getSchool(official), mainKey:'', renderedMode:null,
      discussion:[...card.querySelectorAll('.balance-note')],
      notes:[...card.querySelectorAll('.review-note,.revised-note,.errata-note,.field-signals')],
      change:custom?.querySelector('.house-change')?.textContent || '' };
  });
  const byId = new Map(data.map(entry => [entry.card.id, entry]));
  const mobile = window.matchMedia('(max-width:800px)');
  let active = null;
  let queued = false;
  let pendingNavigation = false;
  let useHash = true;
  const favicon = document.querySelector('link[rel="icon"]');
  if (favicon) favicon.href = icon;

  // A compact header, retaining overview counts without another banner.
  const hero = document.querySelector('.hero-inner');
  const heading = hero.querySelector('h1');
  const sectionNav = hero.querySelector('.slot-nav');
  const counts = hero.querySelector('.counts');
  const brand = make('a','reader-brand');
  brand.href = '#spells';
  const brandIcon = make('img'); brandIcon.src = icon; brandIcon.alt = ''; brandIcon.width = 52; brandIcon.height = 52;
  const brandText = make('div'); brandText.append(heading, make('small','', 'D&D spell reference'));
  brand.append(brandIcon, brandText);
  const stats = make('details','reader-stats'); stats.append(make('summary','', 'Overview'), counts);
  hero.replaceChildren(brand, sectionNav, stats);
  document.querySelector('.footer').textContent = 'Spell Balance · 2014 & 2024 editions · House-rule versions are marked in purple.';

  // Desktop master/detail layout; the same navigation becomes a disclosure on phones.
  root.classList.add('reader-layout');
  const sidebar = make('details','reader-sidebar');
  sidebar.open = !mobile.matches;
  const sideSummary = make('summary','', 'Spells ');
  const sideCount = make('span','reader-sidebar-count'); sideSummary.append(sideCount);
  const sideNav = make('nav'); sideNav.setAttribute('aria-label','Spell list');
  const sideList = make('ul'); sideNav.append(sideList); sidebar.append(sideSummary,sideNav);
  const detail = make('div','reader-detail'); detail.append(emptyState);
  const noResults = make('p','', 'No spells match these filters.');
  const reset = make('button','reader-reset','Clear filters'); reset.type='button';
  emptyState.replaceChildren(noResults,reset);
  root.append(sidebar,detail);
  reset.addEventListener('click', () => {
    searchBox.value=''; classBox.value=''; levelBox.value=''; categoryBox.value='';
    const url=new URL(location.href); ['class','level','label','q'].forEach(key=>url.searchParams.delete(key));
    history.replaceState(null,'',url); applyFilters();
  });
  const keepSidebarOpen = () => { if (!mobile.matches && !sidebar.open) sidebar.open=true; };
  sidebar.addEventListener('toggle',keepSidebarOpen);
  mobile.addEventListener('change',()=> { sidebar.open=!mobile.matches; updateOffsets(); });

  function tabs(host, definitions, prefix, onChange) {
    const bar=make('div','reader-tabs'); bar.setAttribute('role','tablist');
    bar.setAttribute('aria-label',prefix.endsWith('-editions')?'Original editions':'Spell information');
    const buttons=definitions.map((def,i)=> {
      const button=make('button','reader-tab',def.label); button.type='button';
      button.id=prefix+'-tab-'+def.key; button.setAttribute('role','tab');
      button.setAttribute('aria-controls',prefix+'-panel-'+def.key);
      button.setAttribute('aria-selected',String(i===0)); button.tabIndex=i===0?0:-1;
      def.pane.id=prefix+'-panel-'+def.key; def.pane.setAttribute('role','tabpanel');
      def.pane.setAttribute('aria-labelledby',button.id); def.pane.tabIndex=0;
      def.pane.hidden=i!==0; bar.append(button); return button;
    });
    const select = key => {
      definitions.forEach((def,i)=> {
        const selected=def.key===key;
        buttons[i].setAttribute('aria-selected',String(selected)); buttons[i].tabIndex=selected?0:-1; def.pane.hidden=!selected;
      });
      if(onChange) onChange(key);
    };
    buttons.forEach((button,i)=> {
      button.addEventListener('click',()=>select(definitions[i].key));
      button.addEventListener('keydown',event=> {
        let target;
        if(event.key==='ArrowRight') target=(i+1)%buttons.length;
        else if(event.key==='ArrowLeft') target=(i+buttons.length-1)%buttons.length;
        else if(event.key==='Home') target=0;
        else if(event.key==='End') target=buttons.length-1;
        else return;
        event.preventDefault(); select(definitions[target].key); buttons[target].focus();
      });
    });
    host.append(bar,...definitions.map(def=>def.pane));
    return {bar,select};
  }

  // Build the shell once. Primary spell bodies are rendered lazily from the current version.
  for (const entry of data) {
    const {card,official,old,custom,heading,name,school}=entry;
    const main=heading.children[0]; main.classList.add('reader-title-main');
    const title=heading.querySelector('h2'); title.tabIndex=-1;
    const eyebrow=heading.querySelector('.eyebrow');
    const tags=heading.querySelector('.heading-tags');
    const permalink=tags.querySelector('.permalink');
    const titleline=make('div','reader-titleline'); titleline.append(title,tags);
    main.replaceChildren(titleline,eyebrow);
    const aside=make('div','reader-heading-aside');
    if(permalink) aside.append(permalink);
    const emblem=make('img','reader-school-emblem'); emblem.src=icon; emblem.alt='Abjuration'; emblem.title='Abjuration'; emblem.width=82; emblem.height=78;
    emblem.hidden=school!=='Abjuration'; aside.append(emblem); heading.append(aside);
    const meta=make('dl','reader-meta');
    const spellPane=make('div','reader-pane reader-current');
    const comparePane=make('div','reader-pane reader-compare');
    const officialPane=make('div','reader-pane reader-comparison-pane'); officialPane.append(official);
    const oldPane=make('div','reader-pane reader-comparison-pane'); oldPane.append(old);
    const editionTabs=tabs(comparePane,[{key:'2024',label:'2024',pane:officialPane},{key:'2014',label:'2014',pane:oldPane}],card.id+'-editions');
    editionTabs.bar.classList.add('reader-comparison-tabs');
    if(entry.notes.length) { const notes=make('div','reader-revision-notes'); notes.append(...entry.notes); comparePane.append(notes); }
    const definitions=[{key:'spell',label:'Spell',pane:spellPane}];
    if(custom) {
      const whyPane=make('div','reader-pane'); const why=make('div','reader-why');
      why.append(make('h3','', 'House-rule change'),make('p','',entry.change),make('p','', 'This is the recorded change to the 2024 version. The original editions remain available in Compare versions.'));
      whyPane.append(why); definitions.push({key:'why',label:'Why this version?',pane:whyPane});
    }
    definitions.push({key:'compare',label:'Compare versions',pane:comparePane});
    if(entry.discussion.length) {
      const discussion=make('div','reader-pane reader-discussion'); discussion.append(...entry.discussion);
      definitions.push({key:'discussion',label:'Discussion',pane:discussion});
    }
    const store=make('div','reader-source-store'); store.hidden=true;
    if(custom) store.append(custom);
    card.replaceChildren(heading,meta);
    const infoTabs=tabs(card,definitions,card.id+'-info',key=>{entry.mainKey=key;});
    card.append(store); detail.append(card);
    Object.assign(entry,{meta,spellPane,infoTabs,emblem,tags,title,mainKey:'spell'});
    const li=make('li');
    const link=make('a'); link.href='#'+card.id;
    if(school==='Abjuration') { const image=make('img'); image.src=icon; image.alt=''; image.width=26; image.height=26; link.append(image); }
    const label=make('span'); const subtitle=make('small'); label.append(make('strong','',name),subtitle); link.append(label);
    if(custom) { const dot=make('span','reader-house-dot'); dot.title='House-rule version available'; link.append(dot); }
    li.append(link); sideList.append(li);
    Object.assign(entry,{li,link,subtitle});
    link.addEventListener('click',event=> {
      if(event.button!==0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      const url=new URL(location.href); url.hash=card.id;
      history.pushState(null,'',url); activate(entry,true);
    });
  }

  function highlighted(text, token) {
    const fragment=document.createDocumentFragment();
    const i=text.indexOf(token);
    if(i<0) { fragment.append(text); return fragment; }
    fragment.append(text.slice(0,i),make('mark','reader-change',token),text.slice(i+token.length));
    return fragment;
  }
  function emphasizeText(root, phrase, token) {
    const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
    let node;
    while((node=walker.nextNode())) {
      const at=node.data.indexOf(phrase); if(at<0) continue;
      const fragment=document.createDocumentFragment();
      fragment.append(node.data.slice(0,at),highlighted(phrase,token),node.data.slice(at+phrase.length));
      node.replaceWith(fragment); return;
    }
  }
  function addField(host,label,value,changed=false) {
    if(!value) return;
    const item=make('div'); const dt=make('dt','',label); const dd=make('dd');
    if(changed) dd.append(make('mark','reader-change',value)); else dd.textContent=value;
    item.append(dt,dd); host.append(item); return dd;
  }
  function renderPrimary(entry) {
    const isHouse=!!entry.custom && rulesBox.checked;
    if(entry.renderedMode===isHouse) return;
    const source=isHouse?entry.custom:entry.official;
    const metadata=readMeta(source); const school=getSchool(source);
    const type=source.querySelector('.spell-type').textContent;
    const level=type.match(/^Level\s+(\d+)/)?.[1] || 'Cantrip';
    const body=make('div','reader-primary-body');
    [...source.children].forEach(node=> {
      if(node.matches('.version-head,h3,.spell-type,.metadata,.spell-availability,.classes,.house-change')) return;
      const clone=node.cloneNode(true);
      clone.removeAttribute('id'); clone.querySelectorAll('[id]').forEach(el=>el.removeAttribute('id'));
      clone.classList.remove('spell-text-2024','spell-text-2014','spell-text-house');
      body.append(clone);
    });
    body.querySelectorAll('.spell-text p').forEach(p=> {
      const runIn=p.querySelector('.run-in');
      if(runIn && /Higher.Level|At Higher Levels/i.test(runIn.textContent)) p.classList.add('reader-upcast');
    });
    if(isHouse && entry.card.id==='spell-fireball') emphasizeText(body,'taking 6d6 Fire damage','6d6');
    if(isHouse && entry.card.id==='spell-melf-s-acid-arrow') emphasizeText(body,'for each spell slot level above 1.','1');
    const text=source.querySelector('.spell-text')?.textContent || '';
    const first=source.querySelector('.spell-text > p')?.textContent || text;
    const area=[...new Set([...first.matchAll(/\b\d+-foot(?:-radius)?\s+(?:Sphere|Emanation|Cube|Cone|Line|Cylinder)\b/g)].map(match=>match[0]))];
    const saves=[...new Set([...text.matchAll(/\b(?:make|makes|making|succeed on|succeeds on)\s+(?:a|an)\s+(Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma)\s+saving throw\b/g)].map(match=>match[1]+' save'))];
    const attacks=[...new Set([...text.matchAll(/\b(?:ranged|melee) spell attack\b/gi)].map(match=>match[0]))];
    const damages=[...new Set([...first.matchAll(/\b(?:taking|takes|take|deals|deal)\s+(\d+d\d+(?:\s*[+−-]\s*\d+)?\s+(?:Acid|Bludgeoning|Cold|Fire|Force|Lightning|Necrotic|Piercing|Poison|Psychic|Radiant|Slashing|Thunder) damage)\b/g)].map(match=>match[1]))];
    entry.meta.replaceChildren();
    addField(entry.meta,'Level',level,isHouse && entry.card.dataset.houseLevel!==entry.card.dataset.officialLevel);
    addField(entry.meta,'Casting Time',metadata.get('casting time'));
    const range=addField(entry.meta,'Range / Area',metadata.get('range'));
    if(range && area.length===1) range.append(make('small','',area[0]));
    const components=addField(entry.meta,'Components',metadata.get('components'));
    if(components && components.textContent.includes(' (')) {
      const value=components.textContent; const i=value.indexOf(' (');
      components.replaceChildren(value.slice(0,i),make('small','',value.slice(i)));
    }
    addField(entry.meta,'Duration',metadata.get('duration'));
    addField(entry.meta,'School',school); // Text only: the emblem belongs in the header.
    addField(entry.meta,'Attack / Save',[...attacks,...saves].join('; '));
    const damage=damages.length===1?addField(entry.meta,'Damage / Effect',damages[0]):null;
    if(damage && isHouse && entry.card.id==='spell-fireball') damage.replaceChildren(highlighted(damage.textContent,'6d6'));
    entry.meta.dataset.fields=entry.meta.children.length;
    entry.tags.querySelectorAll('.reader-flag').forEach(node=>node.remove());
    if(/\bConcentration\b/i.test(metadata.get('duration')||'')) entry.tags.append(make('span','tag reader-flag','Concentration'));
    if(/\britual\b/i.test(metadata.get('casting time')||'')) entry.tags.append(make('span','tag reader-flag','Ritual'));
    entry.emblem.hidden=school!=='Abjuration';
    entry.card.classList.toggle('reader-house-active',isHouse);
    const footer=make('footer','reader-footer');
    const availability=make('div','reader-availability'); availability.append(make('span','', 'Available for:'));
    const classes=source.querySelector('.classes');
    if(classes) classes.textContent.split(',').forEach(name=> {
      const id=normalizeClass(name); const caption=availableClasses.has(id)?id[0].toUpperCase()+id.slice(1):name.trim();
      const badge=make('button','reader-class-badge',caption); badge.type='button';
      badge.title='Filter the 2024 spell list by '+caption;
      if(!availableClasses.has(id)) badge.disabled=true;
      badge.addEventListener('click',()=>{classBox.value=id; classBox.dispatchEvent(new Event('change',{bubbles:true}));});
      availability.append(badge);
    });
    if(classes) footer.append(availability);
    const attribution=entry.official.querySelector('.edition-note')?.textContent || '';
    footer.append(make('span','reader-source',(isHouse?'Based on ':'')+attribution));
    entry.spellPane.replaceChildren(body,footer);
    entry.renderedMode=isHouse;
  }
  function activate(entry,navigate=false) {
    if(active!==entry) {
      if(active) { active.card.classList.remove('reader-active'); active.link.removeAttribute('aria-current'); }
      active=entry;
      if(active) { active.card.classList.add('reader-active'); active.link.setAttribute('aria-current','true'); renderPrimary(active); }
    } else if(active) renderPrimary(active);
    if(active) requestAnimationFrame(()=> {
      if(mobile.matches || !active) return;
      const item=active.link.getBoundingClientRect(), viewport=sideNav.getBoundingClientRect();
      if(item.top<viewport.top || item.bottom>viewport.bottom) sideNav.scrollTop+=item.top-viewport.top-70;
    });
    if(navigate && active) {
      if(mobile.matches) sidebar.open=false;
      active.title.focus({preventScroll:true});
      active.card.scrollIntoView({block:'start',behavior:'auto'});

    }
  }
  function update() {
    queued=false;
    const matches=data.filter(entry=>!entry.card.hidden);
    for(const entry of data) {
      entry.li.hidden=entry.card.hidden;
      const level=entry.card.dataset.level;
      entry.subtitle.textContent=(level==='0'?'Cantrip':'Level '+level)+' · '+entry.school;
    }
    sideCount.textContent='('+matches.length+')';
    document.getElementById('visible-count').textContent=matches.length+' spells';
    const requested=byId.get(location.hash.slice(1));
    const chosen=(useHash && requested && !requested.card.hidden)?requested:(active && !active.card.hidden)?active:matches[0]||null;
    useHash=false; activate(chosen,pendingNavigation); pendingNavigation=false;
    if(requested && active && requested!==active) { const url=new URL(location.href); url.hash=active.card.id; history.replaceState(null,'',url); }
  }
  function schedule(preferHash=false,navigate=false) {
    pendingNavigation=pendingNavigation||navigate;
    useHash=useHash||preferHash;
    if(!queued) { queued=true; queueMicrotask(update); }
  }
  function filterAndUpdate() { coreFilter(); schedule(); }
  searchBox.removeEventListener('input',coreFilter);
  applyFilters=filterAndUpdate;
  searchBox.addEventListener('input',filterAndUpdate);
  toolbar.addEventListener('input',()=>schedule());
  toolbar.addEventListener('change',event=>schedule(event.target===jumpBox,event.target===jumpBox));
  window.addEventListener('popstate',()=>schedule(true,true));
  window.addEventListener('hashchange',()=>{schedule(true,true); if(mobile.matches && byId.has(location.hash.slice(1))) sidebar.open=false;});
  // All original comparison text remains searchable, including inactive tabs.
  haystacks.splice(0,haystacks.length,...cards.map(card=>card.textContent.toLocaleLowerCase()));
  const q=new URLSearchParams(location.search).get('q'); if(q) searchBox.value=q;
  searchBox.addEventListener('input',()=> {
    const url=new URL(location.href); const q=searchBox.value.trim();
    if(q) url.searchParams.set('q',q); else url.searchParams.delete('q');
    history.replaceState(null,'',url);
  });
  window.addEventListener('popstate',()=> {searchBox.value=new URLSearchParams(location.search).get('q')||''; filterAndUpdate();});
  function updateOffsets() {
    const height=window.matchMedia('(max-width:700px)').matches?0:Math.ceil(toolbar.getBoundingClientRect().height);
    document.documentElement.style.setProperty('--reader-top',(height+12)+'px');
    cards.forEach(card=>{card.style.scrollMarginTop=(height+12)+'px';});
  }
  document.documentElement.dataset.spellReader='1';
  document.body.classList.add('reader-ready');
  updateOffsets();
  if('ResizeObserver' in window) new ResizeObserver(updateOffsets).observe(toolbar);
  else window.addEventListener('resize',updateOffsets);
  filterAndUpdate();
  requestAnimationFrame(()=>{ if(byId.has(location.hash.slice(1)) && active) active.card.scrollIntoView({block:'start',behavior:'auto'}); });
})();
