/* Spell Balance house rules. Official edition text stays in index.html unchanged.
 * Edit only the overrides below to change a custom spell version.
 * Non-Wizard preparation is derived from each row's nine base-slot cells.
 */
(() => {
  'use strict';
  const overrides = [
    { id: 'spell-fireball', level: 3,
      summary: 'Base damage: 8d6 → 6d6. The +1d6 increase per higher-level slot is unchanged.',
      replacements: [['taking 8d6 Fire damage', 'taking 6d6 Fire damage']] },
    { id: 'spell-forcecage', level: 9,
      summary: 'Spell level: 7 → 9. All other effects and requirements are unchanged.',
      replacements: [] },
    { id: 'spell-melf-s-acid-arrow', level: 1,
      summary: 'Spell level: 2 → 1. Base damage is unchanged; upcasting now scales from level 1.',
      replacements: [['for each spell slot level above 2.', 'for each spell slot level above 1.']] },
    { id: 'spell-wall-of-force', level: 7,
      summary: 'Spell level: 5 → 7. All other effects and requirements are unchanged.',
      replacements: [] }
  ];
  const prepareClasses = ['bard', 'cleric', 'druid', 'sorcerer'];
  const require = (condition, message) => { if (!condition) throw new Error('House rules: ' + message); };
  require(!document.getElementById('house-rules-toggle'), 'already initialized');
  require(typeof applyFilters === 'function' && typeof haystacks !== 'undefined', 'spell filters are unavailable');
  const levelControl = document.getElementById('level');
  const categoryControl = document.getElementById('label');
  const jumpControl = document.getElementById('jump');
  const count = document.getElementById('visible-count');
  require(levelControl && categoryControl && jumpControl && count, 'missing page controls');

  // Validate all source nodes and replacements before changing the page.
  const plans = overrides.map(rule => {
    const card = document.getElementById(rule.id);
    const original = card && card.querySelector('.version-2024');
    require(original && card.querySelector('.spell-heading'), 'missing original for ' + rule.id);
    const custom = original.cloneNode(true);
    const text = custom.querySelector('.spell-text-2024');
    require(text && custom.querySelector('.spell-type'), 'missing spell text for ' + rule.id);
    for (const [before, after] of rule.replacements) {
      require(text.innerHTML.split(before).length === 2, 'ambiguous text replacement for ' + rule.id);
      text.innerHTML = text.innerHTML.replace(before, after);
    }
    const officialLevel = card.dataset.level;
    require(/^\d$/.test(officialLevel), 'invalid source level for ' + rule.id);
    custom.classList.remove('version-2024');
    custom.classList.add('version-house');
    custom.setAttribute('aria-label', card.querySelector('h2').textContent + ' house-rule version');
    custom.querySelector('.edition').textContent = 'House Rule';
    custom.querySelector('.edition-note').textContent = 'Based on 2024';
    custom.querySelector('.spell-type').textContent = custom.querySelector('.spell-type').textContent.replace(/^Level \d+/, 'Level ' + rule.level);
    text.classList.remove('spell-text-2024');
    text.classList.add('spell-text-house');
    const change = document.createElement('p');
    change.className = 'house-change';
    change.textContent = rule.summary;
    custom.querySelector('.version-head').after(change);
    return { rule, card, custom, officialLevel, officialEyebrow: card.querySelector('.spell-heading .eyebrow').textContent };
  });
  const preparation = prepareClasses.flatMap(caster => {
    const table = document.querySelector('.slot-table[data-caster="' + caster + '"]');
    require(table && table.tBodies[0].rows.length === 20, 'missing class rows for ' + caster);
    return [...table.tBodies[0].rows].map(row => {
      const cells = [...row.cells];
      const slotCells = cells.slice(-9);
      require(cells.length === 15 && slotCells.every(cell => /^(?:\d+|–)$/.test(cell.textContent.trim())), 'invalid slot cells for ' + caster);
      const total = slotCells.reduce((sum, cell) => sum + (Number(cell.textContent.trim()) || 0), 0);
      return { cell: cells[cells.length - 10], total };
    });
  });

  // Keep the optional layer self-contained; no external libraries are needed.
  const style = document.createElement('style');
  style.id = 'house-rules-styles';
  style.textContent = `
    .rules-controls { display:flex; flex-direction:column; align-items:flex-start; gap:6px; padding-bottom:3px; }
    .house-rules-control { display:flex; align-items:center; gap:7px; color:#285746; font-size:.84rem; font-weight:600; white-space:nowrap; cursor:pointer; }
    .house-rules-control input { width:16px; height:16px; margin:0; accent-color:#326d58; }
    .house-rules-control input:focus-visible { outline:2px solid #477dae; outline-offset:3px; }
    .rules-controls .visible-count { padding:0; font-size:.8rem; }
    .tag-house-rule { color:#285746; background:#dfefe7; }
    .version-house { background:#f2f8f5; border-top:3px solid #4d8a71; }
    .version-house .edition { color:#285746; }
    .version-house .metadata { grid-template-columns:repeat(4,minmax(0,1fr)); }
    .house-change { margin:0 0 17px; font-size:.86rem; color:#345f4f; }
    .spell-text-house { white-space:normal; }
    .spell-text-house p { margin:0 0 .72em; }
    .spell-text-house p:last-child { margin-bottom:0; }
    .official-comparison { border-top:1px solid var(--line); }
    .official-comparison > summary { padding:11px 24px; background:#f7f9fc; color:#52637e; font-size:.86rem; font-weight:600; cursor:pointer; }
    .official-comparison > summary:focus-visible { outline:3px solid #739be0; outline-offset:-3px; }
    .official-comparison[open] > summary { border-bottom:1px solid var(--line); }
    .version-house[hidden], .official-comparison > summary[hidden] { display:none !important; }
    .rules-counter { border-color:#82aa99; }
    @media(max-width:960px) { .version-house .metadata { grid-template-columns:repeat(2,minmax(0,1fr)); } .rules-controls { flex-direction:row; align-items:center; gap:14px; grid-column:1/-1; flex-wrap:wrap; } }
    @media(max-width:560px) { .official-comparison > summary { padding:10px 16px; } }
    @media print { .version-house { border-top-color:#777; } .official-comparison:not([open]) { display:none; } }
  `;
  document.head.append(style);
  for (const { cell, total } of preparation) {
    cell.textContent = total;
    cell.title = 'Prepared spells equal this level’s total base spell slots.';
  }
  for (const caster of prepareClasses) {
    const header = document.querySelector('.slot-table[data-caster="' + caster + '"] thead tr:last-child').cells[5];
    header.title = 'Prepared spells equal the total base spell slots at each class level.';
  }

  for (const plan of plans) {
    const { rule, card, custom, officialLevel } = plan;
    card.classList.add('has-house-rule');
    card.dataset.officialLevel = officialLevel;
    card.dataset.houseLevel = rule.level;
    card.dataset.categories += ' house-rule';
    const badge = document.createElement('span');
    badge.className = 'tag tag-house-rule';
    badge.textContent = 'House Rule';
    card.querySelector('.heading-tags').prepend(badge);
    const reference = document.createElement('details');
    reference.className = 'official-comparison';
    const summary = document.createElement('summary');
    summary.textContent = 'Compare original 2014 & 2024';
    reference.append(summary);
    // Move, rather than rewrite, original edition text and sourced discussion notes.
    const heading = card.querySelector('.spell-heading');
    while (heading.nextSibling) reference.append(heading.nextSibling);
    card.append(custom, reference);
    Object.assign(plan, { reference, summary, badge, comparisonOpen: false });
  }
  const option = document.createElement('option');
  option.value = 'house-rule';
  option.textContent = 'House Rule';
  categoryControl.options[0].after(option);
  const counter = document.createElement('span');
  counter.className = 'count rules-counter';
  const total = document.createElement('strong');
  total.textContent = plans.length;
  counter.append(total, ' house rules');
  document.querySelector('.counts').append(counter);
  document.querySelector('.hero p').textContent = 'Full 2014 and 2024 spell text, with house-rule versions for changed spells. Use the controls to find a spell and compare its versions.';

  const controls = document.createElement('div');
  controls.className = 'rules-controls';
  const toggleLabel = document.createElement('label');
  toggleLabel.className = 'house-rules-control';
  toggleLabel.title = 'Show house-rule spell versions and use their levels in the filter. Class tables are independent of this switch.';
  const toggle = document.createElement('input');
  toggle.type = 'checkbox';
  toggle.id = 'house-rules-toggle';
  const toggleText = document.createElement('span');
  toggleText.textContent = 'House-rule spells';
  toggleLabel.append(toggle, toggleText);
  count.before(controls);
  controls.append(toggleLabel, count);
  const levelLabel = document.querySelector('label[for="level"]');
  let houseMode;
  function setSpellMode(enabled) {
    if (houseMode !== enabled) {
      for (const plan of plans) {
        const { rule, card, custom, officialLevel, reference, summary, badge } = plan;
        if (!enabled && houseMode === true) plan.comparisonOpen = reference.open;
        card.dataset.level = enabled ? String(rule.level) : officialLevel;
        card.querySelector('.spell-heading .eyebrow').textContent = enabled
          ? plan.officialEyebrow.replace(/^Level \d+/, 'Level ' + rule.level) : plan.officialEyebrow;
        custom.hidden = !enabled;
        summary.hidden = !enabled;
        reference.open = enabled ? plan.comparisonOpen : true;
        badge.textContent = enabled ? 'House Rule' : 'House Rule available';
      }
      houseMode = enabled;
    }
    toggle.checked = enabled;
    levelLabel.textContent = enabled ? 'Level (house rules)' : 'Level (2024)';
    // Original text remains searchable, as it is in the existing edition comparison.
    haystacks.splice(0, haystacks.length, ...cards.map(card => card.textContent.toLocaleLowerCase()));
    applyFilters();
  }
  function restoreFilters() {
    const params = new URLSearchParams(window.location.search);
    for (const [key, control] of [['level', levelControl], ['label', categoryControl]]) {
      const value = params.get(key) || '';
      control.value = [...control.options].some(item => item.value === value) ? value : '';
    }
    setSpellMode(params.get('rules') !== 'official');
  }
  toggle.addEventListener('change', () => {
    const url = new URL(window.location.href);
    if (toggle.checked) url.searchParams.delete('rules');
    else url.searchParams.set('rules', 'official');
    history.replaceState(null, '', url);
    setSpellMode(toggle.checked);
  });
  jumpControl.addEventListener('change', () => {
    if (!jumpControl.value) return;
    // The original jump clears filters; retain this new mode and the active class.
    const url = new URL(window.location.href);
    if (!houseMode) url.searchParams.set('rules', 'official');
    const caster = document.querySelector('.slot-tab[aria-selected="true"]');
    if (caster && caster.dataset.caster !== 'wizard') url.searchParams.set('caster', caster.dataset.caster);
    history.replaceState(null, '', url);
  });
  window.addEventListener('popstate', restoreFilters);
  restoreFilters();
  // Account for the toolbar's added switch when navigating to spell anchors.
  const toolbar = document.querySelector('.toolbar');
  const setSpellScrollOffset = () => {
    const offset = Math.ceil(toolbar.getBoundingClientRect().height) + 16 + 'px';
    cards.forEach(card => { card.style.scrollMarginTop = offset; });
  };
  setSpellScrollOffset();
  if ('ResizeObserver' in window) new ResizeObserver(setSpellScrollOffset).observe(toolbar);
  else window.addEventListener('resize', setSpellScrollOffset);
  const anchoredSpell = document.getElementById(window.location.hash.slice(1));
  if (anchoredSpell && anchoredSpell.classList.contains('spell-card') && !anchoredSpell.hidden) {
    requestAnimationFrame(() => anchoredSpell.scrollIntoView({ block: 'start' }));
  }
})();

/* Class filtering uses the 2024 class lists already printed in the document.
 * It is independent of the full-caster table tabs (?caster=) and combines with
 * the existing text, level, category, and house-rule spell controls.
 */
(() => {
  'use strict';
  if (document.getElementById('spell-class')) return;
  const searchControl = document.getElementById('search');
  const jumpControl = document.getElementById('jump');
  const toolbar = document.querySelector('.toolbar-inner');
  if (!searchControl || !jumpControl || !toolbar || typeof applyFilters !== 'function') {
    throw new Error('Class filter: missing existing spell controls.');
  }

  // Normalize two transcription variants for matching only. Do not alter the
  // visible original text: Locate Object has "Wiza rd"; Mind Sliver "VVizard".
  const normalizeClass = name => name.trim().toLowerCase().replace(/\s+/g, '').replace(/^vvizard$/, 'wizard');
  const membership = new Map(cards.map(card => {
    const source = card.querySelector('.version-2024 .classes');
    if (!source || !source.textContent.trim()) throw new Error('Class filter: missing class list for ' + card.id);
    return [card, new Set(source.textContent.split(',').map(normalizeClass).filter(Boolean))];
  }));
  const classIds = [...new Set([...membership.values()].flatMap(names => [...names]))].sort();
  const control = document.createElement('div');
  control.className = 'control class-filter-control';
  const label = document.createElement('label');
  label.htmlFor = 'spell-class';
  label.textContent = 'Class';
  const select = document.createElement('select');
  select.id = 'spell-class';
  select.title = 'Uses the class lists shown in the 2024 spell entries; subclass and other bonus spell access are not added.';
  select.add(new Option('All classes', ''));
  classIds.forEach(id => select.add(new Option(id[0].toUpperCase() + id.slice(1), id)));
  control.append(label, select);
  searchControl.closest('.control').after(control);

  const style = document.createElement('style');
  style.id = 'class-filter-styles';
  style.textContent = `
    .toolbar-inner { grid-template-columns:minmax(180px,1.4fr) minmax(110px,.85fr) minmax(140px,.95fr) minmax(120px,.9fr) minmax(150px,1.15fr) auto; }
    .toolbar-inner .control { min-width:0; }
    @media(max-width:1120px) { .toolbar-inner { grid-template-columns:repeat(3,minmax(0,1fr)); } .toolbar-inner .rules-controls { grid-column:auto; flex-direction:column; align-items:flex-start; gap:4px; } }
    @media(max-width:700px) { .toolbar-inner { grid-template-columns:repeat(2,minmax(0,1fr)); } }
  `;
  document.head.append(style);

  // Retain the existing filtering logic, then intersect with the selected
  // class. Rebind the one listener that held the old function by reference.
  const applyExistingFilters = applyFilters;
  function applyCombinedFilters() {
    applyExistingFilters();
    let shown = 0;
    cards.forEach(card => {
      if (select.value && !membership.get(card).has(select.value)) card.hidden = true;
      if (!card.hidden) shown++;
    });
    document.getElementById('visible-count').textContent = `${shown} shown`;
    document.getElementById('empty').style.display = shown ? 'none' : 'block';
  }
  searchControl.removeEventListener('input', applyExistingFilters);
  applyFilters = applyCombinedFilters;
  searchControl.addEventListener('input', applyCombinedFilters);
  select.addEventListener('change', () => {
    const url = new URL(window.location.href);
    if (select.value) url.searchParams.set('class', select.value);
    else url.searchParams.delete('class');
    history.replaceState(null, '', url);
    applyCombinedFilters();
  });
  function restoreClassFilter() {
    const requested = normalizeClass(new URLSearchParams(window.location.search).get('class') || '');
    select.value = classIds.includes(requested) ? requested : '';
    applyCombinedFilters();
  }
  // "Jump to spell" already clears search/category/level; clear Class before
  // that handler runs so even an off-list target is visible when scrolled to.
  jumpControl.addEventListener('change', () => {
    if (!jumpControl.value || !document.getElementById(jumpControl.value)) return;
    select.value = '';
    const url = new URL(window.location.href);
    url.searchParams.delete('class');
    history.replaceState(null, '', url);
  }, true);
  window.addEventListener('popstate', restoreClassFilter);
  restoreClassFilter();
})();

/* Wizard preparation and class-list placement approved 17 October 2026.
 * Levels 1-13 are unchanged; the later progression finishes at 22.
 * Keep the existing class-list nodes/text intact for edition accuracy and filtering.
 */
(() => {
  'use strict';
  const wizardPrepared = [4,5,6,7,9,10,11,12,14,15,16,16,17,17,18,18,19,20,21,22];
  const table = document.querySelector('.slot-table[data-caster="wizard"]');
  if (!table || table.tBodies[0].rows.length !== wizardPrepared.length) {
    throw new Error('Wizard preparation: expected 20 class-table rows.');
  }
  const rows = [...table.tBodies[0].rows];
  if (!rows.every(row => row.cells.length === 14)) {
    throw new Error('Wizard preparation: unexpected class-table columns.');
  }
  rows.forEach((row, i) => {
    const cell = row.cells[row.cells.length - 10];
    cell.textContent = wizardPrepared[i];
    cell.title = 'Wizard prepared-spell progression; 22 at class level 20.';
  });

  const style = document.createElement('style');
  style.id = 'spell-availability-styles';
  style.textContent = `
    .spell-availability { display:flex; flex-wrap:wrap; align-items:baseline; gap:5px 9px; margin-top:20px; padding-top:11px; border-top:1px solid var(--line,#d6deeb); font: .8rem/1.5 system-ui,sans-serif; }
    .spell-availability-label { font-weight:600; color:#43536a; }
    .spell-availability > .classes { margin:0; color:#5f6e86; overflow-wrap:anywhere; }
    @media print { .spell-availability { break-inside:avoid; } }
  `;
  document.head.append(style);
  document.querySelectorAll('.version > .classes').forEach(classList => {
    const version = classList.parentElement;
    const footer = document.createElement('footer');
    footer.className = 'spell-availability';
    footer.setAttribute('aria-label', 'Spell class availability');
    const label = document.createElement('span');
    label.className = 'spell-availability-label';
    label.textContent = 'Available for:';
    footer.append(label, classList);
    version.append(footer);
  });
  // Moving the same nodes preserves the class filter's membership map.
  // Refresh text-search order after placing availability after the rules text.
  haystacks.splice(0, haystacks.length, ...cards.map(card => card.textContent.toLocaleLowerCase()));
  applyFilters();
})();
