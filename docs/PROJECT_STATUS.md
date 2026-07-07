# Project Status

Living document tracking the finish-the-app plan (phases below), work completed, and the
backlog of new/changed requirements discovered along the way. Update this when a phase
completes or a new requirement appears. (The original product spec is `PRD.md` at the repo
root — that's the *what*; this file is the *where are we*.)

Last updated: 2026-07-07

**Active work (2026-07-05):** benefit preferences & stackability, roadmap
persistence, and roadmap sharing — full approved plan + progress tracker in
`docs/PLAN_BENEFITS_AND_ROADMAP_PERSISTENCE.md` (**source of truth for
phase A/B/C detail — update its Progress section, not just this file**).
Phases A and B completed 2026-07-07; C is next. Phases A/B/C below.

**UI redesign (2026-07-07):** "Ledger" visual/IA redesign implemented per
`docs/design_handoff_ccguru_redesign/` — dark theme (tokens in
`static/css/base.css` `:root`), Space Grotesk/Hanken Grotesk/IBM Plex Mono +
Material Symbols Rounded, 4-tab bottom nav (Home/Roadmap/My Cards/Browse)
replacing the old 6-link hamburger nav. Categories/Issuers pages stay live at
their URLs but dropped from primary nav/footer. Browse (`cards_list.html`)
re-skinned in place (existing filters kept, new filter-chip row added) rather
than merged with Categories/Issuers. Visual restyle only — no new interactions
added (card rows still open the existing detail modal; no deep-linking, no
cancel-suggested/match-value badges, no Add-category button). Auth pages and
the public shared-profile page got the same token sweep for consistency.

## Docs map

This file is the entry point for "where are we." Every other doc below
covers one feature/phase in depth — if you're planning or resuming work on
something, check here first for which file owns it.

| File | Owns | Status |
|---|---|---|
| `PRD.md` (root) | Original product spec — the *what* | Reference, not living |
| `docs/PLAN_BENEFITS_AND_ROADMAP_PERSISTENCE.md` | Phase A/B/C detailed design + Progress checklist (benefit prefs/stackability, roadmap persistence, roadmap sharing) | **Living — update its Progress section as A/B/C move**, not just the phase table here |
| `docs/DEPLOYMENT_GUIDE.md` | PythonAnywhere deploy, MySQL migration incident, scheduled tasks | Living reference |
| `docs/DEPLOYMENT_CHECKLIST.md` | Step-by-step deploy checklist (companion to the guide above) | Living reference |
| `docs/CARD_IMPORT_GUIDE.md` | How `import_cards`/`verified: true` gating works | Living reference, but card counts (24/162) are stale — CLAUDE.md's "~27 of ~160" is current |
| `docs/design_handoff_ccguru_redesign/` | Ledger UI redesign spec (implemented 2026-07-07, see phase table below) | Reference (handoff artifact, not living) |
| `docs/COMPREHENSIVE_DOCUMENTATION.md` | General architecture/API walkthrough | Living reference, not verified as part of this update — spot-check before trusting specifics |
| `docs/README_TESTING.md` | How the JSON scenario test suite works (`data/tests/scenarios/*.json`), how to add scenarios, recalibration workflow | Rewritten 2026-07-07 to match the current system (was describing a pre-refactor single-file setup) |
| `docs/README.md` | Doc folder index | Refreshed 2026-07-07 — now points to this file and the PLAN doc |

## Phase plan

| Phase | Scope | Status |
|---|---|---|
| 0 | Triage & stabilize (.gitignore traps, restore `cards/test_base.py`, commit CSS refactor) | ✅ Done |
| 1 | Phone wallet view (`/wallet/`) + quarter-aware rotating categories (`active_on(date)`) + PWA manifest | ✅ Done |
| 2 | Trust: single allocation source of truth, cap-overflow reallocation, structured signup-bonus reqs, point-valuation transparency, reconciliation guard, `run_scenario --explain`, `jamie_real.json` acceptance scenario | ✅ Done |
| 3 | Deploy: refresh PythonAnywhere per `docs/DEPLOYMENT_GUIDE.md` | ✅ Done — live at https://foresterh.pythonanywhere.com on MySQL (see deploy guide for the SQLite/NFS incident); monthly bonus-refresh task scheduled |
| 4 | Sustainable data pipeline: `import_external_cards` refreshes bonuses/fees from the andenacitelli community API | ✅ Done (monthly cron wiring happens at deploy, Phase 3) |
| 5 | Cleanup: dead deps/scripts removed, `manage_project.py` menu entries | ✅ Mostly done (see backlog) |
| A | Benefit preferences (opt-out toggles on profile+roadmap, server-persisted) + stackability dedup (curated `stackable` flag; non-stackable credits count once per portfolio) — see `PLAN_BENEFITS_AND_ROADMAP_PERSISTENCE.md` | ✅ Done (A1–A5 all landed 2026-07-07 — model/migration, engine dedup, credit-preferences API, index.html/profile.html UI, and full test coverage incl. `credit_stackability.json`; the UI still needs a manual browser pass, unverified) |
| B | Roadmap persistence (survives reload until regenerate; anon via session) + "I have this card"/"remove from my cards" on results | ✅ Done (B1–B5 all landed 2026-07-07 — anon session-timing + loose-fallback fixes, Current Roadmap persisted post-rollback, `GET /api/roadmaps/current/`, shared `roadmap-results.js` renderer + page-load restore + remove-from-my-cards, full test coverage; see PLAN doc Progress section for the two bugs found along the way — a session-cookie suppression that silently broke anon persistence, and a bulk-save hard-delete that would have erased soft-closed eligibility history) |
| C | Roadmap sharing (share toggle + public UUID link, mirrors profile sharing) | 📋 Planned |

## Requirements added/changed since the original plan

- **Signup bonuses must model where the spend comes from** (2026-06): a bonus isn't free
  money — meeting "$4,000 in 3 months" pulls spending off other cards. Engine now emits
  three cases: organic coverage (info line), spending shift with per-source opportunity
  cost (`bonus_shift` line items, net of foregone rewards), unreachable → bonus valued $0.
- **First-year vs ongoing value split** shown per recommendation; point valuations
  (`reward_value_multiplier`) surfaced explicitly ("points valued at 1.5¢").
- **Spending-credit preferences in scenarios**: `user_profile.spending_credit_preferences`
  (SpendingCredit slugs) so CLI scenarios reproduce app results. Keep/cancel verdicts on
  premium cards hinge on which credits the user actually redeems.
- **Reconciliation guard**: every recommendation's line items + signup bonus − fee must
  equal the headline within $1; violations log with context. `--explain` prints the proof.
- **Data pipeline design (2026-06)**: the per-issuer JSONs in `data/input/cards/` stay the
  source of truth for curated detail (categories, credits, valuations, referral URLs); the
  `verified: true` flag is the watchlist (27 of ~160 cards import). `import_external_cards`
  only refreshes the fields that churn — signup bonuses, annual fees, discontinued status —
  by editing the JSON in place and re-importing changed files. `git diff data/input/cards/`
  is the audit trail of offer changes. Renamed cards map via
  `data/input/overrides/external_card_map.json`; genuinely new API cards are reported, not
  auto-created. Idempotent: second run reports "No changes".

## Data maintenance (what runs itself vs. what Jamie does)

**Automated**: a PythonAnywhere scheduled task (daily 09:15 UTC, acts only on the 1st of
the month) resets `data/input/cards/`, pulls main, and runs `import_external_cards` —
production bonuses/fees/discontinued flags refresh themselves monthly. Output appends to
`~/import_external.log` on the server. Nothing to run by hand for production.

**Manual (occasional, ~monthly-ish)**: because the server *resets* its JSON edits before
each refresh, the repo's JSONs only stay current if the import is also run locally and
committed. Routine: `venv/bin/python manage.py import_external_cards`, review
`git diff data/input/cards/` (the offer-change audit trail), commit, push. While there,
skim the command's report for renamed cards needing a mapping in
`data/input/overrides/external_card_map.json` and genuinely new API cards worth curating
(only `verified: true` cards import — 27 of ~160; growing that watchlist is deliberate
hand-curation, not a chore with a deadline).

## Next feature: Strategies (planned 2026-06)

Guide users to a card *strategy* (à la the r/CreditCards strategy-ladder posts) instead of
just a one-shot card list. Design conclusion: a strategy decomposes into three knobs the
engine already has or nearly has — **card-pool filters** (RoadmapFilter presets),
**scoring weights** (bonus emphasis vs ongoing value vs card-count penalty; the engine
already computes `first_year_value`/`ongoing_value` separately), and **portfolio
constraints** (max cards, new-apps-per-year cadence, rotating categories allowed). So a
strategy is *data, not code*: a preset that expands into existing filters + a few new
engine weights, passed as one `strategy` field on the quick-recommendation API.

"Difficulty" is reframed as **effort tolerance**: one user-facing question sets max cards
managed, new applications per year (0 = never churn), and rotating-categories yes/no.
Loyalty (preferred airline/hotel) is a point-valuation boost folded into existing
preferences, not a strategy.

| Phase | Scope | Status |
|---|---|---|
| S1 | Three data-driven presets — **Simple Cash Back**, **Travel Points**, **Maximizer** (the churner tier) — as filter bundles + engine weights; `strategy` param on the quick-rec API; one JSON scenario file per preset (non-negotiable: every preset gets scenario coverage or we're back to untrusted math) | ✅ Done 2026-06-12 (see S1 notes below) |
| S2 | UI: effort-tolerance question picks the default preset; explicit strategy picker is an advanced option, not a gate before the roadmap | ✅ Done 2026-06-12 (see S2 notes below) |
| S3 | Issuer eligibility rules engine (see below) — behind-the-scenes "can you even get this card/bonus" checks feeding next-card selection, plus an eligibility note on recommendation cards in the UI | ✅ Done 2026-07-01 (see S3 notes below) |
| S4 | **Bonus capacity from spend velocity** (added 2026-07 by request): a counted signup bonus consumes `requirement ÷ total monthly spend` months of the year; recommended applies must fit in 12 months. A $2K/mo spender offered three $10K-requirement cards gets two — the third is deferred with a note in the portfolio summary. Sequential windows also keep per-card `bonus_shift` line items honest (no overlapping dollars) | ✅ Done 2026-07-01 |
| — | **Goals with sequencing** (e.g., Southwest Companion Pass: time two bonuses to land after Jan 1) — explicitly **deferred**; it's a goal, not a weighting. S4's capacity cap is the first step; ordering bonuses across the year is the rest | Deferred |

Risks called out at design time: every preset multiplies the scenario-validation surface
(22 scenarios are already stale — recalibrate first or alongside); the quick-rec
serializer footgun (below) gets worse with more state on that endpoint — defuse with S1.

### S1 notes: how strategies are implemented (done 2026-06-12)

- **`roadmaps/strategies.py`** is the whole feature surface: `STRATEGIES` dict with the
  three presets (`simple_cash_back`, `travel_points`, `maximizer`), each = card-pool
  filters + `max_recommendations` default + two selection weights
  (`signup_bonus_weight`, `per_card_penalty`). Adding a preset = adding a dict entry +
  a scenario in `data/tests/scenarios/strategies.json`.
- **Weights shape SELECTION only, never displayed math** — they're applied at the three
  scoring sites in the engine (`_select_optimal_card_combination`, the local
  `calculate_portfolio_value` in `_optimize_card_portfolio`, and
  `_calculate_scenario_portfolio_value`), all of which only rank portfolios. Headline
  values and line items stay honest dollars, so the reconciliation guard is untouched.
- **Filter semantics fix**: `_get_filtered_cards` now ORs same-type filters and ANDs
  across types (previously chained `.filter()` ANDed everything, so Points+Miles would
  match nothing). Needed for the Travel Points pool.
- **API**: `strategy` field on the quick-rec endpoint (`POST /api/roadmaps/quick-recommendation/`),
  validated with a helpful 400 on unknown keys. Explicit `max_recommendations` in the
  payload beats the preset's default; preset filters stack on top of explicit filters.
- **Scenarios/CLI**: scenario JSON takes a top-level `"strategy"` key (unknown key =
  loud error); `run_scenario` and the test base both honor it. Coverage:
  `data/tests/scenarios/strategies.json` — same spender + same mixed pool through each
  preset, so the strategy is the only variable. 3 named tests + a typo-guard test run in
  the standard suite (now 33 tests).
- **Drive-by fix**: CLI `run_scenario` used to leak fixture cards into the dev DB on
  every run (it deleted the scenario user but not the cards it created) — they then
  appeared in real recommendations. Now tracks created-vs-fetched cards and deletes the
  created ones on cleanup. Dev DB was scrubbed back to the 27 real cards.

### S2 notes: strategies UI (done 2026-06-12)

- **Strategy stays data**: presets grew an `effort_label` and a `ui_presets()` helper in
  `roadmaps/strategies.py`; the roadmap page (`index_view`) passes that list to the
  template, which renders the question AND feeds the JS via `json_script` — no preset
  names/captions duplicated in the frontend.
- **The question is optional**: three tappable effort cards above Preferences on
  `/roadmap/`; clicking selects a preset, clicking again clears it. Nothing blocks
  "Get My Roadmap" — unanswered = no `strategy` in the payload = pre-S2 behavior.
- **Advanced picker**: a collapsed "pick a strategy directly" select (preset name +
  pool + card cap, plus "No strategy"), kept in sync with the effort cards both ways.
- **Preset side effects on selection** (user action only, not on page-load restore):
  Max Recommendations is set to the preset's cap (visible, still user-overridable —
  matches the serializer's explicit-beats-preset rule) and the Reward Type filter is
  cleared, because same-type filters OR together so a leftover pick would *widen* the
  preset's pool.
- Selection persists in localStorage (`userStrategy`), the results header names the
  active strategy, and the dev "Export to Test Scenario" includes the top-level
  `"strategy"` key scenarios already understand.
- Tests (standard suite now 36): `ui_presets()` shape, `/roadmap/` renders the
  question/presets/picker (needed a test `SocialApp` for base.html's Google button),
  and the API 400s on a typo'd strategy key.

### S3 notes: how eligibility is implemented (done 2026-07-01)

- **`roadmaps/eligibility.py`** is the whole feature surface (same "rules
  are data" idiom as strategies.py): `ISSUER_RULES` keyed by issuer slug
  holds application rules (Chase 5/24, BofA 2/3/4, Capital One 1/6mo) and
  issuer-default bonus rules (Amex once-per-lifetime, Citi 48-month).
  Card-level rules live in card JSON `metadata.bonus_eligibility`
  (Sapphire lifetime, Southwest 24-month + family) and
  `metadata.application_family` (holding an open family card blocks
  applying for another) — curated in `data/input/cards/chase.json`.
- Rules evaluate against the user's FULL card history including closed
  cards (`engine.card_history`); new `UserCard.bonus_earned_date` field,
  approximated as opened_date + ~3 months when blank. Unknown dates are
  treated conservatively (bonus assumed earned recently).
- Application-blocked cards are silently excluded from applies (all
  paths, including the high-spender fallback). Bonus-ineligible cards
  still compete on ongoing value with `signup_bonus = $0`, a $0 info
  line item, and a user-facing `eligibility_note` ("bonus unlikely — ...")
  rendered on the recommendation card.
- Windows are calendar-accurate (`months_before`), replacing the old
  `24*30 days` drift. `Issuer.max_cards_per_period`/`period_months`
  model fields remain unused (their seeded values are junk).
- Scenario plumbing: owned_cards entries can be history dicts
  (`{"card": ..., "opened_days_ago": 90, "closed_days_ago": ...,
  "bonus_earned_days_ago": ...}`); a top-level scenario
  `max_recommendations` beats the count-derived default. Coverage:
  `data/tests/scenarios/eligibility.json` (4 scenarios) + unit tests in
  `roadmaps/tests.py` (rule-by-rule, incl. business-card reporting
  exceptions and family rules).

### S3 research: issuer eligibility rules (verified via web research 2026-06-12)

Two distinct rule types, both behind-the-scenes (they change *which* card is recommended
next; the UI only gets a small note like "bonus unlikely — you've earned this card's
bonus before"):

1. **Application eligibility** (can you get the card at all) — issuer-level, fits the
   existing unused `Issuer.max_cards_per_period`/`period_months` fields plus a couple of
   new ones.
2. **Bonus eligibility** (you can get the card but the bonus values at $0) — card-level,
   fits card `metadata`. When bonus-ineligible, the engine should still consider the card
   for ongoing value but score `signup_bonus = $0` — the existing "unreachable bonus →
   $0" pathway is the precedent.

Verified rules (all "soft"/unofficial unless marked in terms, but consistently enforced):

| Rule | Issuer | Type | Parameters | Notes |
|---|---|---|---|---|
| 5/24 | Chase | Application | ≥5 personal cards opened (any issuer, incl. since-closed) in 24 mo → denied | Business cards do NOT add to the count (they don't report to personal credit) — except Capital One, Discover, and TD business cards, which do. Chase *business* card applications ARE still subject to 5/24, they just don't increment it. |
| Sapphire lifetime | Chase | Bonus | Once per lifetime **per Sapphire product** | Changed 2025-06-23: the old 48-month rule and "one Sapphire" rule are gone; you can now hold Preferred + Reserve simultaneously, but each card's bonus is once-ever (enforced by a pop-up screening system). |
| Southwest 24-mo | Chase | Application + Bonus | Personal: ineligible if you currently hold ANY SW personal card or earned a SW personal bonus in 24 mo. Business: per-card — can hold both biz cards and earn both bonuses | Business cards don't affect personal eligibility, and vice versa. |
| Once-per-lifetime | Amex | Bonus | One bonus per card, ever (per-card, not per-family) | Enforced via "pop-up jail" at application time, which also jails for high velocity / low spend; enforcement is fuzzy (reports of re-eligibility after ~7 yrs, and "no lifetime language" offers exist). Model as per-card lifetime; treat pop-up as unmodelable noise. |
| 48-month | Citi | Bonus | No bonus if you earned THAT card's bonus in past 48 mo | Now per-card (not per-family — Strata Premier bonus doesn't block Strata Elite); clock runs from bonus receipt, not open/close date. |
| 2/3/4 | Bank of America | Application | Max 2 new BofA cards/30 days, 3/12 mo, 4/24 mo | Only counts BofA's own cards. |
| 1-per-6-mo | Capital One | Application | 1 new card per 6 months (personal + business pooled); max ~5 C1 cards total | Also: most C1 business cards report to personal credit → they count toward Chase 5/24. |

Sources: [TPG — Sapphire eligibility changes](https://thepointsguy.com/news/chase-sapphire-bonus-eligibility-changes/),
[Upgraded Points — 5/24](https://upgradedpoints.com/credit-cards/chase-5-24-rule/),
[TPG — Southwest eligibility](https://thepointsguy.com/credit-cards/ultimate-guide-southwest-credit-card-eligibility/),
[OMAAT — Amex lifetime rule](https://onemileatatime.com/guides/amex-lifetime-rule/),
[OMAAT — Citi 48-month](https://onemileatatime.com/guides/citi-card-48-month-rule/),
[AwardWallet — BofA 2/3/4](https://awardwallet.com/credit-cards/bank-america-234-policy/),
[Upgraded Points — per-bank rules](https://upgradedpoints.com/credit-cards/applying-for-credit-cards-bank-rules/).

~~Gaps in the current implementation~~ — all addressed 2026-07-01 (see S3
notes above): the hardcoded name-matching 5/24 is gone, business cards
count only when their issuer reports to personal credit, windows are
calendar-accurate, bonus rules exist as data, and `UserCard.bonus_earned_date`
was added (approximated from `opened_date` + ~3 mo when blank).

## Done since (2026-07-01)

- ~~Recalibrate stale scenario expectations~~ — the full sweep now passes
  **61/61** (was 21 failures + 7 errors). Root causes were mostly data bugs,
  not just stale numbers: fixture bonuses had no spending requirements
  (free money), four scenarios "owned" cards that were never created
  (silent skip, now a loud error), the test DB lacked the real
  category/credit taxonomy, and credit-integration scenarios never set
  credit preferences. Two engine fixes fell out: selection now counts
  card credits (display already did), and $0-value applies are filtered.
  `DUMP_SCENARIOS=1` prints per-scenario results for future recalibration.
- ~~Quick-recommendation serializer footgun~~ — quick-rec runs in an
  always-rolled-back transaction; stored profiles survive untouched.
- **Preference defaults** (2026-07, by request): empty max annual fee =
  no max (the "95" placeholder lied — it was already no-filter); empty
  max recommendations = 1 (was 5) across UI, serializers, and models.
- **Removed dead `CreditType`/`UserCreditPreference` system** (2026-07-04): the card
  credit/benefit filter on `cards_list.html` was checking `credit.credit_type`, a field
  the serializer never even sends — `SpendingCredit` (added 2025-07-28) superseded
  `CreditType` (added 2025-07-18) as the real, structured system, but the old model,
  its FK on `CardCredit`, the `import_credit_types` command, and admin wiring were never
  deleted. Fixed the filter to use `spending_credit` and removed the dead model/FK/command
  (migration `cards/0004`) plus stale doc references to `import_credit_types`.

## Backlog (known, not yet done)

- **Ownership endpoint consolidation** (Phase 5 leftover): `users/` duplicates some
  `cards/` ownership endpoints; consolidate on `cards/`.
- **UX: negative `bonus_shift` line items** confused at least one user (the user). Options:
  group under a "Cost to earn the bonus" subheading, or collapse to a single net line.
- **Future feature: bonus sequencing** — S4's capacity cap decides HOW MANY bonuses fit
  a year; sequencing decides the ORDER and timing (e.g. Companion Pass timing). Each
  apply's shift plan is still an independent counterfactual; the capacity cap keeps them
  from overlapping, but nothing yet plans month-by-month.
- **Selection-time bonus capacity**: the 12-month cap is enforced at final assembly;
  the greedy optimizer can still pick a portfolio whose later applies get deferred.
  Rarely matters (deferred cards are the lowest-priority applies) but selection-aware
  capacity would be strictly better.
- **Deploy loose ends** (2026-06): after Jamie's first Google login on production,
  promote his user to staff/superuser via the PythonAnywhere console; consider revoking
  the PythonAnywhere API token that was used during deployment.

## Verification quick reference

- Acceptance scenario: `python manage.py run_scenario "Jamie Real" --explain`
  (every line item must reconcile to the headline; runs against the dev DB)
- Full scenario sweep: `RUN_ALL_SCENARIOS=1 python manage.py test cards.test_json_scenarios`
- Standard tests: `python manage.py test` (85 tests)
- Full-sweep baseline (2026-07-07): **OK — 64/64 scenarios pass** (61 + 3 new
  `credit_stackability.json` scenarios from A5). Any failure is a
  regression. To hand-confirm a change's new numbers, re-run the sweep with
  `DUMP_SCENARIOS=1` and diff the printed per-scenario results (the CLI
  `run_scenario` runs against the dev DB, whose real cards pollute fixture pools —
  trust the test-DB dump for scenario work).
- Standard suite grew 76 → 85 with Phase B (2026-07-07):
  `roadmaps.tests.RoadmapPersistenceTests` (7) +
  `users.tests.SoftCloseSurvivesBulkSaveTests` (2). Scenario sweep untouched
  by Phase B (no engine changes).
