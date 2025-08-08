from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, UserPreferences
from cards.models import UserCard, UserSpendingProfile, SpendingAmount
from cards.serializers import CreditCardListSerializer, SpendingCategorySerializer, UserCardSerializer


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['user', 'preferred_issuer', 'preferred_reward_type', 'max_annual_fee', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


# UserCardSerializer moved to cards.serializers to avoid duplication
# Import from cards.serializers import UserCardSerializer


class UserSpendingSerializer(serializers.ModelSerializer):
    category = SpendingCategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = SpendingAmount
        fields = ['id', 'category', 'category_id', 'monthly_amount']
        read_only_fields = ['id']


class UserPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreferences
        fields = [
            'default_issuer_filter', 'default_reward_type_filter', 'default_max_fee_filter',
            'default_max_recommendations', 'theme', 'email_notifications', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class UserDataSerializer(serializers.Serializer):
    """Serializer for bulk user data operations"""
    spending = serializers.DictField(child=serializers.DecimalField(max_digits=10, decimal_places=2))
    cards = serializers.ListField(child=serializers.IntegerField())
    preferences = serializers.DictField(required=False)
    
    def create(self, validated_data):
        user = self.context['request'].user
        spending_data = validated_data.get('spending', {})
        cards_data = validated_data.get('cards', [])
        preferences_data = validated_data.get('preferences', {})
        
        # Get or create user spending profile
        profile, _ = UserSpendingProfile.objects.get_or_create(user=user)
        
        # Update spending
        from cards.models import SpendingCategory
        for category_slug, amount in spending_data.items():
            try:
                category = SpendingCategory.objects.get(slug=category_slug)
                SpendingAmount.objects.update_or_create(
                    profile=profile,
                    category=category,
                    defaults={'monthly_amount': amount}
                )
            except SpendingCategory.DoesNotExist:
                continue
        
        # Update cards
        from cards.models import CreditCard
        # Remove existing cards not in the new list
        UserCard.objects.filter(user=user).exclude(card_id__in=cards_data).delete()
        
        # Add new cards
        for card_id in cards_data:
            try:
                card = CreditCard.objects.get(id=card_id)
                UserCard.objects.get_or_create(
                    user=user, 
                    card=card,
                    defaults={'opened_date': '2023-01-01'}  # Default date
                )
            except CreditCard.DoesNotExist:
                continue
        
        # Update preferences
        if preferences_data:
            prefs, _ = UserPreferences.objects.get_or_create(user=user)
            for key, value in preferences_data.items():
                if hasattr(prefs, key):
                    setattr(prefs, key, value)
            prefs.save()
        
        return validated_data
    
    def to_representation(self, instance):
        user = self.context['request'].user
        profile, _ = UserSpendingProfile.objects.get_or_create(user=user)
        
        # Get spending data
        spending = {}
        for spending_obj in SpendingAmount.objects.filter(profile=profile).select_related('category'):
            spending[spending_obj.category.slug] = spending_obj.monthly_amount
        
        # Get cards data
        cards = list(UserCard.objects.filter(user=user, closed_date__isnull=True).values_list('card_id', flat=True))
        
        # Get preferences
        preferences = {}
        try:
            prefs = UserPreferences.objects.get(user=user)
            preferences = {
                'default_issuer_filter': prefs.default_issuer_filter,
                'default_reward_type_filter': prefs.default_reward_type_filter,
                'default_max_fee_filter': prefs.default_max_fee_filter,
                'default_max_recommendations': prefs.default_max_recommendations,
                'theme': prefs.theme,
                'email_notifications': prefs.email_notifications,
            }
        except UserPreferences.DoesNotExist:
            pass
        
        return {
            'spending': spending,
            'cards': cards,
            'preferences': preferences
        }