# Project Status

Active work only. Completed phase history, design notes, and implementation
detail have been archived to mybrain — see the pointers at the bottom. Check
items off here as they land; when a phase's own detail doc is done, archive
it the same way and trim this file back down.

Last updated: 2026-07-18

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

Detail archived — see pointers under "Where everything else went."

### Open

- [ ] **Phase O — Category-less "easy mode" spending**
      GREENFIELD. Let a user enter total monthly OR yearly spend without
      picking categories ("$4k/month"), for a quick low-effort estimate.
      New builder toggle + input (`templates/index.html`), scratch field in
      `roadmaps/serializers.py`, and engine fallback that values a flat total
      at base/uncategorized rates. Complements, not replaces, the category grid.
- [ ] **Phase P — Surface cards that "pay for themselves" via recurring credits**
      MOSTLY ALREADY COMPUTED — surface it + one real fix. The engine already
      annualizes recurring credits and nets them against the annual fee in
      keep/select decisions (`_counted_card_credits`,
      `_allocate_portfolio_credits`, `_calculate_card_allocated_breakdown`), so
      a high-fee card whose credits cover the fee is already kept without a
      signup bonus. New work: (1) an explicit "pays for itself via credits"
      flag/label when `credits_value >= annual_fee`, surfaced in the
      recommendation payload + UI; (2) optional filter/sort for self-funding
      cards; (3) FIX the pre-sort gap where `_calculate_smart_card_value`
      (~recommendation_engine.py:1751) omits credits, so credit-heavy cards
      aren't under-ranked before the portfolio comparison (which does count
      them). Guard the reconciliation invariant — the label is display-only.

### Technical Debt & Refactoring
- [ ] **Standardize Card Metadata & Rule Representation**
      Implement validation schemas (e.g. via Pydantic or Django JSON schemas) for `CreditCard.metadata` to prevent typos (like `once_per_life_time`) during imports. Refactor the static `ISSUER_RULES` dict in `roadmaps/eligibility.py` into structured classes (`BaseIssuerRule`, `WindowRule`, etc.) to plug in velocity limits cleanly.
- [ ] **Decouple Test Suite from Database Operations**
      Refactor tests in `roadmaps/tests.py` so mathematical algorithms (e.g. the 12-month capacity plan scheduler) can be unit-tested using pure Python mocks/dataclasses instead of Django model database fixtures.

## Operational to-do (not phases)

- [ ] **Manual browser passes** — code has shipped but nothing's been
      eyeballed in a real browser (Jamie runs the dev server himself).
      Checklists already written in `docs/MANUAL_TEST_PLAN.md`:
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
