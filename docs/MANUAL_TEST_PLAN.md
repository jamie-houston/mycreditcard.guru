# Manual Test Plan

Living checklist of manual/browser walkthroughs for changes that automated
tests don't cover well (mostly client-side JS/UI behavior — this repo has no
JS test framework, see `docs/README_TESTING.md` for the automated
Django/scenario suite). Organized by phase/feature; add a new section per
phase, don't delete old ones — they're worth re-running if you touch that
area again.

Run the dev server yourself first (`venv/bin/python manage.py runserver`).
Steps that say "anonymous" should be run in an incognito/private window to
get a clean session.

---

## Phase D: Roadmap-first navigation cleanup (2026-07-08)

Covers: `landing_view`'s `/` → `/roadmap/` redirect, and `/roadmap/`'s
results-first default view with the "Update roadmap" toggle. See
`docs/PROJECT_STATUS.md` phase table and `CLAUDE.md` (`landing_view`/
`index_view`, `templates/index.html`) for the implementation.

### 1. First-time visitor (anonymous, no roadmap yet)
1. Go to `/` → should see the **landing page** (hero + "Create my roadmap" /
   "Add my cards first").
2. Click "Create my roadmap" → lands on `/roadmap/` with the **builder
   open**, heading "Create a Roadmap", empty results below, **no** "Update
   roadmap" bar visible.

### 2. Generate a roadmap
3. Fill in some spending amounts + preferences, click "Get my roadmap".
4. Expect: loading spinner → results render → page scrolls to results →
   builder **collapses** → an "Update roadmap" bar appears above → heading
   flips to "Your Roadmap".

### 3. Reload confirms persistence + results-first view
5. Reload `/roadmap/` (same tab/session). Expect: opens **directly** in
   results mode (little to no builder flash), shows the "Generated on
   {date}" banner, "Update roadmap" bar visible, no need to scroll past a
   form.

### 4. Landing-page skip
6. Navigate to `/` again (or click "Home" in nav). Expect: **redirects
   straight to `/roadmap/`** — you should never see the landing page again
   while this roadmap exists.

### 5. Update roadmap toggle
7. On `/roadmap/`, click "Update roadmap". Expect: builder reveals,
   **pre-filled** with your step-3 values, previous results still visible
   below it, unchanged.
8. Click the "Update roadmap" header again *without* changing anything or
   submitting. Expect: builder collapses again, results untouched, heading
   back to "Your Roadmap" — confirms it's a pure show/hide, not destructive.
9. Change a spending value and click "Get my roadmap" again. Expect: new
   results replace the old ones, builder re-collapses.

### 6. Logged-in path
10. Repeat steps 1–4 while logged in (Google sign-in) to confirm the
    authenticated branch behaves the same as the anonymous-session branch.

### 7. Mobile check
11. Resize to a mobile viewport (or use dev tools device mode). Confirm the
    bottom nav still looks right and the "Update roadmap" bar / builder
    toggle don't look cramped or overlap the sticky footer.

### 8. Dev-only button
12. If testing as `foresterh@gmail.com`: confirm "Export to Test Scenario"
    is still reachable — it now only shows up after opening "Update roadmap"
    (previously always visible). Accepted trade-off, just confirming it's
    not broken.

### 9. Shared roadmap page (sanity check)
13. If you have a shared-roadmap link handy, load it and confirm it looks
    unaffected — that page never touches the new `#roadmapBuilder`/
    `#resultsHeader` elements, so this should be a no-op.

**If something looks off**, the new client-side logic lives in
`templates/index.html`: `setRoadmapViewMode()`, `toggleRoadmapBuilder()`,
and the updated `loadCurrentRoadmap()`/`getRecommendations()`.

---

## Phase C: Roadmap sharing (2026-07-10)

Covers: the share toggle in `#resultsHeader`, `GET/POST
/api/roadmaps/current/share/`, and the public `/roadmap/shared/<uuid>/`
page. See mybrain `Requirements/Complete/PLAN_BENEFITS_AND_ROADMAP_PERSISTENCE_complete.md`
Phase C and `CLAUDE.md`'s roadmap-sharing note for the implementation.

### 1. Share a roadmap (logged in)
1. Log in, generate a roadmap if you don't have a Current Roadmap yet.
2. On `/roadmap/`, click the share icon next to "Update roadmap". Expect: a
   panel opens with Private/Public radios (Private selected) and no share
   URL shown yet.
3. Click "Public". Expect: a "Roadmap is now public and shareable!" toast,
   and a Share URL field + Copy button appear.
4. Click "Copy". Expect: "URL copied to clipboard!" toast, button briefly
   shows "✅ Copied!".

### 2. Open the link logged out
5. Paste the copied URL into an incognito/private window (no session).
   Expect: the roadmap renders read-only — **no** "I have this card" button,
   **no** "Apply Now" button, **no** "Remove from my cards" button on
   keep/cancel rows. Clicking a card row still opens the card detail modal
   (that's expected — it's informational, not an ownership action).
6. Confirm the page shows a "🌐 Public Roadmap" badge and "{name}'s Roadmap"
   heading.

### 3. Reload keeps the share state
7. Back in the logged-in tab, reload `/roadmap/` and reopen the share panel.
   Expect: still shows Public with the same URL (state persisted, not just
   client-side).

### 4. Regenerate keeps the same link
8. Change a spending value and click "Get my roadmap" again. Reopen the
   share panel. Expect: still Public, **same** URL as before (doesn't mint a
   new link on every regeneration) — but the shared page now shows the
   *updated* numbers when reloaded.

### 5. Flip back to private kills the link
9. Click "Private" in the share panel. Expect: "Roadmap is now private"
   toast, Share URL field disappears.
10. Reload the incognito link from step 5. Expect: **404 / "not found"**
    page — the link no longer works.

### 6. Anonymous sharing
11. Repeat steps 1–5 in a fresh incognito window (never logged in). Expect:
    identical behavior — no login prompt, no error. This is the deliberate
    divergence from profile sharing (which requires auth).

### 7. Nothing to share yet
12. In a brand-new incognito window, go to `/roadmap/` without generating
    anything. The share icon shouldn't even be reachable (`#resultsHeader`
    is hidden until a Current Roadmap exists) — confirms the empty-state
    guard on the share panel is unnecessary in practice.

**If something looks off**, the client-side logic lives in
`templates/index.html`: `toggleRoadmapSharePanel()`,
`initializeRoadmapSharePanel()`, `updateRoadmapPrivacySetting()`; the public
page is `templates/shared_roadmap.html`; server-side is
`current_roadmap_share_view`/`shared_roadmap_data_view`/`shared_roadmap_view`
in `roadmaps/views.py`.

---

## Phase E, Step 6: Bonus sequencing timing display (2026-07-17)

Covers: `static/js/roadmap-results.js` `_roadmapTimingLabel()`, the Apply
section's sort by `(recommended_month, priority)`, the new WHEN stat on
each apply card, and the reworked capacity note above the summary table.
Not walked in a browser this session (Jamie's call — automated coverage in
`scripts/test_roadmap_results.js` stood in for it instead); worth a real
pass next time this page is touched. See mybrain
`Requirements/Complete/PLAN_PHASE_E_BONUS_SEQUENCING_complete.md` for the
engine side (archived — Phase E's code is done).

1. Generate a roadmap with several apply recommendations spanning more than
   one bonus-capacity window (e.g. Jamie's real spending profile with a
   strategy that recommends 3+ new cards). Expect: apply cards are ordered
   soonest-first, each showing a WHEN stat — "Apply now" for month 0,
   "Apply in ~N months (Mon YYYY)" otherwise, with the month arithmetic
   matching the "Generated on" date.
2. If any recommended bonus doesn't fit the 12-month capacity, confirm its
   apply card shows a "Signup bonus deferred" info line, $0 signup bonus in
   the summary table, and no WHEN stat implying it needs to happen by a
   specific month (should read "Apply now" — bonus-less applies have no
   window).
3. Confirm the capacity note above "Card summary" appears whenever any
   bonus consumes capacity (not just when something is deferred), lists
   each counted card with its month offset, and — only if applicable —
   appends the deferred-until-next-year and bonus-less sentences.
4. Reload the page (restores the persisted Current Roadmap). Expect: WHEN
   labels and the capacity note are identical to the live-generated view
   (same `generated_at`, same math).
5. Open the roadmap's public share link (logged out). Expect: WHEN labels
   and the capacity note render the same way on the read-only page.

---

## Phase F: Ownership consolidation & line-item polish (2026-07-17)

Covers F4 (bonus_shift $0 filter + aggregation in `roadmap-results.js`) and
F5 (all `UserCard` ownership CRUD moved from `users/` onto `cards/`, with
every frontend caller repointed). Automated coverage is green (109 standard
tests incl. new `cards/tests.py` `UserCardOwnershipSoftCloseTests` /
`UserCardToggleEndpointTests`, 67/67 scenario sweep, `node
scripts/test_roadmap_results.js`) — this pass is about the UI wiring, which
tests don't touch. See `CLAUDE.md`'s "Card ownership (`UserCard`) lives
entirely in `cards/`" bullet and `docs/PLAN_PHASE_F_OWNERSHIP_CLEANUP.md`
for implementation detail.

### 1. F4 — Bonus-window opportunity cost row
1. Generate a roadmap where an apply recommendation shifts spending from
   another owned card to meet a signup bonus (e.g. Jamie's real spending
   profile — several applies shift spend). Expect: **one** "🔁 Bonus-window
   opportunity cost" row per such card (not one row per shifted source),
   signed correctly (net negative usually — shifted spend earns a worse
   rate on the new card), and hovering it shows a tooltip with the
   per-source breakdown.
2. If a recommendation's shifts happen to net to ~$0, confirm **no** row
   renders for it (rather than a pointless "+$0" line).

### 2. F5 — Card ownership through every entry point
Run each of these as **both** an authenticated user and an anonymous
session (anon uses localStorage, should behave identically from the UI).

3. **Card browse page** (`/cards/`): click "I have this card" on an unowned
   card. Expect: chip flips to "OWNED", button becomes "Remove". Click it
   again to remove. Expect: chip disappears, button flips back. Reload the
   page after each step to confirm the state persisted server-side (auth)
   or in localStorage (anon).
4. **Card ownership modal** (`/cards/` → click a card → add/edit details):
   add a card with a nickname + opened date, then edit just the nickname.
   Expect: both save correctly and show up in the profile's "Active cards"
   table.
5. **Profile page** (`/profile/`): use the card search to add a new card.
   Confirm it appears immediately in "Active cards" without a reload.
   Delete it from the table. Confirm it disappears and does **not**
   reappear after a reload (soft-close, not stuck in a weird state).
6. **Generic card-detail modal** (open a card from anywhere — cards list,
   category detail, roadmap results): use "I have this card" / "Edit card
   details" from inside the modal. Expect: same behavior as steps 3–4,
   confirms `base.html`'s `UserDataManager` methods work from every call
   site, not just the page that happens to open the modal first.
7. **Re-add after remove** (the F2/F5 risk spot): remove a card via any
   entry point above, then immediately re-add the *same* card via a
   *different* entry point (e.g. remove from profile, re-add from the
   generic modal). Expect: it comes back as a **single** active row with
   sensible nickname/opened_date (not duplicated, not stuck closed) — this
   exercises the `unique_together` reopen fix in `add_user_card`/
   `toggle_user_card`.
8. **Roadmap results** (`/roadmap/`): on a keep/cancel recommendation,
   click "Remove from my cards". Expect: button shows "Removed", a success
   toast appears. Regenerate the roadmap and confirm the card no longer
   shows as owned/keep. Then re-add it via the card browse page and
   confirm eligibility rules (e.g. Chase 5/24 count) still reflect its
   full history — not reset — since the removal was a soft-close, not a
   delete.

---

## Phase G: Card data & ownership admin (2026-07-17)

Covers: `CardCredit.offer_type` badge, `UserCard.bonus_earned_date`/
`bonus_override` in the shared edit-card modal, and the profile "Renews"
column. Automated coverage is green (110 standard tests incl. new
`roadmaps/tests.py` `test_bonus_override_false_unblocks_repeat_bonus`,
68/68 scenario sweep incl. new `data/tests/scenarios/eligibility.json`
"bonus_override=false unblocks a repeat bonus" scenario) — this pass is
about the UI wiring and visual correctness, which tests don't touch. See
`CLAUDE.md`'s Phase G notes (in the "Card ownership" and profile.html
bullets) for implementation detail.

### 1. Bonus earned date + override (edit modal)
1. Open a card you own (any entry point — cards list, profile, roadmap
   results) → "Edit Details". Expect: two new fields below Opening Date —
   "Bonus Earned Date" (date picker) and "Signup Bonus Status" (Auto / "I
   earned this bonus" / "I did not earn this bonus").
2. Set a bonus earned date and choose "I did not earn this bonus", save.
   Reopen the modal. Expect: both values persisted and re-populate
   correctly (auth: server round-trip; anon: localStorage).
3. Confirm the read-only "Your Card Details" section (before clicking Edit)
   shows the bonus earned date and a "Signup Bonus Status" line reading
   "Confirmed not earned" (or "Confirmed earned" / "Auto (inferred from
   issuer rules)" for the other two states).
4. Pick a scenario where this matters: own a card with a once-per-lifetime
   or months-since-bonus issuer rule (e.g. an Amex card), mark its bonus
   override "I did not earn this bonus", then regenerate the roadmap and
   confirm a fresh application for that same card is recommended with a
   **non-zero** signup bonus (not the usual "$0, bonus unlikely" note).

### 2. offer_type badge
5. `offer_type` ships with no curated data yet, so nothing will show by
   default. To sanity-check the rendering: temporarily set `offer_type`
   on a `CardCredit` row via `manage.py shell` (e.g.
   `CardCredit.objects.filter(pk=X).update(offer_type='statement_credit')`),
   reload the card's detail modal, and confirm a small badge (e.g.
   "Statement credit") appears next to that credit's name. Revert the
   change afterward — no fixture data should be left mutated.

### 3. Renews column
6. On `/profile/`, confirm the "Active cards" table has a new **Renews**
   column, sortable like the others (click the header to toggle asc/desc).
7. For a fee-bearing card whose `opened_date` anniversary falls within the
   next 2 months, confirm the Renews cell is **highlighted** (amber/warning
   style) and the Signup Date cell is plain (no highlight) — the highlight
   moved off Signup Date onto Renews as part of this phase's bug fix.
8. For a no-fee card or one whose anniversary is far off, confirm the
   Renews cell shows a plain (unhighlighted) date, and that the date shown
   is next year's anniversary if this year's has already passed.
