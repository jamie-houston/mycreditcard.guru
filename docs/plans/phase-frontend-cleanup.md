# Frontend Cleanup — Dedup + JS Extraction

Status: **Phases 1–3 done (2026-07-19).** Phase 4 (full inline-`<script>`
extraction into `static/js/pages/*.js`) not started — pick up here later.

## Context

`docs/refactoring.md` flags that templates carry "a ton of js and css... probably
duplicated," asks for duplicate HTML to be extracted, and asks for a CSS
framework recommendation. A codebase survey (Explore agents, 2026-07-18)
confirmed this: templates total ~9,186 lines across 18 files, with the biggest
ones being 71–91% inline `<script>` (`profile.html` 91%, `base.html` 83%,
`index.html` 79%). No build step exists (no npm/webpack) — everything is plain
static files served by Django. Concrete duplication was found and verified by
direct `diff`:

- **Byte-identical HTML**: the `#cardOwnershipModal` markup
  (`index.html:1826-1885` / `cards_list.html:980-1039`) and the profile stat
  grid (`profile.html:63-80` / `shared_profile.html:35-52`) — confirmed via
  `diff`, zero differences.
- **Duplicated JS utilities**: `getCookie` (4 copies), `showNotification` (3
  copies, one diverged), `escapeHtml`/`_roadmapEscapeHtml` (2 names, same
  behavior), `showError` (2 copies), `loadUserCards` (4 near-identical bodies).
- **A live, shipping bug**: `toggleCardOwnership` is defined 3 times
  (`base.html:1086`, `category_detail.html:269`, `index.html:1493`). Verified
  by tracing script placement: `base.html`'s own `<script>` (lines 331–1930)
  sits *after* `{% block content %}` (line 98), so it always executes last and
  always wins — deterministically, on every page. That means
  `category_detail.html`'s version (which re-filters the visible card list
  after a toggle) never runs today; clicking the ownership button on
  `/categories/<slug>/` toggles ownership but the list doesn't refresh until
  reload. Verified `toggleCardOwnership(` has exactly one call site in the
  whole repo (`category_detail.html:251`) — `index.html`'s own copy, plus its
  three helpers `showCardDetailsPopupRoadmap`/`closeCardDetailsPopupRoadmap`/
  `saveCardDetailsPopupRoadmap` (~1493–1620), are entirely unreachable dead
  code from an earlier UX design (the roadmap page's real "I have this card"
  flow goes through the unrelated `openCardOwnershipModal`).

Scope chosen by Jamie (2026-07-18): **"Dedup + full JS extraction"** —
consolidate duplicates, fix the shadowing bug, extract the byte-identical HTML
into `{% include %}` partials, AND move the large inline `<script>` blocks out
of templates into `static/js/pages/*.js`. CSS reorg and CSS-framework adoption
are explicitly **out of scope** — recommendation only (see bottom), no files
touched for those.

This is a production app with real users and no frontend test framework by
design (`docs/README_TESTING.md`) — the only automated check that touches any
of this is `node scripts/test_roadmap_results.js` (a framework-free Node smoke
test over the pure/DOM-free helpers in `static/js/roadmap-results.js`).
Everything else needs manual browser verification; Jamie runs the dev server
himself (CLAUDE.md: "Don't start runserver for Jamie"), so each phase ends
with a specific manual smoke-test checklist for him to run.

Ordering goes lowest-risk → highest-risk: pure utility dedup first, then the
small isolated bug fix, then HTML-only partial extraction, then the large
mechanical script-extraction pass last, one template at a time.

## Work

### Phase 1 — Extract shared JS utilities into `static/js/utils.js` (done)

**New file** `static/js/utils.js` (plain global-scope functions, matching the
existing style of `static/js/card-search.js` — no ES module syntax):
- `escapeHtml(str)` — canonical body from `base.html:338`.
- `getCookie(name)` — canonical body from `base.html:348`.
- `showNotification(message, type = 'info')` — canonical body: the
  byte-identical 3s/`cssText` version from `cards_list.html:770` /
  `profile.html:1371` (**not** `index.html:1792`'s diverged 4s/animated
  version — see tradeoff note below).
- `showError(message)` — canonical body from `profile.html:1269` /
  `shared_profile.html:304` (byte-identical).
- `loadOwnedCardIds()` — new pure helper
  (`async () => new Set(await UserDataManager.getCards())`), extracted from
  the shared core of the 4 `loadUserCards()` copies.

**Load order**: add
`<script src="{% static 'js/utils.js' %}"></script>` in `base.html`'s
`<head>`, right after the existing `const API_BASE = '/api';` script (before
line 98's `{% block content %}`). This guarantees the functions exist before
any page script runs — stricter and safer than `card-search.js`'s late
placement near line 1932.

**Remove local copies, call the global instead:**
- `base.html`: delete local `escapeHtml` (338), `getCookie` (348).
- `cards_list.html`: delete local `getCookie` (801), `showNotification`
  (770); reduce `loadUserCards()` (238) to a thin wrapper around
  `loadOwnedCardIds()`.
- `profile.html`: delete local `getCookie` (1400), `showNotification` (1371),
  `showError` (1269).
- `index.html`: delete local `getCookie` (1380), `showNotification` (1792)
  **and** its now-orphaned `@keyframes slideIn`/`slideOut` (~2027–2035,
  confirm no other referrers before deleting).
- `shared_profile.html`: delete local `showError` (304).
- `categories_list.html`, `category_detail.html`, `issuers_list.html`: reduce
  each `loadUserCards()` (127, 115, 60) to a thin wrapper around
  `loadOwnedCardIds()`.
- `static/js/roadmap-results.js`: delete local `_roadmapEscapeHtml` (24–31),
  replace all ~12 call sites with `escapeHtml(...)`; add `escapeHtml` to the
  header comment's list of base.html-provided globals (alongside the
  already-documented `getCookie()`/`showNotification()`).

**Known tradeoff (flag to Jamie, don't silently decide)**: `index.html`'s
notification loses its slide-in animation since the canonical version is the
plain 3s variant already used by 2 of 3 pages. Cheap to re-add via CSS in a
future pass; out of scope here since it requires touching `index.html`'s
`<style>` block.

**Required test-harness update**: `scripts/test_roadmap_results.js` currently
loads only `roadmap-results.js` into its `vm` sandbox and destructures
`_roadmapEscapeHtml`. Update it to also load `static/js/utils.js` into the
same sandbox (before `roadmap-results.js`), and swap the
destructure/assertions to `escapeHtml`. Without this the smoke test breaks as
soon as `_roadmapEscapeHtml` is deleted.

**Verify:**
1. `node scripts/test_roadmap_results.js` passes.
2. Manual: `/roadmap/` — generate a roadmap, confirm an entity name with an
   apostrophe still escapes correctly in the "as {name}" label. `/cards/` and
   `/profile/` — trigger a notification/error toast, confirm it still appears
   and clears. `/categories/`, `/cards/` — confirm the ownership filter still
   correctly reflects owned cards after page load.

### Phase 2 — Fix the `toggleCardOwnership` shadowing bug (done)

**`index.html`**: delete the entire dead cluster — `toggleCardOwnership`
(1493), `showCardDetailsPopupRoadmap`, `closeCardDetailsPopupRoadmap`,
`saveCardDetailsPopupRoadmap` (~1493–1620). Confirmed via grep: no call sites
anywhere for any of these four names except internal calls within the dead
cluster itself.

**`base.html`**: in the canonical `toggleCardOwnership` (1086), add an
extensibility hook after the existing `updateButtonState(button, hasCard);`
call:
```js
if (typeof window.onCardOwnershipToggled === 'function') {
    window.onCardOwnershipToggled(cardId, hasCard);
}
```

**`category_detail.html`**: delete the shadowed local `toggleCardOwnership`
(269). Near `let userCards = new Set();` (73), add:
```js
window.onCardOwnershipToggled = function(cardId, hasCard) {
    if (hasCard) userCards.add(cardId); else userCards.delete(cardId);
    filterCards();
};
```
This restores the lost refresh behavior while reusing base.html's fuller
implementation (optimistic update + API sync + revert-on-failure). Note:
button text on this page will now read base.html's longer copy ("I have this
card" vs. the shorter "I have this") — this is not a new change, base.html's
text already silently wins in production today.

**Verify:**
1. `node scripts/test_roadmap_results.js` still passes (unaffected, sanity
   check).
2. Manual: `/categories/<slug>/` — click the ownership toggle, confirm the
   button updates AND the list re-filters immediately if a filter is active
   (the actual bug fix), reload and confirm it persisted. `/roadmap/` — run
   the full "I have this card" modal flow end to end (unrelated code path,
   proves the dead-code deletion didn't remove anything live). Check devtools
   console on both pages for errors.

### Phase 3 — Extract duplicated HTML into `{% include %}` partials (done)

**New file** `templates/partials/card_ownership_modal.html` — the verified
byte-identical 60-line `<div id="cardOwnershipModal">` block. Replace it in
both `index.html` (1826-1885) and `cards_list.html` (980-1039) with
`{% include 'partials/card_ownership_modal.html' %}`. The two divergent
`<style>` blocks immediately following (index.html uses `position: fixed`,
cards_list.html uses `position: absolute` — incompatible strategies) **stay in
place, untouched** — reconciling them is CSS reorg, out of scope.

**New file** `templates/partials/profile_stat_grid.html` — the verified
byte-identical 18-line stat grid. Replace it in `profile.html` (63-80) and
`shared_profile.html` (35-52) with
`{% include 'partials/profile_stat_grid.html' %}`.

**Trivial cosmetic fix while touching the modal**: standardize the "Local
Mode" badge to one style (cards_list.html's plain `#5C6675`, no emoji) since
the markup is now shared and can't carry two different inline styles.

**Verify:**
1. `node scripts/test_roadmap_results.js` passes.
2. `venv/bin/python manage.py test` — catches template-rendering errors (bad
   include path, 500s) that wouldn't otherwise be tested.
3. Manual: `/roadmap/` and `/cards/` — open the ownership modal on each,
   confirm all fields render, form still submits, and each page's own
   positioning/scroll behavior is visually unaffected. `/profile/` and a
   shared-profile URL — confirm the 4 stat tiles render correct numbers on
   both.

### Phase 4 — Extract inline `<script>` blocks into `static/js/pages/*.js` (not started)

Highest risk — **one template at a time**, smallest/simplest first, verified
independently before moving to the next, so a regression is attributable to a
single diff:

`issuers_list.html` → `category_detail.html` → `categories_list.html` →
`cards_list.html` → `profile.html` → `index.html` (largest, most stateful) →
`base.html`'s own giant script last (every page depends on it, so smoke-test
the whole app after this one sub-step).

Per template:
1. New file `static/js/pages/<page-name>.js` (naming mirrors the existing
   `static/css/pages/*.css` convention).
2. **Audit for top-level (non-function-wrapped) reads** of base.html-provided
   globals (`isAuthenticated`, `API_BASE`, `UserDataManager`, `LocalStorage`,
   `escapeHtml`, `getCookie`, `showNotification`) before moving — base.html
   declares these *after* `{% block content %}`, so a top-level synchronous
   read would break only if the extracted `<script src>` tag ends up in a
   different position than the original inline script. Keep the tag in the
   exact same position.
3. Move the script body verbatim; replace the inline block with
   `<script src="{% static 'js/pages/<page-name>.js' %}"></script>` in the
   same spot.
4. **Grep the block being moved for `{{` and `{%`** before extraction —
   Django template-tag/variable interpolation cannot survive being moved to a
   raw static file; convert any found instance to a
   `window.SOME_VAR = {{ value }};` snippet left inline in the template, set
   before the external script loads.
5. `index.html` special case: `CATEGORY_ICONS` (552) is read by
   `roadmap-results.js` via a `typeof CATEGORY_ICONS !== 'undefined'` guard,
   always inside function bodies (never top-level) — safe to move into
   `static/js/pages/roadmap.js` as long as script tag order is preserved
   (`roadmap-results.js` before `roadmap.js`, matching today's
   `index.html:209-210`).
6. Confirm `shared_roadmap.html` is untouched by this phase and does **not**
   start loading `pages/roadmap.js` — it's read-only and intentionally lacks
   `CATEGORY_ICONS`/`toggleSection`/etc.; it only needs `roadmap-results.js`,
   same as today.

**Verify per template** (give Jamie each checklist separately, one file at a
time):
- **issuers_list.html** (`/issuers/`): cards render, ownership filter works,
  console clean.
- **category_detail.html** (`/categories/<slug>/`): cards render with correct
  ownership, toggle re-verifies Phase 2's fix, console clean.
- **categories_list.html** (`/categories/`): every filter works,
  `resetFilters()` works, console clean.
- **cards_list.html** (`/cards/`): every filter works, ownership modal
  re-verifies Phase 3's shared partial, add-a-card flow works, console clean.
- **profile.html** (`/profile/`): stat grid populates (re-verifies Phase 3),
  card-search autocomplete still works alongside the new file, share-URL trio
  works, console clean.
- **index.html** (`/roadmap/`, do last, budget extra time): full roadmap
  generation, `CATEGORY_ICONS` render in category breakdowns, every
  collapsible section, ownership modal, share panel, page-reload "Current
  Roadmap" restore, console clean.
- **base.html** (if included in this pass): smoke-test every page in the app
  once, since this file is a dependency of literally all of them — landing,
  roadmap, profile, cards list, category detail, categories list, issuers
  list, shared profile, shared roadmap, help, resources, account pages.
- After the `index.html`/`roadmap.js` step specifically: re-run
  `node scripts/test_roadmap_results.js` (sanity check — it never depended on
  `index.html`, should be unaffected).

## Explicitly deferred (recommendation only, no files touched)

- **CSS framework adoption** (Tailwind/Bootstrap): not recommended as a
  migration target. The app already has a mature, working 1655-line custom
  design system (`static/css/base.css`) built on CSS custom properties, plus
  an established `static/css/pages/*.css` per-page pattern. Retrofitting
  Tailwind onto a coherent existing system is a full rewrite with real
  regression risk for a production app, for a payoff (utility classes vs.
  existing custom classes) that's mostly aesthetic preference, not a
  capability gap. If pursued later, do it incrementally per-page using the
  same `static/css/pages/*.css` boundaries this plan's Phase 4 uses for JS.
- **CSS reorg**: moving remaining inline `<style>` blocks (`index.html` ~148
  lines, `cards_list.html` ~179 lines) into their `static/css/pages/*.css`
  files, reconciling the `#cardOwnershipModal` positioning strategies onto
  base.css's existing unused generic `.modal` system (`base.css:1266-1471`),
  re-adding the dropped `slideIn`/`slideOut` keyframes, and merging
  `openCardOwnershipModal`/`closeCardOwnershipModal`/`saveCardOwnership` once
  the CSS strategies match. Good follow-up once this plan's phases land.
- **`filterCards()`/`displayCards()`** (cards_list vs category_detail) and
  **`showShareableUrl`/`showRoadmapShareableUrl`** trios (profile vs
  index.html): different-enough DOM/features that forcing a merge risks
  introducing the kind of behavior drift this plan is trying to remove. Left
  as a judgment call for whoever next touches those pages.
- **`resetFilters()`**: confirmed NOT a true duplicate (categories page has 5
  filter fields, cards page has 8, different IDs) — no action.

## Verification summary

- After every phase: `node scripts/test_roadmap_results.js` (the only
  automated frontend check).
- After Phase 3 specifically: also `venv/bin/python manage.py test` (catches
  template-rendering breakage from the new `{% include %}`s).
- Every phase ends with a manual browser checklist above — Jamie runs the dev
  server and walks through it himself.
