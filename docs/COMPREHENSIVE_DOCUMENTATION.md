# Credit Card Guru - Comprehensive Documentation

## 🏗️ Project Overview

Credit Card Guru is a sophisticated Django-based credit card optimization platform that generates personalized recommendations for credit card applications, cancellations, and upgrades. The system analyzes user spending patterns, considers issuer policies (like Chase's 5/24 rule), and provides detailed reward calculations to maximize value.

## 📊 Architecture Overview

### Technology Stack
- **Backend**: Django 4.2 + Django REST Framework
- **Database**: SQLite (development) / PostgreSQL (production)
- **Frontend**: HTML/JavaScript with dynamic loading
- **Authentication**: Django Allauth with Google OAuth
- **Data Storage**: JSON imports + PostgreSQL models

### Core Applications
```
mycreditcard.guru/
├── cards/              # Credit card data models & API
├── roadmaps/           # Recommendation engine & roadmap management
├── users/              # User profiles & authentication
├── templates/          # Frontend HTML templates
└── data/               # JSON data files for import
```

## 🗃️ Data Models & Relationships

### Core Models Hierarchy

```
User (Django Auth)
├── UserSpendingProfile
│   ├── SpendingAmount (monthly spending by category)
│   ├── UserSpendingCreditPreference (valued benefits)
│   ├── ProfileEntity (players or business entities in household)
│   ├── UserCreditUsage (tracks benefit check-offs per period)
│   └── Roadmap (saved recommendation scenarios)
└── UserCard (owned credit cards with personal details and owners)

Issuer (Chase, Amex, etc.)
├── CreditCard
│   ├── RewardCategory (earning rates by spending category)
│   ├── CardCredit (benefits like airport lounge, travel credits)
│   └── PointsProgram ( Chase Ultimate Rewards, Amex Membership Rewards, etc. )
└── Policies (5/24 rules, etc.)

SpendingCategory (hierarchical)
├── Parent Categories (Travel, Dining, etc.)
└── Subcategories (Hotels, Airlines, etc.)
```

### Key Model Details

#### CreditCard Model
```python
class CreditCard(models.Model):
    name = models.CharField(max_length=200)
    issuer = models.ForeignKey(Issuer)
    card_type = models.CharField(max_length=20, choices=[('personal', 'Personal'), ('business', 'Business')])
    annual_fee = models.DecimalField(max_digits=8, decimal_places=2)
    signup_bonus_amount = models.IntegerField()
    primary_reward_type = models.ForeignKey(RewardType)  # Points, Miles, Cashback
    points_program = models.ForeignKey(PointsProgram, null=True, blank=True)
    reward_value_multiplier = models.DecimalField(max_digits=6, decimal_places=4, default=0.01)
    metadata = models.JSONField(default=dict)  # Flexible data storage
```

#### UserSpendingProfile Model
```python
class UserSpendingProfile(models.Model):
    user = models.OneToOneField(User, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)  # Anonymous users
    default_reward_type = models.ForeignKey(RewardType)
    
    # Related models:
    # - spending_amounts: Monthly spending by category
    # - spending_credit_preferences: Which benefits user values
    # - entities: Profile entities (household players/businesses)
    # - credit_usages: Used benefit check-offs
    # - roadmaps: Saved recommendation scenarios
```

#### ProfileEntity Model (Phase K Multiplayer)
```python
class ProfileEntity(models.Model):
    profile = models.ForeignKey(UserSpendingProfile, related_name='entities')
    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=10, choices=[('personal', 'Personal'), ('business', 'Business')])
    is_primary = models.BooleanField(default=False)
```

#### UserCard Model (Phase F & K Ownership)
```python
class UserCard(models.Model):
    user = models.ForeignKey(User, related_name='owned_cards')
    card = models.ForeignKey(CreditCard)
    nickname = models.CharField(max_length=100, blank=True)
    opened_date = models.DateField(null=True, blank=True)
    closed_date = models.DateField(null=True, blank=True)
    bonus_earned_date = models.DateField(null=True, blank=True)
    bonus_override = models.BooleanField(null=True, blank=True)  # Override auto eligibility check
    owner = models.ForeignKey(ProfileEntity, on_delete=models.RESTRICT, null=True, blank=True)
```

#### UserCreditUsage Model (Phase L Benefit Tracking)
```python
class UserCreditUsage(models.Model):
    profile = models.ForeignKey(UserSpendingProfile, related_name='credit_usages')
    card_credit = models.ForeignKey(CardCredit, related_name='usages')
    period_key = models.CharField(max_length=20)  # YYYY-MM, YYYY-QX, YYYY-HY, or YYYY
    used = models.BooleanField(default=True)
```

#### SpendingCategory Model (Hierarchical)
```python
class SpendingCategory(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True, blank=True)  # For subcategories
    display_name = models.CharField(max_length=150)
    icon = models.CharField(max_length=50)  # Font Awesome or emoji
    sort_order = models.IntegerField(default=100)
```

### Data Relationships
- **1:N**: User → UserCards, Issuer → CreditCards, CreditCard → RewardCategories, UserSpendingProfile → ProfileEntities
- **M:N**: CreditCard ↔ SpendingCategory (via RewardCategory), UserProfile ↔ SpendingCredit (preferences)
- **Hierarchical**: SpendingCategory self-reference for parent/child relationships

## 🤖 Recommendation Engine Logic

The core recommendation logic is located in [roadmaps/recommendation_engine.py](file:///Users/jamiehouston/src/jamie-houston/mycreditcard.guru/roadmaps/recommendation_engine.py) (and the supporting `roadmaps/engine/` modules). 

For a complete and detailed breakdown of the engine, please refer to the dedicated **[docs/ENGINE.md](file:///Users/jamiehouston/src/jamie-houston/mycreditcard.guru/docs/ENGINE.md)** file.

### High-Level Summary
1. **Card Filtering**: Filters candidate cards based on roadmap parameters (issuers, maximum annual fees).
2. **Greedy Optimization**: Selects the optimal combination of cards that yields the highest net portfolio value without double-counting spending.
3. **Reconciliation Guard**: Verifies that the headline value of every recommendation matches the sum of its displayed terms.
4. **Sequencing (12-Month Capacity)**: Schedules new card applications across a 12-month timeline, deferring signup bonuses that exceed the user's spending capacity.
5. **Multiplayer History & Routing**: Checks rules (like Chase 5/24) per player and assigns business cards to business entities.
6. **Points Pooling**: Values points at the highest redemption rate among cards currently held in the portfolio for Chase Ultimate Rewards and Amex Membership Rewards.

## 🌐 API Endpoints

### Cards App (`/api/cards/`)

#### Reference Data
- `GET /issuers/` - All credit card issuers with policies
- `GET /reward-types/` - Points, Miles, Cashback, etc.
- `GET /spending-categories/` - Hierarchical spending categories
- `GET /spending-credits/` - Available card benefits (airport lounge, etc.)

#### Credit Cards
- `GET /cards/` - All credit cards with full details
- `GET /cards/{id}/` - Individual card with reward categories and credits
- `GET /cards/search/` - Advanced search with filtering

#### User Profiles & Preferences
- `GET /profile/` - Current user's spending profile
- `POST /profile/` - Create/update spending profile
- `GET /recommendations/preview/` - Quick recommendations without saving
- `GET/PUT /credit-preferences/` - Get or update credit preference checkboxes (opt-in/out of specific benefits)
- `GET/PUT /credit-usage/` - Get or update benefit usage check-offs for the current period (month, quarter, half, year)

#### Household Multiplayer Entities
- `GET/POST /profile-entities/` - List or create players/business entities in the household
- `PATCH/DELETE /profile-entities/{id}/` - Update or delete specific players/business entities

#### Card Ownership
- `GET /user-cards/` - User's owned cards with personal details (nickname, dates, owner)
- `POST /user-cards/add/` - Add a card to user's collection
- `PATCH /user-cards/{id}/` - Update card details (nickname, dates, override, owner)
- `DELETE /user-cards/{id}/delete/` - Remove card from collection (sets closed date)

### Roadmaps App (`/api/roadmaps/`)

#### Roadmap Management
- `GET /` - User's saved roadmaps
- `POST /create/` - Create new roadmap with filters
- `GET /{id}/` - Roadmap details with recommendations
- `POST /{id}/generate/` - Generate recommendations for roadmap
- `GET/POST /current/share/` - Toggle and share the current roadmap publicly
- `GET /shared/{uuid}/` - Read-only public shared roadmap payload

#### Quick Operations
- `POST /quick-recommendation/` - Generate recommendations without saving
- `GET /stats/` - User's recommendation statistics

## 🎨 Frontend Pages & Features

### 1. Home Page (`/`) - `templates/index.html`
**Purpose**: Main user interface for spending input and quick recommendations

**Key Features**:
- **Dynamic Category Loading**: Categories loaded from API with icons
- **Real-time Calculations**: Monthly total updates as user types
- **Auto-save Functionality**: Data persisted on form changes
- **Anonymous Support**: Works without login using localStorage
- **Google OAuth Integration**: Seamless authentication

**JavaScript Components**:
```javascript
// Dynamic category rendering with icons and subcategories
function renderSpendingCategories(categories) {
    // Handles hierarchical categories (travel → hotels, airlines)
    // Font Awesome icons with emoji fallbacks
    // Parent categories show totals from subcategories
}

// Real-time recommendation generation
function generateRecommendations() {
    // Builds spending profile from form inputs
    // Calls API for quick recommendations
    // Displays results with detailed breakdowns
}
```

### 2. Card Browse Page (`/cards/`) - `templates/cards_list.html`
**Purpose**: Comprehensive credit card database with filtering

**Features**:
- **Advanced Filtering**: By issuer, reward type, annual fee, ownership
- **Card Details**: Full reward categories, benefits, signup bonuses
- **Ownership Management**: Add/remove cards from personal collection
- **Detailed Modal**: Click for comprehensive card information

### 3. Profile System
**Anonymous Users**: Full functionality using localStorage
**Authenticated Users**: Server-side persistence with Google OAuth

### 4. Responsive Design
- **Mobile Optimized**: Works on all screen sizes
- **Modern UI**: Clean, professional interface
- **Real-time Updates**: Immediate feedback on user actions

## 📁 Data Import System

### JSON Data Structure

#### Credit Cards (`data/input/system/credit_cards.json`)
```json
{
  "name": "Chase Sapphire Reserve",
  "issuer": "Chase",
  "annual_fee": 795,
  "signup_bonus": {
    "bonus_amount": 100000,
    "spending_requirement": 5000,
    "time_limit_months": 3,
    "referral_url": "https://..."
  },
  "reward_type": "Points",
  "reward_value_multiplier": 0.01,
  "reward_categories": [
    {
      "category": "travel",
      "reward_rate": 4,
      "max_annual_spend": null
    }
  ],
  "credits": [
    {
      "category": "travel",
      "value": 150,
      "times_per_year": 2
    },
    {
      "credit_type": "airport_lounge",
      "value": 469,
      "times_per_year": 1
    }
  ]
}
```

#### Spending Categories (`data/input/system/spending_categories.json`)
```json
{
  "name": "travel",
  "display_name": "Travel",
  "description": "Airlines, hotels, rental cars, and travel booking services",
  "icon": "fas fa-plane",
  "sort_order": 20,
  "subcategories": [
    {
      "name": "hotels",
      "display_name": "Hotels",
      "description": "Hotels and accommodations"
    }
  ]
}
```

### Import Commands
```bash
# Import all system data
python manage.py import_cards data/input/system/credit_cards.json
python manage.py import_spending_credits

# Import issuer-specific cards
python manage.py import_cards data/input/cards/chase.json
python manage.py import_cards data/input/cards/american_express.json
```

## 🔧 Configuration & Setup

### Environment Variables
```bash
DEBUG=True                          # Development mode
SECRET_KEY=your-secret-key         # Django secret
DATABASE_URL=sqlite:///db.sqlite3  # Database connection
GOOGLE_OAUTH_CLIENT_ID=...         # Google OAuth (optional)
GOOGLE_OAUTH_CLIENT_SECRET=...     # Google OAuth (optional)
```

### Development Setup
```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run migrations
python manage.py migrate

# 4. Import data
python setup_data.py

# 5. Create superuser (optional)
python manage.py createsuperuser

# 6. Start development server
python manage.py runserver
```

### Production Considerations
- **Database**: PostgreSQL with proper indexing
- **Static Files**: Configure STATIC_ROOT and STATICFILES_STORAGE
- **Security**: Set proper ALLOWED_HOSTS, use HTTPS
- **Caching**: Redis for session storage and caching
- **Background Tasks**: Celery for async processing

## 🧪 Testing & Quality Assurance

### Test Structure
```
data/tests/scenarios/
├── basic_profiles.json      # Common user spending patterns
├── portfolio_optimization.json  # Card combination tests
├── signup_bonus.json       # Bonus calculation tests
└── spending_credits.json   # Benefits calculation tests
```

### Running Tests
```bash
# Run all tests
python manage.py test

# Run a specific scenario with full line-item math
python manage.py run_scenario "Jamie Real" --explain

# Audit every JSON scenario against its expectations
RUN_ALL_SCENARIOS=1 python manage.py test cards.test_json_scenarios
```

## 🚀 Key Features Summary

### For Users
- **Personalized Recommendations**: Based on actual spending patterns
- **Detailed Calculations**: See exactly how rewards are calculated
- **Portfolio Optimization**: Best card combinations without double-counting
- **Anonymous or Authenticated**: Works with or without account
- **Real-time Updates**: Immediate feedback on changes

### For Developers/Businesses
- **Extensible Architecture**: Easy to add new cards, rules, features
- **Rich Data Model**: Supports complex card products and benefits
- **API-First Design**: RESTful APIs for all functionality
- **Production Ready**: Scalable, secure, maintainable codebase
- **Comprehensive Documentation**: This document + inline comments

## 🔮 Future Enhancement Areas

### Near-term Opportunities
1. **Enhanced Issuer Rules**: More sophisticated eligibility logic
2. **Credit Score Integration**: Approval probability calculations  
3. **Spending Prediction**: Machine learning for spending forecasts
4. **Mobile App**: Native iOS/Android applications

### Long-term Vision
1. **Bank Integration**: Automatic spending import via APIs
2. **Market Data**: Real-time offer and bonus tracking
3. **Community Features**: User reviews and experiences
4. **Advanced Analytics**: Portfolio performance tracking over time

## 🎯 How to Use This Documentation with LLMs

This documentation provides a complete understanding of the Credit Card Guru system. When working with LLMs on this project:

### What to Include:
1. **This entire document** for comprehensive system understanding
2. **Specific model definitions** from `cards/models.py` and `roadmaps/models.py`
3. **API endpoint details** from `cards/urls.py` and `roadmaps/urls.py`
4. **Recommendation engine code** from `roadmaps/recommendation_engine.py`

### Key Concepts to Emphasize:
- **Portfolio optimization**: No double-counting of spending across cards
- **Hierarchical categories**: Parent/child relationship in spending categories
- **Card credits vs rewards**: Benefits (travel credits) vs earning rates
- **Anonymous vs authenticated**: Dual-mode user support
- **Smart prioritization**: Balance value optimization with user preferences

### Common Tasks LLMs Can Help With:
- Adding new card data and import logic
- Enhancing recommendation algorithms
- Extending API endpoints
- Improving frontend user experience
- Adding new spending categories or card benefits
- Implementing new issuer rules and policies

This system is production-ready and handles real-world credit card optimization scenarios with sophisticated calculations and user-friendly interfaces.