from rest_framework import serializers
from .models import (
    Issuer, RewardType, SpendingCategory, CreditCard,
    RewardCategory, CardCredit, UserSpendingProfile,
    SpendingAmount, UserCard, SpendingCredit, ProfileEntity
)


class IssuerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Issuer
        fields = ['id', 'name', 'slug', 'max_cards_per_period', 'period_months']


class RewardTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardType
        fields = ['id', 'name', 'slug']


class SpendingCategorySerializer(serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField()
    parent = serializers.SerializerMethodField()
    
    class Meta:
        model = SpendingCategory
        fields = ['id', 'name', 'slug', 'display_name', 'description', 'icon', 'sort_order', 'parent', 'subcategories']
    
    def get_subcategories(self, obj):
        if obj.subcategories.exists():
            return SpendingCategorySerializer(obj.subcategories.all(), many=True).data
        return []
    
    def get_parent(self, obj):
        if obj.parent:
            return {
                'id': obj.parent.id,
                'name': obj.parent.name,
                'slug': obj.parent.slug,
                'display_name': obj.parent.display_name
            }
        return None


class SpendingCreditSerializer(serializers.ModelSerializer):
    category = SpendingCategorySerializer(read_only=True)
    
    class Meta:
        model = SpendingCredit
        fields = ['id', 'name', 'slug', 'display_name', 'description', 'category', 'icon', 'sort_order', 'stackable']


class RewardCategorySerializer(serializers.ModelSerializer):
    category = SpendingCategorySerializer(read_only=True)
    reward_type = RewardTypeSerializer(read_only=True)
    
    class Meta:
        model = RewardCategory
        fields = [
            'id', 'category', 'reward_rate', 'reward_type',
            'start_date', 'end_date', 'max_annual_spend', 'is_active'
        ]


class CardCreditSerializer(serializers.ModelSerializer):
    spending_credit = SpendingCreditSerializer(read_only=True)
    category = SpendingCategorySerializer(read_only=True)
    
    class Meta:
        model = CardCredit
        fields = [
            'id', 'description', 'value', 'times_per_year', 'weight', 'currency',
            'spending_credit', 'category', 'is_active', 'offer_type'
        ]


class CreditCardSerializer(serializers.ModelSerializer):
    issuer = IssuerSerializer(read_only=True)
    primary_reward_type = RewardTypeSerializer(read_only=True)
    signup_bonus_type = RewardTypeSerializer(read_only=True)
    reward_categories = RewardCategorySerializer(many=True, read_only=True)
    credits = CardCreditSerializer(many=True, read_only=True)
    
    # Add referral URL fields
    referral_url = serializers.ReadOnlyField()
    apply_url = serializers.ReadOnlyField()
    
    class Meta:
        model = CreditCard
        fields = [
            'id', 'name', 'slug', 'issuer', 'card_type', 'annual_fee', 'signup_bonus_amount',
            'signup_bonus_type', 'signup_bonus_requirement', 'primary_reward_type',
            'reward_categories', 'credits', 'is_active', 'created_at', 'metadata',
            'url', 'referral_url', 'apply_url'
        ]


class CreditCardListSerializer(serializers.ModelSerializer):
    """Lighter serializer for card lists"""
    issuer = serializers.StringRelatedField()
    primary_reward_type = serializers.StringRelatedField()
    signup_bonus_type = serializers.StringRelatedField()
    
    # Add referral URL for Apply buttons
    referral_url = serializers.ReadOnlyField()
    apply_url = serializers.ReadOnlyField()
    
    class Meta:
        model = CreditCard
        fields = [
            'id', 'name', 'slug', 'issuer', 'card_type', 'annual_fee', 'signup_bonus_amount',
            'signup_bonus_type', 'primary_reward_type', 'url', 'referral_url', 'apply_url'
        ]


class SpendingAmountSerializer(serializers.ModelSerializer):
    category = SpendingCategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = SpendingAmount
        fields = ['id', 'category', 'category_id', 'monthly_amount']


class ProfileEntitySerializer(serializers.ModelSerializer):
    """A person or business within a household profile (Phase K)."""
    active_card_count = serializers.SerializerMethodField()

    class Meta:
        model = ProfileEntity
        fields = ['id', 'name', 'kind', 'is_primary', 'active_card_count']
        read_only_fields = ['is_primary']

    def get_active_card_count(self, obj):
        return obj.cards.filter(closed_date__isnull=True).count()


class UserCardSerializer(serializers.ModelSerializer):
    """Serializer for UserCard model with detailed ownership information"""
    card = CreditCardListSerializer(read_only=True)
    card_id = serializers.IntegerField(write_only=True)
    display_name = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = UserCard
        fields = [
            'id', 'card', 'card_id', 'nickname', 'opened_date', 'closed_date',
            'bonus_earned_date', 'bonus_override', 'owner', 'owner_name',
            'notes', 'display_name', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_owner_name(self, obj):
        if obj.owner_id:
            return obj.owner.name
        profile = UserSpendingProfile.objects.filter(user=obj.user_id).first()
        return profile.primary_entity().name if profile else None

    def validate(self, data):
        """Validate that closed_date is not before opened_date"""
        opened_date = data.get('opened_date')
        closed_date = data.get('closed_date')

        if opened_date and closed_date and closed_date < opened_date:
            raise serializers.ValidationError(
                "Closed date cannot be before opened date"
            )

        return data


class UserSpendingProfileSerializer(serializers.ModelSerializer):
    spending_amounts = SpendingAmountSerializer(many=True, read_only=True)
    user_cards = UserCardSerializer(many=True, read_only=True)
    
    class Meta:
        model = UserSpendingProfile
        fields = ['id', 'spending_amounts', 'user_cards', 'created_at', 'updated_at']


class CreateSpendingProfileSerializer(serializers.Serializer):
    """Serializer for creating/updating spending profiles"""
    spending_amounts = serializers.ListField(
        child=serializers.DictField(child=serializers.DecimalField(max_digits=10, decimal_places=2)),
        required=False
    )
    user_cards = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    
    def create(self, validated_data):
        request = self.context['request']
        
        # Create or get profile
        if request.user.is_authenticated:
            profile, created = UserSpendingProfile.objects.get_or_create(user=request.user)
        else:
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
            profile, created = UserSpendingProfile.objects.get_or_create(session_key=session_key)
        
        # Update spending amounts
        if 'spending_amounts' in validated_data:
            profile.spending_amounts.all().delete()
            for category_data in validated_data['spending_amounts']:
                for category_id, amount in category_data.items():
                    SpendingAmount.objects.create(
                        profile=profile,
                        category_id=int(category_id),
                        monthly_amount=amount
                    )
        
        # Note: User cards are now managed separately via UserCard API endpoints
        # They are no longer part of the UserSpendingProfile serializer
        
        return profile


class UserCardCreateUpdateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating/updating UserCard"""
    owner = serializers.PrimaryKeyRelatedField(
        queryset=ProfileEntity.objects.none(),  # Set dynamically in __init__
        required=False,
        allow_null=True
    )

    class Meta:
        model = UserCard
        fields = ['nickname', 'opened_date', 'closed_date', 'bonus_earned_date', 'bonus_override', 'notes', 'owner']
        extra_kwargs = {
            'owner': {'required': False},
            'bonus_earned_date': {'required': False},
            'bonus_override': {'required': False},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            self.fields['owner'].queryset = ProfileEntity.objects.filter(
                profile__user=request.user
            )

    def validate_owner(self, value):
        """Ensure owner belongs to the current user's household"""
        request = self.context.get('request')
        if value and request and hasattr(request, 'user') and request.user.is_authenticated:
            # Check that the owner belongs to this user's profile
            if not ProfileEntity.objects.filter(profile__user=request.user, id=value.id).exists():
                raise serializers.ValidationError("This entity does not belong to your household.")
        return value


class UserSpendingCreditPreferenceSerializer(serializers.Serializer):
    def to_representation(self, instance):
        return {
            pref.spending_credit.slug: pref.values_credit
            for pref in instance.spending_credit_preferences.select_related('spending_credit')
        }


class CategoryDetailCardSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='card.id')
    name = serializers.CharField(source='card.name')
    issuer = serializers.CharField(source='card.issuer.name')
    reward_rate = serializers.FloatField()
    annual_fee = serializers.FloatField(source='card.annual_fee')
    max_annual_spend = serializers.FloatField(required=False, allow_null=True)
    signup_bonus_amount = serializers.IntegerField(source='card.signup_bonus_amount')


class CategoryDetailSerializer(serializers.ModelSerializer):
    top_reward_rate = serializers.SerializerMethodField()
    cards_with_rewards = serializers.SerializerMethodField()

    class Meta:
        model = SpendingCategory
        fields = ['id', 'name', 'display_name', 'description', 'icon', 'slug', 'sort_order', 'top_reward_rate', 'cards_with_rewards']

    def get_top_reward_rate(self, obj):
        return self.context.get('top_rate', 0.0)

    def get_cards_with_rewards(self, obj):
        reward_categories = self.context.get('reward_categories', [])
        return CategoryDetailCardSerializer(reward_categories, many=True).data


class CategoryWithRewardsSerializer(serializers.ModelSerializer):
    top_reward_rate = serializers.SerializerMethodField()
    cards_with_rewards_count = serializers.SerializerMethodField()

    class Meta:
        model = SpendingCategory
        fields = ['id', 'name', 'display_name', 'description', 'icon', 'slug', 'sort_order', 'top_reward_rate', 'cards_with_rewards_count']

    def get_top_reward_rate(self, obj):
        from django.db.models import Max
        top_rate = obj.reward_categories.filter(is_active=True).aggregate(max_rate=Max('reward_rate'))['max_rate'] or 0
        return float(top_rate)

    def get_cards_with_rewards_count(self, obj):
        return obj.reward_categories.filter(is_active=True, reward_rate__gt=1.0).count()


class RecommendationPreviewItemSerializer(serializers.Serializer):
    card_id = serializers.IntegerField(source='card.id')
    card_slug = serializers.CharField(source='card.slug')
    card_name = serializers.SerializerMethodField()
    action = serializers.CharField()
    estimated_rewards = serializers.FloatField()
    reasoning = serializers.CharField()
    priority = serializers.IntegerField()

    def get_card_name(self, obj):
        return str(obj['card'])


class RecommendationPreviewSerializer(serializers.Serializer):
    recommendations = RecommendationPreviewItemSerializer(many=True)


class SharedProfileDataSerializer(serializers.ModelSerializer):
    spending_amounts = SpendingAmountSerializer(many=True, read_only=True)
    user_cards = UserCardSerializer(many=True, read_only=True)
    profile_owner = serializers.SerializerMethodField()
    portfolio_summary = serializers.SerializerMethodField()
    card_recommendations = serializers.SerializerMethodField()

    class Meta:
        model = UserSpendingProfile
        fields = ['id', 'spending_amounts', 'user_cards', 'created_at', 'updated_at', 'profile_owner', 'portfolio_summary', 'card_recommendations']

    def get_profile_owner(self, obj):
        return obj.user.username if obj.user else 'Anonymous User'

    def get_portfolio_summary(self, obj):
        if obj.user:
            user_cards = obj.user.owned_cards.filter(closed_date__isnull=True)
            total_cards = user_cards.count()
            total_annual_fees = sum(float(card.card.annual_fee or 0) for card in user_cards)
            return {
                'total_cards': total_cards,
                'total_annual_fees': total_annual_fees,
                'has_cards': total_cards > 0
            }
        return {
            'total_cards': 0,
            'total_annual_fees': 0,
            'has_cards': False
        }

    def get_card_recommendations(self, obj):
        card_recommendations = []
        if obj.user:
            user_cards = obj.user.owned_cards.filter(closed_date__isnull=True)
            spending_amounts = obj.spending_amounts.all().order_by('-monthly_amount')
            
            for spending in spending_amounts:
                if float(spending.monthly_amount) < 50:
                    continue
                    
                category_name = spending.category.display_name
                category_slug = spending.category.slug
                monthly_amount = float(spending.monthly_amount)
                
                best_card = None
                reward_rate = "1x"
                
                for user_card in user_cards:
                    card = user_card.card
                    has_category = card.reward_categories.filter(
                        category__slug=category_slug
                    ).exists()
                    
                    if has_category:
                        reward_cat = card.reward_categories.filter(
                            category__slug=category_slug
                        ).first()
                        if reward_cat:
                            best_card = card.name
                            reward_rate = f"{reward_cat.reward_rate}x"
                            break
                
                if not best_card:
                    if category_slug in ['dining']:
                        best_card = "Chase Sapphire Reserve"
                        reward_rate = "3x"
                    elif category_slug in ['airlines', 'hotels', 'rental_cars']:
                        best_card = "Chase Sapphire Reserve"
                        reward_rate = "3x" 
                    elif category_slug in ['in_store_grocery', 'groceries']:
                        best_card = "Blue Cash Preferred Card from American Express"
                        reward_rate = "6x"
                    elif category_slug in ['gas']:
                        best_card = "Blue Cash Preferred Card from American Express"
                        reward_rate = "3x"
                    elif category_slug in ['streaming']:
                        best_card = "Blue Cash Preferred Card from American Express"
                        reward_rate = "6x"
                    else:
                        best_card = "Chase Sapphire Reserve"
                        reward_rate = "1x"
                
                card_recommendations.append({
                    'category': category_name,
                    'monthly_spending': monthly_amount,
                    'recommended_card': best_card,
                    'reward_rate': reward_rate,
                    'percentage': f"${monthly_amount:,.0f}/month"
                })
        return card_recommendations