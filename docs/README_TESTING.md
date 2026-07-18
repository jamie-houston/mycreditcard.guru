# Data-Driven Testing Guide

This guide explains how to use the JSON-based scenario test suite for credit
card recommendations. For day-to-day verification commands (what to run
before calling anything done), see `docs/PROJECT_STATUS.md`'s "Verification
quick reference" and `CLAUDE.md`'s "Verification gates" — this doc is about
how the scenario system itself works and how to add to it.

## Test Data vs Production Data

- **Django test framework** (`manage.py test ...`) creates an isolated test
  database — production data is never touched.
- **`run_scenario` management command** runs against your actual dev
  database (SQLite locally). Real cards in that DB can pollute fixture pools
  for scenarios that don't pin `available_cards` — use the Django test
  framework for anything you need trustworthy, and reserve `run_scenario`
  for interactive debugging and the `--explain` acceptance check.

## How scenarios are organized

- **`data/tests/scenarios/*.json`** — one JSON file per topic (not a single
  file): `basic_profiles.json`, `portfolio_optimization.json`,
  `zero_fee_cards.json`, `spending_credits.json`,
  `card_count_optimization.json`, `edge_cases.json`, `signup_bonus.json`,
  `strategies.json`, `eligibility.json`, and `jamie_real.json` (the
  hand-verified acceptance scenario using Jamie's real cards). The loader
  globs every `*.json` in the directory — `index.json` is a human-readable
  manifest of what's in each file, not something the loader consults.
- **`data/tests/cards.json`** — the fixture card pool shared by scenarios
  that don't reference real cards.
- **`cards/test_json_scenarios.py`** — Django `TestCase`s, one per named
  scenario, built on the shared plumbing in **`cards/test_base.py`**
  (`JSONScenarioTestBase`).
- **`cards/management/commands/run_scenario.py`** — CLI runner for one
  scenario, all scenarios, or `--list`.

## Running tests

```bash
# Standard suite (includes a handful of named scenario tests)
venv/bin/python manage.py test

# Full sweep — every scenario in data/tests/scenarios/*.json (currently 61)
RUN_ALL_SCENARIOS=1 venv/bin/python manage.py test cards.test_json_scenarios

# Print full per-scenario results (recalibration workflow)
DUMP_SCENARIOS=1 RUN_ALL_SCENARIOS=1 venv/bin/python manage.py test cards.test_json_scenarios

# CLI — list scenarios / run one against the dev DB / run with math shown
venv/bin/python manage.py run_scenario --list
venv/bin/python manage.py run_scenario "Jamie Real" --explain
venv/bin/python manage.py run_scenario --all --verbose
```

Without `RUN_ALL_SCENARIOS=1`, `test_json_scenarios` only runs a named subset
(useful for fast local iteration); the full 61-scenario sweep is the gate
that must pass before calling any change done (see CLAUDE.md).

## Adding a new scenario

Add an entry to the array in the relevant `data/tests/scenarios/<topic>.json`
file (or create a new topic file — no registration needed, the loader globs
the directory):

```json
{
  "name": "Your Scenario Name",
  "description": "Brief description of what this tests",
  "user_profile": {
    "spending": {
      "dining": 300,
      "groceries": 500,
      "gas": 200,
      "travel": 100,
      "other": 400
    },
    "preferences": {
      "max_annual_fee": 100,
      "preferred_reward_type": "cashback"
    },
    "spending_credit_preferences": ["uber_eats"]
  },
  "owned_cards": ["card-slug-if-user-already-has-it"],
  "available_cards": [
    {
      "name": "Test Card",
      "issuer": "chase",
      "annual_fee": 95,
      "signup_bonus_amount": 20000,
      "signup_bonus_type": "points",
      "signup_bonus": {"amount": 3000, "requirement_type": "spend", "months": 3},
      "primary_reward_type": "points",
      "metadata": {"reward_value_multiplier": 0.015},
      "reward_categories": [
        {"category": "dining", "rate": 3.0, "type": "points", "max_spend": 6000},
        {"category": "other", "rate": 1.0, "type": "points"}
      ]
    }
  ],
  "expected_recommendations": {
    "count": 1,
    "actions": ["apply"],
    "min_total_value": 200,
    "must_include_cards": ["Test Card"],
    "reasoning_must_contain": ["dining", "3.0x"]
  }
}
```

Notes on the fields above (see CLAUDE.md's "Scenario test system" section
for the authoritative rules):

- Every `signup_bonus` **must** have a realistic structured requirement — a
  bonus without one is free money that corrupts any scenario that touches it.
- `owned_cards` entries can be a plain slug (opened ~6 months ago) or a
  history dict `{"card": slug, "opened_days_ago": 90, "closed_days_ago": 30,
  "bonus_earned_days_ago": 60}` for eligibility scenarios. Owned cards must
  also appear in `available_cards`, or the loader raises a loud error.
- A top-level `"strategy"` key applies a strategy preset (see
  `roadmaps/strategies.py`); a top-level `"max_recommendations"` overrides
  the count-derived default.
- Real cards (e.g. `jamie_real.json`) are imported on demand from
  `data/input/cards/` via the normal import machinery, not from the fixture
  pool.

### Spending categories

Current categories (`data/input/system/spending_categories.json`): `dining`,
`travel`, `groceries`, `gas`, `entertainment`, `shopping`, `transportation`,
`drugstores`, `telecommunications`, `other`, `business`.

### Issuers

Current issuer files live in `data/input/cards/` — one per issuer (Chase,
American Express, Capital One, Bank of America, Citi, Discover, Barclays,
Wells Fargo, US Bank, PenFed, FNBO, Synchrony, and a few smaller ones). Use
the matching issuer slug in `available_cards`.

## Recalibration workflow

When a change legitimately shifts expected numbers: run the sweep with
`DUMP_SCENARIOS=1` (see command above), hand-confirm each new number against
the printed line items, then update the expectation JSON. **Never update an
expectation to a number you haven't verified line-by-line** — that's how
untrusted math creeps back in.

## Frontend (JS) smoke coverage

This repo has no JS test framework — client-side behavior is normally
verified by hand (see `docs/MANUAL_TEST_PLAN.md`). The one exception is
`scripts/test_roadmap_results.js`, a plain Node script (just `assert` +
`vm`, no dependency added) covering the pure, DOM-free helpers in
`static/js/roadmap-results.js` (Phase E's `_roadmapTimingLabel`, plus the
older `_roadmapFormatSigned`/rewards-vs-benefits split). Run it with:

```bash
node scripts/test_roadmap_results.js
```

## Troubleshooting

- **Missing categories / invalid issuers** — check the current lists above
  against your scenario JSON.
- **Owned-card loud error** — the card slug in `owned_cards` isn't present
  in `available_cards`.
- **Reconciliation errors in the log** — a recommendation's line items +
  signup bonus − fee don't sum to the headline within $1. Fix the math, not
  the guard (see CLAUDE.md).
