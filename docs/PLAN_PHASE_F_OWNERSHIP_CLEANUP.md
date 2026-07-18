# Plan: Phase F — Cleanup: Ownership Consolidation & Line-Item Polish

Approved implementation plan (2026-07-17). If you are picking this up in a
new session: read `CLAUDE.md` first, then this file top to bottom. The
**Progress** section at the bottom says exactly what's done and what's next.

When Phase F is complete, archive this doc to mybrain
`Requirements/Complete/` and trim `PROJECT_STATUS.md`, per the existing
convention (see `PLAN_PHASE_E_BONUS_SEQUENCING_complete.md` there for the
precedent).

## Context

Two problems accumulated in `cards/`/`users/`:

1. **Two parallel `UserCard` ownership subsystems** exist side by side: the
   `users/` app's soft-close toggle (`POST /api/users/cards/toggle/`,
   `closed_date`-based) and the `cards/` app's add/update/**hard-delete**
   endpoints (`cards/user-cards/<id>/delete/` calls `.delete()`). The
   hard-delete path permanently erases eligibility-relevant history (Chase
   5/24, BofA 2/3/4, Amex lifetime bonus rules — all evaluated against
   `UserCard.bonus_earned_date`/opened/closed dates *including closed
   cards*, per `roadmaps/eligibility.py`). This is exactly the class of bug
   that already bit `/api/users/data/`'s bulk save once (it used to
   hard-delete soft-closed rows too — fixed, see CLAUDE.md's `cards/views.py`
   section) — a second, still-live hard-delete path is a standing risk of
   the same mistake recurring.
2. **A duplicate `UserCardSerializer` definition** in `cards/serializers.py`
   (two classes, same name, different field sets) that silently resolves
   differently depending on evaluation order vs. import order — a
   maintenance trap, not a live bug today, but worth collapsing.

Two smaller display-quality items round out the phase: `$0` line items
leaking into the portfolio/display rewards-breakdown builder, and raw
unaggregated (including `+$0`) `bonus_shift` lines in the roadmap UI.

### Non-negotiable invariant

Same as every engine-touching phase: displayed dollars come from
`_calculate_portfolio_allocation` and the reconciliation guard
(`roadmaps/recommendation_engine.py:571-582`, headline ≈ line items +
signup bonus − fee within $1) must keep holding. F3/F4 only remove/aggregate
**zero-valued or already-summed** line items — see each step for why the
guard is unaffected.

---

## Implementation steps

Recommended order: **F1 → F3 → F4 → F2 → F5** — isolated/low-risk first,
then the ownership fix as two independently shippable pieces (correctness
before structural churn), so we never ship a half-migrated state. Each step
leaves the suite green — run the gates before moving on.

### F1 — Fix the duplicate `UserCardSerializer` (isolated, low risk)

`cards/serializers.py` defines the class **twice** at module scope:
- `:127` "simpler" version — fields `id, card, card_id, nickname,
  opened_date, is_active`. Comment above calls it "kept for basic
  operations."
- `:186` "detailed" version — adds `closed_date, notes, display_name,
  created_at, updated_at` + a `validate()` (closed_date ≥ opened_date).

The bug is name-shadowing by evaluation order: every `import
UserCardSerializer` (from `cards/views.py`, and re-exported through
`users/serializers.py` → `users/views.py`) resolves to the detailed `:186`
class. **But** `UserSpendingProfileSerializer.user_cards`
(`cards/serializers.py:138`) captures the **simpler `:127`** class, because
Python evaluates class bodies top-to-bottom and `:138` runs before `:186`
is even defined. Same name → two different field sets depending on call
site — a landmine for the next person who edits either class expecting the
other's fields to be present.

**Fix:**
1. Move the detailed serializer (currently `:186-209`) to **above**
   `UserSpendingProfileSerializer` (currently `:136`).
2. Delete the simpler `:127-133` duplicate.
3. Confirm `UserSpendingProfileSerializer.user_cards` (`:138`) now binds the
   canonical (detailed) class — it will, since it's the only remaining
   definition.
4. Before deleting, grep every `UserSpendingProfileSerializer` consumer to
   confirm nothing depends on `user_cards` **excluding**
   `closed_date`/`notes` (they're read-only fields, so this should be inert,
   but verify — e.g. a frontend template that iterates `user_cards` and
   would now render fields it didn't expect).

**Gate:** standard suite (103 tests). No scenario-sweep impact (serializers
aren't in the engine's path).

### F3 — $0 line-item filtering (engine, keeps reconciliation)

The single-card builder `_calculate_card_rewards_breakdown` guards
`if annual_spend > 0:` (`roadmaps/recommendation_engine.py:1959`) so
zero-spend categories never become lines. The portfolio/display builder
`_calculate_card_allocated_breakdown` (`:1845`, reward lines at `:1863`) —
used on the assembly/display path, called from `:471/:474`, `:1042`,
`:2100` — has **no such guard**, so a $0 allocation entry attributed to a
card emits a `$0` `reward_category` line.

**Fix:** add the same value guard (`if annual_spend > 0:` or equivalent on
the computed reward value) to the allocated builder at `:1863`, mirroring
`:1959`.

**Why the reconciliation guard still holds:** a $0 line contributes exactly
0 to `Σ item['category_rewards']` (`:575`). Removing a term that's already
0 cannot change `line_total`, so `expected = line_total + signup_bonus_value
- fee_in_headline` (`:576-577`) is unaffected. The frontend already hides
$0 `reward_category`/`credit`/`fee` lines (`roadmap-results.js:289, 309,
332`) — this step just stops the dead data from being generated at the
source, rather than relying on the frontend to hide it.

**Gate:** full sweep (67/67) — expect **no** numeric changes (only line
presence changes for $0 lines), but recalibrate/hand-verify per the usual
`DUMP_SCENARIOS=1` workflow to be sure no scenario asserts on the *count* of
breakdown items. `run_scenario "Jamie Real" --explain` reconciles.

### F4 — Negative `bonus_shift`: filter $0 + aggregate (frontend, display-only)

Today `static/js/roadmap-results.js:298-306` renders **one raw signed line
per shifted spending source** (🔁 `Category window: …` `+$8` / `-$22`) with
**no value guard** — a net-$0 shift renders as a pointless `+$0` line.
`bonus_shift` items are built in `_signup_bonus_plan`
(`roadmaps/recommendation_engine.py:790-800`; `category_rewards = net =
earn - forgo` at `:783`, can be negative when the incumbent card earned a
better rate on the shifted spend).

**Fix:**
1. In the `bonusShifts.forEach` block (`roadmap-results.js:298-306`), stop
   rendering per-source lines directly. Instead:
   - Compute `const shiftTotal = bonusShifts.reduce((sum, item) => sum +
     item.value, 0);`
   - If `bonusShifts.length === 0` or `Math.round(shiftTotal) === 0`, render
     nothing for this group.
   - Otherwise render **one** aggregated row: "🔁 Bonus-window opportunity
     cost" with the signed `shiftTotal`, `title` attribute built from the
     per-source detail (existing `item.calculation`/`item.name` strings
     joined), so the detail isn't lost — just moved to a tooltip.
2. Leave every other consumer of the raw `bonus_shift` items untouched:
   - `_roadmapRewardsValue` (sums raw `bonus_shift` items into the Card
     Summary table's "Rewards" column, per CLAUDE.md) — **do not touch**;
     it must keep summing the underlying items, not the aggregated display
     row, so Card Summary math stays independent of this rendering change.
   - The engine's `line_total`/reconciliation guard — untouched; we're
     aggregating **rendering** of already-computed items, not changing what
     the engine emits or sums.

**Gate:** no Python touched — run
`node scripts/test_roadmap_results.js` (extend it with a case verifying the
aggregated-row behavior: net-zero shifts render nothing, non-zero shifts
produce one row with the correct signed subtotal). Manual browser check
recommended since this is a visible display change (see Verification).

### F2 — Convert hard-delete paths to soft-close (correctness — before F5)

Two paths permanently delete `UserCard` rows today, erasing eligibility
history:
- `cards/views.py:767 remove_user_card` → calls `user_card.delete()` at
  `:779`.
- `users/views.py:37 UserCardDetailView`
  (`RetrieveUpdateDestroyAPIView`, full queryset — no `closed_date` filter)
  — its inherited `DELETE` hard-deletes via the default `destroy()`.

**Fix:**
1. `remove_user_card` (`cards/views.py:767`): replace `user_card.delete()`
   with a soft-close — set `closed_date = timezone.now().date()` (or
   `timezone.now()` if the field is a DateTimeField — check
   `UserCard.closed_date`'s type first) and `.save()`. Mirror the existing
   soft-close pattern in `users/views.py:126` (`toggle_user_card`'s
   `action=remove` branch, which uses `.update()`).
2. `UserCardDetailView` (`users/views.py:37`): override `destroy()` (or
   `perform_destroy()`) to soft-close instead of calling `instance.delete()`.
3. URLs and response shapes stay identical — the sole frontend caller of
   the hard-delete endpoint (`templates/cards_list.html:841`) needs **no**
   edit; the card still disappears from the active list (both `cards/` and
   `users/` active-card queries already filter on `closed_date__isnull`
   /active status).
4. Double-check `unique_together`/re-add semantics: if a user removes then
   re-adds the same card, does `add_user_card`
   (`cards/views.py:670`, `get_or_create`) correctly find/reopen the
   soft-closed row rather than erroring on a uniqueness conflict or
   creating a duplicate? This is the main behavioral risk of the change —
   test it explicitly.

**Gate:** standard suite + new/updated tests asserting the row **survives**
with `closed_date` set (not deleted) after hitting both endpoints, plus the
add-after-soft-close-remove round trip from step 4. No scenario-sweep
impact (this is ownership CRUD, not the recommendation engine) — but note
`run_scenario`/eligibility tests that construct owned-card history via
`closed_days_ago` (per CLAUDE.md's scenario-system section) are unaffected
since they build fixtures directly, not through these endpoints.

### F5 — Structural consolidation onto `cards/` (the long-term fix)

End state: `cards/` is the **single** ownership home; the redundant
`users/` ownership endpoints are retired outright, not left as parallel
copies. This is the larger, higher-churn piece of Phase F — give it its own
commit and a careful manual pass.

1. Consolidate onto the `cards/` app:
   - `user-cards/` (list — already `cards/`), `user-cards/add/`
     (create/update), `user-cards/<id>/` (update), `user-cards/<id>/delete/`
     (soft-close, after F2), `cards/<id>/ownership/` (existing).
   - Add a soft-close **toggle** equivalent under `cards/` if the frontend
     still wants the single add/remove toggle ergonomics that
     `users/cards/toggle/` currently provides (used by `base.html:812, 903`
     and `roadmap-results.js:113`) — don't force those callers into a
     two-step add-then-remove flow if toggle semantics are genuinely
     useful; port the behavior, not just the URL.
2. Retire the duplicate `users/` ownership endpoints entirely
   (`users/urls.py:15-19`: `cards/`, `cards/<pk>/`, `cards/toggle/`,
   `cards/update-details/`, `cards/details/`) and repoint every frontend
   caller to the `cards/` equivalents:
   - `templates/base.html:812, 903` (toggle)
   - `templates/base.html:790` (details)
   - `templates/base.html:844` (update-details)
   - `static/js/roadmap-results.js:113` (toggle)
3. **Leave `/api/users/data/` exactly where it is.** It's the profile bulk
   save (spending + cards together), a different concern from single-card
   CRUD, and it already correctly preserves soft-closed rows
   (`users/serializers.py:83-85`, only hard-deletes *active* cards missing
   from the posted list — see CLAUDE.md). Do not fold it into this
   migration; scope creep here is exactly how the original two-serializer
   duplication problem got created.
4. Standardize auth handling on the surviving `cards/` endpoints while
   here: `users/` used DRF `permission_classes = [IsAuthenticated]`;
   `cards/` does manual `if not request.user.is_authenticated: return
   401` checks. Pick one pattern (DRF permission classes are the more
   idiomatic/consolidated choice) and apply it consistently across the
   surviving endpoints — but only within the endpoints this phase already
   touches; don't scope-creep into unrelated `cards/views.py` endpoints.

**Note:** this step's whole value is removing a second code path — that
means regressions hide in "did I repoint every caller correctly," not in
new logic. Verify every repointed caller by hand in the browser (see
Verification) in addition to the automated suite.

---

## Risk notes

- **F5 is the actual risk in this phase.** F1/F3 are mechanical and
  contained; F4 is a pure-frontend display change with test coverage; F2 is
  a small, well-scoped behavior swap. F5 touches five-plus call sites across
  three templates and one JS file — a missed repoint silently breaks a
  button, not a test (unless the manual pass catches it).
- **F2 → F5 ordering matters.** If F5's endpoint moves happened before F2's
  soft-close fix, the *new* consolidated delete endpoint could inherit the
  hard-delete bug. Doing F2 first means every endpoint F5 later relocates
  is already correct.
- **`add_user_card`'s `get_or_create` vs. re-adding a soft-closed card**
  (flagged in F2 step 4) is the one place a subtle bug could hide: if
  re-adding a previously-removed card doesn't correctly find and reopen the
  soft-closed row, users could end up with duplicate rows for the same
  card, which would confuse `unique_together` assumptions elsewhere
  (Phase K's plan already flags relaxing `unique_together
  ['user','card']` for households — don't let this phase's fix silently
  create *accidental* duplicates instead of intentional multi-owner ones).

## Verification (Phase F definition of done)

```bash
venv/bin/python manage.py test                                                # standard suite
RUN_ALL_SCENARIOS=1 venv/bin/python manage.py test cards.test_json_scenarios  # sweep: 67/67
venv/bin/python manage.py run_scenario "Jamie Real" --explain                 # every line item reconciles
node scripts/test_roadmap_results.js                                          # F4's aggregation logic
```

Plus:
- New/updated API tests for F1 (serializer field consistency) and F2/F5
  (soft-close-on-delete survives with `closed_date` set; re-add-after-remove
  round trip).
- A manual browser pass for F4 (aggregated bonus-shift row renders
  correctly, net-zero shifts produce nothing) and F5 (add/remove/soft-close
  a card through every repointed UI entry point — `base.html` toggle,
  `cards_list.html` add/update/delete, `profile.html`, `index.html`,
  `roadmap-results.js` — confirm the card leaves the active list but
  survives in eligibility history). Append a Phase F checklist to
  `docs/MANUAL_TEST_PLAN.md` before/while doing this.
- `CLAUDE.md`'s ownership-related bullets (`cards/views.py`
  `landing_view`/`index_view` section and the "Remove from my cards"
  bullet under `templates/index.html`) updated to reflect the consolidated
  single ownership path, in the same commit as the code, per working rules.
- `docs/PROJECT_STATUS.md` Phase F line updated/checked off in the same
  commit.

## Progress

- [ ] F1 — duplicate `UserCardSerializer` fix
- [ ] F3 — $0 line-item filtering (allocated breakdown builder)
- [ ] F4 — bonus_shift $0 filter + aggregation
- [ ] F2 — hard-delete → soft-close (both endpoints)
- [ ] F5 — structural consolidation onto `cards/`, retire `users/`
      ownership endpoints, repoint frontend callers
- [ ] Manual browser pass (F4 + F5)
- [ ] Docs updated (CLAUDE.md, PROJECT_STATUS.md, this file) in the same
      commit as the code
