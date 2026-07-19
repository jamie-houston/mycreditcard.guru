# Project Status

Active work only. Completed phase history, design notes, and implementation
detail have been archived to mybrain — see the pointers at the bottom. Check
items off here as they land; when a phase's own detail doc is done, archive
it the same way and trim this file back down.

Last updated: 2026-07-19

## Phases (E–Q)

E–I planned in `.claude/plans/look-at-any-outstanding-wild-wirth.md`;
J–M planned in `.claude/plans/plan-out-the-following-sharded-nest.md`
(scoping decisions with Jamie, 2026-07-17); N–Q added 2026-07-18 from
Jamie's backlog. Phase N built ahead of M (2026-07-18, Jamie's call —
greenfield feature over a verify-and-document pass). Recommended order for
what's left: **O → P → Q** — O/P (spending-input modes) before Q (surfacing
existing credit math) since they touch the same builder UI.

### Completed

- [x] **Phase E** — Selection-aware bonus capacity & sequencing (2026-07-17).
- [x] **Phase F** — Ownership consolidation onto `cards/`, line-item polish (2026-07-17).
- [x] **Phase G** — Card data & ownership admin: `offer_type`, `bonus_override`, Renews column (2026-07-17).
- [x] **Phase H** — Sortable profile table + inline network marks on card thumbnails (2026-07-11).
- [x] **Phase J** — Points-program pooled valuation (2026-07-18).
- [x] **Phase K** — Multi-player households & per-entity eligibility rules (2026-07-18).
- [x] **Phase K follow-up** — Card ownership now defaults by card kind on
      add (business → the household's business entity, personal → the
      primary; `cards/views.py` `_resolve_owner_entity(profile, owner_id,
      card=None)`), mirroring the engine's existing
      `eligible_entity_for_card()` preference. The owner picker (edit modal
      `templates/base.html`, and the add/edit popup shared by
      `templates/cards_list.html` + `templates/index.html`'s
      `openCardOwnershipModal()`) now filters candidates to the card's own
      kind and only appears when there's more than one of that kind — no
      prompt for the common single-person/single-business case (2026-07-18).
- [x] **Phase I** — Roadmap analysis views: Cards × categories allocation
      matrix, first-year-vs-ongoing value panel, curated redemption
      guidance per card (2026-07-18).
- [x] **Phase L** — Benefit/credit usage tracking: Current period check-offs
      and expiring-soon grouping on profile and modal (2026-07-18).
- [x] **Phase N** — One-off upcoming-expense mode: "Best card for your
      purchase" panel, ranking new-card applies (lump-sum-aware signup-bonus
      reachability + category rate − fee) and the best already-owned card,
      independent of and alongside the regular monthly roadmap (2026-07-18).
- [x] **Help & Resources** — Created a user-friendly, Ledger-themed Help & Docs page, an external Resources page recommending high-quality points/rewards sites, and restored start page landing features grid for all users (2026-07-19).
- [x] **Phase M** — Verified max-cards-per-lifetime/per-issuer enforcement
      (2026-07-19). No code changes — closed as verify-and-document per
      Jamie's call. See below.
- [x] **Phase O** — Category-less "easy mode" spending (2026-07-19). Added builder toggle and Easy Mode input, scratch field in serializer, engine fallback mapping to uncategorized base rate.
- [x] **Phase P** — Surface cards that "pay for themselves" via recurring credits (2026-07-19). Added `pays_for_itself` flag in orchestrator/serializer when allocated credits value >= annual fee. Added client-side filter checkbox and sort selector in results UI with non-scrolling re-renders. Fixed pre-sort gap in `calculate_smart_card_value`.

Detail archived — see pointers under "Where everything else went."

### Open

### Technical Debt & Refactoring
- [x] **Global Tab Design Alignment** (2026-07-19). Aligned the tabs component styles across all pages with the clean, bottom-bordered style of the profile page and moved styling rules to `components.css`. Reordered and shortened top-level and results tabs on the roadmap page.
- [x] **Frontend cleanup — Phases 1–3** (dedup, bug fix, HTML partials;
      2026-07-19). `static/js/utils.js` now holds `escapeHtml`, `getCookie`,
      `showNotification`, `showError`, `loadOwnedCardIds` — removed from
      `base.html`, `cards_list.html`, `profile.html`, `index.html`,
      `shared_profile.html`; `categories_list.html`/`category_detail.html`/
      `issuers_list.html`'s `loadUserCards()` are now thin wrappers over
      `loadOwnedCardIds()`. `roadmap-results.js`'s `_roadmapEscapeHtml`
      replaced by the shared `escapeHtml` (11 call sites);
      `scripts/test_roadmap_results.js` updated to load `utils.js` into its
      sandbox first. Fixed the live `toggleCardOwnership` shadowing bug:
      deleted `index.html`'s dead cluster (unreachable
      `toggleCardOwnership`/`showCardDetailsPopupRoadmap`/
      `closeCardDetailsPopupRoadmap`/`saveCardDetailsPopupRoadmap`), added a
      `window.onCardOwnershipToggled` hook to `base.html`'s canonical
      `toggleCardOwnership`, and wired `category_detail.html` to it so its
      card list now re-filters immediately after a toggle. Extracted the two
      byte-identical HTML blocks into `templates/partials/
      card_ownership_modal.html` (used by `index.html` + `cards_list.html`)
      and `templates/partials/profile_stat_grid.html` (used by `profile.html`
      + `shared_profile.html`); standardized the JS-generated "Local Mode"
      badge to the plain `#5C6675` style (no emoji) while touching the
      modal. Verified: `node scripts/test_roadmap_results.js` (28/28),
      `venv/bin/python manage.py test` (178/178), full scenario sweep clean,
      `manage.py check` clean. **Phase 4 (full inline-`<script>` extraction
      into `static/js/pages/*.js` and `static/js/base.js`) completed** on
      2026-07-19. Extracted script blocks from all HTML templates and
      updated template files. Verified via Django test suite (all 178 tests
      passed). CSS reorg / CSS-framework adoption remain out of scope (recommendation
      only). Detail: `docs/plans/phase-frontend-cleanup.md`. **Still
      needed: Phase 1-4 manual browser checklists** — add to the manual-passes
      list below.
- [ ] **Standardize Card Metadata & Rule Representation**
      Implement validation schemas (e.g. via Pydantic or Django JSON schemas) for `CreditCard.metadata` to prevent typos (like `once_per_life_time`) during imports. Refactor the static `ISSUER_RULES` dict in `roadmaps/eligibility.py` into structured classes (`BaseIssuerRule`, `WindowRule`, etc.) to plug in velocity limits cleanly.
- [ ] **Decouple Test Suite from Database Operations**
      Refactor tests in `roadmaps/tests.py` so mathematical algorithms (e.g. the 12-month capacity plan scheduler) can be unit-tested using pure Python mocks/dataclasses instead of Django model database fixtures.

## Operational to-do (not phases)

- [ ] **Manual browser passes** — code has shipped but nothing's been
      eyeballed in a real browser (Jamie runs the dev server himself).
      Checklists already written in `docs/MANUAL_TEST_PLAN.md`:
  - [ ] Frontend cleanup Phases 1–4 (`docs/plans/phase-frontend-cleanup.md`)
        — P1: `/roadmap/` entity name with an apostrophe still escapes in
        the "as {name}" label; `/cards/`, `/profile/` a toast still appears
        and clears; `/categories/`, `/cards/` ownership filter reflects
        owned cards. P2: `/categories/<slug>/` ownership toggle updates the
        button AND re-filters immediately with a filter active (the actual
        bug fix), persists on reload; `/roadmap/` "I have this card" modal
        flow still works; console clean on both. P3: `/roadmap/` and
        `/cards/` ownership modal opens/renders/submits, each page's
        positioning unaffected; `/profile/` and a shared-profile URL — 4
        stat tiles render correct numbers. P4: Verify that all pages load
        properly with externalized scripts, AJAX actions (toggles, preferences,
        saving) succeed, and the browser console has zero script errors.
  - [ ] Phase E timing labels (`static/js/roadmap-results.js`
        `_roadmapTimingLabel`) on live generation, reload-restore, and the
        shared read-only page — check "Apply in ~N months (Mon YYYY)"
        arithmetic against `generated_at`, the Apply-section sort, and the
        reworked capacity note (sequenced timeline + deferred/bonus-less
        sentences). Skipped in favor of the automated
        `scripts/test_roadmap_results.js` smoke test, 2026-07-17.
  - [ ] Phase A credit-preferences UI (`index.html`/`profile.html`
        checkbox wiring, grey-out + "counted once" visuals for
        non-stackable credits)
  - [ ] Phase C roadmap sharing (share toggle, public link, private 404)
  - [ ] Phase D roadmap-first navigation (`/` redirect, results-first
        view, "Update roadmap" toggle)
  - [ ] Roadmap "Card summary" table (Rewards/Signup Bonus/Benefits/Fee
        columns reconciling to Value/yr) and card-detail modal credit
        opt-out checkboxes (`templates/base.html` `populateCardCredits()`)
        — confirm the checkbox state matches `/profile/`'s and that
        toggling either place updates the other after a roadmap refresh
  - [ ] Phase G card data & ownership admin (bonus_earned_date/
        bonus_override fields in the edit-card modal, offer_type badge,
        profile.html "Renews" column + highlight fix) — checklist in
        `docs/MANUAL_TEST_PLAN.md`
  - [ ] Phase K multi-player households (household panel CRUD on
        profile.html, Owner column + owner selector in the edit-card
        modal, second-copy apply_as attribution, household summary line
        on index.html) — checklist in `docs/MANUAL_TEST_PLAN.md`
  - [ ] Phase K follow-up owner-by-kind (add a business card with one vs.
        two business entities declared — auto-assign vs. picker; same for
        a personal card with two people; confirm the picker on
        `cards_list.html`'s "I have this card"/"Edit card details" buttons
        and the roadmap results "I have this card" button agree with the
        edit-card modal's default/filtering)
  - [ ] Phase N one-off upcoming-expense mode (`index.html` "Upcoming large
        purchase" collapsible input, with and without a category selected)
        — confirm the "Best card for your purchase" panel ranks sensibly,
        each row's line items sum to the shown total, the panel survives
        reload-restore (Current Roadmap) and the public shared-roadmap
        page, and it's absent entirely when no expense is entered
- [ ] **Deploy loose ends** — after Jamie's first Google login on
      production, promote his user to staff/superuser via the
      PythonAnywhere console; consider revoking the PythonAnywhere API
      token used during deployment.

See mybrain `Requirements/Backlog/Review.md` for the larger feature backlog
(referral/affiliate links, hotel/airline-specific modes, ecosystem presets,
etc.) — those are candidate future work pending product/business decisions,
not scheduled.

## Recurring maintenance

Run `venv/bin/python manage.py import_external_cards` locally ~monthly,
review `git diff data/input/cards/`, commit, push — the repo only stays in
sync with production's automated monthly refresh if this also runs locally
(production resets its own JSON edits before each refresh). Full detail in
`CLAUDE.md`.

## Verification quick reference

```bash
venv/bin/python manage.py test                                                # standard suite (170 tests)
RUN_ALL_SCENARIOS=1 venv/bin/python manage.py test cards.test_json_scenarios   # full sweep must pass clean
venv/bin/python manage.py run_scenario "Jamie Real" --explain                  # every line item reconciles
node scripts/test_roadmap_results.js                                          # roadmap-results.js pure-helper smoke test
```

Baseline as of 2026-07-19 (post Phase M verification): 174 standard tests
green, scenario sweep clean (`test_all_scenarios`, 77/77), "Jamie Real"
reconciles, JS smoke test green. Any failure is a regression.

**Phase M verification (2026-07-19)**: confirmed existing `roadmaps/
eligibility.py` rules — Chase 5/24, BofA 2/3/4, CapOne 1/6mo (window
rules), Amex 5-card open cap (`max_open_cards`), once-per-lifetime bonus
(Amex) + application (`application_eligibility`, Sapphire family) blocks,
business-vs-personal card routing, and per-entity headroom (2 players ⇒ 2×
5/24 budget) — all pass the standard suite and full scenario sweep with no
code changes needed. `data/tests/scenarios/multi_player.json`'s "both
players at 5/24, card excluded" scenario (5 cards × 2 entities = 10 Chase
cards total) is the "10 Chase cards in 24mo for 2 people" case from the
phase's own description — confirmed passing. Closed as verify-and-document
per Jamie's call (2026-07-19); three related gaps remain deliberately
unscoped, not bugs: (a) no aggregate cross-issuer open-card cap, (b) Amex's
per-rule counter is flat (doesn't split charge vs. credit or business vs.
personal sub-limits), (c) no cross-issuer new-account velocity throttle.
Revisit only if a specific gap becomes a real complaint — `roadmaps/
eligibility.py`'s module docstring is the place to extend `ISSUER_RULES`
if so.

## Where everything else went

- **Completed phase history (0–5, A–D, S1–S4, eligibility research)** →
  mybrain `Requirements/Complete/PROJECT_STATUS_history_through_2026-07-11.md`
- **Full Phase A/B/C design + bug-fix log** (benefit preferences/
  stackability, roadmap persistence, roadmap sharing) → mybrain
  `Requirements/Complete/PLAN_BENEFITS_AND_ROADMAP_PERSISTENCE_complete.md`
- **Full Phase E design + step-by-step progress log** (selection-aware
  bonus capacity & sequencing) → mybrain
  `Requirements/Complete/PLAN_PHASE_E_BONUS_SEQUENCING_complete.md`
- **Full Phase F design + step-by-step progress log** (ownership
  consolidation onto `cards/`, line-item polish) → mybrain
  `Requirements/Complete/PLAN_PHASE_F_OWNERSHIP_CLEANUP_complete.md`
- **Full Phase K design + step-by-step progress log** (multi-player
  households & per-entity rules) → mybrain
  `Requirements/Complete/PLAN_PHASE_K_HOUSEHOLDS_complete.md`
- **Phases G, H, J detail** (no standalone plan doc) → git history + the
  originating plans in `.claude/plans/look-at-any-outstanding-wild-wirth.md`
  and `.claude/plans/plan-out-the-following-sharded-nest.md`
- **Phase N design** (one-off upcoming-expense mode) →
  `.claude/plans/cantinue-with-next-phase-foamy-dragonfly.md`
- **Feature backlog / future ideas** → mybrain
  `Requirements/Backlog/Review.md`
- **Architecture, working rules** → `CLAUDE.md` (this repo)
- **Operational references** (deploy, card import, testing) stay in this
  `docs/` folder — see `docs/README.md` for the index.
