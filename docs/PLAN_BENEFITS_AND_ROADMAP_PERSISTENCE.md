# Plan: Benefit Preferences & Stackability, Roadmap Persistence, Roadmap Sharing

Approved implementation plan (2026-07-05). If you are picking this up in a new
session: read CLAUDE.md first, then this file top to bottom. The **Progress**
section at the bottom says exactly what's done and what's next.

## Context

Three user-facing gaps, planned as three phases:

- **Benefits are counted wrong for real users.** Jamie doesn't value airport
  lounge access, but it inflates his card values; and non-stackable benefits
  (lounge, Dashpass, Apple TV) held on multiple cards are double-counted in
  per-card math. Worse, the engine is already internally inconsistent:
  `_calculate_portfolio_summary` dedups ALL credits unconditionally while
  per-card breakdowns count each instance — summary ≠ Σ line items for
  duplicate credits, violating the trustworthy-math promise.
- **The generated roadmap vanishes on reload.** The quick-recommendation flow
  deliberately rolls back everything; nothing is persisted, so users can't
  return to their roadmap.
- **No way to share a roadmap** with a spouse; profile sharing exists
  (`share_uuid` pattern) but nothing for roadmaps.

Decisions made with Jamie: toggles on **both** profile and roadmap pages
sharing one server-persisted preference; stackability is a **curated data
flag** (users never set it); sharing via **link + share toggle**
(profile-share pattern); anonymous persistence is **server-side via session**.

Key existing machinery to reuse: `UserSpendingCreditPreference` (opt-in prefs,
currently localStorage-only), `Roadmap`/`RoadmapCalculation` models (exist,
unused by live flow), `UserSpendingProfile.share_uuid` sharing pattern,
`toggle_user_card` endpoint, `openCardOwnershipModal` in index.html.

---

## Phase A — Benefit preferences & stackability

### A1. Model + data

- Migration: `SpendingCredit.stackable = BooleanField(default=True)`
  (cards/models.py:142-155). Default True = today's per-card behavior for
  unclassified credits.
- `data/input/system/spending_credits.json`: add `"stackable"` to all 18 entries.
  - **false** (membership/subscription — a second one covers nothing):
    airport_lounge, apple_music, apple_tv, disney_plus, dashpass,
    walmart_plus, google_workspace, ziprecruiter, clear
  - **true** (separately redeemable statement credits): airlines, doordash,
    uber_eats, grubhub, dunkin, lyft, precheck (usable for family), stubhub,
    shopping
- `cards/management/commands/import_spending_credits.py`: set `stackable` in
  BOTH the create defaults and the update branch (it uses get_or_create then
  updates fields).
- `cards/serializers.py` `SpendingCreditSerializer` (~line 45-50): add
  `stackable` to fields.

### A2. Engine — single dedup authority (roadmaps/recommendation_engine.py)

Opt-out needs no engine change: `filter(values_credit=True)` at line 1946-1948
already treats an explicit-False row like no row. The engine work is
stackability, done once and used by selection, display, and summary:

1. **`_counted_card_credits(card)`** — refactor the matching half of
   `_calculate_card_credits_value` (1933-1996) into a per-engine-instance
   **cached** lookup (dict keyed by card.id — selection loops call this
   heavily) returning counted CardCredits tagged
   `(dedup_key, stackable, annual_value)`. dedup_key = spending_credit slug;
   category-based credits are always stackable=True (spend-offset statement
   credits).
2. **`_allocate_portfolio_credits(cards)`** — for each stackable=False
   dedup_key on multiple cards, attribute the dollars to exactly ONE card
   (highest annual_value, ties by card id) and give the other carriers a
   **$0 info line** ("Airport Lounge — counted once, on Chase Sapphire
   Reserve", via `_info_item` ~line 468). Returns
   `{card_id: (credits_value, credits_breakdown)}`. Line items always sum ⇒
   reconciliation guard (~439-448) stays green by construction.
3. **Display**: `_calculate_card_allocated_breakdown` (~1594) takes a
   `credit_allocation` param; call sites (~362 keeps/applies, ~826 owned,
   ~1879 fallback) pass allocation over `held_cards`; cancel counterfactual
   (~359-360) passes allocation over `held_cards + [card]`.
4. **Selection**: replace per-card credit sums in `calculate_portfolio_value`
   (~905) and `_calculate_scenario_portfolio_value` (~1140) with the
   allocation sum, so a second lounge card can't win selection on phantom
   value. Leave the single-card candidate-scoring paths alone (no portfolio
   context; never displayed as assembled portfolios).
5. **Summary**: `_calculate_portfolio_summary` (2084-2124) — delete the
   unconditional `unique_credits` dedup; total = sum of the allocation.
   Summary becomes ≡ Σ per-card line items (fixes the pre-existing
   inconsistency; duplicated *stackable*/category credits now count per-card
   in the summary too).

### A3. API — credit preferences for auth + anon

New in `cards/` (anon-capable via session, like `spending_profile_view`
cards/views.py:80), wired in cards/urls.py:

- `GET /api/cards/credit-preferences/` →
  `{"preferences": {"airport_lounge": false, "uber_eats": true}}` (only
  existing rows; absent = untouched = unchecked).
- `PUT /api/cards/credit-preferences/` — upserts
  `UserSpendingCreditPreference` rows both ways (True AND False). Anon:
  `request.session.create()` if needed +
  `UserSpendingProfile.objects.get_or_create(session_key=...)`.

Do NOT change the `GenerateRoadmapSerializer` slug-list contract
(roadmaps/serializers.py:110-114, 219-234) — scenarios and the quick-rec
payload keep working; scratch writes stay inside the rollback.

### A4. Frontend

- **index.html**: `loadSpendingCreditPreferences()` (~676) fetches server
  state first, localStorage as fallback. `saveSpendingCreditPreferences()`
  (~657, has a TODO for exactly this) PUTs the full checkbox state so
  unchecking persists an explicit False. Add "counted once across cards" hint
  on stackable:false checkboxes.
- **profile.html** `loadCreditsProfile()` (619-740, already groups credits by
  type across cards): add an "I use this" toggle per credit group wired to the
  same GET/PUT endpoint; unchecked groups grey out at $0. For stackable:false
  groups spanning >1 card, count only the best instance in the group total and
  "Total Annual Benefits" tile; badge the others "counted once — on {card}"
  (mirrors engine attribution).

### A5. Tests

- Unit (roadmaps/tests.py): allocation — non-stackable duplicate → one winner
  + $0 info lines; stackable duplicate → both count; opt-out row ≡ absent row;
  deterministic tie-break; cancel counterfactual.
- Endpoint (cards/tests.py): GET/PUT auth + anon (session creation),
  False-row round-trip.
- Scenarios: `data/tests/cards.json` currently has only one card with credits
  and no duplicates — add fixture pairs (two lounge cards with different
  values so attribution is testable; two uber_eats cards), each with realistic
  structured `signup_bonus` (hard rule). New
  `data/tests/scenarios/credit_stackability.json`: lounge counted once + both
  headlines reconcile; uber_eats counted twice; no pref → $0.

---

## Phase B — Roadmap persistence + ownership actions

### B1. Anon plumbing fixes (prerequisites — without these, anon persistence silently fails)

- **Session rollback trap**: sessions are DB-backed; for first-time anon users
  `request.session.create()` currently happens INSIDE the rolled-back
  transaction (serializers.py:160-163), and the view then sets
  `session.modified = False` (views.py:188-189) — so the anon user has no
  durable session after generating. Fix: in `quick_recommendation_view`
  (views.py:125), create the session at the top, BEFORE
  `generate_recommendations()`.
- **Remove the loose-profile fallback** (serializers.py:166-177): it grabs
  *any* anonymous profile with spending data for a session-less user — with
  persistence this would attach your roadmap (and share link) to a stranger's
  profile. Replace with plain `get_or_create(session_key=session_key)`.

### B2. Persist on generate — outside the rollback

No migration: reuse `Roadmap` (unique_together [profile, name]) with reserved
name `"Current Roadmap"` + `RoadmapCalculation.calculation_data` JSONField. In
`quick_recommendation_view`, extract the inline response building (~140-184)
into `_build_quick_rec_response()`, then after generation resolve the REAL
profile (user= or session_key= — not the serializer's scratch one) and
`update_or_create` Roadmap + RoadmapCalculation storing
`{'response': data, 'request': request.data, 'generated_at': ...}`. Store
JSON, not RoadmapRecommendation rows (re-render is the only consumer; rows add
FK fragility). Leave `generate_roadmap()` (engine ~219) untouched.

### B3. `GET /api/roadmaps/current/`

New view + `current/` path in roadmaps/urls.py. Resolve profile (no session
auto-create on GET); return `calculation_data['response']` + generated_at;
404 → frontend empty state.

### B4. Frontend (index.html)

- Extract the inline results renderer (~866-1313) into
  `static/js/roadmap-results.js` → `renderRoadmapResults(data, opts)`
  (Phase C reuses it).
- On page load, fetch `/api/roadmaps/current/`; if found, render with
  "Generated on {date} — inputs may have changed" banner. Generate replaces it
  (server overwrites on next POST).
- "I have this card" stays (index.html ~1277-1283 →
  `openCardOwnershipModal`/`saveCardOwnership`); consider showing it beyond
  `apply` actions.
- New "Remove from my cards" on keep/cancel recommendations. Auth:
  `POST /api/users/cards/toggle/` `{card_id, action:'remove'}`
  (users/views.py:88-140 — **soft-close via closed_date; never the hard-delete
  `cards/user-cards/<id>/delete/`**, which would erase eligibility history for
  5/24/Amex-lifetime rules). Anon: remove from localStorage `userCards`. After
  either, show "card list changed — regenerate for updated math"; don't
  silently mutate displayed math.
- Skip the stub `toggle_card_ownership` (cards/views.py:357-383) entirely;
  delete it while in here (existing backlog item).

### B5. Tests

Generate persists Current Roadmap (auth); anon fresh-client persists
(regression test for B1); GET current returns stored JSON; regenerate
overwrites; real profile data untouched by generate (rollback intact);
stale-cookie anon gets its own profile (fallback removal).

---

## Phase C — Roadmap sharing

### C1. Migration on `Roadmap`

`privacy_setting` (private/public, default private) + `share_uuid` (UUID,
null, unique) + `generate_share_uuid()` — copy the pattern from
`UserSpendingProfile` (cards/models.py:189-215).

### C2. Endpoints + page

- `GET/POST /api/roadmaps/current/share/` — mirror
  `update_profile_privacy`/`get_profile_privacy` (cards/views.py:387-470) but
  anon-capable; POST `{privacy_setting}`, generates uuid on public, returns
  `shareable_url`.
- `GET /api/roadmaps/shared/<uuid>/` — public; filters
  `share_uuid=..., privacy_setting='public'`; returns stored response JSON +
  generated_at + owner display name. Build payload from `calculation_data`
  directly (don't reuse `UserSpendingProfileSerializer` — it has a broken
  `user_cards` field).
- Page: `/roadmap/shared/<uuid>/` in creditcard_guru/urls.py → view in
  roadmaps/views.py → new `templates/shared_roadmap.html` (modeled on
  `shared_profile.html`), loads `roadmap-results.js`, calls
  `renderRoadmapResults(data, {readOnly: true})` (hides ownership/apply
  buttons).

### C3. Share UI

Share toggle + copy-link in the results header, copied from profile.html
(16-38, 854-925). Rendered only when a current roadmap exists; works for anon
(session-owned roadmap).

### C4. Tests

Toggle creates uuid; private → 404 (page + data); public renders for
logged-out client; regenerate keeps the same uuid; flipping to private kills
the link.

---

## Docs (same commits as code, per working rules)

- `docs/PROJECT_STATUS.md`: new phases, stackability classification rationale,
  new sweep baseline, note the summary-vs-line-items fix and anon
  session/fallback fixes.
- `CLAUDE.md` architecture map: stackable is curated data in
  spending_credits.json; credit dedup lives in `_allocate_portfolio_credits`
  (all selection/display/summary paths must use it); Current Roadmap
  persistence happens in the view AFTER the rolled-back transaction; roadmap
  sharing mirrors profile sharing.

## Verification

```bash
venv/bin/python manage.py test                                                 # standard suite
RUN_ALL_SCENARIOS=1 venv/bin/python manage.py test cards.test_json_scenarios   # sweep: existing 61 + new scenarios
venv/bin/python manage.py run_scenario "Jamie Real" --explain                  # every line item reconciles
```

Manual: profile toggle ↔ roadmap checkbox stay in sync (auth + incognito
anon); generate → reload → roadmap still shown; remove-card soft-closes; share
link works logged-out; private link 404s.

## Risks

- **Reconciliation guard**: dedup must be $0 info lines on non-winning cards,
  never invisible subtraction. If the guard fires, fix the allocation, not the
  guard.
- **Scenario drift**: summary change (stackable/category duplicates now
  per-card in summary) could shift `portfolio_summary` expectations — fixtures
  have no duplicates and jamie_real holds one card per preferred credit, so
  likely safe; verify any drift via `DUMP_SCENARIOS=1` line-by-line before
  recalibrating.
- **Perf**: selection loops call credit valuation heavily — the per-card cache
  in A2 is required, not optional.
- **Note**: CSR + Sapphire Preferred was the motivating example, but Preferred
  carries no lounge credit in the data; real duplicate pairs are CSR +
  CSR-for-Business and Venture X + Venture X Business. The Dashpass example
  does apply (CSR carries dashpass). Doesn't change the design.

---

## Progress

Update this section as work proceeds. Uncommitted work-in-progress lives on
`main` (check `git status`).

- [x] **A1 — DONE**, committed `0bac083`:
  - `SpendingCredit.stackable` added (cards/models.py) + migration
    `cards/migrations/0005_spendingcredit_stackable.py`
  - `data/input/system/spending_credits.json`: stackable on all 18 entries
  - `import_spending_credits.py` handles stackable in create + update paths
  - `SpendingCreditSerializer` exposes `stackable`
- [x] **A2 — DONE**, committed `0bac083` (same commit as A1, engine work just
      wasn't reflected here at the time): `_counted_card_credits` and
      `_allocate_portfolio_credits` implemented in
      `roadmaps/recommendation_engine.py`; all selection, display, and
      summary call sites route through the allocation (verified by grep —
      `_calculate_portfolio_summary`, `_calculate_card_allocated_breakdown`,
      and both scoring sites call `_allocate_portfolio_credits`). Standard
      suite (63 tests) and scenario sweep pass as of 2026-07-07.
- [x] **A3 — DONE** (2026-07-07): `credit_preferences_view` (GET/PUT) added
      to `cards/views.py`, wired at `/api/cards/credit-preferences/` in
      `cards/urls.py`. GET resolves the profile read-only (auth `filter`,
      anon `session_key` lookup, no creation) and returns only existing
      rows. PUT upserts both True and False rows via `update_or_create`
      (never assumes a default), creates the session for first-time anon
      users (`request.session.create()`) before `get_or_create`-ing the
      profile, and silently ignores unknown slugs. Did NOT touch
      `GenerateRoadmapSerializer`'s slug-list contract
      (roadmaps/serializers.py) — that scratch write stays True-only,
      inside the rollback, as designed.
- [x] A5 (partial) — endpoint tests added: `cards/tests.py`
      `CreditPreferencesAPITests` (5 tests: empty GET, auth round-trip incl.
      explicit-False persistence, anon session creation, unknown-slug
      ignored, 400 on non-dict `preferences`). Standard suite now 68 tests,
      all green; full scenario sweep (`cards.test_json_scenarios`) still
      green. Allocation unit tests and the `credit_stackability.json`
      scenario (the rest of A5) still not started.
- [ ] A4 — not started (no `stackable`-aware UI in index.html/profile.html yet;
      this is what will call the A3 endpoint)
- [ ] B1–B5 — not started
- [ ] C1–C4 — not started
- [ ] Docs updates — PROJECT_STATUS.md phase table + this file kept in sync
      as of 2026-07-07; CLAUDE.md architecture-map note on
      `credit_preferences_view` added same commit as A3. Still need a
      similar note once A4 lands.
