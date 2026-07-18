# Plan: Phase E — Selection-Aware Bonus Capacity & Sequencing

Approved implementation plan (2026-07-11). If you are picking this up in a
new session: read `CLAUDE.md` first, then this file top to bottom. The
**Progress** section at the bottom says exactly what's done and what's next.

When Phase E is complete, archive this doc to mybrain
`Requirements/Complete/` and trim `PROJECT_STATUS.md`, per the existing
convention.

## Context

Bonus capacity (`BONUS_CAPACITY_MONTHS = 12.0`,
`roadmaps/recommendation_engine.py:22`) is enforced only at **final
assembly** today: `generate_quick_recommendations` (:147-217) sorts the
already-chosen applies by priority, accumulates
`_bonus_months_needed(card)` (:493-506, requirement ÷ total monthly spend),
and silently **drops** any apply that doesn't fit — the card survives only
as a name in the `bonus_capacity.deferred_applies` summary list (:212-217).

The greedy optimizer that chose those applies knows nothing about this. All
three of its valuation sites count every apply's full (strategy-weighted)
signup bonus, so it happily picks portfolios whose bonuses can't all be
earned, then loses cards at assembly that a capacity-aware selection would
never have picked — or, worse, misses a portfolio that fits and is worth
more overall.

There is also **no timing anywhere**: no "apply in month N" field in the
engine, API, or frontend. `priority` is just selection rank (:822, :1127,
:1462). Sequencing applies inside the 12-month window is the groundwork
that later unlocks Southwest Companion Pass timing.

### Scope decisions (made with Jamie, 2026-07-11 — locked)

1. **Sequencing infrastructure only.** No Companion Pass modeling in this
   phase (CP is entirely unmodeled today — Southwest cards carry only
   `application_family`/`bonus_eligibility` metadata). The sort-key hook in
   the capacity plan (below) is where CP timing rules slot in later.
2. **Over-capacity applies compete bonus-less.** When a candidate's bonus
   doesn't fit the remaining budget, selection scores it WITHOUT the bonus —
   it can still win on ongoing value or lose its slot to a card that fits.
   Assembly-time deferral stays only as a safety net.
3. **Timing display: relative + calendar.** Engine emits a per-apply month
   offset; frontend renders "Apply now" / "Apply in ~4 months (Nov 2026)"
   using the roadmap's `generated_at`.

### Non-negotiable invariant

Displayed dollars come from `_calculate_portfolio_allocation` and the
reconciliation guard (:452-461) must keep holding: headline ≈ line items +
signup bonus − fee, within $1. Every capacity adjustment flows through line
items and the `signup_bonus_value` field — never the headline directly.

---

## Core design — one capacity authority, set-based

### New method: `_bonus_capacity_plan(cards) -> dict`

Place near `_bonus_months_needed` (:493). Input: a list of `CreditCard`
apply candidates. Output:

```python
{
  'by_card_id': {card.id: {'bonus_value': float, 'months': float,
                           'counted': bool, 'start_month': float}},
  'months_committed': float,   # sum of counted months
  'sequence': [card.id, ...],  # counted cards in spend-consumption order
}
```

Rules:

- `bonus_value = _get_signup_bonus_value(card)` (:1895),
  `months = _bonus_months_needed(card)` — **reuses the existing math, no
  second source of truth**.
- Bonuses with no spending requirement (`months == 0`): always
  `counted=True, start_month=0.0`, consume no budget.
- Bonuses with `months > 0`: sort by **value density**
  (`bonus_value / months` desc; ties: `bonus_value` desc, then `card.id` —
  a total order, so equal-density fixtures can't flap), then walk the
  budget: fits within `BONUS_CAPACITY_MONTHS` → `counted=True`,
  `start_month = committed`, `committed += months`; else `counted=False`.
  `months == inf` (zero total spending) falls out as uncounted.
- **All-or-nothing per bonus** — no partial fits; matches the existing
  `months_committed` accounting and `_signup_bonus_plan`'s
  serialized-spend assumption.

Why density order: it's the right greedy heuristic for "budget of months,
maximize counted bonus dollars"; it's derived from the **set** (not the
greedy add order), so the same portfolio always yields the same
counted/uncounted split; and it doubles as the sequencing order — you
commit spend first to the card earning the most per committed month.
`time_limit_months` urgency is deliberately not a factor in this phase.

`start_month` treats spend commitments as strictly serial, exactly like the
existing `months_committed` sum. No change to `_signup_bonus_plan`'s
organic/shift/unreachable logic — that's orthogonal (requirement vs. spend
inside the card's own window).

---

## Implementation steps

Each step leaves the suite green — run the gates before moving on.

### Step 1 — Selection seam: capacity-aware portfolio valuation

File: `roadmaps/recommendation_engine.py`. Three valuation sites currently
sum every apply's full weighted bonus; all three switch to counting only
`counted` entries from `_bonus_capacity_plan(<apply cards in the
combination>)`, summing `bonus_value * signup_bonus_weight` over them:

1. `_calculate_scenario_portfolio_value` (:1132) — the per-action bonus sum
   at :1150-1154.
2. The same function's **efficiency-boost block** (:1238-1250) —
   `card_signup_value` at :1245 must use the counted value (0 if uncounted),
   otherwise an over-budget bonus still inflates the portfolio through the
   boost and partially defeats bonus-less competition. Subtlest site;
   comment it.
3. The inner `calculate_portfolio_value` closure in
   `_optimize_card_portfolio` (:898, bonus at :914-918) — same substitution.
   (The greedy add-loop itself evaluates via site 1, so it becomes
   capacity-aware for free: a candidate whose bonus doesn't fit contributes
   ongoing value only.)

Pre-sort scoring (`_select_optimal_card_combination` :780-788) keeps the
full bonus — capacity is portfolio-relative and a solo card has the whole
budget — with one defensive cap: zero the bonus contribution when
`_bonus_months_needed(card) > BONUS_CAPACITY_MONTHS` (can't fit even
alone). Ranking big-bonus cards high in the candidate pool is desirable;
the capacity-aware marginal evaluation makes the real decisions.

Do **not** touch `_select_best_new_cards` (:1087) or the
`_get_best_signup_bonus_card` fallback — their outputs are re-valued
through site 1 before a scenario wins.

Optional: memoize `_get_signup_bonus_value` per `card.id` in a
per-instance dict (the plan is rebuilt per greedy test-combination).

**Gate:** 100 standard tests + 64/64 sweep. Expect scenario shifts —
recalibrate via `DUMP_SCENARIOS=1 RUN_ALL_SCENARIOS=1 venv/bin/python
manage.py test cards.test_json_scenarios`, hand-verify every changed number
line-by-line before updating expectations (never rubber-stamp). Do this
step in isolation so every diff is attributable to it.

### Step 2 — Display agreement: bonus-less applies show $0 bonus

File: `roadmaps/recommendation_engine.py`,
`_generate_portfolio_optimized_recommendations`. After `best_portfolio` is
deduped (:350) and `held_cards` computed (:354):

```python
apply_cards = [ca['card'] for ca in best_portfolio if ca['action'] == 'apply']
capacity_plan = self._bonus_capacity_plan(apply_cards)
```

In the per-card apply branch (:381-442), before `_signup_bonus_plan`: if
the card's entry has `counted == False`, take a third pathway parallel to
the existing `bonus_block` one (:389-398):

- `signup_bonus_value = 0`
- `plan = {'items': [_info_item('Signup bonus deferred', "Doesn't fit this
  year's bonus capacity at your spending level — card recommended on
  ongoing value; earn the bonus next year")], 'value_delta': 0.0,
  'bonus_earnable': False}`
- New rec field `bonus_deferred = True` (distinct from `eligibility_note`,
  which tests assert on for issuer rules).

No `bonus_shift` items for a deferred bonus (we're not chasing it), so the
reconciliation guard holds by construction. Extend the existing
`not plan['bonus_earnable']` reasoning branch (:435-439) with the deferral
wording. Stash the plan (e.g. `self._last_capacity_plan`) so Step 3 can
sequence against the same computation.

**Gate:** suite + `run_scenario "Jamie Real" --explain` reconciles (no
"Breakdown mismatch" log lines).

### Step 3 — Sequencing annotations + assembly loop becomes a safety net

File: `roadmaps/recommendation_engine.py`, `generate_quick_recommendations`
(:147-217). Keep the capacity loop (:166-179) structurally intact — it
still enforces `max_new_card_applications` — with these changes:

1. Step 2 zeroed `signup_bonus_value` for uncounted bonuses, so their
   `months` at :169-170 is 0 and nothing should legitimately overflow now.
   Add a `logger.warning` when anything with a positive bonus lands in
   `deferred_applies` — that indicates a selection/display divergence bug.
   (Assembly only ever removes applies — the `estimated_rewards > 0` filter
   at :162 and the max cap — and removing a card from a density-ordered
   budget can only move remaining counted cards earlier, never evict them.)
2. After `selected_applies` is final, run
   `sequence_plan = self._bonus_capacity_plan([rec['card'] for rec in
   selected_applies])` and annotate each apply rec:
   - `recommended_month`: `int(round(start_month))` for counted bonuses
     with `months > 0`; `0` for counted-no-requirement bonuses; `0` for
     bonus-less/deferred applies (they consume no bonus budget — "apply
     whenever"; pushing them past month 12 to earn next year's bonus is
     the CP-era follow-up).
   - `bonus_months_needed`: `round(months, 1)` (0 for bonus-less).
   - Keep raw float `start_month` in the timeline (below) so months sum to
     `months_committed` exactly; only the display offset is rounded.
3. Extend the `bonus_capacity` summary dict (:212-217) — all four existing
   keys untouched — with:
   ```python
   'timeline': [  # applies ascending by start_month, bonus-less last
     {'card_name', 'recommended_month', 'months_needed', 'bonus_counted'},
   ],
   'bonus_less_applies': [<names of applies with bonus_deferred=True>],
   ```
   `months_committed` should now equal `sequence_plan['months_committed']`
   — assert-log if not.
4. Non-apply recs get no `recommended_month` (key absent/None). `priority`
   stays selection rank; month-based display ordering is client-side.

Optional, no migration: in `generate_roadmap`, populate the dormant
`RoadmapRecommendation.recommended_date` (roadmaps/models.py:85) as
today + `recommended_month` months. Skip if it drags in dateutil questions.

**Gate:** suite. Update the hand-written capacity test now (see Step 4's
fixture note) if it breaks here.

### Step 4 — Tests

- **Schema extension (minimal):** a shared validator (pattern:
  `validate_portfolio_optimization`) used by both `cards/test_base.py`
  `assert_expectations` (:82-133) and
  `cards/management/commands/run_scenario.py` `validate_expectations`
  (:281), supporting two optional expectation keys:
  - `expected_apply_sequence`: ordered card slugs, asserted against applies
    sorted by `(recommended_month, priority)`.
  - `expected_recommended_months`: `{slug: int}` exact match.
  Zero impact on the 64 existing scenarios.
- **Update the hand-written capacity test**
  (`cards/test_json_scenarios.py:131-140`) and its fixture ("Bonus capacity
  - only two 10K bonuses fit a year", `data/tests/scenarios/
  eligibility.json`): under new semantics Gamma competes bonus-less
  mid-greedy and — fixture cards being bonus vehicles with weak ongoing
  value — should lose its slot in selection rather than defer at assembly.
  Expected: `deferred_applies == []`, `months_committed ≈ 10.0`, Gamma
  still excluded, `expected_recommended_months` for alpha/beta (equal
  densities — the tie-break decides; pin whatever DUMP shows and note the
  tie-break in the scenario's comments). If DUMP instead shows Gamma
  squeaking in bonus-less, flip to asserting `signup_bonus_value == 0` +
  the deferral info line — either is valid Phase-E behavior; hand-verify
  which the fixture produces.
- **New `data/tests/scenarios/bonus_sequencing.json`** (update
  `index.json`'s files list/total too), with hand-written companions in
  `cards/test_json_scenarios.py` where the JSON schema can't reach:
  1. *Capacity overflow with reordering* — old code's priority order would
     defer a fitting card; new selection picks the fitting, higher-total
     pair. Assert `must_include_cards`, `deferred_applies == []`.
  2. *Bonus-less competition* — budget exhausted by two dense bonuses; a
     third card with genuinely strong ongoing value wins a slot anyway.
     Hand-assert `signup_bonus_value == 0.0`, `bonus_deferred` true, the
     deferral info line, and reconciliation (shared
     `validate_breakdown_accuracy` covers it).
  3. *Sequencing order* — two-bonus case asserting
     `expected_apply_sequence` + `expected_recommended_months`
     {first: 0, second: N}.

**Gate:** sweep 64/64 + the new scenarios green.

### Step 5 — API payload

File: `roadmaps/views.py`.

- `_build_quick_rec_response` (:136-180): per-rec, add
  `recommended_month`, `bonus_deferred`, `bonus_months_needed`. The
  `bonus_capacity` dict already passes through at :178 — the new
  `timeline`/`bonus_less_applies` keys ride along free.
- **`generated_at` gap:** the live POST response from
  `quick_recommendation_view` does NOT carry `generated_at` today — only
  the GET current/shared endpoints add it. Compute
  `timezone.now().isoformat()` once in the view, set
  `response_data['generated_at']` before `_persist_current_roadmap(...)`,
  and reuse the same value for `calculation_data['generated_at']`. Required
  for calendar-month rendering on the live path.

**Gate:** suite; manual curl of `/api/roadmaps/quick-recommendation/` and
`/api/roadmaps/current/` to eyeball the new fields.

### Step 6 — Frontend

File: `static/js/roadmap-results.js` — shared by index.html live
generation, index.html restore-on-load, and the read-only shared page, so
one change covers all three.

1. Derive `const baseDate = data.generated_at ? new
   Date(data.generated_at) : new Date();` in `renderRoadmapResults`.
2. Timing helper: `recommended_month` null/0 → `"Apply now"`; else
   `"Apply in ~N months (Mon YYYY)"` (baseDate + N months,
   `toLocaleString({month:'short', year:'numeric'})`).
3. Apply-card branch (:284-312): sort `groupedRecs.apply` by
   `(recommended_month ?? 0, priority)`; add a **WHEN** stat to
   `apply-card-stats` (:294-302) with the helper's label. `bonus_deferred`
   recs already explain themselves via the Step 2 info line rendered by the
   existing `infoNotes` block — no extra chip (avoids colliding with
   `eligibility_note` chips).
4. Capacity note (:93-98) currently renders only when `deferred_applies`
   is non-empty (now rare). Rework: render whenever
   `bonus_capacity.months_committed > 0`, showing the sequenced timeline
   ("Card A now, Card B in ~5 months…" from `bonus_capacity.timeline`),
   plus the old deferred sentence only if `deferred_applies.length > 0`,
   plus a `bonus_less_applies` sentence ("X is recommended on ongoing
   value alone — its bonus doesn't fit this year's spending"). Portfolio
   story lives in this note; per-card timing lives on each apply card.

**Gate:** manual browser pass (Jamie runs the dev server) — live generate,
reload-restore, and shared read-only page all show timing labels; check the
"Apply in ~N months (Mon YYYY)" arithmetic against `generated_at`. Append a
Phase E checklist to `docs/MANUAL_TEST_PLAN.md`.

---

## Risk notes

- **Sweep churn is the main risk.** Step 1 changes portfolio values even
  for scenarios under capacity (the efficiency-boost change can flip close
  greedy comparisons and the scenario1-vs-scenario2 choice). Land Step 1
  alone and recalibrate before anything else.
- **Strategy weights × bonus-less scoring:** `signup_bonus_weight` now
  multiplies only counted bonuses. Maximizer (1.5) shifts from "biggest
  bonuses" toward "densest bonuses that fit" — intended, but expect
  `strategies.json` scenario recalibration. simple_cash_back (0.5 weight,
  100 per-card penalty) is barely affected.
- **Two plan invocations** (display-time in Step 2, sequence-time in
  Step 3) run on possibly different sets — but assembly only shrinks the
  apply set, and shrinking never un-counts a counted bonus under density
  order, so display can only be conservative (a $0-shown bonus that would
  now fit). Log if the sequence-time plan counts a card whose rec says
  `bonus_deferred`; never overstates value, self-heals on regenerate.
- **`estimated_rewards > 0` filter (:162):** a bonus-less apply must clear
  it on ongoing value alone; if it can't, selection filled a slot with a
  card assembly then drops. Same class of selection/assembly gap that
  exists today — accepted for this phase.
- **Determinism:** every tie-break in `_bonus_capacity_plan` must be total
  (density → bonus value → card.id) or equal-density scenarios flap.

## Verification (Phase E definition of done)

```bash
venv/bin/python manage.py test                                                # standard suite
RUN_ALL_SCENARIOS=1 venv/bin/python manage.py test cards.test_json_scenarios  # sweep: all pass (64 + new)
venv/bin/python manage.py run_scenario "Jamie Real" --explain                 # every line item reconciles
```

Plus: new `bonus_sequencing.json` scenarios green, manual browser pass
(timing labels on live/restored/shared views), `docs/MANUAL_TEST_PLAN.md`
gains a Phase E checklist, and `CLAUDE.md`'s engine section +
`docs/PROJECT_STATUS.md` updated in the same commit as the code (per
working rules).

## Progress

- [x] Step 1 — `_bonus_capacity_plan` + three valuation sites; sweep
      recalibrated (hand-verified, 2026-07-15). Zero behavioral diffs
      across the existing 64 scenarios — verified via debug trace that the
      capacity-aware code path is exercised (e.g. Bonus Card Gamma is
      correctly recognized as not-counted), but the pre-existing
      efficiency-boost quirk (uses each card's standalone value, not its
      marginal portfolio contribution) meant no scenario's final selection
      actually flipped yet — expected, since assembly-time deferral
      (unchanged until Step 2) still drove the one capacity fixture's
      outcome.
- [x] Step 2 — bonus-less display pathway ($0 bonus, deferral info line,
      `bonus_deferred` flag). This is what actually changed the capacity
      fixture's outcome: Gamma's bonus now shows $0, its ongoing value is
      also $0 (category already claimed by a better-rate card), so it's
      filtered out by the `estimated_rewards > 0` check before ever
      reaching assembly — `deferred_applies` is now `[]` instead of
      `['Bonus Card Gamma']`. Updated `eligibility.json`'s capacity test
      and fixture comments accordingly.
- [x] Step 3 — `recommended_month`/`bonus_months_needed` annotations,
      `bonus_capacity.timeline`, safety-net warning. Also enhanced
      `cards/test_base.py print_scenario_results` to print the new fields
      (recommended_month, bonus capacity timeline) — needed for the
      DUMP_SCENARIOS hand-verification workflow going forward.
- [x] Step 4 — expectation-schema extension
      (`validate_apply_sequencing` on the `run_scenario.py` Command class,
      shared by both `test_base.py` and `run_scenario.py` per the existing
      `validate_portfolio_optimization` pattern; supports
      `expected_apply_sequence` and `expected_recommended_months`).
      Capacity fixture updated (see Step 2). New
      `data/tests/scenarios/bonus_sequencing.json` (3 scenarios + 9 new
      fixture cards in `data/tests/cards.json`): selection avoiding a
      wasted select-then-defer round trip, a bonus-less card winning a
      slot on ongoing value alone, and two-card sequencing order. Sweep is
      67/67. Note: the "capacity overflow with reordering" case from the
      original plan turned out to not be constructible as a genuinely
      *different final portfolio* given `_optimize_card_portfolio`'s
      forward-only greedy (it only ever adds cards, never swaps out an
      earlier pick) — the first card chosen is invariant to capacity
      awareness since solo evaluation is identical either way. What *is*
      demonstrable, and what the first new scenario asserts, is the
      cleaner accounting: selection now avoids ever choosing a card whose
      bonus can't coexist with a bigger one already claiming the budget,
      rather than picking it and deferring it at assembly.
- [x] Step 5 — API fields (`recommended_month`, `bonus_deferred`,
      `bonus_months_needed` per rec; `bonus_capacity.timeline`/
      `bonus_less_applies` already rode along free) + `generated_at` on
      the live POST response (`quick_recommendation_view` sets it once,
      `_persist_current_roadmap` reuses the same value). Verified via a
      throwaway `TestCase` hitting the view through Django's test client
      (test DB, not dev DB) rather than curl, since no dev server was
      running and it shouldn't be started for this — confirmed
      `generated_at`, all `bonus_capacity` keys, and per-rec sequencing
      fields all present and consistent with the test-suite numbers.
- [ ] Step 6 — frontend timing labels, apply sort, reworked capacity note
      (deferred — needs Jamie's browser pass; not started this session)
- [ ] Manual browser pass done (Jamie); MANUAL_TEST_PLAN.md updated
- [x] Docs updated (CLAUDE.md engine section, PROJECT_STATUS.md) for
      Steps 1–5, 2026-07-15. This doc archives to mybrain once Step 6 +
      the manual pass land.
