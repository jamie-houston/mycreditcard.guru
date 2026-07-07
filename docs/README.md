# Credit Card Guru Documentation

This folder contains detailed documentation for the Credit Card Guru project.

## 📄 Documentation Index

### 📍 Start here
- **[PROJECT_STATUS.md](PROJECT_STATUS.md)** - **Where the project is right now**: phase
  plan, active work, backlog. Read this first — it links out to the plan doc for
  whatever feature is currently in progress.
- **[PLAN_BENEFITS_AND_ROADMAP_PERSISTENCE.md](PLAN_BENEFITS_AND_ROADMAP_PERSISTENCE.md)** -
  Detailed design + progress checklist for the active benefit-preferences/
  roadmap-persistence/sharing work (Phases A/B/C in PROJECT_STATUS.md)
- **[../CLAUDE.md](../CLAUDE.md)** - Architecture map and working rules for Claude Code

### 🚀 Getting Started
- **[../RUNNING.md](../RUNNING.md)** - Complete setup and troubleshooting guide
- **[../QUICKSTART.md](../QUICKSTART.md)** - Quick reference for common tasks
- **[CARD_IMPORT_GUIDE.md](CARD_IMPORT_GUIDE.md)** - **How credit card imports work (which cards get imported)**

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
- See `docs/PROJECT_STATUS.md`'s "Verification quick reference" for the current
  scenario-sweep baseline and how recommendations are proven correct

## 💡 Common Questions

**"Which credit cards will be imported?"**
→ See [CARD_IMPORT_GUIDE.md](CARD_IMPORT_GUIDE.md) - Only cards with `"verified": true` are imported
(count drifts as the watchlist grows — see PROJECT_STATUS.md/CLAUDE.md for the current figure)

**"How do I import more cards?"**
→ Edit the JSON files in `data/input/cards/` and set `"verified": true`, then run import

**"How do I run the project locally?"**
→ See [../RUNNING.md](../RUNNING.md) for complete setup instructions

**"What's the easiest way to manage the project?"**
→ Use `python manage_project.py` - interactive menu for all common tasks

## 📝 Documentation Status

Last reviewed 2026-07-07: PROJECT_STATUS.md and the PLAN doc are the living
sources of truth (start there); README_TESTING.md was rewritten to match the
current scenario system; the stale FINAL_TEST_ANALYSIS.md snapshot was
removed (fully superseded by PROJECT_STATUS.md's verification baseline).

---

**Note**: For general project information and quick start instructions, see the main [README.md](../README.md) in the project root.