# Project Status

Active work only. Completed phase history, design notes, and implementation
detail have been archived to mybrain — see the pointers at the bottom. Check
items off here as they land; when a phase's own detail doc is done, archive
it the same way and trim this file back down.

Last updated: 2026-07-17

## Planned phases (E–M)

E–I planned in `.claude/plans/look-at-any-outstanding-wild-wirth.md`;
J–M planned in `.claude/plans/plan-out-the-following-sharded-nest.md`
(scoping decisions with Jamie, 2026-07-17). Recommended order:
**E (done) → F (done) → J → K → G → L → M → I** — engine work first, L after G
(needs G's `CardCredit.offer_type` to tell coupon-book credits from
always-on perks), I last so analysis views can use program-aware
valuations.

- [x] **Phase E — Engine: selection-aware bonus capacity & sequencing**
      Made the greedy optimizer bonus-capacity-aware during selection (not
      just at final assembly), then layered in sequencing/timing decisions.
      All 6 steps done (2026-07-17): `_bonus_capacity_plan`, capacity-aware
      valuation, bonus-less display pathway, sequencing annotations, API
      payload (`recommended_month`/`bonus_deferred`/`bonus_capacity.timeline`),
      and frontend timing labels. Archived to mybrain `Requirements/Complete/
      PLAN_PHASE_E_BONUS_SEQUENCING_complete.md`. The one open item — a real
      browser walkthrough (skipped this session per Jamie's call in favor of
      `scripts/test_roadmap_results.js`) — lives on in the operational to-do
      below, not blocking archival.
- [x] **Phase F — Cleanup: ownership consolidation & line-item polish**
      Consolidated `users/` and `cards/` ownership endpoints onto `cards/`
      (soft-close semantics; stop hard-deleting eligibility history). Fixed
      duplicate `UserCardSerializer` definition bug. Polished $0 line-item
      filtering and negative `bonus_shift` grouping. All 5 steps done
      (2026-07-17): F1 (duplicate serializer), F3 ($0 line-item guard on
      the allocated breakdown builder), F4 (bonus_shift aggregation in
      `roadmap-results.js`, with a new `_roadmapBonusShiftAggregate`
      pure helper + smoke tests), F2 (hard-delete → soft-close on both
      `remove_user_card` and the retired `UserCardDetailView`, plus a
      re-add-after-soft-close reopen fix in `add_user_card`), F5
      (retired all `users/` ownership endpoints, added `cards/user-cards/
      toggle/`, repointed every frontend caller, standardized the five
      surviving endpoints on DRF `IsAuthenticated`). 109 standard tests,
      67/67 scenario sweep, "Jamie Real" reconciles. Manual browser pass
      still outstanding (see Operational to-do below).
      **Plan: [PLAN_PHASE_F_OWNERSHIP_CLEANUP.md](PLAN_PHASE_F_OWNERSHIP_CLEANUP.md)**
      (F1–F5 breakdown, recommended order F1→F3→F4→F2→F5, 2026-07-17).
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
- [ ] **Phase J — Engine: points-program pooled valuation** If the
      portfolio holds a higher-redemption card in the same points program
      (e.g. Sapphire Reserve for Chase UR), value all that program's points
      at the best held card's multiplier. Hand-curated `points_program`
      metadata key in `data/input/cards/*.json` (survives external refresh,
      like `bonus_eligibility`). Engine: centralize the ~15 raw
      `reward_value_multiplier` reads into one helper first, then make it
      portfolio-aware (`max(own, best same-program multiplier in
      portfolio)`); selection values per-combination (same shape as Phase
      E's capacity plan), pre-sort solo scoring keeps own multiplier; a
      "points valued via {card}" info line keeps the reconciliation guard
      holding by construction. Same-program pooling only — no transfer-
      partner modeling (locked scope). Expect sweep recalibration.
- [ ] **Phase K — Multi-player households & per-entity rules** Replace the
      implicit one-person assumption with N personal players + M business
      entities on `UserSpendingProfile`, plus `UserCard.owner` (relax
      `unique_together ['user','card']` — a household can hold two of the
      same card). Eligibility (`application_block`/`bonus_ineligibility`)
      evaluated per entity's own history — 2 players ⇒ 2× 5/24 headroom;
      business cards require a business entity; new rule types for
      max-cards-held-per-issuer and once-per-lifetime *applications*
      (e.g. one Sapphire per person). Bonus capacity stays global (spend
      is shared household spend); only apply slots multiply. UI: entity
      counts in preferences, owner selector on owned cards, "as Player 2"
      note on apply recs. Biggest phase — write its own PLAN doc at pickup.
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
venv/bin/python manage.py test                                                # standard suite (109 tests)
RUN_ALL_SCENARIOS=1 venv/bin/python manage.py test cards.test_json_scenarios   # full sweep: 67/67 must pass
venv/bin/python manage.py run_scenario "Jamie Real" --explain                  # every line item reconciles
```

Baseline as of 2026-07-17: 109 standard tests green, 67/67 scenario sweep,
"Jamie Real" reconciles. Any failure is a regression.

## Where everything else went

- **Completed phase history (0–5, A–D, S1–S4, eligibility research)** →
  mybrain `Requirements/Complete/PROJECT_STATUS_history_through_2026-07-11.md`
- **Full Phase A/B/C design + bug-fix log** (benefit preferences/
  stackability, roadmap persistence, roadmap sharing) → mybrain
  `Requirements/Complete/PLAN_BENEFITS_AND_ROADMAP_PERSISTENCE_complete.md`
- **Full Phase E design + step-by-step progress log** (selection-aware
  bonus capacity & sequencing) → mybrain
  `Requirements/Complete/PLAN_PHASE_E_BONUS_SEQUENCING_complete.md`
- **Feature backlog / future ideas** → mybrain
  `Requirements/Backlog/Review.md`
- **Architecture, working rules** → `CLAUDE.md` (this repo)
- **Operational references** (deploy, card import, testing) stay in this
  `docs/` folder — see `docs/README.md` for the index.
