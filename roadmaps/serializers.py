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
    
    def generate_recommendations(self):
        """Generate recommendations without saving to database"""
        from .recommendation_engine import RecommendationEngine
        from cards.models import UserSpendingProfile, SpendingAmount, UserCard
        
        request = self.context['request']
        validated_data = self.validated_data
        
        # Create temporary profile
        if request.user.is_authenticated:
            profile, created = UserSpendingProfile.objects.get_or_create(user=request.user)
        else:
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
            profile, created = UserSpendingProfile.objects.get_or_create(session_key=session_key)
        
        # Update spending amounts if provided
        if 'spending_amounts' in validated_data:
            profile.spending_amounts.all().delete()
            for category_id, amount in validated_data['spending_amounts'].items():
                SpendingAmount.objects.create(
                    profile=profile,
                    category_id=int(category_id),
                    monthly_amount=amount
                )
        
        # Update user cards if provided
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
        
        # Create temporary roadmap for filtering
        roadmap = Roadmap.objects.create(
            profile=profile,
            name="Temporary Quick Recommendation",
            max_recommendations=validated_data.get('max_recommendations', 5)
        )
        
        # Add filters if provided
        if 'filters' in validated_data:
            for filter_data in validated_data['filters']:
                filter_obj, created = RoadmapFilter.objects.get_or_create(
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