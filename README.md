# Spell Balance

A static-first reference for the existing 2014/2024 spell catalog and approved house rules.

## Architecture

- `data/catalog.json`: the 391 original spell records, their edition text, source attribution, categories and discussion annotations. Original-body checksums make accidental edits fail the build.
- `data/house-rules.json`: the explicitly approved house-rule overrides. Each can use exact substitutions or a complete `body_override`; original edition text stays in the catalog. Optional `highlight_phrases` mark new rules in purple. Overrides are applied **during the build**, never by patching the page on load.
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

## URLs

Existing `#spell-*` anchors are preserved. Filters use `q`, `class`, `level`, `label` and `rules=official`; class-table selection uses `caster`. Invalid filter values clear safely. The legacy `label=balance` parameter shows all categories. House-rule mode is the default.

## Publication

GitHub Pages continues to build from `main` / root. `_config.yml` excludes development sources from the published site; the published page uses only the generated HTML and required browser assets. No change to Pages source settings is required.
