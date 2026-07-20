# Value points-denominated card credits at real redemption worth (DB-backed)

> Plan authored 2026-07-20 for execution in a fresh session. Self-contained:
> all research findings, decisions, and exact file/line anchors are below.

## Context

`CardCredit.annual_value` and the roadmap engine treat a credit's `value` as raw
USD regardless of `CardCredit.currency`. 13 credits across 8 cards are denominated
in points, so e.g. a **7,500-point Southwest anniversary bonus adds $7,500** to a
card's "Estimated Annual Value" instead of its ~$105 redemption worth. This was the
`### Open` item in [PROJECT_STATUS.md](../PROJECT_STATUS.md). Decision (Jamie):
fix it **DB-backed** — reuse the existing `PointsProgram`/`PointsValuation` infra so
values are admin/user-overridable, not hardcoded.

Two findings shape the fix:

1. **The valuation chokepoint is one line.** Every valuation site (single-card
   value, portfolio dedup allocation, `pays_for_itself`, optimizer scenario
   scoring, the displayed breakdown) funnels through
   `roadmaps/engine/calculators/credits.py:53`:
   `annual_value = float(card_credit.value) * card_credit.times_per_year`.
   Discounting here propagates to all five sites automatically (verified: the
   optimizer/orchestrator only ever consume `CreditsCalculator`'s output;
   `grep -rn currency roadmaps/` returns nothing today).

2. **Two of the 13 "points" credits are mislabeled dollar amounts** and must be
   retagged, not discounted (confirmed by Jamie):
   - Hilton Honors Business (`hilton-honors-business`,
     `data/input/cards/american_express.json`) — *"$60 Hilton credit per quarter"*,
     value **240**, currency `HILTON` → really a **$240 USD** statement credit.
   - World of Hyatt (`world-of-hyatt`, `data/input/cards/chase.json`) —
     *"FNC @ Category 1-4 Property"*, value **225**, currency `HYATT` → a free-night
     cert whose 225 is already a **$USD** estimate.

   After retag, the genuine points credits are the remaining **11**:
   SOUTHWEST (4), WYNDHAM (3), UNITED (2), JETBLUE (2).

Currently **no** points program is defined for these currencies —
`data/input/system/points_programs.json` only has `chase_ultimate_rewards` and
`amex_membership_rewards`, and `CardCredit.currency` is a free-text
`CharField(max_length=20, default='USD', blank=True)` (no choices, no FK, `cards/models.py:230`)
with no link to any program. So the DB approach means seeding 4 programs and giving
`PointsProgram` a way to resolve a credit currency string.

### Full non-USD credit inventory (for reference)
| card (slug) | file | description | value | tpy | currency |
|---|---|---|---|---|---|
| hilton-honors-business | american_express.json | $60 Hilton credit per quarter | 240 | – | HILTON → **retag USD** |
| world-of-hyatt | chase.json | FNC @ Category 1-4 Property | 225 | – | HYATT → **retag USD** |
| jetblue | barclays.json | 5k yearly anniversary credit | 5000 | – | JETBLUE |
| jetblue-premier | barclays.json | 5k yearly anniversary credit | 5000 | 1 | JETBLUE |
| wyndham-rewards-earner | barclays.json | Anniversary bonus points | 7500 | – | WYNDHAM |
| wyndham-rewards-earner-business | barclays.json | Anniversary bonus points | 15000 | – | WYNDHAM |
| wyndham-rewards-earner-plus | barclays.json | Anniversary bonus points | 7500 | 1 | WYNDHAM |
| southwest-rapid-rewards-plus-credit-card | chase.json | Anniversary Points | 3000 | 1 | SOUTHWEST |
| southwest-premier | chase.json | Anniversary Points | 6000 | 1 | SOUTHWEST |
| southwest-premier-business | chase.json | Anniversary Points | 6000 | 1 | SOUTHWEST |
| southwest-rapid-rewards-priority-credit-card | chase.json | Anniversary Points | 7500 | 1 | SOUTHWEST |
| united-explorer | chase.json | 10k award flight discount | 10000 | – | UNITED |
| united-quest | chase.json | 10k award flight discount | 10000 | – | UNITED |

(`tpy` omitted defaults to 1 in the model.)

## Design

### 1. `PointsProgram.currency_code` (model + migration)
Add `currency_code = models.CharField(max_length=20, blank=True, default='')` to
`PointsProgram` (`cards/models.py:26-34`). Lets a credit's currency string
(`'SOUTHWEST'`) resolve straight to a program+valuation — no separate mapping table,
fully data-driven. `makemigrations cards` + `migrate`.

### 2. Seed 4 programs in `data/input/system/points_programs.json`
Append entries carrying `currency_code` + `default_valuation` (dollars/point).
Conservative baselines (admin/user overridable via `PointsValuation`):

| name | slug | currency_code | default_valuation |
|---|---|---|---|
| Southwest Rapid Rewards | `southwest_rapid_rewards` | `SOUTHWEST` | `0.0140` |
| Wyndham Rewards | `wyndham_rewards` | `WYNDHAM` | `0.0110` |
| United MileagePlus | `united_mileageplus` | `UNITED` | `0.0120` |
| JetBlue TrueBlue | `jetblue_trueblue` | `JETBLUE` | `0.0130` |

Update `import_points_programs` (`cards/management/commands/import_cards.py:119-150`)
to persist `currency_code` in both the create-`defaults` and the update branch.

### 3. Reusable valuation helper — new `cards/valuations.py`
Factor the inline lookup pattern from `roadmaps/redemption.py:62-73` into shared
helpers:

```python
def value_per_point(program, user=None):
    """Dollars per point: user override -> system default (user=None) -> None."""
    val = None
    if user and getattr(user, 'is_authenticated', False):
        val = PointsValuation.objects.filter(points_program=program, user=user).first()
    if not val:
        val = PointsValuation.objects.filter(points_program=program, user=None).first()
    return float(val.value) if val else None

def credit_currency_rate(currency, user=None):
    """Dollars per unit for a CardCredit.currency. USD/blank -> 1.0."""
    if not currency or currency.upper() == 'USD':
        return 1.0
    program = PointsProgram.objects.filter(currency_code=currency).first()
    if program:
        vpp = value_per_point(program, user)
        if vpp is not None:
            return vpp
    logger.warning("No valuation for credit currency %r; defaulting to 0.01/pt", currency)
    return 0.01   # conservative safety net for any unmapped non-USD currency
```

Unmapped non-USD → **0.01/pt + a logged warning** (never the old raw-dollar face
value), so a future unseeded points currency degrades safely instead of re-opening
the bug. After the retag, no current data hits this path.
*(Optional cleanup: point `redemption.py`'s inline lookup at the new `value_per_point`.)*

### 4. Apply the rate at the chokepoint — `roadmaps/engine/calculators/credits.py`
In `counted_card_credits`, resolve the rate (memoized per-engine so hot optimizer
loops don't re-query) and multiply:

```python
rate = self._currency_rate(card_credit.currency)   # 1.0 for USD
annual_value = float(card_credit.value) * card_credit.times_per_year * rate
```

`_currency_rate` memoizes on the engine (mirror `_credit_prefs`/`_card_credits_cache`
at `credits.py:19-35`), keyed by currency string, reading
`getattr(self.engine.profile, 'user', None)` (nullable for anonymous/mock scenarios —
see `orchestrator.py:29` `if profile.user:`) via `credit_currency_rate`.

**Trustworthy-math display:** the breakdown strings at `credits.py:56, 82-84, 93`
render `value` as `$`, which for a points credit would misleadingly show "$5000".
For non-USD credits, show the derivation instead, e.g.
`5,000 SOUTHWEST pts × $0.014 → $70`, so the line item still reconciles to the
discounted dollars that flow into totals. USD credits keep today's `$`-only display.
Store the display-facing dollar figures (per-period + annual) on the entry dict
(`credits.py:58-68`).

### 5. Retag the two mislabeled credits (data fix)
- `data/input/cards/american_express.json` `hilton-honors-business`: drop
  `"currency": "HILTON"` (defaults to USD). Value 240 stays.
- `data/input/cards/chase.json` `world-of-hyatt`: drop `"currency": "HYATT"`. Value 225 stays.

Re-import both files (`import_cards`) so the DB rows match.

## Critical files
- `cards/models.py` — add `PointsProgram.currency_code`.
- `cards/migrations/000X_pointsprogram_currency_code.py` — new migration.
- `cards/valuations.py` — new: `value_per_point`, `credit_currency_rate`.
- `roadmaps/engine/calculators/credits.py` — rate at :53, `_currency_rate` memo, currency-aware display strings.
- `data/input/system/points_programs.json` — 4 new programs.
- `cards/management/commands/import_cards.py` — persist `currency_code` in `import_points_programs`.
- `data/input/cards/american_express.json`, `data/input/cards/chase.json` — retag 2 credits to USD.
- `docs/PROJECT_STATUS.md` — move the currency item from `### Open` to Completed.
- Tests: `cards/tests.py` (helper unit tests) + `roadmaps/tests.py` (`CreditAllocationTests`, class starts ~line 621).

## Verification
1. **New unit tests** — `credit_currency_rate`: USD/blank→1.0; seeded currency→its
   default valuation; user override wins over system default; unmapped non-USD→0.01
   (+ warning). `CreditsCalculator`: a 7,500-pt `SOUTHWEST` credit →
   `annual_value == 105.0` (not 7500); a USD credit still equals face value.
   Existing raw-dollar assertions at `roadmaps/tests.py:756` and `:804-805` use
   USD/no-currency credits and **must stay green** (rate 1.0).
2. **Migration**: `venv/bin/python manage.py makemigrations cards` then `migrate`;
   re-run `import_cards data/input/system/points_programs.json` + the 2 retagged card files.
3. **Shell spot-check**: confirm `world-of-hyatt`/`hilton-honors-business` credits
   are USD, and a Southwest card's credit dollar value reflects the discounted rate.
4. **Regression gates (must stay green):**
   `venv/bin/python manage.py test`,
   `RUN_ALL_SCENARIOS=1 venv/bin/python manage.py test cards.test_json_scenarios`,
   `venv/bin/python manage.py run_scenario "Jamie Real" --explain`,
   `node scripts/test_roadmap_results.js`,
   `venv/bin/python manage.py check`.

## Commit plan
Two commits (Jamie asked to "commit and fix"):
1. **Pending andenacitelli credit-map normalization** — ALREADY ON DISK, uncommitted
   (see "Session state" below): `external_credit_map.json` (Disney / PreCheck /
   Incidental Airline), source-split `compute_proposal` in `import_external_cards.py`,
   `CARD_IMPORT_GUIDE.md`, tests in `cards/test_import_external_cards.py`, and the
   resynced `data/input/cards/*.json`.
2. **This currency-valuation fix** — model/migration, seed programs, helper, engine
   discount, retagged data, tests, PROJECT_STATUS update.

Each commit ends with the `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` trailer.

## Session state carried over (read before starting the new session)
- **Uncommitted work is in the working tree.** The prior task (andenacitelli credit-map
  normalization) is fully implemented and tested but **never committed** — it lives as
  modified/untracked files. `git status` in the new session will show it. Commit #1
  above is that work; verify with `git diff` before committing. Nothing is lost by
  switching sessions — it's all on disk.
- The 3 exploration passes that produced this plan are fully distilled here (chokepoint,
  mislabeled entries, currency inventory, absence of seeded programs). No live agent
  state is needed to execute.

## Out of scope
- Valuing points currencies that never appear on a credit today (ALASKA, DELTA, …) —
  the safety-net 0.01 rate + warning covers them if one ever shows up.
- Threading per-credit currency into the roadmap API payload (`CreditCardListSerializer`
  drops credits entirely; the engine's already-discounted dollar output is what reaches the UI).
- Re-modeling `CardCredit.currency` as an FK — the `currency_code` resolve keeps it
  free-text and backward compatible.
