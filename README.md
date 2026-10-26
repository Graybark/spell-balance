# Spell Balance

A static-first reference for the existing 2014/2024 spell catalog and house rules.

## Architecture

- `data/catalog.json`: the 391 original spell records, their edition text, source attribution, categories and discussion annotations. Original-body checksums make accidental edits fail the build.
- `data/house-rules.json`: the five house-rule overrides. Each can use exact substitutions or a complete `body_override`; original edition text stays in the catalog. Optional `highlight_phrases` mark new rules in purple. Overrides are applied **during the build**, never by patching the page on load.
- `data/classes.json`: the shared revised slot progression and each class's features, resources, cantrips and prepared-spell counts. These are rendered into HTML during the build.
- `tools/build.py`: deterministic HTML generation. `src/app.css` is the single stylesheet; `src/app.js` contains only interaction logic.
- `index.html` (or `Spell Balance.html` in the private mirror): the complete generated page. The new header, all spell versions and all class rows exist before JavaScript executes.
- `assets/app.<hash>.css` and `.js`: content-addressed assets. CSS is linked directly in the document head; one deferred script handles filters and navigation. There is no runtime loader, layout reconstruction, injected stylesheet or full-page loading mask.

The d20 is the site brand and favicon. School artwork is used only for spell cards and sidebar entries. School names in the metadata grid remain text-only.

Native radio-based section controls are styled as tabs and remain usable by keyboard, even without JavaScript. Sidebar fragment links and class tables remain usable when scripts are disabled or fail to download. Search/filter controls enable when their script is ready. A tiny head script restores only the URL's official/house-rule display state before paint; it does not construct or replace any UI.

## Edit and build

Use Python 3.11 or newer:

```sh
python -m pip install -r requirements-build.txt
python tools/build.py
python tools/verify.py
python tools/build.py --check
```

In the private mirror, use `--output "Spell Balance.html"` for the build and pass `"Spell Balance.html"` to `tools/verify.py`.

For browser regressions:

```sh
python -m pip install -r requirements-test.txt
python -m playwright install chromium
python tools/browser_test.py
```

The browser tests serve the generated page over HTTP and cover delayed script loading, disabled scripts, script download failure, first-render header stability, native tabs, filters, browser history, school artwork, class values and responsive widths. Do not approve a release based only on its final screenshot.

Commit the edited sources **and regenerated HTML/assets together**. Validation fails when generated files are stale. Keep the public reference and private reference folder synchronized. Do not add unrelated campaign content to this repository.

## Condition references

`data/conditions.json` stores complete, edition-specific effects for all 15 conditions, with one item per original effect. The 2024 definitions retain their bold effect headings; the 2014 definitions retain their original lists and the six-level Exhaustion table. Definitions were checked against Roll20 on 2026-10-24. Each entry retains its source URL as metadata. The condition text is SRD material; see [Rules attribution](attribution.html).

The build decorates exact, case-insensitive condition words only inside spell text and associated creature stat blocks, including comparisons and house-rule replacements. Capitalized 2024 Invisible references also work for magical objects. Original catalog wording, checksums, paragraphs, formatting, links, discussions, and class tables stay intact.

One shared desktop popover stays open over the word or preview and scrolls when necessary. Its complete definition has no external “read full rules” link. Keyboard focus opens it; Arrow Down focuses the scrollable popover, Enter opens the dialog, and Escape dismisses it. Click or touch opens one native modal dialog (a bottom sheet on narrow screens) with focus containment, close button, backdrop dismissal, Escape, and focus return. Navigation, filters, and edition changes dismiss stale references. All definitions are local assets; no hover/tap fetches are needed. Without JavaScript, the original condition anchors retain their Roll20 fallback.

`tools/conditions_test.py` checks all 30 edition entries for the original effect counts, bold headings, the 2014 Exhaustion table, absence of popup source links, text/HTML preservation, scope and exact matching, edition-specific content, hover traversal and viewport boundaries, keyboard behavior, touch dismissal and focus, scrolling, navigation cleanup, and no-script fallback. Discussion tests also verify that Mordenkainen’s Sword appears under the Buff filter on desktop and mobile.

## Magic items

The header's Magic Items section is independent of spells and class tables. `data/magic-items.json` contains the union of Roll20's 2024 Free Basic Rules and 2024 Dungeon Master's Guide A–Z indexes, including templates and named variants. Source keys in the coverage manifest make omissions and duplicate records fail validation.

Full descriptions are imported only from Free Basic Rules (2024), preserving paragraphs, emphasis, lists and tables. Other variants can use the matching openly licensed family description and are identified as variants. Entries outside that corpus retain factual metadata and their Roll20 reference; proprietary descriptions are not copied. Unknown source metadata is marked “Not listed.” The original spell catalog and five house rules are unchanged.

`tools/import_magic_items.py` explicitly refreshes the catalog from its two source indexes. This is an editorial maintenance step, not part of a normal build. It checks edition/title, sanitization, readable text, paragraph/table counts, IDs, coverage, and per-description checksums. `tools/magic_items.py` renders every entry before JavaScript. Shared family descriptions are stored once in the source data.

The reader supports search, type, rarity, attunement, jump controls, history and direct `#item-*` links. Item URL filters are `itemq`, `itemtype`, `rarity` and `attuned`; spell filters keep their existing parameters. Condition references reuse the edition-aware popover and touch dialog. Native item list links and descriptions remain usable without JavaScript. `tools/magic_items_test.py` verifies coverage, source text/structure, independent reader state, keyboard/touch interactions, narrow tables and native fallbacks.

## URLs

Existing `#spell-*` anchors are preserved. Filters use `q`, `class`, `level`, `label` and `rules=official`; class-table selection uses `caster`. Invalid filter values clear safely. The legacy `label=balance` parameter shows all categories. House-rule mode is the default.

## Publication

GitHub Pages continues to build from `main` / root. `_config.yml` excludes development sources from the published site; the published page uses only the generated HTML and required browser assets. No change to Pages source settings is required.
