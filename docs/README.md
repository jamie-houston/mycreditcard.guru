# Credit Card Guru Documentation

This folder contains detailed documentation for the Credit Card Guru project.

## 📄 Documentation Index

### 🚀 Getting Started
- **[../RUNNING.md](../RUNNING.md)** - Complete setup and troubleshooting guide
- **[../QUICKSTART.md](../QUICKSTART.md)** - Quick reference for common tasks
- **[CARD_IMPORT_GUIDE.md](CARD_IMPORT_GUIDE.md)** - **How credit card imports work (which cards get imported)**

### 🔧 Deployment
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Comprehensive PythonAnywhere deployment instructions
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Step-by-step deployment checklist

### 🧪 Testing
- **[README_TESTING.md](README_TESTING.md)** - Complete guide to the data-driven test suite
- **[FINAL_TEST_ANALYSIS.md](FINAL_TEST_ANALYSIS.md)** - Analysis of recommendation algorithm improvements

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
- See [FINAL_TEST_ANALYSIS.md](FINAL_TEST_ANALYSIS.md) for algorithm performance analysis

## 💡 Common Questions

**"Which credit cards will be imported?"**
→ See [CARD_IMPORT_GUIDE.md](CARD_IMPORT_GUIDE.md) - Only cards with `"verified": true` are imported (currently 24 out of 162 cards)

**"How do I import more cards?"**
→ Edit the JSON files in `data/input/cards/` and set `"verified": true`, then run import

**"How do I run the project locally?"**
→ See [../RUNNING.md](../RUNNING.md) for complete setup instructions

**"What's the easiest way to manage the project?"**
→ Use `python manage_project.py` - interactive menu for all common tasks

## 📝 Documentation Status

All documentation is current as of October 2024:
- ✅ Removed outdated and duplicate documentation
- ✅ Added comprehensive card import guide
- ✅ Updated all guides to reference new `manage_project.py` script
- ✅ Maintained essential documentation only

---

**Note**: For general project information and quick start instructions, see the main [README.md](../README.md) in the project root.