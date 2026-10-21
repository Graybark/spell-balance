# Spellwright — Repository Instructions

## Scope and privacy
- This repository publishes the Spellwright D&D spell reference and house-rule material only.
- Never add or publish private Doldrum campaign notes, session recaps, characters, secrets, or other campaign assets here.
- Keep the separate `Graybark/Doldrum` repository private. Do not change its visibility or copy its unrelated contents into this repository.

## Preserve the existing site
- The published site is a lightweight, primarily single-file HTML app: `index.html`, with `favicon.svg` as a root asset.
- Prefer targeted edits over a rebuild or framework migration.
- Unless explicitly requested, preserve spell text, spell IDs and anchors, filters and URL parameters, search, tabs, class/category/level behavior, responsive/mobile layout, school icons, header, favicon, and saved UI state.
- Do not remove, rename, or duplicate existing entries or assets as a side effect of an unrelated change.
- Keep any displayed counts and filters consistent with the actual data.

## Rules, balance notes, and sources
- Clearly distinguish official rules text, official errata, community discussion, and house-rule text.
- Do not describe a house rule as “approved,” “adopted,” or official unless that status is explicitly established and the wording is appropriate for the public audience. Prefer neutral descriptions such as “House rule” or “This version changes…”.
- A community discussion tag indicates that a spell is discussed, not that there is consensus or that the campaign uses a proposed change.
- Do not invent mechanics or silently change a spell’s mechanics. Make mechanical changes only when explicitly requested by the user; preserve the intended wording and scope.
- When researching or adding claims about online discussion, verify the cited sources, link directly to relevant evidence, and accurately represent disagreement and uncertainty. Do not imply consensus from an individual comment.
- Keep 2014 and 2024 rules/version labels accurate. Check relevant official errata when a claim depends on the current rules text.

## Editing and validation
- Read the current file and inspect the relevant section before editing. Do not overwrite a large file with an empty or partial fetch result.
- Make the smallest change that satisfies the request; avoid unrelated formatting churn.
- After edits, validate HTML/JavaScript syntax where practical and check affected spell entries, filters, anchors, counts, and responsive behavior.
- If a change is intended for publication, verify the commit and GitHub Pages deployment rather than assuming that a successful write means the live site is updated.
- Report exactly which files changed, what was changed, and any checks that could not be completed. Mark uncertain details “To confirm.”
