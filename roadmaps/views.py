from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

from cards.models import UserSpendingProfile
from .models import Roadmap, RoadmapFilter
from .serializers import (
    RoadmapFilterSerializer, RoadmapSerializer, 
    CreateRoadmapSerializer, GenerateRoadmapSerializer
)
from .recommendation_engine import RecommendationEngine


class RoadmapFilterListView(generics.ListCreateAPIView):
    queryset = RoadmapFilter.objects.all().order_by('filter_type', 'name')
    serializer_class = RoadmapFilterSerializer


class RoadmapListView(generics.ListAPIView):
    serializer_class = RoadmapSerializer
    
    def get_queryset(self):
        # Get roadmaps for current user/session
        if self.request.user.is_authenticated:
            return Roadmap.objects.filter(
                profile__user=self.request.user
            ).prefetch_related(
                'filters', 'recommendations__card', 'calculation'
            ).order_by('-updated_at')
        else:
            session_key = self.request.session.session_key
            if session_key:
                return Roadmap.objects.filter(
                    profile__session_key=session_key
                ).prefetch_related(
                    'filters', 'recommendations__card', 'calculation'
                ).order_by('-updated_at')
        return Roadmap.objects.none()


class RoadmapDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RoadmapSerializer
    
    def get_queryset(self):
        # Get roadmaps for current user/session
        if self.request.user.is_authenticated:
            return Roadmap.objects.filter(
                profile__user=self.request.user
            ).prefetch_related(
                'filters', 'recommendations__card', 'calculation'
            )
        else:
            session_key = self.request.session.session_key
            if session_key:
                return Roadmap.objects.filter(
                    profile__session_key=session_key
                ).prefetch_related(
                    'filters', 'recommendations__card', 'calculation'
                )
        return Roadmap.objects.none()


@api_view(['POST'])
def create_roadmap_view(request):
    """Create a new roadmap with filters"""
    serializer = CreateRoadmapSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        roadmap = serializer.save()
        response_serializer = RoadmapSerializer(roadmap)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def generate_roadmap_view(request, roadmap_id):
    """Generate recommendations for an existing roadmap"""
    
    # Get roadmap for current user/session
    if request.user.is_authenticated:
        roadmap = get_object_or_404(
            Roadmap.objects.prefetch_related('filters'),
            id=roadmap_id,
            profile__user=request.user
        )
    else:
        session_key = request.session.session_key
        if not session_key:
            return Response(
                {'error': 'No session found'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        roadmap = get_object_or_404(
            Roadmap.objects.prefetch_related('filters'),
            id=roadmap_id,
            profile__session_key=session_key
        )
    
    try:
        # Generate recommendations using the engine
        engine = RecommendationEngine(roadmap.profile)
        recommendations = engine.generate_roadmap(roadmap)
        
        # Return updated roadmap
        roadmap.refresh_from_db()
        serializer = RoadmapSerializer(roadmap)
        return Response(serializer.data)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to generate roadmap: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def quick_recommendation_view(request):
    """Get quick recommendations without saving a roadmap"""
    serializer = GenerateRoadmapSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        try:
            recommendations = serializer.generate_recommendations()
            
            # Get portfolio summary from the first recommendation (they all have the same summary)
            portfolio_summary = recommendations[0].get('portfolio_summary', {}) if recommendations else {}
            
            return Response({
                'recommendations': [
                    {
                        'card': {
                            'id': rec['card'].id,
                            'name': rec['card'].name,
                            'issuer': rec['card'].issuer.name,
                            'annual_fee': float(rec['card'].annual_fee),
                            'effective_annual_fee': 0 if (rec['action'] == 'apply' and rec['card'].metadata.get('annual_fee_waived_first_year', False)) else float(rec['card'].annual_fee),
                            'annual_fee_waived_first_year': rec['card'].metadata.get('annual_fee_waived_first_year', False),
                            'signup_bonus_amount': rec['card'].signup_bonus_amount,
                        },
                        'action': rec['action'],
                        'estimated_rewards': float(rec['estimated_rewards']),
                        'reasoning': rec['reasoning'],
                        'rewards_breakdown': rec.get('rewards_breakdown', []),
                        'priority': rec['priority']
                    }
                    for rec in recommendations
                ],
                'total_estimated_rewards': sum(
                    float(rec['estimated_rewards']) for rec in recommendations
                ),
                'portfolio_summary': {
                    'total_annual_fees': portfolio_summary.get('total_annual_fees', 0),
                    'total_portfolio_rewards': portfolio_summary.get('total_portfolio_rewards', 0),
                    'net_portfolio_value': portfolio_summary.get('net_portfolio_value', 0),
                    'category_optimization': portfolio_summary.get('category_optimization', {}),
                    'card_count': portfolio_summary.get('card_count', 0),
                    'total_credits_value': portfolio_summary.get('total_credits_value', 0),
                    'total_annual_spending': portfolio_summary.get('total_annual_spending', 0)
                }
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to generate recommendations: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def roadmap_stats_view(request):
    """Get roadmap statistics for the user"""
    
    if request.user.is_authenticated:
        queryset = Roadmap.objects.filter(profile__user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            return Response({'message': 'No session found'}, status=status.HTTP_404_NOT_FOUND)
        queryset = Roadmap.objects.filter(profile__session_key=session_key)
    
    from django.db.models import Count, Sum, Avg
    
    stats = queryset.aggregate(
        total_roadmaps=Count('id'),
        total_recommendations=Count('recommendations'),
        avg_recommendations_per_roadmap=Avg('recommendations__id'),
        total_estimated_rewards=Sum('calculation__total_estimated_rewards')
    )
    
    return Response({
        'roadmap_count': stats['total_roadmaps'] or 0,
        'total_recommendations': stats['total_recommendations'] or 0,
        'avg_recommendations_per_roadmap': round(stats['avg_recommendations_per_roadmap'] or 0, 1),
        'total_estimated_rewards': float(stats['total_estimated_rewards'] or 0),
        'recent_roadmaps': RoadmapSerializer(
            queryset.order_by('-updated_at')[:3], 
            many=True
        ).data
    })


@api_view(['POST'])
def export_scenario_view(request):
    """Export current user input as a test scenario JSON"""
    
    # Only allow for the specific dev user
    if not request.user.is_authenticated or request.user.email != 'foresterh@gmail.com':
        return Response(
            {'error': 'Unauthorized access'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        scenario_data = request.data
        
        # Add metadata
        scenario_data['exported_by'] = request.user.email
        scenario_data['exported_at'] = timezone.now().isoformat()
        scenario_data['export_type'] = 'debug_scenario'
        
        # Return the formatted scenario
        return Response({
            'success': True,
            'scenario': scenario_data,
            'message': 'Scenario exported successfully'
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )