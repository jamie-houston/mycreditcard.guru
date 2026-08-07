# Operations

Operational reference that must stay with the code: how to verify a change, and
the recurring maintenance this project needs. Planning docs, status, and phase
history live in Obsidian (`areas/work/coding/side-projects/mycreditcard.guru/`)
and load only when Jamie names a story file.

## Verification quick reference

```bash
venv/bin/python manage.py validate_cards                                      # card catalog audit — 0 fails before verifying any card
venv/bin/python manage.py test                                                # standard suite (233 tests)
RUN_ALL_SCENARIOS=1 venv/bin/python manage.py test cards.test_json_scenarios   # full sweep must pass clean
venv/bin/python manage.py run_scenario "Jamie Real" --explain                  # every line item reconciles
node scripts/test_roadmap_results.js                                          # roadmap-results.js pure-helper smoke test
venv/bin/pytest tests/e2e/ -v                                                 # Playwright E2E UI test suite (18 tests)
```

Baseline as of 2026-08-06 (post Phase M scenario lock-in): 233 standard
tests green, scenario sweep clean (`test_all_scenarios`, 82 scenarios),
"Jamie Real" reconciles, JS smoke test green (28/28), Playwright E2E UI
test suite green (18/18), `validate_cards` clean (162/162 cards, 0 fails).
Any failure is a regression.

**Phase M closed (2026-08-06)**: five scenarios added to lock in rules that
were shipped but never scenario-tested — BofA 2/30 and CapOne 1/6mo (each
with an "allows" companion so an exclusion can never pass for the wrong
reason), plus a per-entity 5/24 headroom case where the second household
member has 4 of 5 slots used. Five fixture cards back them (`bofa-test-*`,
`capone-test-*`). Three of the five carry explicit `test_*` methods so they
run in the default suite, not only under the sweep.

**Phase M verification (2026-07-19)**: confirmed existing `roadmaps/
eligibility.py` rules — Chase 5/24, BofA 2/3/4, CapOne 1/6mo (window
rules), Amex 5-card open cap (`max_open_cards`), once-per-lifetime bonus
(Amex) + application (`application_eligibility`, Sapphire family) blocks,
business-vs-personal card routing, and per-entity headroom (2 players ⇒ 2×
5/24 budget) — all pass the standard suite and full scenario sweep with no
code changes needed. `data/tests/scenarios/multi_player.json`'s "both
players at 5/24, card excluded" scenario (5 cards × 2 entities = 10 Chase
cards total) is the "10 Chase cards in 24mo for 2 people" case from the
phase's own description — confirmed passing. Closed as verify-and-document
per Jamie's call (2026-07-19); three related gaps remain deliberately
unscoped, not bugs: (a) no aggregate cross-issuer open-card cap, (b) Amex's
per-rule counter is flat (doesn't split charge vs. credit or business vs.
personal sub-limits), (c) no cross-issuer new-account velocity throttle.
Revisit only if a specific gap becomes a real complaint — `roadmaps/
eligibility.py`'s module docstring is the place to extend `ISSUER_RULES`
if so.

## Recurring maintenance

Run `venv/bin/python manage.py import_external_cards` locally ~monthly,
review `git diff data/input/cards/`, commit, push — the repo only stays in
sync with production's automated monthly refresh if this also runs locally
(production resets its own JSON edits before each refresh). Full detail in
`CLAUDE.md`.

The sync now also pulls **credits** from andenacitelli and is
**provenance-aware**: each card JSON carries a `_sources` map tagging which
side owns each section (`annual_fee`, `signup_bonus`, `discontinued`,
`annual_fee_waived`, `credits`). Sections tagged (or defaulted to)
`"andenacitelli"` auto-update as before; sections tagged `"manual"` (e.g.
hand-curated credits) are never overwritten — if andenacitelli's data
disagrees, a `PendingCardUpdate` row is queued instead. After each sync run,
check Django admin → **Pending Card Updates** and approve/reject any
conflicts (approving writes into the JSON and re-imports; reject suppresses
identical future proposals). Detail in `docs/CARD_IMPORT_GUIDE.md`.

andenacitelli only reflects what its own maintainers have entered, so it
can lag real issuer refreshes by months (e.g. it still showed Chase
Sapphire Preferred's old $50 hotel credit in July 2026, weeks after
Chase's own June 2026 announcement of $100). For the small set of
premium/high-fee cards, it's worth periodically web-searching the issuer's
own announcements directly rather than relying solely on the sync — that
pass on 2026-07-20 caught the Sapphire Preferred refresh, a brand-new
Chase Sapphire Reserve "Edit" hotel credit, and missing/stale Amex
Platinum FHR hotel credits across 4 variants, none of which the API had
picked up.
