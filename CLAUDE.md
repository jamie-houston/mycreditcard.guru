# CLAUDE.md

Guidance for Claude Code (claude.ai/code) working in this repository.

## What this is

Credit Card Guru (mycreditcard.guru) — a Django app that recommends credit
card portfolios (apply/keep/cancel) from a user's real spending. The core
product promise is **trustworthy math**: every recommendation's headline
value must be reproducible from its visible line items. Protect that above
all else.

Production: https://foresterh.pythonanywhere.com (PythonAnywhere, **MySQL** —
see `docs/DEPLOYMENT_GUIDE.md`, including why SQLite is dev-only there).
Local dev uses SQLite. Current status and backlog live in
`docs/PROJECT_STATUS.md` — read it before starting work, update it when
phases complete or requirements change.

## Working rules

- Run Python via the project venv: `venv/bin/python manage.py ...`
  Never pip install outside the venv.
- Don't start `runserver` for Jamie — he runs the dev server himself.
- Git branch is `main`. Deploys happen by pushing (server has a post-merge
  hook + `deploy.sh`).
- When you change code or requirements: update `docs/PROJECT_STATUS.md`
  (status/backlog) and this file (architecture) in the same commit.

## Verification gates (run before calling anything done)

```bash
venv/bin/python manage.py test                                   # standard suite (103 tests)
RUN_ALL_SCENARIOS=1 venv/bin/python manage.py test cards.test_json_scenarios   # full sweep: 67/67 must pass
venv/bin/python manage.py run_scenario "Jamie Real" --explain    # acceptance: every line item reconciles
```

- The full sweep passes 67/67 as of 2026-07-15. Any failure is a regression.
- `run_scenario` (CLI) runs against the **dev DB**, so real cards pollute
  fixture pools. For scenario debugging use the test DB instead:
  `DUMP_SCENARIOS=1 RUN_ALL_SCENARIOS=1 venv/bin/python manage.py test cards.test_json_scenarios`
  prints every scenario's full results.
- The engine logs a reconciliation error if a headline value stops matching
  its line items (line items + signup bonus − fee = headline, within $1).
  If that fires, the math regressed — fix the math, never the guard.

## Architecture map

Three Django apps: `cards/` (card database, spending profiles, ownership),
`roadmaps/` (recommendation engine + API), `users/` (auth via allauth,
preferences). Anonymous users work via session keys.

Key modules:

- `roadmaps/recommendation_engine.py` — the engine. Portfolio selection
  (greedy, strategy-weighted) is separate from displayed math (allocation-
  consistent): **selection weights/boosts may shape which cards win, but
  displayed dollars always come from `_calculate_portfolio_allocation`**
  (best-rate-per-category with cap rollover; totals always equal the user's
  actual spending). Signup bonuses model where the money comes from
  (`_signup_bonus_plan`: organic / shifted-with-opportunity-cost /
  unreachable→$0). Bonus capacity: counted bonuses consume
  `requirement ÷ monthly spend` months; applies must fit 12 months
  (`BONUS_CAPACITY_MONTHS`) — enforced by **`_bonus_capacity_plan(cards)`**
  (Phase E, near `_bonus_months_needed`), the single capacity authority.
  It sorts candidate applies by bonus value density (`bonus_value/months`
  desc, total-order tie-break on bonus value then `card.id`) and walks the
  12-month budget all-or-nothing, returning which bonuses are `counted`
  and each one's `start_month`. **Selection is capacity-aware**: the three
  portfolio-valuation sites (`_calculate_scenario_portfolio_value`'s bonus
  sum and its efficiency-boost block, and the `calculate_portfolio_value`
  closure in `_optimize_card_portfolio`) all count only `counted` bonuses,
  so an over-budget bonus can't inflate a portfolio's score — it can still
  win a slot on ongoing value alone. Pre-sort scoring
  (`_select_optimal_card_combination`) keeps the full bonus (capacity is
  portfolio-relative; a solo card has the whole budget) except a defensive
  cap when a bonus can't fit even alone. Display
  (`_generate_portfolio_optimized_recommendations`) recomputes the plan
  over the final apply set and shows `$0` + a "Signup bonus deferred" info
  line + `bonus_deferred=True` for anything not counted — a third pathway
  alongside the existing issuer-ineligibility (`bonus_block`) one.
  `generate_quick_recommendations`'s assembly loop is now just a **safety
  net** (logs a warning if a positive bonus still lands in
  `deferred_applies` — selection should have already zeroed it) and
  annotates each apply with `recommended_month`/`bonus_months_needed`
  (bonus-less applies get `0`/`0.0` — "apply whenever") plus a
  `bonus_capacity.timeline` (applies ascending by start_month, bonus-less
  last) and `bonus_capacity.bonus_less_applies` list. Frontend timing
  display (Step 6: "Apply in ~N months") is not yet built — see
  `docs/PLAN_PHASE_E_BONUS_SEQUENCING.md` for remaining scope. Southwest
  Companion Pass timing is explicitly unmodeled; the density sort-key is
  where that would slot in later.
- `roadmaps/strategies.py` — strategy presets are data, not code
  (filters + max_recommendations + selection weights). UI effort question
  maps onto these.
- `roadmaps/eligibility.py` — issuer rules are data, not code. Application
  rules (Chase 5/24, BofA 2/3/4, CapOne 1/6mo, family blocks) exclude cards
  from applies; bonus rules (Amex lifetime, Citi 48-month, Sapphire/
  Southwest via card `metadata.bonus_eligibility`) zero the bonus but keep
  the card competing on ongoing value, with a user-facing note. Evaluated
  against full card history INCLUDING closed cards
  (`UserCard.bonus_earned_date`, approximated when blank).
- `roadmaps/serializers.py` — quick-recommendation writes the request
  payload into profile tables to feed the engine, inside an
  **always-rolled-back transaction**. Never let it persist; saving profiles
  is `/api/users/data/`'s job.
- `roadmaps/views.py` `quick_recommendation_view` — anonymous users need a
  durable session created **before** `generate_recommendations()`'s
  transaction starts, or `request.session.create()` gets rolled back with
  everything else and the anon user ends up with no session at all. The
  view sets `response_data['generated_at'] = timezone.now().isoformat()`
  itself (Phase E) — previously only the GET current/shared endpoints
  carried this field, but sequencing's calendar-month display needs a base
  date on the live path too. After generation, `_persist_current_roadmap()`
  resolves the REAL profile (never the scratch one from the rollback) and
  `update_or_create`s a `Roadmap(name="Current Roadmap")` +
  `RoadmapCalculation.calculation_data = {response, request, generated_at}`
  — reusing the SAME `generated_at` the caller already set on
  `response_data`, so the live response and the persisted copy always
  agree — a normal, committed write that runs *after* the rollback.
  `GET /api/roadmaps/current/` (`current/` in
  roadmaps/urls.py) reads it back read-only (no session/profile
  auto-creation; 404 = nothing generated yet) via `get_current_roadmap(request)`
  (`roadmaps/models.py`) — the shared auth/anon-session lookup, also used by
  `cards/views.py` `landing_view` (see below) and `index_view`'s
  `has_current_roadmap` context flag. Don't reintroduce a
  "mark session unmodified" hack here — that was the OLD fix for the
  rollback trap, and it silently suppresses the Set-Cookie header needed
  for the session to actually reach the anon user's browser.
- `cards/views.py` `landing_view`/`index_view` — `landing_view` (`/`)
  redirects straight to `/roadmap/` for any visitor who already has a
  persisted Current Roadmap (`get_current_roadmap(request)`), so returning
  users skip the marketing landing page. `index_view` passes
  `has_current_roadmap` into `templates/index.html` only to pick the
  *initial* CSS display state (avoids a builder-flash on paint) — it does
  not own the view-mode toggle; that's client-side (see below).
- `templates/index.html` — the roadmap page (all inline JS). Preferences:
  empty max annual fee = no max; empty max recommendations = 1. The builder
  (strategy/preferences/spending/sticky-footer) is wrapped in
  `#roadmapBuilder`; `setRoadmapViewMode('results'|'builder')` shows/hides it
  as a unit and swaps the `#pageHeading`/`#pageSubtitle` text, toggled
  manually via the `#resultsHeader` "Update roadmap" bar
  (`toggleRoadmapBuilder()`, same accordion pattern as Preferences/Monthly
  spending). `loadCurrentRoadmap()` (called on page load) is the
  authoritative source of truth for initial view mode — it opens on results
  ("Your Roadmap") if a Current Roadmap exists, builder otherwise, correcting
  any stale `has_current_roadmap` server hint within one round trip;
  `getRecommendations()` settles back into results mode on a successful
  generation. The results renderer lives in `static/js/roadmap-results.js`
  (`renderRoadmapResults(data, opts)`), shared with the (planned) public
  shared-roadmap page via `opts.readOnly`; index.html calls it both from
  live generation and from `loadCurrentRoadmap()` on page load (restores
  the persisted Current Roadmap with a "Generated on {date}" banner).
  `renderRoadmapResults()` renders a "Card summary" table
  (`_roadmapSummaryTableHtml`) above "Best card per category" and the
  detailed Apply/Keep/Cancel sections (which are unchanged below it) — one
  row per recommendation with Rewards / Signup Bonus / Benefits / Fee
  columns that sum to Value/yr by construction: Rewards is every non-credit
  `rewards_breakdown` line (`_roadmapRewardsValue`, includes `bonus_shift`
  opportunity-cost adjustments), Benefits is the credit lines
  (`_roadmapBenefitsValue`), Signup Bonus is `rec.signup_bonus_value`
  (apply only), Fee is `rec.card.effective_annual_fee` (already the
  waived-year-aware fee the engine's reconciliation guard checks against).
  Don't add a column here without checking it's actually one of the terms
  in that guard's `line_total + signup_bonus_value - fee_in_headline`
  equation, or the columns will stop adding up to Value/yr.
  "Remove from my cards" on keep/cancel recommendations soft-closes via
  `POST /api/users/cards/toggle/` (auth) or localStorage (anon) — never the
  hard-delete `cards/user-cards/<id>/delete/` endpoint, which would erase
  eligibility history. Note: `/api/users/data/`'s bulk save (`users/
  serializers.py` `UserDataSerializer.create`) only hard-deletes ACTIVE
  (`closed_date__isnull=True`) cards missing from the posted list — it used
  to delete soft-closed rows too (since they're never in that list), which
  would have erased a card's closed_date on the very next roadmap
  generation (`saveCurrentData()` calls this endpoint every time).
- `cards/views.py` `credit_preferences_view` (`GET`/`PUT
  /api/cards/credit-preferences/`) — server-persisted
  `UserSpendingCreditPreference` rows (which spending credits a user values),
  auth + anon (session-key) capable. Distinct from the quick-rec
  serializer's scratch `spending_credit_preferences` slug list (roadmaps/
  serializers.py, True-only, inside the rollback) — this is the durable
  read/write path; PUT upserts True *and* False rows so an explicit opt-out
  survives. Stackability (`SpendingCredit.stackable`, curated data) is
  separate: it controls engine dedup (`_allocate_portfolio_credits`), not
  which credits count at all.
- `templates/base.html` `UserDataManager.getCreditPreferences()`/
  `saveCreditPreferences()` — the frontend's only entry point to the
  endpoint above; no auth/anon branching needed there (the endpoint already
  handles both via session). `index.html` PUTs the full checkbox state
  (true and false) on every change; `profile.html`'s `loadCreditsProfile()`
  reads it to grey out un-opted-in credits at $0 and, for
  `stackable: false` credits spanning multiple owned cards, count only the
  highest-value card (mirrors `_allocate_portfolio_credits`'s tiebreak) with
  a "counted once — on {card}" note on the rest. The generic card-detail
  modal (`templates/base.html` `populateCardCredits()`, opened via
  `openCardModal()` from anywhere — cards list, category detail, profile,
  roadmap results) reads/writes the same preferences and shows the same
  checkbox toggle for any credit backed by a `spending_credit` (calling
  `toggleModalCreditUsage()`, which re-renders just the credits section);
  category-based credits (`credit.category`, no `spending_credit`) have no
  checkbox there since the engine counts them automatically whenever the
  user has matching spending (`_counted_card_credits`), not via opt-in.
  `_formatCreditValue()` shows the per-occurrence rate alongside the annual
  total for `times_per_year > 1` credits (e.g. "$7/mo = $84/yr") instead of
  just the raw per-occurrence value.
- Roadmap sharing mirrors `UserSpendingProfile`'s privacy/`share_uuid`
  pattern (cards/models.py) but on `Roadmap` and **anon-capable** (a
  session-owned Current Roadmap is a first-class case; profile sharing
  requires auth). `GET/POST /api/roadmaps/current/share/`
  (`current_roadmap_share_view`, roadmaps/views.py) resolves the roadmap via
  `get_current_roadmap(request)` — no `is_authenticated` gate. `GET
  /api/roadmaps/shared/<uuid>/` (`shared_roadmap_data_view`) is the public,
  no-auth data endpoint, built straight from `calculation_data` (never a
  profile serializer). `/roadmap/shared/<uuid>/` (`shared_roadmap_view` →
  `templates/shared_roadmap.html`) is the public page — it's the first real
  caller of `renderRoadmapResults(data, {readOnly: true})` from
  `roadmap-results.js` (built in Phase B, unused until now). Share UI lives
  in index.html's `#resultsHeader` (a share icon opens a collapsible
  private/public toggle + copy-link, mirroring profile.html's privacy
  panel). `_persist_current_roadmap`'s `update_or_create` only ever sets
  `max_recommendations` in `defaults`, so regenerating a roadmap preserves
  its `privacy_setting`/`share_uuid` — don't add sharing fields to that
  `defaults` dict.

## Data

- `data/input/cards/*.json` (per issuer) is the source of truth for curated
  card detail. `verified: true` is the import watchlist (~27 of ~160 cards).
  `git diff data/input/cards/` is the offer-change audit trail.
- `import_external_cards` refreshes churn fields (bonuses/fees/discontinued)
  from the andenacitelli community API by editing those JSONs in place.
  Production runs it monthly (scheduled task, 1st @ 09:15 UTC); run it
  locally ~monthly too and commit, or the repo drifts behind the server.
- `import_cards <file>` imports a card file (or
  `data/input/system/spending_categories.json`). `import_spending_credits`
  seeds SpendingCredits. `setup_data.py` does a full fresh setup.
- Hand-curated metadata (e.g. `bonus_eligibility`, `application_family`,
  `reward_value_multiplier`) lives in the card JSONs and survives the
  external refresh.

## Scenario test system

JSON scenarios in `data/tests/scenarios/*.json` run through the REAL engine
(`cards/test_base.py` reuses `run_scenario`'s plumbing).

- Fixture cards: `data/tests/cards.json`. Every bonus must have a realistic
  structured `signup_bonus` requirement — a bonus without one is free money
  that corrupts every scenario it touches.
- Owned cards: `"slug"` (opened ~6 months ago) or a history dict
  `{"card": slug, "opened_days_ago": 90, "closed_days_ago": 30,
  "bonus_earned_days_ago": 60}` for eligibility scenarios (days-ago keeps
  them evergreen). Owned cards MUST appear in `available_cards` (loud error).
- A top-level `"strategy"` key applies a preset; a top-level
  `"max_recommendations"` beats the count-derived default (needed when a
  scenario must allow more applies than it expects, e.g. capacity tests).
- Real cards referenced by a scenario (e.g. jamie_real) are imported into
  the test DB on demand from `data/input/cards/` via the import machinery.
- Recalibration workflow: run the sweep with `DUMP_SCENARIOS=1`, hand-confirm
  the new numbers from the dump, then update the expectation JSON. Never
  update an expectation to a number you haven't verified line-by-line.

## Docs

- `docs/PROJECT_STATUS.md` — where we are, backlog, S1–S4 design notes,
  eligibility rules research (with sources). **Keep it current.**
- `docs/DEPLOYMENT_GUIDE.md` — PythonAnywhere deploy, MySQL migration
  incident, scheduled tasks.
- `PRD.md` — original product spec (the *what*).
