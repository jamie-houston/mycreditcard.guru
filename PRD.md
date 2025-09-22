# Product Requirements Document: Credit Card Guru

## Executive Summary

Credit Card Guru is a sophisticated credit card portfolio optimization platform that generates personalized roadmaps for maximizing credit card rewards through intelligent application, retention, and cancellation strategies. Unlike traditional comparison sites that suggest individual cards, this platform uses portfolio theory and advanced algorithms to optimize entire card collections while respecting issuer policies and user spending patterns.

## Product Vision

**Mission**: Democratize credit card optimization by providing institutional-grade portfolio analysis to everyday consumers, enabling them to maximize rewards while minimizing fees through data-driven strategies.

**Target Users**:
- Primary: Credit card enthusiasts and churners seeking to optimize rewards
- Secondary: Average consumers looking to improve their credit card strategy
- Tertiary: Financial advisors and consultants needing optimization tools

## Core Functionality

### 1. User Management System

#### Anonymous User Support
- **Full Feature Access**: Complete platform functionality without registration
- **Local Storage Persistence**: Browser-based data storage using localStorage
- **Session Tracking**: Server-side anonymous user tracking via Django sessions
- **Seamless Upgrade Path**: One-click transition to authenticated account with data preservation

#### Authenticated Users
- **Google OAuth Integration**: Single sign-on via Google OAuth 2.0
- **Cross-Device Synchronization**: Automatic data sync across devices
- **Conflict Resolution**: Intelligent merging when local and server data diverge
- **Profile Sharing**: Public profile URLs with granular privacy controls

### 2. Spending Profile Management

#### Spending Categories
- **Hierarchical Structure**: Parent categories (e.g., "Dining") with subcategories (e.g., "Restaurants", "Food Delivery")
- **Smart Aggregation**: Automatic rollup of subcategory spending to parent levels
- **Annual Spending Input**: Monthly or annual spending amounts per category
- **Total Calculation**: Real-time spending total updates

#### Credit Preferences
- **Benefit Selection**: Choose which credits/benefits user values (e.g., airline credits, hotel credits, TSA PreCheck)
- **Automatic Matching**: System matches card benefits to user preferences
- **Value Calculation**: Converts credits to annual dollar value based on usage frequency

### 3. Card Portfolio Management

#### Current Cards Tracking
- **Ownership Status**: Track which cards user currently owns
- **Open/Close Dates**: Historical tracking of card acquisition and closure
- **Quick Search**: Real-time card search with instant addition
- **Portfolio Summary**: Total annual fees, estimated rewards, net value

#### Card Database
- **Comprehensive Coverage**: All major US credit cards from major issuers
- **Rich Metadata**: Annual fees, reward categories, signup bonuses, benefits
- **Regular Updates**: Maintained card data with current offers and terms
- **Issuer Organization**: Cards grouped by issuing bank

### 4. Recommendation Engine

#### Core Algorithm Architecture

##### Portfolio Optimization Approach
The system evaluates entire card portfolios rather than individual cards:
- **Scenario Comparison**: Evaluates keeping profitable current cards vs. full portfolio optimization
- **Marginal Value Analysis**: Each new card evaluated for incremental portfolio improvement
- **Anti-Overlap Logic**: Prevents double-counting rewards across multiple cards

##### Recommendation Rules

**KEEP Actions**:
- Applied to cards with positive net value (rewards > annual fee)
- All $0 annual fee cards (never cancelled regardless of rewards)
- Cards providing unique category coverage in optimal portfolio
- Automatically converted to CANCEL if validation shows negative value

**CANCEL Actions**:
- Cards with negative net value where annual fee > rewards generated
- Cards providing redundant coverage (another card covers same categories better)
- Priority display (shown first) as these save immediate money

**APPLY (Sign Up) Actions**:
- New cards adding positive marginal value to portfolio
- Cards optimizing spending allocation better than current holdings
- Limited by user-specified maximum recommendations parameter
- Ordered by total value including signup bonus

##### Spending Allocation Algorithm

```
For each spending category:
1. Identify highest reward rate across all portfolio cards
2. Allocate spending to that card up to any category limits
3. Calculate rewards using card-specific multipliers
4. Sum total rewards across all categories
5. Subtract total annual fees
6. Add signup bonuses for new cards
7. Add annual credit/benefit values
```

##### Anti-Overlap Implementation
- **Single Best Rate**: Only the highest reward rate per category is used
- **No Double Counting**: Spending in each category allocated to exactly one card
- **Category Limits**: Respects maximum spend limits (e.g., $1,500/quarter on rotating categories)
- **Overflow Handling**: Excess spending beyond limits uses next-best card

#### Issuer Policy Enforcement

##### Chase 5/24 Rule
- Automatically excludes Chase cards for users with 5+ new accounts in 24 months
- Tracks card opening dates for accurate calculation
- Provides explanatory messaging when cards excluded

##### Application Velocity Limits
- Respects issuer-specific application frequency rules
- Prevents recommendations violating velocity limits
- Extensible framework for adding new issuer policies

#### Valuation Components

##### Signup Bonus Valuation
- **Cashback Bonuses**: Direct dollar value
- **Points/Miles**: Converted using card-specific multipliers
  - Chase Ultimate Rewards: 1.4¢ per point
  - Amex Membership Rewards: 1.2¢ per point
  - Airline Miles: 1.0-1.5¢ per mile (varies by program)
- **Spending Requirement Check**: Validates user can meet minimum spend
- **First-Year Fee Waiver**: Accounts for waived fees in year-one calculations

##### Annual Rewards Calculation
- **Category Matching**: Maps user spending to card reward categories
- **Multiplier Application**: Applies appropriate earning rates
- **Cap Enforcement**: Respects category spending limits
- **Default Rate**: Uses base earning rate for uncategorized spending

##### Credits and Benefits Valuation
- **User Preference Matching**: Only values benefits user will use
- **Frequency Calculation**: Accounts for monthly/annual benefit frequency
- **Dollar Conversion**: Converts all benefits to annual dollar value

### 5. Roadmap Generation

#### Input Parameters
- **Spending Profile**: Annual spending by category
- **Current Cards**: Existing card portfolio
- **Credit Preferences**: Which benefits/credits user values
- **Filters**:
  - Issuer restrictions
  - Annual fee limits
  - Reward type preferences
  - Maximum new card recommendations

#### Output Structure
- **Action List**: Prioritized list of KEEP/CANCEL/APPLY recommendations
- **Portfolio Summary**:
  - Total annual fees
  - Total estimated rewards
  - Net annual value
  - Signup bonus value
- **Individual Card Details**:
  - Action (Keep/Cancel/Apply)
  - Reasoning with specific dollar amounts
  - Estimated annual value
  - Relevant reward categories

### 6. Sharing and Export

#### Public Profile Sharing
- **Privacy Toggle**: Enable/disable public profile
- **Unique URLs**: UUID-based shareable links
- **Read-Only View**: Clean presentation for sharing
- **Data Protection**: Hides sensitive information

## Technical Requirements

### Architecture

#### Backend Requirements
- **Framework**: Django 4.2+ with Django REST Framework
- **Database**: PostgreSQL (production), SQLite (development)
- **Authentication**: django-allauth with Google OAuth provider
- **Session Management**: Django sessions for anonymous users
- **Caching**: Redis for performance optimization

#### Frontend Requirements
- **Templating**: Django templates with server-side rendering
- **Styling**: Modern CSS with gradient backgrounds, glass-morphism effects
- **JavaScript**: Vanilla JS for interactivity, localStorage management
- **Responsive Design**: Mobile-first approach

#### Data Model Requirements

##### Core Models
- **User**: Extended Django user with profile preferences
- **SpendingCategory**: Hierarchical categories with parent/child relationships
- **CreditCard**: Card details with JSON metadata field
- **UserCard**: Ownership tracking with open/close dates
- **UserSpendingProfile**: Spending amounts by category
- **Roadmap**: Saved recommendation parameters
- **RoadmapRecommendation**: Individual card recommendations
- **RoadmapCalculation**: Portfolio value calculations

##### Key Relationships
- User → UserSpendingProfile (1:1)
- User → UserCard (1:many)
- UserCard → CreditCard (many:1)
- SpendingCategory → self (parent/child hierarchy)
- CreditCard → RewardCategory (many:many)
- Roadmap → RoadmapRecommendation (1:many)

### Performance Requirements

- **Response Time**: <2 seconds for roadmap generation
- **Concurrent Users**: Support 1,000+ simultaneous users
- **Data Volume**: Handle 10,000+ cards, 1M+ user profiles
- **Optimization**: Database query optimization with prefetch_related/select_related
- **Caching Strategy**: Cache card data, category hierarchies

### Security Requirements

- **Authentication**: OAuth 2.0 with secure token storage
- **Data Protection**: Encrypted sensitive data at rest
- **CSRF Protection**: Django CSRF tokens on all forms
- **Rate Limiting**: API throttling to prevent abuse
- **Privacy**: GDPR-compliant data handling

## User Interface Requirements

### Design Principles
- **Progressive Disclosure**: Show essential information first
- **Mobile-First**: Optimize for mobile devices
- **Visual Hierarchy**: Clear action priorities
- **Consistent Patterns**: Reusable UI components
- **Accessibility**: WCAG 2.1 AA compliance

### Key Screens

#### Landing Page
- Value proposition and key benefits
- Two clear CTAs: "Get Started" and "Learn More"
- Social proof and testimonials
- Feature highlights

#### Roadmap Builder
- Collapsible spending category inputs
- Real-time total calculation
- Advanced filter options
- Clear "Generate Roadmap" CTA

#### Results Display
- Action-based grouping (Cancel → Keep → Apply)
- Portfolio summary metrics
- Individual card details with reasoning
- Apply/signup links for new cards

#### Profile Management
- Current cards list with quick search
- Portfolio value summary
- Privacy settings
- Sharing controls

## Success Metrics

### User Engagement
- **Activation Rate**: % of visitors who create first roadmap
- **Retention**: % returning users within 30 days
- **Completion Rate**: % completing full roadmap flow

### Business Metrics
- **Roadmaps Generated**: Total monthly roadmap count
- **Card Applications**: Click-through to card applications
- **Revenue**: Affiliate commission from card signups

### Quality Metrics
- **Recommendation Accuracy**: User-reported value achievement
- **Algorithm Performance**: Portfolio optimization effectiveness
- **User Satisfaction**: NPS score and feedback ratings

## Future Enhancements

### Phase 2 Features
- Credit score integration and impact analysis
- Automated application tracking and reminders
- Community features and strategy sharing
- Mobile native applications

### Phase 3 Features
- AI-powered spending prediction
- Automated churning strategies
- Business card optimization
- International card support

### Phase 4 Features
- Banking product optimization
- Investment account recommendations
- Comprehensive financial planning tools
- White-label B2B offering

## Data Sources and Maintenance

### Card Data Management
- **Import System**: JSON-based card data import
- **Update Frequency**: Monthly card offer updates
- **Data Validation**: Automated testing for data integrity
- **Version Control**: Historical tracking of card changes

### External Integrations
- **Affiliate Networks**: Commission Junction, ShareASale
- **Card Issuer APIs**: Direct offer feeds where available
- **Points Valuation**: Third-party valuation services

## Compliance and Legal

### Regulatory Requirements
- **FCRA Compliance**: No credit scoring or lending decisions
- **Affiliate Disclosure**: Clear disclosure of affiliate relationships
- **Privacy Policy**: Comprehensive data usage policy
- **Terms of Service**: User agreement and liability limitations

### Data Privacy
- **GDPR Compliance**: Right to deletion, data portability
- **CCPA Compliance**: California privacy rights
- **Data Retention**: Defined retention periods
- **Security Audits**: Regular security assessments

## Launch Strategy

### MVP Scope
1. Anonymous user support with local storage
2. Basic recommendation engine with portfolio optimization
3. Core spending categories and credit cards
4. Google OAuth authentication
5. Public profile sharing

### Post-Launch Iterations
- Week 1-2: Bug fixes and performance optimization
- Week 3-4: Additional card data and issuer policies
- Month 2: Enhanced recommendation algorithms
- Month 3: Mobile optimization and PWA support

## Risk Mitigation

### Technical Risks
- **Scalability**: Implement caching and query optimization early
- **Data Accuracy**: Regular validation and user feedback loops
- **Algorithm Complexity**: Extensive testing and edge case handling

### Business Risks
- **Affiliate Relationships**: Diversify across multiple networks
- **Regulatory Changes**: Legal review and compliance monitoring
- **Competition**: Focus on unique portfolio optimization value

## Conclusion

Credit Card Guru represents a paradigm shift in credit card optimization, moving from simple card comparison to sophisticated portfolio management. By combining advanced algorithms with user-friendly design and supporting both anonymous and authenticated users, the platform democratizes access to optimization strategies previously available only to financial professionals. The extensible architecture and comprehensive feature set position the product for long-term growth and market leadership in the credit card optimization space.