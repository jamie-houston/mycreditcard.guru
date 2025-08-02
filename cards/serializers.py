from rest_framework import serializers
from .models import (
    Issuer, RewardType, SpendingCategory, CreditCard,
    RewardCategory, CardCredit, UserSpendingProfile,
    SpendingAmount, UserCard, SpendingCredit
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
        fields = ['id', 'name', 'slug', 'display_name', 'description', 'category', 'icon', 'sort_order']


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
            'spending_credit', 'category', 'is_active'
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


class UserCardSerializer(serializers.ModelSerializer):
    card = CreditCardListSerializer(read_only=True)
    card_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = UserCard
        fields = ['id', 'card', 'card_id', 'nickname', 'opened_date', 'is_active']


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
        
        # Update user cards
        if 'user_cards' in validated_data:
            profile.user_cards.all().delete()
            for card_data in validated_data['user_cards']:
                UserCard.objects.create(
                    profile=profile,
                    card_id=card_data['card_id'],
                    nickname=card_data.get('nickname', ''),
                    opened_date=card_data['opened_date'],
                    is_active=card_data.get('is_active', True)
                )
        
        return profile


class UserCardSerializer(serializers.ModelSerializer):
    """Serializer for UserCard model with detailed ownership information"""
    card = CreditCardListSerializer(read_only=True)
    card_id = serializers.IntegerField(write_only=True)
    display_name = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    
    class Meta:
        model = UserCard
        fields = [
            'id', 'card', 'card_id', 'nickname', 'opened_date', 'closed_date',
            'notes', 'display_name', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate(self, data):
        """Validate that closed_date is not before opened_date"""
        opened_date = data.get('opened_date')
        closed_date = data.get('closed_date')
        
        if opened_date and closed_date and closed_date < opened_date:
            raise serializers.ValidationError(
                "Closed date cannot be before opened date"
            )
        
        return data


class UserCardCreateUpdateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating/updating UserCard"""
    
    class Meta:
        model = UserCard
        fields = ['card', 'nickname', 'opened_date', 'closed_date', 'notes']