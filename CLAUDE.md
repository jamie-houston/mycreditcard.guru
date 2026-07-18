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
venv/bin/python manage.py test                                   # standard suite (151 tests)
RUN_ALL_SCENARIOS=1 venv/bin/python manage.py test cards.test_json_scenarios   # full sweep: 77/77 must pass
venv/bin/python manage.py run_scenario "Jamie Real" --explain    # acceptance: every line item reconciles
```

- The full sweep passes 77/77 as of 2026-07-18 (post Phase K). Any failure is a regression.
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
  last) and `bonus_capacity.bonus_less_applies` list. Southwest Companion
  Pass timing is explicitly unmodeled; the density sort-key is where that
  would slot in later. **Points pooling (Phase G→J)**: a card's points are
  valued at `max(own multiplier, best same-program multiplier among cards
  actually HELD)` via `_effective_multiplier(card, program_multipliers)`,
  where `program_multipliers` comes from `_program_multipliers(held_cards)`
  — a portfolio-relative map computed once per portfolio/combination, same
  shape as `_bonus_capacity_plan`. `_own_multiplier(card)` is now the ONLY
  place the raw `metadata.reward_value_multiplier` key is read (default
  `0.01`) — every other site goes through one of the three helpers. Threaded
  into the canonical display path (`_calculate_card_allocated_breakdown`,
  `_get_signup_bonus_value` — a points/miles bonus pools too) and the three
  portfolio-valuation sites above; solo pre-sort scoring
  (`_calculate_smart_card_value`, `_select_optimal_card_combination`) and
  two legacy/summary paths (`_calculate_card_rewards_breakdown`,
  `_calculate_portfolio_summary`) deliberately keep the card's own
  multiplier only, noted inline. When pooling lifts a card, a $0
  `_info_item` ("Points valued via {redemption card}", from
  `_program_best_cards(held_cards)`) is appended to its breakdown — the
  dollar lift already lives in the real line items, so the reconciliation
  guard holds by construction. Same-program pooling only — no
  transfer-partner modeling (locked scope). Hand-curated
  `metadata.points_program` (e.g. `chase_ultimate_rewards`,
  `amex_membership_rewards`) drives it; cards without the key never pool.
  **Multi-player households (Phase K)**: `self.entities` (`[primary] +`
  other players/businesses, primary-first — `ProfileEntity.Meta.ordering`;
  anon/session users get one implicit `SimpleNamespace` entity) and
  `self.entity_histories` (`{entity_id: [UserCard...]}`, bucketed by
  `owner_id`, NULL→primary) are built once per engine instance.
  `_eligible_entity_for_card(card)` (cached per `card.id`) is the
  per-entity replacement for the old household-wide held-card check:
  business cards prefer a business entity (falling back to the primary for
  sole proprietors — Jamie Real has no declared business entity), personal
  cards consider personal entities primary-first; returns the first entity
  with no open copy of the card AND no `application_block` against ITS OWN
  history. Backs `_is_eligible_for_card` and `_bonus_ineligibility_note`
  (issuer bonus rules evaluated against the APPLYING entity's history, not
  the household's — a card one entity's bonus-blocked on can still be
  earnable for another). `apply_as` (`{entity_id, name, kind}`) is set on
  apply recs only when the profile has >1 entity — omitted entirely (not
  `None`) for single-entity households, so anon/single-player payloads
  stay byte-identical; threaded through `roadmaps/views.py`
  `_build_quick_rec_response` the same way. **Second-copy applies**
  (another entity applying for a card someone else already holds):
  `_generate_portfolio_optimized_recommendations`'s portfolio de-dup key
  became `(card.id, action == 'apply')` (was just `card.id`) so a 'keep'
  and a second-copy 'apply' for the same card can coexist; after that dedup
  it walks every 'keep' action and, for each entity `_eligible_entity_for_card`
  still returns, appends a synthetic apply entry tagged `duplicate_copy`/
  `duplicate_copy_owner`. Those bypass `_calculate_card_allocated_breakdown`
  entirely (the held copy already earns the category rewards — `held_cards`
  for allocation explicitly excludes `duplicate_copy` entries so the card
  isn't double-counted) and are valued at `signup_bonus_value −
  effective_annual_fee` alone (no `_signup_bonus_plan` shift modeling — no
  allocation baseline to shift from/to), so the reconciliation guard holds
  by construction. Ranked after every normal apply candidate
  (`priority = 500 + card.id`) — prefer giving each household member their
  own best card before doubling up. This whole mechanism reduces to a
  provable no-op for single-entity households (the sole candidate is
  always the holder, always ineligible for their own card) — see
  `roadmaps/tests.py` `SecondCopyApplyTests`. Bonus capacity
  (`_bonus_capacity_plan`) stays household-wide (shared spend, locked
  scope) — only apply slots multiply per entity.
- `static/js/roadmap-results.js` `_roadmapTimingLabel(recommendedMonth,
  baseDate)` — Phase E Step 6: renders "Apply now" (falsy month) or "Apply
  in ~N month(s) (Mon YYYY)" from `rec.recommended_month` and the roadmap's
  `generated_at`. `renderRoadmapResults` derives `baseDate` once per call
  (falls back to `new Date()` for older data with no `generated_at`), sorts
  the Apply section by `(recommended_month, priority)`, and shows the label
  in a WHEN stat on each apply card. The capacity note above the summary
  table (previously shown only when `deferred_applies` was non-empty) now
  renders whenever `bonus_capacity.months_committed > 0`, listing the
  sequenced timeline plus the deferred/bonus-less sentences from
  `bonus_capacity.deferred_applies`/`bonus_less_applies`. Pure-logic
  coverage (no DOM) lives in `scripts/test_roadmap_results.js` — a
  framework-free Node smoke test (`node scripts/test_roadmap_results.js`)
  that loads the file via `vm` and asserts on `_roadmapTimingLabel`,
  `_roadmapFormatSigned`, and the rewards/benefits split; this repo has no
  JS test framework by design (see `docs/README_TESTING.md`), so this is a
  plain script, not a new dependency. `_roadmapApplyAsLabel(rec)` (Phase K)
  renders " · as {name}" under both `.apply-card-reason` and
  `.grouped-row-reason` when `rec.apply_as` is present, via
  `_roadmapEscapeHtml()` (`ProfileEntity.name` is user input) — absent
  entirely on old payloads/single-entity households, both covered in the
  same Node smoke test.
- `roadmaps/strategies.py` — strategy presets are data, not code
  (filters + max_recommendations + selection weights). UI effort question
  maps onto these.
- `roadmaps/eligibility.py` — issuer rules are data, not code. Application
  rules (Chase 5/24, BofA 2/3/4, CapOne 1/6mo, family blocks) exclude cards
  from applies; bonus rules (Amex lifetime, Citi 48-month, Sapphire/
  Southwest via card `metadata.bonus_eligibility`) zero the bonus but keep
  the card competing on ongoing value, with a user-facing note. Evaluated
  against full card history INCLUDING closed cards
  (`UserCard.bonus_earned_date`, approximated when blank). `UserCard.
  bonus_override` (Phase G) is a tri-state escape hatch over that
  rule-based inference: `null` (default) infers as before, `True` confirms
  the user actually earned that prior card's bonus, `False` says they
  didn't (referred instead of applying, never activated) — `bonus_
  ineligibility()`'s `prior` list excludes any `False`-overridden card
  before checking once-per-lifetime/months-since-bonus, so it can't block
  a new bonus the user never actually got credit for. **Phase K** added two
  application-side rule shapes: an `application_rules` entry with
  `max_open_cards` (vs. the existing windowed `max_new_cards` +
  `period_months`/`period_days`) counts currently-OPEN same-issuer cards,
  uncapped by time — Amex's own 5-card limit
  (`ISSUER_RULES['american-express']`). `card.metadata.
  application_eligibility = {once_per_lifetime, family, label}` is a
  stronger, forever block (scans OPEN and CLOSED history) distinct from
  the existing `application_family` (open-cards-only) — curated on
  `chase-sapphire-reserve`/`chase-sapphire-preferred-card` sharing a
  `chase-sapphire-personal` family, deliberately excluding the business
  Sapphire (`chase-sapphire-reserve-for-business`, no metadata key).
  `application_block`/`bonus_ineligibility` keep their exact `(card,
  card_history, today)` signatures — Phase K passes a per-entity history
  slice instead of the household-wide one (see `_eligible_entity_for_card`
  above); anon/single-entity households pass the same slice as before.
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
  `POST /api/cards/user-cards/toggle/` (auth) or localStorage (anon). Note:
  `/api/users/data/`'s bulk save (`users/
  serializers.py` `UserDataSerializer.create`) only hard-deletes ACTIVE
  (`closed_date__isnull=True`) cards missing from the posted list — it used
  to delete soft-closed rows too (since they're never in that list), which
  would have erased a card's closed_date on the very next roadmap
  generation (`saveCurrentData()` calls this endpoint every time).
- **Card ownership (`UserCard`) lives entirely in `cards/`** (Phase F5) —
  the `users/` app's parallel `cards/`, `cards/<pk>/`, `cards/toggle/`,
  `cards/update-details/`, `cards/details/` endpoints were retired, and
  every frontend caller (`templates/base.html`'s `UserDataManager`,
  `static/js/roadmap-results.js`'s `removeCardOwnership`) repointed to the
  `cards/` equivalents. `cards/urls.py` `user-cards/*`: `GET` (list, all
  cards incl. closed — used for the browse-page OWNED badge), `POST add/`
  (create-or-reopen), `POST toggle/` (single-call add/remove ergonomics —
  add reopens a soft-closed row rather than erroring on the `['user',
  'card']` `unique_together` constraint or creating a duplicate; remove
  soft-closes), `PATCH/PUT <id>/` (edit nickname/dates, keyed by `UserCard`
  id — `base.html`'s `updateCardDetails()` resolves that id from
  `getUserCardsDetails()` first, since it's only ever handed a `CreditCard`
  id), `DELETE <id>/delete/` (soft-close). **Every removal path sets
  `closed_date` — none hard-delete** — eligibility rules (Chase 5/24, BofA
  2/3/4, Amex lifetime, Citi 48-month) evaluate closed cards' history too.
  All five endpoints use DRF `permission_classes = [IsAuthenticated]`
  (anon → 403, not 401 — no `WWW-Authenticate` challenge is configured, so
  don't add a 401 assertion for these). `cards/serializers.py`
  `UserCardSerializer` is now defined exactly once (a stale duplicate used
  to shadow itself depending on which consumer imported it first — fixed
  in Phase F1). Its fields now also include `bonus_earned_date` and
  `bonus_override` (Phase G) — both editable via `PATCH .../user-cards/
  <id>/` and surfaced in `base.html`'s shared edit-card modal
  (`#editCardDetailsModal`, `openEditCardDetailsModal()`/
  `saveCardDetails()`), the single edit path opened from both the card
  browse page and `/profile/`. `CardCredit.offer_type` (Phase G, choices:
  `statement_credit`/`discount`/`points_miles`/`membership`/
  `companion_pass`/`other`, blank=unknown) is a display-only taxonomy
  rendered as a small badge next to each credit's name in the same modal
  (`populateCardCredits()`) — nothing in the engine reads it yet, and no
  card JSON has been curated with it. **Multi-player households (Phase
  K)**: `UserCard.owner` (nullable FK to `ProfileEntity`, `related_name=
  'cards'`; NULL means "the profile's primary entity" — legacy rows and
  the anon/session mock path never set it) replaced `unique_together
  ['user', 'card']` with `UniqueConstraint(user, card, owner)` (migration
  `0007`, hand-ordered — the new index must exist before the old
  `unique_together` drops, or MySQL raises error 1553 on the `user_id` FK's
  index requirement; `0008` backfills a primary `ProfileEntity` for every
  existing profile and points existing `UserCard`s at it), so a household
  can hold two copies of the same card. `on_delete=RESTRICT`, not
  `PROTECT` — `0009` fixed this after `run_scenario`'s cleanup started
  raising `ProtectedError`: `PROTECT` unconditionally blocks deleting the
  referenced `ProfileEntity` even when the referencing `UserCard` is ALSO
  being deleted in the same cascade (e.g. a whole `User.delete()`);
  `RESTRICT` still blocks a standalone entity delete with live cards
  (`profile_entity_detail_view`'s DELETE catches both `ProtectedError` and
  `RestrictedError` → 400 "reassign or remove this player's N cards
  first") but defers to same-batch cascades. `ProfileEntity` hangs off
  `UserSpendingProfile` (`related_name='entities'`; `name`, `kind`
  personal/business, `is_primary`); `UserSpendingProfile.primary_entity()`
  lazily creates the primary on first touch. `cards/urls.py`
  `profile-entities/` (`GET`/`POST`) and `profile-entities/<id>/`
  (`PATCH`/`DELETE`) are the CRUD surface (all `IsAuthenticated` — auth-only
  feature, anon stays single-player). `add_user_card`/`toggle_user_card`
  resolve an `owner` param (or default to the primary) via
  `_resolve_owner_entity`/`_get_or_create_owned_card` — the latter also
  matches a legacy NULL-owner row when the target is the primary, since
  NULL and the primary entity are the same row conceptually but the DB
  constraint treats them as distinct values. **Security note**: both
  `add_user_card`'s re-add branch and `update_user_card` instantiate
  `UserCardCreateUpdateSerializer` with `context={'request': request}` —
  without it, `validate_owner`'s cross-household check silently no-ops
  (this was a real gap, fixed alongside the K3 owner selector). `base.html`
  `#editCardDetailsModal` gained a "Held By" `<select>` (`#cardOwnerGroup`),
  shown only when authenticated with >1 entity; `updateCardDetails()`'s
  row resolution still targets the FIRST matching `UserCard` for a given
  `CreditCard` id when multiple copies exist — a longstanding ambiguity
  (predates Phase K) not fully resolved here. `profile.html` has a new
  Household management panel (list/add/rename/remove entities) and an
  Owner column on the card table (`owner_name`, stacked per instance like
  the existing signup-date/renewal columns for multi-copy cards).
- `templates/profile.html` `renderCardCollectionTable()`/`buildCardRow()` —
  the "Active cards" dashboard's sortable columns (`CARD_SORT_COLUMNS`)
  include a **Renews** column (Phase G) showing the next anniversary of
  `opened_date` (`nextAnniversary()` helper), highlighted when within 2
  months and the card carries an annual fee. This replaced a pre-existing
  bug where the "renewal soon" highlight compared the raw (always-past)
  `opened_date` straight to `today..+2mo` and could therefore never fire —
  the fix moved that highlight logic onto the Renews column and rebased it
  on the anniversary instead. The Signup Date column itself is now
  unhighlighted, plain formatted dates.
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
  `reward_value_multiplier`, `points_program`) lives in the card JSONs and
  survives the external refresh. `points_program` (Phase J) is curated on
  the Chase Ultimate Rewards and Amex Membership Rewards transferable
  families only (`chase_ultimate_rewards`/`amex_membership_rewards`) — never
  on co-brand cards that earn their own loyalty currency (Delta, Hilton,
  Marriott, etc.), which must NOT carry the key.

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
- **Multi-player households (Phase K)**: a top-level `"entities": [{"name":
  ..., "kind": "personal"|"business"}]` list adds household entities beyond
  the implicit primary (named via top-level `"primary_name"`, default
  `'Player 1'`). A history-dict owned card's `"owner"` key names an entity
  from that list (or the primary's name) — must resolve, or it's a loud
  error; omitted defaults to the primary. Scenarios with no `"entities"`
  key get exactly one entity, so the engine's per-entity refactor is
  provably a no-op for them — enforced automatically:
  `expected_recommendations.apply_as` is absent → every recommendation must
  have NO `apply_as` key at all. `expected_recommendations.apply_as =
  {slug: entity_name}` asserts a specific apply's attribution (checked
  against APPLY recs only — a second-copy apply can share a slug with a
  'keep' rec for the same card, which never carries `apply_as`).
  `data/tests/scenarios/multi_player.json` (6 scenarios, one per Phase K
  behavior: per-entity 5/24 headroom, both-entities-blocked exclusion,
  business attribution, second-copy bonus-only apply, once-per-lifetime
  application rule surviving a close, Amex 5-card cap) brought the sweep
  from 71 to 77.
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
