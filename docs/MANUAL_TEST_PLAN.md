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
