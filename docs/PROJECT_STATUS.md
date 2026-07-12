# Project Status

Active work only. Completed phase history, design notes, and implementation
detail have been archived to mybrain — see the pointers at the bottom. Check
items off here as they land; when a phase's own detail doc is done, archive
it the same way and trim this file back down.

Last updated: 2026-07-11

## Planned phases (E–I) — see `.claude/plans/look-at-any-outstanding-wild-wirth.md`

- [ ] **Phase E — Engine: selection-aware bonus capacity & sequencing**
      Make the greedy optimizer bonus-capacity-aware during selection (not
      just at final assembly), then layer in sequencing/timing decisions.
      Lays the timing rails for the Southwest Companion Pass use case
      (CP modeling itself is a follow-up, not in E).
      **Plan: [PLAN_PHASE_E_BONUS_SEQUENCING.md](PLAN_PHASE_E_BONUS_SEQUENCING.md)**
- [ ] **Phase F — Cleanup: ownership consolidation & line-item polish**
      Consolidate `users/` and `cards/` ownership endpoints onto `cards/`
      (soft-close semantics; stop hard-deleting eligibility history). Fix
      duplicate `UserCardSerializer` definition bug. Polish $0 line-item
      filtering and negative `bonus_shift` grouping.
- [ ] **Phase G — Card data & ownership admin** Add `offer_type` choices
      to `CardCredit`, expose `bonus_earned_date` + new bonus-override field
      in profile.html, add renewal-date tracking to card dashboard.
- [x] **Phase H — Roadmap display polish** Scope narrowed per product decision
      (Jamie, 2026-07-11) to two items: (1) click-to-sort column headers on
      the profile page's "Active cards" table (`templates/profile.html`
      `renderCardCollectionTable()`/`sortCardCollection()`), and (2) inline
      SVG network marks (Visa/Mastercard/Amex/Discover) on the card-browse
      thumbnails (`templates/cards_list.html` `networkMark()`), replacing the
      issuer-gradient square when `card.metadata.network` is known — falls
      back to the gradient otherwise. **Dropped, not done:** the responsive
      multi-column grid for recommendation tiles and the "5x gas" bonus
      multiplier badges on Apply tiles — explicitly out of scope, not
      scheduled elsewhere.
- [ ] **Phase I — Roadmap analysis views** Cards × categories matrix,
      per-category value-over-time split, redemption guidance/links per card.

## Operational to-do (not phases)

- [ ] **Manual browser passes** — code has shipped but nothing's been
      eyeballed in a real browser (Jamie runs the dev server himself).
      Checklists already written in `docs/MANUAL_TEST_PLAN.md`:
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
venv/bin/python manage.py test                                                # standard suite (100 tests)
RUN_ALL_SCENARIOS=1 venv/bin/python manage.py test cards.test_json_scenarios   # full sweep: 64/64 must pass
venv/bin/python manage.py run_scenario "Jamie Real" --explain                  # every line item reconciles
```

Baseline as of 2026-07-11: 100 standard tests green, 64/64 scenario sweep,
"Jamie Real" reconciles. Any failure is a regression.

## Where everything else went

- **Completed phase history (0–5, A–D, S1–S4, eligibility research)** →
  mybrain `Requirements/Complete/PROJECT_STATUS_history_through_2026-07-11.md`
- **Full Phase A/B/C design + bug-fix log** (benefit preferences/
  stackability, roadmap persistence, roadmap sharing) → mybrain
  `Requirements/Complete/PLAN_BENEFITS_AND_ROADMAP_PERSISTENCE_complete.md`
- **Feature backlog / future ideas** → mybrain
  `Requirements/Backlog/Review.md`
- **Architecture, working rules** → `CLAUDE.md` (this repo)
- **Operational references** (deploy, card import, testing) stay in this
  `docs/` folder — see `docs/README.md` for the index.
