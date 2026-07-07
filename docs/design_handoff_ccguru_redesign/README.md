# Handoff: Credit Card Guru — Mobile Redesign ("Ledger")

## Overview
A mobile-first cleanup of **foresterh.pythonanywhere.com** (Credit Card Guru), a tool that helps people optimize their credit-card portfolio. The redesign has two jobs:

1. **Build a "roadmap"** — the user enters the cards they hold and their monthly spending by category; the app outputs a plan of what to **keep**, **cancel**, and **apply for**.
2. **Show which card to use for which spending category.**

Goals of the redesign: less scrolling, denser but calmer layout, clean icons instead of emoji, and a simpler information architecture.

## About the Design Files
The file in this bundle (`Credit Card Guru Redesign.dc.html`) is a **design reference created in HTML** — a prototype showing intended look and behavior, **not production code to copy directly**. It renders five phone screens side-by-side on a canvas.

The task is to **recreate these screens in the existing codebase** (the live app is Django server-rendered templates). Implement them using the project's established stack and patterns — Django templates + CSS, or a JS framework if one is being introduced. Reuse the app's existing data models (cards, issuers, categories, user card holdings); this handoff describes the **UI and IA only**, not the backend.

## Fidelity
**High-fidelity.** Colors, typography, spacing, and layout are final and specified below. Recreate pixel-closely, but adapt to the target environment's conventions (component library, spacing utilities). The sample data shown (card names, dollar figures) is **placeholder** — wire real data in.

## Information Architecture (the key change)
The current site has **6 nav destinations**: Home, Roadmap, Profile, Cards, Categories, Issuers. Collapse to a **4-tab bottom nav**:

| Tab | Icon (Material Symbols) | Absorbs | Purpose |
|---|---|---|---|
| **Home** | `home` | Home | Landing / entry to roadmap |
| **Roadmap** | `route` | Roadmap (build + result), **Categories** | Build a plan and view it; best-card-per-category lives inside the result |
| **My Cards** | `style` | **Profile** | Cards the user owns + fee/rewards summary; feeds the roadmap |
| **Browse** | `search` | **Cards**, **Issuers** | Card database; issuers & categories become **filter chips**, not pages |

- **Categories** is not a standalone page — it appears as the "Best card per category" table inside the Roadmap result, where the answer is actionable.
- **Issuers** becomes a filter/chip inside Browse.
- **Profile** is renamed/reframed as **My Cards**; the cards + spending it holds are the same inputs the Roadmap builder uses.

Bottom nav is fixed to the viewport bottom on mobile; on desktop it can become a left sidebar or top nav.

## Design Tokens

### Color (dark theme, "Ledger")
| Token | Hex | Use |
|---|---|---|
| `bg` | `#0F1319` | App background / screen |
| `bezel` | `#05070A` | (device frame only — ignore in app) |
| `surface` | `#171C24` | Cards, inputs, tiles |
| `border` | `#232A34` | Default 1px borders / dividers |
| `border-danger` | `#3A2A2A` | Border on cancel/warning cards |
| `text` | `#E7EBF1` | Primary text |
| `text-strong` | `#FFFFFF` | Big figures |
| `muted` | `#8B95A4` | Secondary text |
| `muted-2` | `#5C6675` | Labels, uppercase eyebrows, inactive nav |
| `accent` | `#3FCF8E` | Primary green — CTAs, positive values, active nav, icons |
| `accent-ink` | `#06251A` | Text on the green button |
| `accent-soft` | `rgba(63,207,142,0.12–0.16)` | Green tint fills/chips |
| `danger` | `#F87171` | Cancel / negative values |
| `danger-soft` | `rgba(248,113,113,0.14)` | Cancel chip fill |

### Typography
- **UI / headings:** `Space Grotesk` (400/500/600/700). Headings 600–700, letter-spacing `-0.02em` on large sizes.
- **Body / secondary text:** `Hanken Grotesk` (400/500/600). Used for descriptive/muted subtext.
- **Numeric figures:** `IBM Plex Mono` (400/500/600) — dollar amounts, multipliers, counts, stat values. This tabular/mono treatment is a signature of the design; use it for **all** numbers.
- Sizes seen: screen title 20px/700; section eyebrow 12px/700 uppercase `letter-spacing:.08em` in `muted-2`; card title 14–15px/600; subtext 12–13px; big hero figure 40px/600 mono; stat figures 20px mono.

### Spacing / radius / shadow
- Screen horizontal padding: **18px**. Bottom-nav padding: `9px 4px 24px` (extra bottom for home indicator).
- Card/tile padding: 11–14px. Gaps between list items: 8–9px.
- Radius: inputs/tiles/list rows **13–14px**; hero/summary cards **20px**; pills/chips **999px**; card-art thumbnail **6px**; icon chips **11px**.
- Icon chip (feature icons on Home): 24px icon, 9px padding, `accent-soft` bg, 11px radius.
- Card-art thumbnail: **46×30px**, radius 6, `linear-gradient(135deg, …)` by issuer color (Amex Gold `#D9B24B→#8A6A1F`; Chase blue `#3A5BA0→#1E2C4F`; dark/Reserve `#2B2B2E→#0E0E10`; Wells red `#C0392B→#7A2018`; grey `#6E7B8B→#3A424D`).
- Device frame in the mock (bezel + 46px radius + shadow) is **presentation only** — do not build it.

### Icons
[Material Symbols Rounded](https://fonts.google.com/icons) (ligature font). Names used: `credit_card`, `route`, `grid_view`, `search`, `arrow_forward`, `arrow_back`, `add_circle`, `add`, `check_circle`, `cancel`, `chevron_right`, `expand_more`, `home`, `style`, `bolt`, `flight_takeoff`, `table_chart`, `restaurant`, `shopping_cart`, `flight`, `local_gas_station`, `play_circle`, `category`. Use the codebase's existing icon set if it has one; otherwise Material Symbols.

---

## Screens / Views

### 1. Home
**Purpose:** Orient a new/returning user and route them into the roadmap.
**Layout:** Vertical stack, 22px header padding. Top bar: wordmark (`credit_card` accent icon + "Card Guru", 16px/700) left, "Sign in" (13px/600 accent) right.
- **Hero:** H1 "Your cards, optimized." (34px/700, `-0.02em`). Sub (15px Hanken, `muted`): "A plan for what to keep, cancel, and apply for — built around what you actually spend."
- **Primary CTA:** full-width green button, `accent` bg / `accent-ink` text, 16px/700, 16px padding, 15px radius, label "Create my roadmap" + `arrow_forward`.
- **Secondary CTA:** full-width, `surface` bg, `border`, `accent` text, "Add my cards first".
- **"What you get" list (eyebrow in `muted-2`):** three `surface` rows (icon chip + title 15px/600 + subtitle 13px Hanken `muted`): "Personal roadmap / Keep · cancel · apply for" (`route`), "Best card per category / Dining, travel, groceries…" (`grid_view`), "Browse 200+ cards / Compare fees & rewards" (`search`).

### 2. Roadmap builder (input)
**Purpose:** Capture strategy, preferences, and monthly spending, then generate the plan.
**Layout:** Header "Create roadmap" (18px/700 + back arrow). Scrollable body; **sticky footer**.
- **Effort selector (eyebrow "How much effort?"):** 3 equal pills (`surface`; selected = `accent-soft` bg + 1.5px `accent` border + accent icon/text). Each: centered icon (22px) + 2-line label. Options: "Set & forget" (`bolt`), "Travel points" (`flight_takeoff`, selected), "Maximize" (`table_chart`). This maps to the existing "strategy" concept (cashback-only / travel / maximizer).
- **Preferences (eyebrow):** 2×2 grid of dropdown fields (`surface`, 13px radius, `expand_more` chevron): each shows a tiny `muted-2` label + 14px/600 value. Fields: Card type (Personal), Rewards (Any), Max annual fee (No limit), Max new cards (4).
- **Monthly spending (eyebrow, with "Add category" accent link right):** list of category rows (`surface`, 13px radius): category icon (accent) + name (14px/500) + amount right-aligned in **IBM Plex Mono** 14px/600. These are editable amount inputs. Sample rows: Dining $620, Groceries $840, Travel $1,100, Gas $260, Streaming $80, Everything else $1,400.
- **Sticky footer** (top `border`, `bg`): row "Total monthly spend" (`muted`) + total in mono 18px/700 white ($4,300); then full-width green CTA "Get my roadmap" + `arrow_forward`.

### 3. Roadmap result (the plan) — most important screen
**Purpose:** Show the plan in one screen with minimal scrolling: the payoff, then keep/apply/cancel, then per-category guidance.
**Layout:** Header "Your roadmap" + back arrow. Scrollable body, 18px padding.
- **Summary hero card** (20px radius, subtle green gradient `linear-gradient(160deg,#1B2A24,#141C19)`, `#2A3A32` border): label "Estimated rewards / year" (`muted`); big figure **$1,840** (40px/600 mono, white) + delta chip **+$740** (`accent-soft`, accent, mono, pill); sub "vs $1,100 today · $4,300/mo tracked" (Hanken `muted`). Then 3 stat tiles in a row (`bg`, `border`): **3 Keep / 2 Apply / 1 Cancel** (figure 20px mono, label 11px `muted`).
- **Section header pattern** (repeated): icon + bold title (15px/700) + count in `muted`. Icons/colors: Apply = `add_circle` accent; Keep = `check_circle` accent; Cancel = `cancel` danger; Categories = `grid_view` accent.
- **"Apply for these" (2):** rich cards (`surface`). Top row: name (15px/600) + reason (13px Hanken `muted`); right = green value chip (`accent-soft`, accent, mono, e.g. "+$330"). Bottom row (divider above): 3 stats — BONUS / FEE / SPEND — label 11px `muted-2`, value 14px/600 mono. Samples: Sapphire Preferred (5× travel · 3× dining; 60k / $95 / $4k/3mo; +$330), Blue Cash Preferred (6% streaming · 3% gas; $250 / $95 / $3k/6mo; +$220).
- **"Keep" (3):** single grouped `surface` card, rows divided by `border`: name (14px/600) + reason (12px Hanken `muted`) + annual value right (13px/600 accent mono). Amex Gold $180, Citi Double Cash $210, Freedom Unlimited $120.
- **"Cancel" (1):** `surface` card with `border-danger`: name + reason (e.g. "$550 fee — travel now covered cheaper") + value "−$550" in danger mono.
- **"Best card per category":** grouped `surface` card; rows: category icon (accent) + name (14px/500) + best card name (13px/600) + rate right (12px `muted` mono, fixed 28px width). Rows: Dining→Amex Gold 4×, Groceries→Amex Gold 4×, Travel→Sapphire Pref. 5×, Gas→Blue Cash Pref. 3%, Streaming→Blue Cash Pref. 6%, Everything else→Double Cash 2%.

### 4. My Cards (Profile)
**Purpose:** See/manage cards the user owns; this is the portfolio the roadmap optimizes.
**Layout:** Header "My cards" (20px/700) + `add_circle` accent (28px) right. Scroll body + bottom nav (My Cards active).
- **Summary strip:** 3 tiles (`surface`, centered): 4 Cards / $800 Annual fees / $1.1k Rewards/yr (figures mono 20px; the rewards one accent).
- **"Active cards" list:** rows (`surface`, 14px radius): card-art thumbnail (gradient) + name (14px/600) + opened date (12px Hanken `muted`) + annual fee (12px mono `muted`) + `chevron_right` (`muted-2`). Cancel-flagged card uses `border-danger` and a **CANCEL SUGGESTED** chip (10px/700 danger on `danger-soft`) in place of the date. Samples: Amex Gold (Mar 2023, $250), Citi Double Cash (Jun 2021, $0), Freedom Unlimited (Jan 2022, $0), Sapphire Reserve ($550, flagged).
- **"Add a card":** dashed-border row (`#2E3742`), `muted` text + `add` icon.

### 5. Browse
**Purpose:** Search/filter the full card database (replaces Cards + Issuers + Categories pages).
**Layout:** Header "Browse cards" (20px/700). Fixed top area: search field (`surface`, `search` icon + placeholder "Search 200+ cards") + horizontal **filter chip row** (active chip = `accent` bg / `accent-ink`; others `surface`+`border`): All / No fee / Travel / Issuer (chips scroll horizontally; Issuer opens a picker). Scroll body + bottom nav (Browse active).
- **Result rows:** (`surface`, 14px radius) card-art thumbnail + name (14px/600) + "Issuer · reward summary" (12px Hanken `muted`) + right column: annual fee (mono `muted`) and, when relevant, a green match value "+$330/yr" **or** an **OWNED** chip (accent on `accent-soft`). Samples: Sapphire Preferred ($95, +$330), Blue Cash Preferred ($95, +$220), Amex Gold (OWNED), Venture X ($395), Active Cash ($0), Custom Cash ($0).

---

## Interactions & Behavior
- **Home → Roadmap builder** via "Create my roadmap"; **Home → My Cards** via "Add my cards first".
- **Builder:** effort pills are single-select and preset the preference fields + max-new-cards; preference fields open pickers/dropdowns; spending amounts are numeric inputs that live-update the sticky **Total**; "Add category" appends a spending row. "Get my roadmap" runs the optimization → Result.
- **Result:** "Apply" cards link to that card in Browse; "Cancel" card links to My Cards; category rows link to the recommended card. Sections can be collapsible if the list grows.
- **My Cards:** row → card detail (existing modal in current app); `add_circle` / "Add a card" → add-card flow; cancel-flagged cards deep-link into the roadmap rationale.
- **Browse:** search filters live; chips toggle filters (Issuer = picker); row → card detail; OWNED reflects My Cards state.
- **Bottom nav:** persistent, 4 tabs, active tab in `accent`.
- Suggested transitions: 150–200ms ease for button/press and tab changes; no elaborate animation required.

## State Management
- **User card holdings** (My Cards): id, product, nickname, opened/closed dates, notes. Supports local/guest mode + synced-when-logged-in (the current app already does this).
- **Roadmap inputs:** strategy/effort, preferences (card type, reward type, max annual fee, max new cards), spending map {category → monthly $}, derived total.
- **Roadmap result:** keep[] / apply[] / cancel[] with per-card annual value, and category→best-card map + estimated annual rewards (new vs current) — computed server-side by the existing optimizer.
- **Browse:** search query, active filters (fee, reward type, issuer, category), results; each result annotated with owned + optional roadmap match value.

## Assets
- No raster assets. Card "art" is a CSS gradient placeholder (46×30, radius 6) keyed to issuer — replace with real card images if the DB has them.
- Icons: Material Symbols Rounded (or the codebase's icon set).
- Fonts: Space Grotesk, Hanken Grotesk, IBM Plex Mono (Google Fonts). Substitute the app's existing families if it standardizes elsewhere, keeping the mono treatment for numbers.

## Files
- `Credit Card Guru Redesign.dc.html` — the five-screen reference prototype (Home, Roadmap builder, Roadmap result, My Cards, Browse). Open in a browser to inspect exact markup, colors, and spacing.
