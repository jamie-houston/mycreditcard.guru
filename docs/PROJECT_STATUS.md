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
Jamie's backlog. Recommended order for what's left: **L → M → N → O →
P → Q** — N is mostly verification (see below) so it's cheap to clear
early; O/P (spending-input modes) before Q (surfacing existing credit
math) since they touch the same builder UI.

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

Detail archived — see pointers under "Where everything else went."

### Open
- [ ] **Phase L — Benefit/credit usage tracking** Track which monthly/
      quarterly credits were actually used this period. New
      `UserCreditUsage` model (profile × `CardCredit` × period key derived
      from `times_per_year` — `2026-07` / `2026-Q3` / `2026`), GET/PUT
      endpoint cloning `credit_preferences_view`'s auth+anon pattern.
      UI: this-period check-offs + "unused, expiring soon" grouping on
      profile.html's credits section and the base.html card modal. No
      engine impact. Sequence after Phase G (needs `offer_type`).
- [ ] **Phase M — "Export for AI" (LLM doc export)** Button on profile +
      roadmap `#resultsHeader` generating a self-contained markdown doc —
      owned cards with rewards/credits/open dates, spending, persisted
      Current Roadmap (`get_current_roadmap`), plus suggested prompts
      ("Which card should I use for groceries?", "Am I under 5/24?") —
      copy-to-clipboard + `.md` download. Anon-capable. Markdown export
      only, no public URL (locked scope). Smallest phase.
- [ ] **Phase N — Enforce max cards per lifetime & per issuer (business/personal)**
      Largely ALREADY DONE in Phase K — verify then close gaps. Existing
      (`roadmaps/eligibility.py`): Chase 5/24, BofA 2/3/4, CapOne 1/6mo
      (window rules), Amex 5-card open cap (`max_open_cards`), once-per-lifetime
      bonus (Amex) + application (`application_eligibility`, Sapphire family)
      blocks, business-vs-personal card routing, and PER-ENTITY headroom
      (2 players ⇒ 2× 5/24; each can hold a personal Sapphire, business gets
      the business card). Gaps to decide/scope: (a) no aggregate cross-issuer
      open-card cap, (b) coarse Amex business/charge sub-limit modeling,
      (c) no cross-issuer velocity throttle. Also confirm the "10 Chase cards
      in 24mo for 2 people" example behaves right via a scenario. Likely a
      small verify-and-document phase unless a specific gap is prioritized.
- [ ] **Phase O — One-off upcoming-expense mode**
      GREENFIELD. Let a user say "I have a $10k expense coming up" (instead of,
      or alongside, monthly spending) and recommend the best card to use/get
      for it (signup-bonus minimum-spend fit + best category rate). Today
      spending is only per-category monthly `SpendingAmount` (cards/models.py).
      New input on the roadmap builder (`templates/index.html`), a scratch
      field threaded through `roadmaps/serializers.py`, and engine handling
      that treats the lump sum as spend directed at one card. Interacts with
      bonus-capacity/min-spend logic (`_bonus_capacity_plan`).
- [ ] **Phase P — Category-less "easy mode" spending**
      GREENFIELD. Let a user enter total monthly OR yearly spend without
      picking categories ("$4k/month"), for a quick low-effort estimate.
      New builder toggle + input (`templates/index.html`), scratch field in
      `roadmaps/serializers.py`, and engine fallback that values a flat total
      at base/uncategorized rates. Complements, not replaces, the category grid.
- [ ] **Phase Q — Surface cards that "pay for themselves" via recurring credits**
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
venv/bin/python manage.py test                                                # standard suite (156 tests)
RUN_ALL_SCENARIOS=1 venv/bin/python manage.py test cards.test_json_scenarios   # full sweep must pass clean
venv/bin/python manage.py run_scenario "Jamie Real" --explain                  # every line item reconciles
node scripts/test_roadmap_results.js                                          # roadmap-results.js pure-helper smoke test
```

Baseline as of 2026-07-18 (post Phase I): 156 standard tests green (151 +
5 from Phase I), scenario sweep clean, "Jamie Real" reconciles, JS smoke
test green. Any failure is a regression.

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
- **Feature backlog / future ideas** → mybrain
  `Requirements/Backlog/Review.md`
- **Architecture, working rules** → `CLAUDE.md` (this repo)
- **Operational references** (deploy, card import, testing) stay in this
  `docs/` folder — see `docs/README.md` for the index.
