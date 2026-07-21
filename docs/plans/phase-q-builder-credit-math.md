# Phase Q — Surface Existing Credit Math in the Spending-Input Builder

Status: **Not started.** Scoping complete (this doc). No code written yet.
Tracked in `docs/PROJECT_STATUS.md` (the only Open lettered phase).

## Context

The roadmap builder (`templates/index.html`, the "Monthly spending" section)
already renders a per-category **"Credits You Use"** checkbox list
(`static/js/pages/roadmap.js:550-582`, populated from
`GET /cards/spending-credits/`). Each checkbox shows only the credit's
icon / display name / description / a stackability hint — **no dollar value**.
The builder is otherwise input-only: nothing shows credit *math* until the user
clicks "Get my roadmap" and the results view renders it.

Meanwhile the engine already computes all the credit math we'd want to surface:
- `CardCredit.annual_value` (`cards/models.py:248-254`) — `value × times_per_year
  × rate`, where `rate = credit_currency_rate(currency)` discounts
  points-denominated credits to real redemption dollars (`cards/valuations.py`).
- The single valuation chokepoint `CreditsCalculator` in
  `roadmaps/engine/calculators/credits.py` (gating by opt-in preference +
  matching spend category, stackability dedup in `allocate_portfolio_credits`).
- The profile **Benefits & Credits** tab (`static/js/pages/profile.js:748-880`)
  already re-derives a reconciling "Total Annual Benefits $/yr" client-side from
  owned cards + opt-in prefs + stackability dedup (mirroring the engine).

Two decisions from Jamie (2026-07-21) set the scope:
1. **Shape**: show each credit's annual value beside its checkbox, **plus** a
   live running total of the credits the user has selected.
2. **Value basis**: use the **user's real owned-card value** where they own a
   card carrying the credit (reconciles with the engine), **falling back to a
   representative "typical" value** (clearly labelled) when they don't — so
   anonymous / no-card users still see numbers to inform the opt-in.

One load-bearing data gap blocks the "reconciling" half: the discounted
`annual_value` is **not exposed** by `CardCreditSerializer`
(`cards/serializers.py:65-74`), so the profile tab already silently falls back
to face-value (`profile.js:792`, `credit.annual_value || value*times_per_year`).
Fixing that serializer is a prerequisite and also quietly corrects the existing
profile-tab approximation.

**Engine math is untouched** by this phase — this is a read-only surfacing of
values the engine already produces, so there is no reconciliation-guard risk.

Ordering: backend data-exposure first (small, testable), then a shared JS
helper extracted from the profile tab (reuse over duplication, per the frontend
cleanup ethos), then the builder wiring, then docs. Lowest-risk → highest-risk.

## Work

### Phase Q.0 — Commit this plan to the repo

Copy this doc to `docs/plans/phase-q-builder-credit-math.md` (matches the
`phase-frontend-cleanup.md` precedent — approved plans live in-repo). Done as
the first execution step, since plan-mode can't write there.

### Phase Q.1 — Expose discounted `annual_value` on `CardCreditSerializer`

`cards/serializers.py` `CardCreditSerializer` (65-74): add
`annual_value = serializers.ReadOnlyField()` and append `'annual_value'` to
`fields`. This surfaces the model property (system-default point rate,
`user=None`) — the same baseline the profile tab wants. The engine may apply a
user's custom point-value override at generation time; for builder/profile
*display* the system-default discounted value is the correct shared baseline
(accepted minor divergence, identical to what the profile tab already assumes).

Immediate side benefit: `profile.js:792`'s `credit.annual_value || …` fallback
now takes the real discounted value instead of face value — a silent correction
for any points-denominated owned credit. Re-verify the profile "Total Annual
Benefits" figure still looks right after (manual, no automated profile test).

### Phase Q.2 — Add a `typical_value` to the spending-credits endpoint

So no-card users still see a number. `SpendingCreditListView`
(`cards/views.py:48`) + `SpendingCreditSerializer` (`cards/serializers.py:45-50`):

- In the view, compute a `{spending_credit_id → typical_value}` map in one pass:
  the **median** of `CardCredit.annual_value` across `is_active` `CardCredit`s on
  active cards that reference each `spending_credit` (median = robust "typical",
  not skewed by one premium outlier). Pass the map via serializer `context`.
- Add `typical_value = serializers.SerializerMethodField()` reading from context
  (NOT a per-object query — avoids N+1 across the credit catalog); `None` when no
  active card carries it. Append `'typical_value'` to `fields`.

Flag to Jamie: median is the recommended "typical"; swap to max/mode if he'd
rather the label read optimistically.

### Phase Q.3 — Extract the owned-card credit aggregation into a shared helper

The builder needs the *exact* reconciling math the profile tab already does.
Extract it rather than duplicate (frontend-cleanup dedup ethos):

- **New file** `static/js/credits.js` (plain global-scope, matching
  `static/js/utils.js` style — no ES modules), loaded in `base.html`'s `<head>`
  after `utils.js` so both `profile.js` and `roadmap.js` see it:
  - `fetchOwnedCardDetails(cardIds)` — the per-card `GET /cards/cards/{id}/`
    loop currently inline at `profile.js:768-810`, returning
    `{cardId → cardDetail}`.
  - `aggregateOwnedCredits(cardDetails, preferences)` — the aggregation +
    stackability dedup at `profile.js:819-839`, returning
    `{slug → {name, slug, stackable, isUsed, winnerCardId, rawAmount,
    effectiveAmount, cards[]}}`. `effectiveAmount` is 0 when not opted in,
    exactly as today.
- **Refactor** `profile.js loadCreditsProfile()` to call the two helpers so its
  behaviour is byte-for-behaviour unchanged (it keeps building
  `trackableCredits` and the total box from the returned map).

### Phase Q.4 — Wire owned-card values into the builder (non-blocking)

`static/js/pages/roadmap.js`:

- Module-level `let ownedCreditsBySlug = {};`.
- In `loadData()` (346-398), after categories/credits load, **kick off a
  non-blocking** load: owned card ids (`UserDataManager.getCards()`) →
  `fetchOwnedCardDetails` + `getCreditPreferences()` →
  `aggregateOwnedCredits` → store in `ownedCreditsBySlug`, then call
  `updateCreditLabels()` + `updateSelectedCreditsTotal()` to fill in the
  personalized values. The builder must render and stay responsive without this
  (anonymous / no cards ⇒ empty map ⇒ everything shows typical).

### Phase Q.5 — Per-credit value labels + running total in the builder

**Per-credit labels** — in `renderSpendingCategories()`'s credit loop
(`roadmap.js:561-576`), append a value span to each checkbox row, with a
`data-credit-slug` on the row so labels can be refreshed after owned data
arrives. Value resolution (`resolveCreditValue(slug, typicalValue)`):
- owned carrying card present (`ownedCreditsBySlug[slug]`): show its
  `rawAmount` as `$N/yr` — reconciling, no "typical" tag.
- else if `typical_value != null`: show `~$N/yr (typical)`.
- else: no label.
Because owned data loads after first render, render typical (or blank) first,
then `updateCreditLabels()` rewrites the spans when `ownedCreditsBySlug` fills.

**Running total** — render a `#creditsValueSummary` line at the end of
`renderSpendingCategories()` output (bottom of the credits area, visible in
By-Category mode). `updateSelectedCreditsTotal()` sums the resolved value of
each **checked** `input[name="spending_credit_preferences"]`. One checkbox per
catalog slug ⇒ owned-card stackability is already resolved inside
`effectiveAmount`, so the total is a straight sum — no cross-checkbox dedup.
Label as an estimate: `Credits you value: ~$205/yr`. Call it from
`handleSpendingCreditChange()` (609-612), after initial render, and after the
owned-data refresh.

Placement note (small UI call for Jamie): total sits at the bottom of the
credits list; alternative is a secondary line in the sticky footer
(`index.html:211-218`) beside "Total monthly spend". Recommend the credits-area
placement so it's adjacent to the checkboxes it summarises and naturally hidden
in Easy Mode (where the grid + checkboxes aren't shown).

### Phase Q.6 — Docs & help

- `templates/help.html`: document that the builder now shows each credit's
  annual value and a running total, and the owned-vs-`~typical` distinction
  (near the existing Easy Mode copy, ~140-143). Required by CLAUDE.md for any
  user-facing feature change.
- `docs/PROJECT_STATUS.md`: move Phase Q from **Open** (67-69) to **Completed**
  with a one-paragraph summary; update the "Phases (E–Q)" narrative (18-20) to
  read Q as done / no unstarted phases; add a manual-browser checklist bullet
  under "Operational to-do" (150+). Same commit as the code (CLAUDE.md rule).

## Verification

Automated (must stay green — engine untouched, so all should be unaffected
except the new serializer tests):
```bash
venv/bin/python manage.py test                                                 # 228 tests + new serializer tests
RUN_ALL_SCENARIOS=1 venv/bin/python manage.py test cards.test_json_scenarios    # full sweep, unaffected
venv/bin/python manage.py run_scenario "Jamie Real" --explain                   # reconciles, unaffected
node scripts/test_roadmap_results.js                                            # unaffected (28/28)
```
New backend tests to add:
- `CardCreditSerializer` includes `annual_value`, and it's **discounted** for a
  points-denominated credit (not face value).
- `GET /cards/spending-credits/` returns `typical_value` (a number for a credit
  carried by ≥1 active card; `null` otherwise).

Manual browser checklist (Jamie runs the dev server himself):
- **Builder, owning cards** (`/roadmap/`): each "Credits You Use" checkbox for a
  credit on an owned card shows a `$N/yr` value that **matches the profile
  Benefits tab** figure for the same credit; toggling checkboxes updates the
  "Credits you value" total live; the total equals the sum of checked values.
- **Builder, no cards / anonymous**: checkboxes show `~$N/yr (typical)`; total
  still adds up; no console errors; builder still renders instantly (owned-data
  fetch is non-blocking).
- **Owned data races render**: on a slow load, labels start typical/blank then
  upgrade to personalized values without flicker or double-counting.
- **Easy Mode**: credits section + total are hidden (grid not shown); switching
  back to By Category restores them with state intact.
- **Profile tab regression** (`/profile/`): "Total Annual Benefits" still
  correct after the Q.1 serializer change + Q.3 refactor; for a
  points-denominated owned credit it now shows the **discounted** value, not
  face value.
- Console clean on `/roadmap/` and `/profile/`.
