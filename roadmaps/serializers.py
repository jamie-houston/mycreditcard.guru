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
    max_recommendations = serializers.IntegerField(default=5, min_value=1, max_value=20)
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
        
        # Create roadmap
        filters_data = validated_data.pop('filters', [])
        roadmap = Roadmap.objects.create(
            profile=profile,
            **validated_data
        )
        
        # Create filters
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
    max_recommendations = serializers.IntegerField(default=5, min_value=1, max_value=20)
    credit_preferences = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    spending_credit_preferences = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    
    def generate_recommendations(self):
        """Generate recommendations without saving to database"""
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
            
            # Try to find existing profile first, then create if needed
            profile = UserSpendingProfile.objects.filter(session_key=session_key).first()
            if not profile:
                # If no profile found with current session, don't create empty one
                # Instead, find any existing profile with data and use it temporarily
                existing_profile = UserSpendingProfile.objects.filter(
                    user=None,
                    spending_amounts__isnull=False
                ).first()
                if existing_profile:
                    profile = existing_profile
                else:
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
            profile.user_cards.all().delete()
            # Get valid card IDs to prevent foreign key errors
            valid_card_ids = set(CreditCard.objects.values_list('id', flat=True))
            
            for card_data in validated_data['user_cards']:
                card_id = card_data['card_id']
                # Only create user card if card exists
                if card_id in valid_card_ids:
                    UserCard.objects.create(
                        profile=profile,
                        card_id=card_id,
                        nickname=card_data.get('nickname', ''),
                        opened_date=card_data['opened_date'],
                        is_active=card_data.get('is_active', True)
                    )
        
        # Update credit preferences if provided
        if 'credit_preferences' in validated_data:
            from cards.models import CreditType, UserCreditPreference
            # Clear existing preferences
            profile.credit_preferences.all().delete()
            # Get valid credit type slugs
            valid_credit_slugs = set(CreditType.objects.values_list('slug', flat=True))
            
            for credit_slug in validated_data['credit_preferences']:
                if credit_slug in valid_credit_slugs:
                    credit_type = CreditType.objects.get(slug=credit_slug)
                    UserCreditPreference.objects.create(
                        profile=profile,
                        credit_type=credit_type,
                        values_credit=True
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
        
        # Create temporary roadmap for filtering
        roadmap = Roadmap.objects.create(
            profile=profile,
            name="Temporary Quick Recommendation",
            max_recommendations=validated_data.get('max_recommendations', 5)
        )
        
        # Add filters if provided
        if 'filters' in validated_data:
            for filter_data in validated_data['filters']:
                filter_obj, _ = RoadmapFilter.objects.get_or_create(
                    name=filter_data['name'],
                    filter_type=filter_data['filter_type'],
                    value=filter_data['value']
                )
                roadmap.filters.add(filter_obj)
        
        # Generate recommendations using quick method (includes breakdowns)
        engine = RecommendationEngine(profile)
        recommendations = engine.generate_quick_recommendations(roadmap)
        
        # Clean up temporary roadmap
        roadmap.delete()
        
        return recommendations