# Credit Card Guru Documentation

This folder contains detailed documentation for the Credit Card Guru project.

## 📄 Documentation Index

### 📍 Start here
- **[../CLAUDE.md](../CLAUDE.md)** - Architecture map and working rules. For a
  one-off task this is the whole context.
- **[OPERATIONS.md](OPERATIONS.md)** - Verification gates and recurring maintenance
- **Status, planning, and stories live in Obsidian**, not this repo:
  `areas/work/coding/side-projects/mycreditcard.guru/` — start at
  `stories/README.md`, which carries the current position. Jamie names the
  story file when there's planned work.

### 🚀 Getting Started
- **[../RUNNING.md](../RUNNING.md)** - Complete setup and troubleshooting guide
- **[../QUICKSTART.md](../QUICKSTART.md)** - Quick reference for common tasks
- **[CARD_IMPORT_GUIDE.md](CARD_IMPORT_GUIDE.md)** - **How credit card imports work (which cards get imported)**
- **[CARD_VERIFICATION.md](CARD_VERIFICATION.md)** - Sanity-pass checklist for
  flipping a card to `verified: true` (run `validate_cards`, then reconcile
  credits/fee/bonus against the issuer's page)

### 🔧 Deployment
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Comprehensive PythonAnywhere deployment instructions
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Step-by-step deployment checklist

### 🧪 Testing
- **[README_TESTING.md](README_TESTING.md)** - Guide to the JSON scenario test
  suite (`data/tests/scenarios/*.json`) — how it's organized, how to add
  scenarios, the recalibration workflow

### 📚 Technical Documentation
- **[COMPREHENSIVE_DOCUMENTATION.md](COMPREHENSIVE_DOCUMENTATION.md)** - Complete technical documentation including:
  - Architecture overview
  - Data models and relationships
  - API endpoints
  - Development workflows
  - Troubleshooting guides

## 🎯 Quick Navigation

### For Developers
- **New to the project?** Start with [../README.md](../README.md)
- **Need to import cards?** See [CARD_IMPORT_GUIDE.md](CARD_IMPORT_GUIDE.md) ⭐
- **Running tests?** Use [README_TESTING.md](README_TESTING.md)
- **Deep dive?** Reference [COMPREHENSIVE_DOCUMENTATION.md](COMPREHENSIVE_DOCUMENTATION.md)

### For Deployment
- Follow [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) step-by-step
- Use [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) to ensure nothing is missed

### For Understanding the Algorithm
- See `docs/OPERATIONS.md`'s "Verification quick reference" for the current
  scenario-sweep baseline and how recommendations are proven correct

## 💡 Common Questions

**"Which credit cards will be imported?"**
→ See [CARD_IMPORT_GUIDE.md](CARD_IMPORT_GUIDE.md) - Only cards with `"verified": true` are imported
(count drifts as the watchlist grows — see `CLAUDE.md` for the current figure)

**"How do I import more cards?"**
→ Edit the JSON files in `data/input/cards/` and set `"verified": true`, then run import

**"How do I run the project locally?"**
→ See [../RUNNING.md](../RUNNING.md) for complete setup instructions

**"What's the easiest way to manage the project?"**
→ Use `python manage_project.py` - interactive menu for all common tasks

## 📝 Documentation Status

Last reviewed 2026-07-26: status and planning moved to Obsidian; this folder now
holds only operational and reference docs. `OPERATIONS.md` carries the
verification baseline that `PROJECT_STATUS.md` used to.

---

**Note**: For general project information and quick start instructions, see the main [README.md](../README.md) in the project root.