# Credit Card Guru - Recommendation Engine Refactoring & Codebase Cleanups (Archived)

This document archives the completed structural improvements and cleanups performed on the **Credit Card Guru** codebase. It outlines the modularization of the recommendation engine, view deserialization cleanup, and database integration of points programs.

---

## 🏗️ Refactoring Summary

Between July 17 and July 18, 2026, the codebase underwent a major refactoring to address technical debt, reduce file sizes, transition hardcoded rules to dynamic configurations, and improve overall maintainability.

The key accomplishments include:
1. **Decomposed `RecommendationEngine` Monolith**: Split the 2,700-line `roadmaps/recommendation_engine.py` into a clean package under `roadmaps/engine/`.
2. **Standardized API Serialization**: Rewrote ad-hoc dictionary builders in Django views (`cards/views.py`, `roadmaps/views.py`) to leverage Django Rest Framework (DRF) serializers.
3. **Database-Backed Points Programs & Valuations**: Shifted hardcoded point valuations (e.g. Chase UR, Amex MR) into relational tables with user-specific valuation overrides.

---

## 🗂️ Completed Refactoring Phases (Recommendation Engine Split)

All phases of the core engine modularization have been successfully executed and validated against the full 157-test suite.

### Phase 1: Package Initialization
- Created the package directory structure under `roadmaps/engine/` and sub-packages.
- Defined initialization logic in `__init__.py`.

### Phase 2: Eligibility Logic Extraction
- Extracted Chase 5/24, application limits, entity rules, and caching logic to `roadmaps/engine/eligibility_manager.py`.

### Phase 3: Benefit Valuation & Credit Calculations Extraction
- Extracted preference matching, credit allocations, and portfolio credit value calculations to `roadmaps/engine/calculators/credits.py`.

### Phase 4: Spending & Category Rewards Extraction
- Extracted spend allocation, category mappings, effective multiplier calculations, and mathematical breakdown builders to `roadmaps/engine/calculators/rewards.py`.

### Phase 5: Signup Bonus Eligibility & Scheduling
- Extracted signup bonus requirements, minimum spend checks, and the 12-month scheduling algorithm to `roadmaps/engine/calculators/bonus.py`.

### Phase 6: Search & Portfolio Optimization
- Extracted portfolio combination searches and greedy optimization algorithms to `roadmaps/engine/optimizer.py`.

### Phase 7: Orchestrator Hookup & Monolith Redirection
- Constructed the coordination facade `roadmaps/engine/orchestrator.py` which exposes the unified `RecommendationEngine` interface.
- Modified `roadmaps/recommendation_engine.py` to forward calls to the orchestrator package, maintaining API compatibility.

### Phase 8: Cleanup and Documentation
- Removed dead/duplicated code, preserved in-line mathematical and business comments, and verified output reconciliation.

---

## 🧹 Completed Codebase Cleanups

### 1. View & Serialization Decoupling
- Replaced custom JSON dictionary builders in `cards/views.py` and `roadmaps/views.py` with declarative DRF serializers (e.g. `RoadmapRecommendationResponseSerializer`, `SharedProfileDataSerializer`).
- Cleaned up bloated view files, significantly improving readability and input validation rules.

### 2. Relational Points Programs & Valuations
- Replaced the hardcoded static values dictionary in `roadmaps/redemption.py` with Django models:
  - `PointsProgram` model (name, slug, portal url, transfer partners, custom note).
  - `PointsValuation` model (points program, user reference, decimal value).
- Created database seeding script integration (`data/input/system/points_programs.json` loaded via `setup_data.py`).
- Integrated dynamic lookup in the recommendation response serializer, falling back gracefully to system defaults or metadata for anonymous users while supporting customized valuation rates for authenticated users.
