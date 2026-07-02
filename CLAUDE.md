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
venv/bin/python manage.py test                                   # standard suite (54 tests)
RUN_ALL_SCENARIOS=1 venv/bin/python manage.py test cards.test_json_scenarios   # full sweep: 61/61 must pass
venv/bin/python manage.py run_scenario "Jamie Real" --explain    # acceptance: every line item reconciles
```

- The full sweep passes 61/61 as of 2026-07-01. Any failure is a regression.
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
  (`BONUS_CAPACITY_MONTHS`); excess applies are deferred.
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
- `templates/index.html` — the roadmap page (all inline JS). Preferences:
  empty max annual fee = no max; empty max recommendations = 1.

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
