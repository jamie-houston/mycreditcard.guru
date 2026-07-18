# Credit Card Guru - Codebase Refactoring & Cleanup Recommendations

This document provides a comprehensive architectural analysis of the **Credit Card Guru** codebase, with a specific focus on decomposing the monolithic recommendation engine, cleaning up bloated Django view files, standardizing issuer rule structures, and improving testability.

---

## 🏗️ Executive Summary

Credit Card Guru implements a highly sophisticated credit card portfolio optimization algorithm. It evaluates entire portfolios rather than individual cards, enforcing complex rules (like Chase 5/24, credit limits, first-year fee waivers, and signup bonus scheduling).

While the core logic is functionally correct (evidenced by 156 passing tests), it was heavily consolidated within `roadmaps/recommendation_engine.py` (over 2,700 lines of code) and views/serialization modules. To ensure future maintainability, readability, and extensibility (such as adding AI-driven spending patterns or international card support), the codebase is being refactored into modular sub-systems.

---

## 📊 Summary of Recommendations

The table below ranks the recommended cleaning and refactoring tasks by risk, complexity, and rewards.

| Rank | Recommendation | Risk | Complexity | Rewards | Status | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Split `RecommendationEngine` into a Modular Package** | Medium | High | **Very High** | **COMPLETED** | Decompose the 2,700-line monolith into dedicated submodules (orchestration, eligibility, spend allocation, credits, bonus capacity, and optimization). |
| **2** | **Decouple Django Views from API Serialization** | Medium | Medium | **High** | **COMPLETED** | Refactor views in `cards/views.py` and `roadmaps/views.py` to use DRF Serializers rather than custom dictionary builders. |
| **3** | **Decouple Points Programs & Valuations into Models** | Low | Low | **High** | **COMPLETED** | Move hardcoded point valuations (e.g. Chase UR = 1.4¢) into database tables, allowing user customization. |
| **4** | **Standardize Card Metadata & Rule Representation** | Low | Medium | **Medium** | *PENDING* | Define schemas (e.g. via Pydantic or Django JSON schemas) for card metadata to prevent bugs from freeform JSON keys. |
| **5** | **Decouple Test Suite from Database Operations** | Low | Medium | **Medium** | *PENDING* | Refactor tests so that complex algorithmic components (like capacity planning) can be unit-tested using pure Python mocks instead of Django model fixtures. |

---

## 🔍 Detailed Recommendations

---

### 1. Modularize the Monolithic Recommendation Engine (COMPLETED)

Decomposed `roadmaps/recommendation_engine.py` into a package package `roadmaps/engine/` structured as follows:
- `roadmaps/engine/orchestrator.py`: Coordination facade.
- `roadmaps/engine/eligibility_manager.py`: Application limits and entity eligibility.
- `roadmaps/engine/calculators/rewards.py`: Spent calculations and category allocation.
- `roadmaps/engine/calculators/credits.py`: Benefit preference matching and value allocation.
- `roadmaps/engine/calculators/bonus.py`: Signup bonus qualifications and timeline capacity.
- `roadmaps/engine/optimizer.py`: Portfolio combo scenario search and greedy optimizer.

---

### 2. Decouple Django Views from Custom API Serialization (COMPLETED)

Cleaned up dictionary builders in `cards/views.py` and `roadmaps/views.py` by transitioning to structured DRF serializers (e.g. `RoadmapRecommendationResponseSerializer`, `SharedProfileDataSerializer`, etc.).

---

### 3. Decouple Points Programs & Valuations into Database Models (COMPLETED)

Transitioned hardcoded point valuations into structured database tables and customizable user valuation rates.

---

### 4. Standardize Card Metadata & Rule Representation (PENDING)

#### Context
Card details (like signup bonus rules and issuer restrictions) are stored in a database `JSONField` called `metadata` on the `CreditCard` model. The engine accesses keys like `metadata['bonus_eligibility']['once_per_lifetime']`. 

Because this is a freeform JSON field, there is no validation on imports. A typo like `once_per_life_time` in a JSON import file will silently bypass the rule, leading to incorrect recommendations.

#### Proposed Changes
- **Use Pydantic or Typed Dicts**: Implement validation schemas that parse `CreditCard.metadata` on model instantiation or import time.
- **Formalize Issuer Rules**: Transition the static dictionary `ISSUER_RULES` in `roadmaps/eligibility.py` into structured classes (e.g. `BaseIssuerRule`, `WindowRule`, `CapRule`). This will allow new issuers or complex rules (like Capital One's approval velocity limits or Amex's family restrictions) to be plugged in cleanly.

---

### 5. Decouple Test Suite from Database Operations (PENDING)

#### Context
`roadmaps/tests.py` runs calculations by instantiating database fixtures for credit cards, categories, profiles, and entities. This results in tests that must hit the database, making them slow and making it hard to test math edge cases in isolation.

#### Proposed Changes
- **Separate Algorithmic Unit Tests**: Create unit tests that operate on mock dataclasses or simple namespaces representing cards and categories. The core calculation engines (like the bonus capacity plan scheduler) should not require database queries.
- **Test Scenarios Separately**: Keep the integration tests in `cards/test_json_scenarios.py` to assert full database/business logic convergence, but write fast unit tests for mathematical calculations under `roadmaps/tests/`.
