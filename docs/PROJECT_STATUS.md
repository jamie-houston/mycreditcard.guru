# Project Status

Living document tracking the finish-the-app plan (phases below), work completed, and the
backlog of new/changed requirements discovered along the way. Update this when a phase
completes or a new requirement appears. (The original product spec is `PRD.md` at the repo
root — that's the *what*; this file is the *where are we*.)

Last updated: 2026-06-12

## Phase plan

| Phase | Scope | Status |
|---|---|---|
| 0 | Triage & stabilize (.gitignore traps, restore `cards/test_base.py`, commit CSS refactor) | ✅ Done |
| 1 | Phone wallet view (`/wallet/`) + quarter-aware rotating categories (`active_on(date)`) + PWA manifest | ✅ Done |
| 2 | Trust: single allocation source of truth, cap-overflow reallocation, structured signup-bonus reqs, point-valuation transparency, reconciliation guard, `run_scenario --explain`, `jamie_real.json` acceptance scenario | ✅ Done |
| 3 | Deploy: refresh PythonAnywhere per `docs/DEPLOYMENT_GUIDE.md` | ✅ Done — live at https://foresterh.pythonanywhere.com on MySQL (see deploy guide for the SQLite/NFS incident); monthly bonus-refresh task scheduled |
| 4 | Sustainable data pipeline: `import_external_cards` refreshes bonuses/fees from the andenacitelli community API | ✅ Done (monthly cron wiring happens at deploy, Phase 3) |
| 5 | Cleanup: dead deps/scripts removed, `manage_project.py` menu entries | ✅ Mostly done (see backlog) |

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
| S3 | Issuer eligibility rules engine (see below) — behind-the-scenes "can you even get this card/bonus" checks feeding next-card selection, plus an eligibility note on recommendation cards in the UI | Planned |
| — | **Goals with sequencing** (e.g., Southwest Companion Pass: time two bonuses to land after Jan 1) — explicitly **deferred**; it's a goal, not a weighting, and depends on the bonus-sequencing backlog item | Deferred |

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

### S3 detail: issuer eligibility rules (verified via web research 2026-06-12)

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

**Gaps in the current implementation** (`roadmaps/recommendation_engine.py`,
`_is_eligible_for_card`): the existing 5/24 check is hardcoded to issuer name "chase",
counts ALL the user's cards including business cards (wrong per the table above), and
uses `24*30 days` as the window. No bonus-eligibility rules exist at all. **Data gap**:
modeling bonus rules needs a per-UserCard "bonus earned" date (approximate from
`opened_date` + ~3 mo when unknown) and `card_type` awareness in the count — both exist
on the models, neither is used here. Rules themselves should be data
(Issuer fields + card `metadata.bonus_eligibility`), not more name-matching branches.

## Backlog (known, not yet done)

- **Recalibrate 22 stale scenario expectations** — engine rework changed verdicts/values;
  math integrity passes on all 53 scenarios but 22 expectation files predate the rework.
  Workflow: `RUN_ALL_SCENARIOS=1 python manage.py test cards.test_json_scenarios`, then
  per failure `python manage.py run_scenario "<name>" --explain` and update the JSON only
  after hand-confirming the new number.
- **Quick-recommendation serializer footgun** (`roadmaps/serializers.py`,
  `generate_recommendations`): deletes and recreates the user's stored UserCards/spending/
  credit prefs from the form payload on every quick run. Fine for a single dev user; will
  destroy real users' saved profiles. Defuse before opening to anyone else.
- **Ownership endpoint consolidation** (Phase 5 leftover): `users/` duplicates some
  `cards/` ownership endpoints; consolidate on `cards/`.
- **UX: negative `bonus_shift` line items** confused at least one user (the user). Options:
  group under a "Cost to earn the bonus" subheading, or collapse to a single net line.
- **Future feature: bonus sequencing** — each apply's shift plan is an independent
  counterfactual today; sequencing multiple signup bonuses over time is the actual
  "roadmap" the product is named for. (Also the prerequisite for the deferred
  goals/Companion Pass work in the Strategies section above.)
- **Deploy loose ends** (2026-06): after Jamie's first Google login on production,
  promote his user to staff/superuser via the PythonAnywhere console; consider revoking
  the PythonAnywhere API token that was used during deployment.

## Verification quick reference

- Acceptance scenario: `python manage.py run_scenario "Jamie Real" --explain`
- Full scenario sweep: `RUN_ALL_SCENARIOS=1 python manage.py test cards.test_json_scenarios`
- Standard tests: `python manage.py test` (36 tests)
- Full-sweep baseline (2026-06-12): `FAILED (failures=21, errors=7)` — all pre-existing
  stale expectations/test-DB data gaps; any change to these numbers means a regression
