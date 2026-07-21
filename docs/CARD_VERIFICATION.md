# Card Verification Sanity Pass

How to safely flip a card from unverified to `"verified": true` in
`data/input/cards/*.json`. `verified: true` is what puts a card's math in
front of users — see [CARD_IMPORT_GUIDE.md](CARD_IMPORT_GUIDE.md) for how the
flag gates import. This doc is the checklist for the manual review that has
to happen first.

## Why this exists

`import_cards` has no data-quality gate beyond the `verified` flag itself —
bad references (unknown category/credit_type/currency) are only a WARNING and
the offending row is silently dropped, not rejected. Two real bugs slipped
into the catalog by hand before this checklist existed:

- **`a00e4c2`** — United Explorer had the same "Global Entry, TSA PreCheck,
  NEXUS Credit" $100 line item listed twice in its `credits` array, double-
  counting it toward the card's computed value.
- **`61b11ce`** — Amex Platinum's Fine Hotels + Resorts credit was missing
  entirely on 2 of 4 variants, stale at $200 (should've been $600, split
  2x/yr $300) on the other 2, and mislabeled on a Delta co-brand card (a
  $150 Delta Stays credit tagged as the $600 FHR benefit).

Neither would have been caught by the importer. The first is a mechanical,
automatable check; the second only a human cross-checking the issuer's
actual page would catch.

## The checklist

1. **Run the validator** — catches the mechanical defect class
   (duplicates, broken references) before you spend time on anything else:

   ```bash
   venv/bin/python manage.py validate_cards --issuer <file>
   ```

   Clear every `FAIL`. `validate_cards` mirrors `import_cards`'s exact lookup
   semantics (issuer/reward-type/category/credit_type/points-program/currency
   resolution), so a clean run means the data will import faithfully — it
   does **not** mean the dollar values are current or correctly labeled.

2. **Reconcile against the issuer's own page**, per fee-bearing card:
   - Does every credit the card actually offers appear in `credits`? Is the
     `value` current, and is `times_per_year` split correctly (e.g. a
     "$600/yr, $300 twice" benefit should be `value: 300, times_per_year: 2`,
     not `value: 600, times_per_year: 1`)?
   - Does the `description` match what the credit actually is? (The Delta
     Stays / FHR mixup above was exactly a mislabeling, not a stale number.)
   - Are `annual_fee` and `signup_bonus` current?
   - `andenacitelli` (the community sync source — see CARD_IMPORT_GUIDE.md)
     can lag real issuer refreshes by months, especially for premium/high-fee
     cards. For those, prefer a direct web search of the issuer's own
     announcement over trusting the synced value.

3. **Re-run the validator** after edits, to confirm the fix didn't introduce
   a new duplicate or a bad reference.

4. **Flip `"verified": true`**, then:

   ```bash
   venv/bin/python manage.py import_cards data/input/cards/<file>   # confirm no new WARN/ERROR
   venv/bin/python manage.py test
   RUN_ALL_SCENARIOS=1 venv/bin/python manage.py test cards.test_json_scenarios
   venv/bin/python manage.py run_scenario "Jamie Real" --explain
   node scripts/test_roadmap_results.js
   ```

   Any failure here is a regression — see PROJECT_STATUS.md's "Verification
   quick reference" for the current green baseline.

## What the validator does and doesn't cover

`validate_cards` (read-only, never touches the DB or the JSON) catches:
- Duplicate credit line items within a card (same `credit_type`/`category`/
  `description` + same `value`).
- References that won't resolve at import time: `issuer`, `reward_type`/
  `primary_reward_type`, `reward_categories[].category` (by name),
  `credits[].category` (by slug — note this is a *different* field than
  `reward_categories` uses), `credits[].credit_type`, `metadata.points_program`,
  and non-USD `credits[].currency` with no seeded `PointsProgram.currency_code`
  (these silently value at $0.01/unit instead of failing loudly).
- Malformed fields (`weight` outside 0–1, non-positive `times_per_year`,
  non-numeric `value`/`annual_fee`, missing `reward_rate`), duplicate `slug`s,
  missing `url`/`image_url`, and a loose "credit total is way more than 3x the
  fee" heuristic that's worth a second look but isn't necessarily wrong.

It does **not** know whether a dollar amount is stale or a description is
accurate — that's step 2 above, and there's no way around doing it by hand.

## Known deferred modeling gap

Don't try to "fix" this during a verification pass — it needs its own category
first: Amex Gold's prepaid-hotel-via-Amex-Travel rate went from 2x to 5x in
the April 2026 refresh, but `american_express.json`'s Gold entry only has a
blanket `hotels` category with no portal-specific split (unlike Chase's
`chase_travel` or Capital One's `capital_one_travel`). Bumping the blanket
rate to 5x would overstate value for direct hotel bookings. See
PROJECT_STATUS.md's open items for tracking.
