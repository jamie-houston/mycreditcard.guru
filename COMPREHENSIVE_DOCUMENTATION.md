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
│   └── Roadmap (saved recommendation scenarios)
└── UserCard (owned credit cards with personal details)

Issuer (Chase, Amex, etc.)
├── CreditCard
│   ├── RewardCategory (earning rates by spending category)
│   └── CardCredit (benefits like airport lounge, travel credits)
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
    annual_fee = models.DecimalField(max_digits=8, decimal_places=2)
    signup_bonus_amount = models.IntegerField()
    primary_reward_type = models.ForeignKey(RewardType)  # Points, Miles, Cashback
    metadata = models.JSONField(default=dict)  # Flexible data storage
    
    # Key Properties:
    @property
    def reward_value_multiplier(self):
        """Point/mile value (e.g., 0.02 = 2¢ per point)"""
        return self.metadata.get('reward_value_multiplier', 0.01)
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
    # - roadmaps: Saved recommendation scenarios
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
- **1:N**: User → UserCards, Issuer → CreditCards, CreditCard → RewardCategories
- **M:N**: CreditCard ↔ SpendingCategory (via RewardCategory), UserProfile ↔ SpendingCredit (preferences)
- **Hierarchical**: SpendingCategory self-reference for parent/child relationships

## 🤖 Recommendation Engine Logic

### Core Algorithm: `RecommendationEngine` Class

Located in: `roadmaps/recommendation_engine.py`

#### Initialization
```python
def __init__(self, profile: UserSpendingProfile):
    self.profile = profile
    self.user_cards = profile.user.owned_cards.filter(closed_date__isnull=True)
    self.spending_amounts = {
        sa.category.slug: sa.monthly_amount 
        for sa in profile.spending_amounts.all()
    }
```

#### Recommendation Generation Process

1. **Card Filtering**: Apply roadmap filters (issuer, card type, fees, etc.)
2. **Portfolio Optimization**: Select optimal card combinations avoiding double-counting
3. **Value Calculation**: Calculate annual rewards + signup bonuses - fees
4. **Action Assignment**: Determine apply/keep/cancel actions based on value
5. **Smart Prioritization**: Balance high-value cards with user preferences

#### Key Methods

##### `generate_quick_recommendations(roadmap)` → List[dict]
Main entry point for generating recommendations without database persistence.

**Returns recommendation dict:**
```python
{
    'card': CreditCard,
    'action': 'apply|keep|cancel|upgrade|downgrade',
    'priority': int,  # Lower = higher priority
    'estimated_rewards': float,
    'reasoning': str,
    'rewards_breakdown': [
        {
            'category_name': 'Travel',
            'monthly_spend': 1000,
            'annual_spend': 12000,
            'reward_rate': 3.0,
            'reward_multiplier': 0.02,  # 2¢ per point
            'points_earned': 36000,
            'category_rewards': 720.00,
            'calculation': '$12,000 × 3.0x × 0.020 = $720.00'
        }
    ],
    'first_year_value': float,
    'annual_value': float
}
```

##### `_calculate_smart_card_value(card, signup_bonus=True)` → float
Sophisticated value calculation considering:
- **Spending Allocation**: Maps user spending to card's reward categories
- **Rate Optimization**: Finds best earning rates across user's portfolio
- **Credit Benefits**: Includes valued benefits (airport lounge, travel credits)
- **Signup Bonuses**: First-year bonus calculations
- **Fee Considerations**: Handles first-year fee waivers

##### `_calculate_card_credits_value(card)` → (float, list)
Calculates annual value of card benefits:
```python
def _calculate_card_credits_value(self, card):
    """
    Examples:
    - Travel credit: $150 × 2/year = $300 (if user spends on travel)
    - Airport lounge: $469 × 1/year = $469 (if user values this benefit)
    """
    for card_credit in card.credits.filter(is_active=True):
        if credit_matches_user_preferences(card_credit):
            annual_value = card_credit.value * card_credit.times_per_year
            credits_value += annual_value
```

### Recommendation Rules & Logic

#### 1. Portfolio Optimization
- **No Double Counting**: Each dollar of spending allocated to best card only
- **Category Competition**: Higher reward rates take precedence
- **Spending Caps**: Respects annual maximums on bonus categories

#### 2. Action Logic
```python
if card.id in current_card_ids:
    action = 'keep' if (annual_rewards - annual_fee) > 0 else 'cancel'
else:
    if self._is_eligible_for_card(card):
        action = 'apply'
    else:
        continue  # Skip ineligible cards
```

#### 3. Eligibility Rules
- **Issuer Policies**: Respects Chase 5/24, etc. (expandable)
- **Card Limits**: Prevents recommending owned cards
- **Business vs Personal**: Considers card type preferences

#### 4. Priority Scoring
```python
priority_score = base_net_value + efficiency_boost + signup_bonus_boost
# Lower score = higher priority in recommendations
```

#### 5. Smart Filtering
- **Zero-Fee Keeps**: Always include $0 annual fee cards to keep
- **High-Value Applies**: Prioritize new cards with best ROI
- **Strategic Cancels**: Remove negative-value cards
- **Balance**: Limit recommendations to prevent overwhelm

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

#### User Profiles
- `GET /profile/` - Current user's spending profile
- `POST /profile/` - Create/update spending profile
- `GET /recommendations/preview/` - Quick recommendations without saving

#### Card Ownership
- `GET /user-cards/` - User's owned cards with personal details
- `POST /user-cards/add/` - Add card to user's collection
- `PATCH /user-cards/{id}/` - Update card details (nickname, dates, notes)
- `DELETE /user-cards/{id}/delete/` - Remove card from collection

### Roadmaps App (`/api/roadmaps/`)

#### Roadmap Management
- `GET /` - User's saved roadmaps
- `POST /create/` - Create new roadmap with filters
- `GET /{id}/` - Roadmap details with recommendations
- `POST /{id}/generate/` - Generate recommendations for roadmap

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
python manage.py import_credit_types

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

# Run specific test scenarios
python manage.py run_scenario data/tests/scenarios/basic_profiles.json

# Performance testing
python analyze_scenarios.py
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