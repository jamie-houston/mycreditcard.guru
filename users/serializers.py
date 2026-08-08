from rest_framework import serializers
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from .models import UserProfile, UserPreferences
from cards.models import UserCard, UserSpendingProfile, SpendingAmount
from cards.serializers import CreditCardListSerializer, SpendingCategorySerializer


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
        primary = profile.primary_entity()
        
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
        # This flat list is the browse page's view of the PRIMARY's OPEN
        # cards, and it is applied in both directions: cards absent from it
        # are closed, cards present in it are opened. Only rows owned by the
        # primary entity (or legacy NULL-owner rows, which read as the
        # primary) are touched either way, so other household members' cards
        # (Phase K) survive untouched.
        primary_rows = UserCard.objects.filter(user=user).filter(
            Q(owner__isnull=True) | Q(owner=primary)
        )

        # Close cards not in the new list. Never delete: eligibility rules
        # (5/24, Amex lifetime, etc.) read full history including closed
        # cards, so destroying a row silently hands back approval
        # eligibility the user should not have.
        primary_rows.filter(closed_date__isnull=True).exclude(
            card_id__in=cards_data
        ).update(closed_date=timezone.now().date())

        # Add cards in the list, reopening the primary's own soft-closed row
        # rather than spawning a second one.
        for card_id in cards_data:
            try:
                card = CreditCard.objects.get(id=card_id)
            except CreditCard.DoesNotExist:
                continue
            household_rows = UserCard.objects.filter(user=user, card=card)
            # Already open for SOMEONE in the household: the id's presence in
            # the list is fully explained, so there is nothing to do. This is
            # the guard that keeps the reopen honest — to_representation()
            # builds the list household-wide and unscoped by owner, so Sam
            # holding a card open is enough to put its id here, and that must
            # not resurrect a row the primary deliberately closed.
            if household_rows.filter(closed_date__isnull=True).exists():
                continue
            own_closed = household_rows.filter(
                Q(owner__isnull=True) | Q(owner=primary),
                closed_date__isnull=False)
            if own_closed.exists():
                own_closed.update(closed_date=None)
                continue
            # Only another entity's closed row: not ours to reopen, and
            # spawning a parallel primary-owned row would double-count the
            # card in eligibility math.
            if household_rows.exists():
                continue
            UserCard.objects.create(
                user=user, card=card, owner=primary,
                opened_date='2023-01-01'  # Default date
            )
        
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