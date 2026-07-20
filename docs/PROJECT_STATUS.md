# Project Status

Active work only. Completed phase history, design notes, and implementation
detail have been archived to mybrain — see the pointers at the bottom. Check
items off here as they land; when a phase's own detail doc is done, archive
it the same way and trim this file back down.

Last updated: 2026-07-20

## Phases (E–Q)

Scoping decisions with Jamie: E–I on 2026-07-17, J–M on 2026-07-17, N–Q
added 2026-07-18 from Jamie's backlog. (The original per-phase planning
scratch files lived under `.claude/plans/`, which is gitignored and doesn't
persist across sessions — decisions and implementation detail live here and
in the mybrain archives linked below instead.) Phase N was built ahead of M
(2026-07-18, Jamie's call — greenfield feature over a verify-and-document
pass). O and P are done; **Phase Q** (surfacing existing credit math in the
spending-input builder UI) is the only phase left unstarted — see Open
below.

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
- [x] **Points-currency credit valuation** (2026-07-20). Points-denominated
      credits (e.g. a 7,500-point Southwest anniversary bonus) now value at
      real redemption worth (~$105) instead of face value ($7,500), via a
      new `PointsProgram.currency_code` and shared `cards/valuations.py`
      helpers applied at the engine's single valuation chokepoint. Full
      design + implementation log archived to mybrain
      `Requirements/Complete/PLAN_POINTS_CURRENCY_CREDIT_VALUATION_complete.md`.

Detail archived — see pointers under "Where everything else went."

### Open

- [ ] **Phase Q** — Surface existing credit math in the spending-input
      builder UI. Not started; scoping only so far (see "Phases (E–Q)"
      above). No plan doc written yet.
- [ ] **Card catalog verification backlog**. A full `import_cards` sweep
      across every issuer file (2026-07-20) found roughly 130 cards still
      `verified: false` and sitting out of the DB entirely — most of
      American Express, and all of Bank of America, Barclays, Citi, US
      Bank, Wells Fargo, PenFed, First, FNBO. Only a small "headline"
      subset (Chase, a handful of Amex/Capital One) is actually live.
      Barclays specifically has zero verified cards, including the 5
      points-denominated ones already reviewed (`data/input/cards/
      barclays.json`: JetBlue, JetBlue Premier, Wyndham Rewards Earner,
      Earner Business, Earner Plus). No plan yet for clearing this at
      scale — each card needs the same kind of sanity pass that caught
      the united-explorer duplicate-credit bug (2026-07-19) and the
      missing/stale Amex Platinum hotel credits (2026-07-20) before
      bulk-verifying, since `verified: true` is what puts a card's math in
      front of users.
- [ ] **Amex Gold 5x hotel-booking-channel rate not modeled**. The
      April 2026 refresh raised prepaid-hotel-via-Amex-Travel earn from 2x
      to 5x, but `data/input/cards/american_express.json`'s Gold entry only
      has a blanket `hotels` category — no portal-specific split like
      Chase's `chase_travel` or Capital One's `capital_one_travel`. Bumping
      the blanket rate to 5x would overstate value for anyone who books
      hotels directly. Needs a new `amex_travel`-style category in
      `data/input/system/spending_categories.json` before this can be
      applied correctly.

See `docs/plans/` and mybrain `Requirements/Backlog/Review.md` for other
future/candidate work.

### Technical Debt & Refactoring
- [x] **Consistent card detail/edit modal everywhere** (2026-07-19). Every
      card listing now opens the shared `#cardModal` on click instead of My
      Cards' old inline accordion, and wired up several previously inert
      card-name links (profile, roadmap category matrix) along the way.
      Full detail archived to mybrain
      `Requirements/Complete/TASK_MODAL_CONSOLIDATION_complete.md`.
- [x] **Global Tab Design Alignment** (2026-07-19). Aligned the tabs component styles across all pages with the clean, bottom-bordered style of the profile page and moved styling rules to `components.css`. Reordered and shortened top-level and results tabs on the roadmap page.
- [x] **Frontend cleanup — Phases 1–4** (dedup, bug fix, HTML partials, full
      JS extraction; 2026-07-19). Shared JS utilities deduped into
      `static/js/utils.js`, a live `toggleCardOwnership` shadowing bug
      fixed, byte-identical HTML extracted into `templates/partials/`, and
      all inline `<script>` blocks extracted into `static/js/pages/*.js` +
      `static/js/base.js`. CSS reorg / CSS-framework adoption remain
      recommendation-only, out of scope. Verified: JS smoke test (28/28),
      standard suite (178/178), full scenario sweep clean, `manage.py check`
      clean. Full plan + verification log: `docs/plans/phase-frontend-cleanup.md`
      (kept live — manual browser checklists below still need to run).
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
- [ ] **Verify/reschedule the production monthly card-sync cron** — the
      PythonAnywhere scheduled task described in `docs/DEPLOYMENT_GUIDE.md`
      (daily 09:15 UTC, acts only on the 1st of the month) is believed to
      not actually be firing. Confirm in the PythonAnywhere console and fix
      or recreate it once the provenance-aware `import_external_cards`
      workflow below has been used locally a few times and is trusted.

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

The sync now also pulls **credits** from andenacitelli and is
**provenance-aware**: each card JSON carries a `_sources` map tagging which
side owns each section (`annual_fee`, `signup_bonus`, `discontinued`,
`annual_fee_waived`, `credits`). Sections tagged (or defaulted to)
`"andenacitelli"` auto-update as before; sections tagged `"manual"` (e.g.
hand-curated credits) are never overwritten — if andenacitelli's data
disagrees, a `PendingCardUpdate` row is queued instead. After each sync run,
check Django admin → **Pending Card Updates** and approve/reject any
conflicts (approving writes into the JSON and re-imports; reject suppresses
identical future proposals). Detail in `docs/CARD_IMPORT_GUIDE.md`.

andenacitelli only reflects what its own maintainers have entered, so it
can lag real issuer refreshes by months (e.g. it still showed Chase
Sapphire Preferred's old $50 hotel credit in July 2026, weeks after
Chase's own June 2026 announcement of $100). For the small set of
premium/high-fee cards, it's worth periodically web-searching the issuer's
own announcements directly rather than relying solely on the sync — that
pass on 2026-07-20 caught the Sapphire Preferred refresh, a brand-new
Chase Sapphire Reserve "Edit" hotel credit, and missing/stale Amex
Platinum FHR hotel credits across 4 variants, none of which the API had
picked up.

## Verification quick reference

```bash
venv/bin/python manage.py test                                                # standard suite (228 tests)
RUN_ALL_SCENARIOS=1 venv/bin/python manage.py test cards.test_json_scenarios   # full sweep must pass clean
venv/bin/python manage.py run_scenario "Jamie Real" --explain                  # every line item reconciles
node scripts/test_roadmap_results.js                                          # roadmap-results.js pure-helper smoke test
```

Baseline as of 2026-07-20 (post points-currency credit valuation): 228
standard tests green, scenario sweep clean (`test_all_scenarios`), "Jamie
Real" reconciles, JS smoke test green (28/28). Any failure is a regression.

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
- **Phases G, H, J, N detail** (no standalone plan docs) → git history; the
  original planning-session scratch files under `.claude/plans/` are
  gitignored and don't persist, but each phase's implementation summary is
  captured inline in the Completed section above.
- **Points-currency credit valuation design + session log** → mybrain
  `Requirements/Complete/PLAN_POINTS_CURRENCY_CREDIT_VALUATION_complete.md`
- **Modal consolidation task detail** → mybrain
  `Requirements/Complete/TASK_MODAL_CONSOLIDATION_complete.md`
- **Feature backlog / future ideas** → mybrain
  `Requirements/Backlog/Review.md`
- **Architecture, working rules** → `CLAUDE.md` (this repo)
- **Operational references** (deploy, card import, testing) stay in this
  `docs/` folder — see `docs/README.md` for the index.
