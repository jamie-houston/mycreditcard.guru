from rest_framework import serializers
from cards.serializers import CreditCardListSerializer, UserSpendingProfileSerializer
from .models import RoadmapFilter, Roadmap, RoadmapRecommendation, RoadmapCalculation


class RoadmapFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoadmapFilter
        fields = ['id', 'name', 'filter_type', 'value']


class RoadmapRecommendationSerializer(serializers.ModelSerializer):
    card = CreditCardListSerializer(read_only=True)
    
    class Meta:
        model = RoadmapRecommendation
        fields = [
            'id', 'card', 'action', 'priority', 'estimated_rewards',
            'reasoning', 'recommended_date', 'created_at'
        ]


class RoadmapCalculationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoadmapCalculation
        fields = ['total_estimated_rewards', 'calculation_data', 'calculated_at']


class RoadmapSerializer(serializers.ModelSerializer):
    filters = RoadmapFilterSerializer(many=True, read_only=True)
    recommendations = RoadmapRecommendationSerializer(many=True, read_only=True)
    calculation = RoadmapCalculationSerializer(read_only=True)
    profile = UserSpendingProfileSerializer(read_only=True)
    
    class Meta:
        model = Roadmap
        fields = [
            'id', 'name', 'description', 'filters', 'max_recommendations',
            'recommendations', 'calculation', 'profile', 'created_at', 'updated_at'
        ]


class CreateRoadmapSerializer(serializers.Serializer):
    """Serializer for creating roadmaps with filters"""
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    max_recommendations = serializers.IntegerField(default=1, min_value=1, max_value=20)
    filters = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    
    def create(self, validated_data):
        request = self.context['request']
        
        # Get or create user profile
        if request.user.is_authenticated:
            from cards.models import UserSpendingProfile
            profile, created = UserSpendingProfile.objects.get_or_create(user=request.user)
        else:
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
            from cards.models import UserSpendingProfile
            profile, created = UserSpendingProfile.objects.get_or_create(session_key=session_key)
        
        # Create or update roadmap
        filters_data = validated_data.pop('filters', [])
        roadmap, created = Roadmap.objects.get_or_create(
            profile=profile,
            name=validated_data.get('name', 'Default Roadmap'),
            defaults=validated_data
        )
        
        # If roadmap already exists, update its fields
        if not created:
            for key, value in validated_data.items():
                setattr(roadmap, key, value)
            roadmap.save()
        
        # Clear existing filters and create new ones
        roadmap.filters.clear()
        for filter_data in filters_data:
            filter_obj, created = RoadmapFilter.objects.get_or_create(
                name=filter_data['name'],
                filter_type=filter_data['filter_type'],
                value=filter_data['value']
            )
            roadmap.filters.add(filter_obj)
        
        return roadmap


class GenerateRoadmapSerializer(serializers.Serializer):
    """Serializer for generating roadmap recommendations"""
    spending_amounts = serializers.DictField(
        child=serializers.DecimalField(max_digits=10, decimal_places=2),
        required=False
    )
    user_cards = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    filters = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    max_recommendations = serializers.IntegerField(default=1, min_value=1, max_value=20)
    spending_credit_preferences = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    strategy = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_strategy(self, value):
        from .strategies import get_strategy, STRATEGIES
        if value and get_strategy(value) is None:
            raise serializers.ValidationError(
                f"Unknown strategy '{value}'. Choices: {', '.join(sorted(STRATEGIES))}"
            )
        return value

    def generate_recommendations(self):
        """Generate recommendations without persisting anything.

        The engine reads spending/cards/preferences from the database, so
        the request payload is written there for the computation — but the
        whole thing runs in a transaction that is ALWAYS rolled back.
        Before this, every quick run deleted and recreated the user's
        stored UserCards/spending/credit preferences from the form payload,
        which would destroy real users' saved profiles (see
        docs/PROJECT_STATUS.md backlog: "quick-recommendation serializer
        footgun"). Saving the profile is the /users/data/ endpoint's job.
        """
        from django.db import transaction

        with transaction.atomic():
            recommendations = self._generate_with_scratch_data()
            # Computation only — undo every write (spending amounts, user
            # cards, credit prefs, the temporary roadmap).
            transaction.set_rollback(True)
        return recommendations

    def _generate_with_scratch_data(self):
        """Write the payload into the profile tables and generate
        recommendations. Only ever called inside the rolled-back
        transaction above."""
        from .recommendation_engine import RecommendationEngine
        from cards.models import UserSpendingProfile, SpendingAmount, UserCard

        request = self.context['request']
        validated_data = self.validated_data
        
        # Create temporary profile
        if request.user and request.user.is_authenticated:
            profile, created = UserSpendingProfile.objects.get_or_create(user=request.user)
        else:
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key

            profile, created = UserSpendingProfile.objects.get_or_create(session_key=session_key)
        
        # Update spending amounts if provided
        if 'spending_amounts' in validated_data:
            from cards.models import SpendingCategory
            profile.spending_amounts.all().delete()
            # Get valid category IDs to prevent foreign key errors
            valid_category_ids = set(SpendingCategory.objects.values_list('id', flat=True))
            
            for category_id, amount in validated_data['spending_amounts'].items():
                category_id_int = int(category_id)
                # Only create spending amount if category exists
                if category_id_int in valid_category_ids and amount > 0:
                    SpendingAmount.objects.create(
                        profile=profile,
                        category_id=category_id_int,
                        monthly_amount=amount
                    )
        
        # Update user cards if provided
        if 'user_cards' in validated_data:
            from cards.models import CreditCard
            # Clear existing user cards for this user
            if profile.user:
                UserCard.objects.filter(user=profile.user).delete()
                # Get valid card IDs to prevent foreign key errors
                valid_card_ids = set(CreditCard.objects.values_list('id', flat=True))
                
                for card_data in validated_data['user_cards']:
                    card_id = card_data['card_id']
                    # Only create user card if card exists
                    if card_id in valid_card_ids:
                        UserCard.objects.create(
                            user=profile.user,
                            card_id=card_id,
                            nickname=card_data.get('nickname', ''),
                            opened_date=card_data['opened_date'],
                            # Note: is_active is now a property based on closed_date
                            # If the old data says is_active=False, set a closed_date
                            closed_date=None if card_data.get('is_active', True) else card_data['opened_date']
                        )
        
        # Update spending credit preferences if provided
        if 'spending_credit_preferences' in validated_data:
            from cards.models import SpendingCredit, UserSpendingCreditPreference
            # Clear existing spending credit preferences
            profile.spending_credit_preferences.all().delete()
            # Get valid spending credit slugs
            valid_spending_credit_slugs = set(SpendingCredit.objects.values_list('slug', flat=True))
            
            for credit_slug in validated_data['spending_credit_preferences']:
                if credit_slug in valid_spending_credit_slugs:
                    spending_credit = SpendingCredit.objects.get(slug=credit_slug)
                    UserSpendingCreditPreference.objects.create(
                        profile=profile,
                        spending_credit=spending_credit,
                        values_credit=True
                    )
        
        # Resolve strategy preset (validated above, so lookup can't fail)
        from .strategies import get_strategy, apply_strategy_to_roadmap
        strategy = get_strategy(validated_data.get('strategy'))

        # An explicit max_recommendations in the request beats the preset's
        # default; the serializer default (1) only applies with no strategy.
        if 'max_recommendations' in self.initial_data:
            max_recommendations = validated_data.get('max_recommendations', 1)
        elif strategy:
            max_recommendations = strategy['max_recommendations']
        else:
            max_recommendations = validated_data.get('max_recommendations', 1)

        # Create or get temporary roadmap for filtering
        roadmap, created = Roadmap.objects.get_or_create(
            profile=profile,
            name="Temporary Quick Recommendation",
            defaults={'max_recommendations': max_recommendations}
        )

        # Update max_recommendations if roadmap already exists
        if not created:
            roadmap.max_recommendations = max_recommendations
            roadmap.save()

        # Clear existing filters and add new ones if provided
        roadmap.filters.clear()
        if 'filters' in validated_data:
            for filter_data in validated_data['filters']:
                filter_obj, _ = RoadmapFilter.objects.get_or_create(
                    name=filter_data['name'],
                    filter_type=filter_data['filter_type'],
                    value=filter_data['value']
                )
                roadmap.filters.add(filter_obj)
        # Strategy filters add on top of explicit ones (narrowing the pool)
        apply_strategy_to_roadmap(roadmap, strategy)

        # Generate recommendations using quick method (includes breakdowns)
        # Pass user_cards data directly for session-based users
        user_cards_data = validated_data.get('user_cards', []) if not profile.user else None
        engine = RecommendationEngine(profile, user_cards_data=user_cards_data, strategy=strategy)
        recommendations = engine.generate_quick_recommendations(roadmap)
        
        # Clean up temporary roadmap
        roadmap.delete()
        
        return recommendations


class RecommendationItemCardSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='card.id')
    name = serializers.CharField(source='card.name')
    issuer = serializers.CharField(source='card.issuer.name')
    annual_fee = serializers.FloatField(source='card.annual_fee')
    effective_annual_fee = serializers.SerializerMethodField()
    annual_fee_waived_first_year = serializers.SerializerMethodField()
    signup_bonus_amount = serializers.IntegerField(source='card.signup_bonus_amount')
    signup_bonus_type = serializers.SerializerMethodField()
    signup_spending_requirement = serializers.SerializerMethodField()
    signup_time_limit_months = serializers.SerializerMethodField()
    apply_url = serializers.CharField(source='card.apply_url')
    redemption = serializers.SerializerMethodField()

    def get_effective_annual_fee(self, obj):
        card = obj['card']
        action = obj['action']
        if action == 'apply' and card.metadata.get('annual_fee_waived_first_year', False):
            return 0.0
        return float(card.annual_fee)

    def get_annual_fee_waived_first_year(self, obj):
        card = obj['card']
        return card.metadata.get('annual_fee_waived_first_year', False)

    def get_signup_bonus_type(self, obj):
        card = obj['card']
        return card.signup_bonus_type.name if card.signup_bonus_type else 'points'

    def get_signup_spending_requirement(self, obj):
        card = obj['card']
        return float((card.metadata.get('signup_bonus') or {}).get('spending_requirement') or 0)

    def get_signup_time_limit_months(self, obj):
        card = obj['card']
        return (card.metadata.get('signup_bonus') or {}).get('time_limit_months')

    def get_redemption(self, obj):
        from .redemption import redemption_guidance_for
        card = obj['card']
        request = self.context.get('request')
        user = request.user if request and hasattr(request, 'user') else None
        return redemption_guidance_for(card, user=user)



class RecommendationItemSerializer(serializers.Serializer):
    card = serializers.SerializerMethodField()
    action = serializers.CharField()
    estimated_rewards = serializers.FloatField()
    first_year_value = serializers.SerializerMethodField()
    ongoing_value = serializers.SerializerMethodField()
    reward_value_multiplier = serializers.SerializerMethodField()
    valuation_note = serializers.CharField(required=False, default='')
    reasoning = serializers.CharField()
    rewards_breakdown = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    total_spending_on_card = serializers.SerializerMethodField()
    signup_bonus_value = serializers.SerializerMethodField()
    eligibility_note = serializers.CharField(required=False, default='')
    bonus_deferred = serializers.BooleanField(required=False, default=False)
    recommended_month = serializers.IntegerField(required=False, allow_null=True)
    bonus_months_needed = serializers.FloatField(required=False, allow_null=True)
    priority = serializers.IntegerField()
    apply_as = serializers.DictField(required=False)

    def get_card(self, obj):
        return RecommendationItemCardSerializer(obj).data

    def get_first_year_value(self, obj):
        return float(obj.get('first_year_value', obj['estimated_rewards']))

    def get_ongoing_value(self, obj):
        return float(obj.get('ongoing_value', obj['estimated_rewards']))

    def get_reward_value_multiplier(self, obj):
        return float(obj.get('reward_value_multiplier', 0.01))

    def get_total_spending_on_card(self, obj):
        return float(obj.get('total_spending_on_card', 0))

    def get_signup_bonus_value(self, obj):
        return float(obj.get('signup_bonus_value', 0))

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if 'apply_as' not in instance:
            ret.pop('apply_as', None)
        return ret


class PortfolioSummarySerializer(serializers.Serializer):
    total_annual_fees = serializers.FloatField(required=False, default=0.0)
    total_portfolio_rewards = serializers.FloatField(required=False, default=0.0)
    net_portfolio_value = serializers.FloatField(required=False, default=0.0)
    category_optimization = serializers.DictField(required=False, default=dict)
    category_allocation = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    card_count = serializers.IntegerField(required=False, default=0)
    total_credits_value = serializers.FloatField(required=False, default=0.0)
    total_annual_spending = serializers.FloatField(required=False, default=0.0)
    bonus_capacity = serializers.DictField(required=False, default=dict)


class RoadmapRecommendationResponseSerializer(serializers.Serializer):
    recommendations = RecommendationItemSerializer(many=True)
    total_estimated_rewards = serializers.SerializerMethodField()
    portfolio_summary = serializers.SerializerMethodField()

    def get_total_estimated_rewards(self, obj):
        recommendations = obj.get('recommendations', [])
        return sum(float(rec['estimated_rewards']) for rec in recommendations)

    def get_portfolio_summary(self, obj):
        recommendations = obj.get('recommendations', [])
        portfolio_summary = recommendations[0].get('portfolio_summary', {}) if recommendations else {}
        return PortfolioSummarySerializer(portfolio_summary).data