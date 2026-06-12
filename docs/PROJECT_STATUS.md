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
| 3 | Deploy: refresh PythonAnywhere per `docs/DEPLOYMENT_GUIDE.md` | ⏸ Blocked on PythonAnywhere login (Jamie) |
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
  "roadmap" the product is named for.

## Verification quick reference

- Acceptance scenario: `python manage.py run_scenario "Jamie Real" --explain`
- Full scenario sweep: `RUN_ALL_SCENARIOS=1 python manage.py test cards.test_json_scenarios`
- Standard tests: `python manage.py test` (29 tests)
