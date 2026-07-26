# CLAUDE.md

Guidance for Gemini, Antigravity, and Claude Code working in this repository.

## 🚀 Core Product Promise
Credit Card Guru is a Django-based optimization platform recommending card portfolios (apply/keep/cancel) based on real user spending. The core promise is **trustworthy math**: every recommendation's value must be reproducible from its visible line items.

## 🛠️ Verification Gates (Run before declaring tasks done)
Ensure all test suites pass cleanly after any changes:

```bash
# Standard test suite (230 tests as of 2026-07-26; must be OK, 0 failures)
venv/bin/python manage.py test

# Full scenario sweep (all scenarios in data/tests/scenarios/*.json must pass)
RUN_ALL_SCENARIOS=1 venv/bin/python manage.py test cards.test_json_scenarios

# Run specific scenario (with line-item math explanation)
venv/bin/python manage.py run_scenario "Jamie Real" --explain

# Run JavaScript rendering smoke tests (Node.js)
node scripts/test_roadmap_results.js

# Run Playwright E2E UI test suite
venv/bin/pytest tests/e2e/ -v
```

## 📋 General Development Rules
- **Python Environment**: Always run Python via the project virtual environment: `venv/bin/python manage.py <command>`. Never install packages outside the venv.
- **Dev Server**: Do not start `runserver` unless explicitly asked. The developer/user runs the dev server.
- **Git Branch**: All work is committed directly to the `main` branch.
- **Status Updates**: Status and planning live in Obsidian, **not this repo** — `areas/work/coding/side-projects/mycreditcard.guru/`. Update the story file and `stories/README.md`'s CURRENT POSITION block there, not a doc in this repo. For a one-off task, this file is the whole context; don't go looking for planning docs.
- **Help Updates**: When adding/modifying user-facing features (roadmap settings, math logic, multiplayer support, credits), always update `templates/help.html` to match.

## 🗂️ Core Documentation Map
For deep dives into the application architecture, models, and logic, refer to:
- **[COMPREHENSIVE_DOCUMENTATION.md](file:///Users/jamiehouston/src/jamie-houston/mycreditcard.guru/docs/COMPREHENSIVE_DOCUMENTATION.md)**: Architecture overview, core Django model details, relationships, API endpoints list, frontend pages map, and development workflows.
- **[ENGINE.md](file:///Users/jamiehouston/src/jamie-houston/mycreditcard.guru/docs/ENGINE.md)**: Recommendation Engine logic, optimization formulas, points pooling, multiplayer household routing, 12-month bonus capacity sequencing, upcoming large purchase mode, and "Pays for Itself" tracking.
- **[README_TESTING.md](file:///Users/jamiehouston/src/jamie-houston/mycreditcard.guru/docs/README_TESTING.md)**: Details on the JSON scenario test suite (`data/tests/scenarios/*.json`) and how to recalibrate expectations.
- **[CARD_IMPORT_GUIDE.md](file:///Users/jamiehouston/src/jamie-houston/mycreditcard.guru/docs/CARD_IMPORT_GUIDE.md)**: Explanation of system card JSON formats and how external import commands work.
- **[OPERATIONS.md](file:///Users/jamiehouston/src/jamie-houston/mycreditcard.guru/docs/OPERATIONS.md)**: Verification quick reference and recurring maintenance (monthly card sync, cron, data hygiene).

These are **conditional** — read one when the task touches its area, not by default.

## 🗃️ Card Imports & Maintenance
- **Import Single Card File**: `venv/bin/python manage.py import_cards data/input/cards/<issuer>.json`
- **Import Categories**: `venv/bin/python manage.py import_cards data/input/system/spending_categories.json`
- **Seed Spending Credits**: `venv/bin/python manage.py import_spending_credits`
- **Full Clean Setup**: `venv/bin/python setup_data.py`
- **External Offers Sync**: Run `venv/bin/python manage.py import_external_cards` monthly to sync card data with the community offers API.

## Subagents

The `awesome-claude-agents` pack this file used to reference (`@django-backend-expert`,
`@django-api-developer`, `@django-orm-expert`, `@performance-optimizer`) was
uninstalled on 2026-07-26 — those names no longer resolve. Use the built-in
`Explore` agent for broad codebase searches and `Plan` for implementation
design; spawn subagents only when Jamie asks.

### Tech stack (detected)

Django 5.1.3 · Django REST Framework · django-allauth · Django ORM ·
SQLite (dev) / PostgreSQL (prod) · WhiteNoise · django-cors-headers ·
django-filter · Gunicorn · django-extensions · Pillow
