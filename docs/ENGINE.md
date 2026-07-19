# Recommendation Engine Architecture

This document details the design, algorithms, and logic of the **Credit Card Guru Recommendation Engine** located in [recommendation_engine.py](file:///Users/jamiehouston/src/jamie-houston/mycreditcard.guru/roadmaps/recommendation_engine.py) (and supported modules in `roadmaps/engine/`).

---

## 🏗️ Core Philosophy & Mathematical Trust

The central promise of the recommendation engine is **trustworthy, reproducible math**. Every recommendation's headline annual value must match its visible line items:

$$\text{Headline Value} = \text{Category Rewards} + \text{Counted Signup Bonuses} + \text{Credits Value} - \text{Annual Fees}$$

A strict reconciliation guard in the engine runs a sanity check on every generated roadmap. If any headline value drifts from the sum of its displayed terms by more than $1, the engine raises a reconciliation exception.

- **Selection vs. Display**: The engine separates portfolio selection (which uses heuristic boosts, strategy weights, and prioritizations to find the best candidate cards) from the display math. The displayed dollars are always calculated via `_calculate_portfolio_allocation` (using category rates and caps) so that the sum of rewards across all categories exactly matches the user's actual spending budget.

---

## 🔍 Optimization Algorithm

The engine uses a **Greedy Search Optimization** strategy to find the highest-value portfolio:

1. **Category Rate Allocation**: The engine scans all available cards in the portfolio. For each category of user spending, it assigns the spend to the card yielding the highest reward rate. It also respects annual spending caps (e.g., $6,000 max spend on 6% back), rolling remaining spend over to the next best card.
2. **First-Year vs. Ongoing Valuation**:
   - **First-Year Net Value** includes the signup bonus and waives first-year annual fees if applicable.
   - **Ongoing Net Value (Annual Value)** reflects the recurring category rewards and benefit values minus the recurring annual fee.
3. **Greedy Iteration**: Starting with the user's currently held cards as the baseline, the engine iteratively evaluates portfolios with one additional card, selecting the step that yields the highest net portfolio value. It stops when it reaches the limit set by the user's selected **Effort-Tolerance Preset**.

---

## ⏳ 12-Month Signup Bonus Capacity & Sequencing

It is unrealistic to apply for multiple credit cards at once due to the minimum spending requirements of signup bonuses. The engine manages this using the **Bonus Capacity Plan** (`_bonus_capacity_plan`):

1. **Spend Budget Allocation**: A signup bonus consumes a monthly portion of the user's total spending budget over its time limit:
   $$\text{Monthly Spend Committed} = \frac{\text{Spending Requirement}}{\text{Time Limit Months}}$$
2. **Timeline Budgeting**: The engine allocates signup bonuses sequentially across a 12-month timeline (`BONUS_CAPACITY_MONTHS = 12`).
3. **Density Sorting**: Candidate cards are sorted by **bonus value density**:
   $$\text{Bonus Density} = \frac{\text{Signup Bonus Value}}{\text{Months Needed}}$$
   Ties are broken by highest bonus value, then by card ID.
4. **All-or-Nothing Walk**: The engine walks the timeline and commits monthly spend to the highest density cards. If a card's requirement exceeds the remaining available monthly budget in its slot, its bonus is **Deferred**.
5. **Deferred Bonuses**: Deferred bonuses are valued at **$0** for the first year (labeled as "Signup bonus deferred" in the UI). However, the card can still be recommended for application based on the strength of its long-term category rewards alone.

---

## 🔄 Points Program Pooling

Points programs (e.g., Chase Ultimate Rewards, Amex Membership Rewards) allow transferring points between cards to unlock higher redemption rates. The engine models this automatically:

1. **Effective Multipliers**: A card's points are valued at the maximum redemption value of the program among all cards currently **HELD** in the portfolio:
   $$\text{Effective Multiplier} = \max(\text{Card's Multiplier}, \text{Best Same-Program Multiplier in Portfolio})$$
2. **Program Mapping**: Driven by the hand-curated `metadata.points_program` key in card definitions (e.g., `chase_ultimate_rewards`, `amex_membership_rewards`). Co-branded cards earning co-branded miles (e.g., Delta, Hilton) do not pool.
3. **Transparency badge**: When a card's points are boosted by another card in the portfolio, a badge reading `"Points valued via [Redemption Card]"` is rendered in the rewards breakdown.

---

## 👥 Multi-Player Households & Entities

The system supports multi-player household profiles (e.g., Player 1, Player 2, and Business Entities) to maximize household-wide rewards while maintaining individual eligibility limits.

### Entity Setup
- **Entities**: Managed under `self.entities`. Anonymous users default to a single mock entity.
- **Card History**: Tracked separately for each entity under `self.entity_histories` by `owner_id`.

### Eligibility Routing
- **Eligibility Checks**: Rule evaluations (like Chase 5/24 or Amex limits) run against the history of the *applying entity*, not the household as a whole.
- **Business Cards**: The engine routes business cards to a business entity first, falling back to the primary player (as a sole proprietor) if no business entity is declared.
- **Personal Cards**: Considers personal entities, primary-first.

### Second-Copy Applies
To allow a household to hold multiple copies of the same high-value card (e.g., both players applying for their own Chase Sapphire card):
- The portfolio de-duplication key is `(card.id, action == 'apply')` (rather than just `card.id`), allowing a keep and apply for the same card ID to coexist.
- Synthetic applies are generated for eligible players and tagged as `duplicate_copy` with a priority score of `500 + card.id`.
- Duplicate applies are valued at their signup bonus and annual fee only (their category rewards are omitted to prevent double-counting, as the category is already optimized by the held copy).

---

## 🎯 Special Modes & Indicators

### 1. Upcoming Large Purchase Mode
When a user inputs a one-off upcoming large expense (e.g., $10,000 for Home Improvement):
- **Owned Card Selection**: Renders the best already-owned card to swipe for the purchase based on category multipliers.
- **New Card Applications**: Renders eligible new cards to apply for, calculating reachability by adding the large expense to the monthly spending budget:
  $$\text{Expense + (Total Monthly Spend } \times \text{ Time Limit Months)} \ge \text{ Spending Requirement}$$
- **Reconciliation**: Renders a simple, three-term sum representing net yield ($Bonus + Rewards - Fee$).

### 2. Category-Less "Easy Mode" Spending
Designed for users who do not want to input detailed category spending:
- Accepts a single total spending amount (monthly or yearly).
- The engine maps this amount to the **"other" (uncategorized)** spending category.
- Portfolios are evaluated using base earning rates (e.g., 1.5% or 2% flat-rate cash back cards win in this mode).

### 3. "Pays for Itself" Indicator
- A card is flagged as `pays_for_itself = true` if the annual value of its allocated benefits/credits meets or exceeds its annual fee:
  $$\text{Allocated Credits Value} \ge \text{Annual Fee}$$
- Allows users to filter out cards that require high category spend to justify their fees, focusing instead on cards that offset their own cost.
