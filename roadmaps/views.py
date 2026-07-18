from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from cards.models import UserSpendingProfile
from .models import (
    Roadmap, RoadmapCalculation, RoadmapFilter,
    CURRENT_ROADMAP_NAME, get_current_roadmap,
)
from .serializers import (
    RoadmapFilterSerializer, RoadmapSerializer,
    CreateRoadmapSerializer, GenerateRoadmapSerializer,
    RoadmapRecommendationResponseSerializer
)
from .recommendation_engine import RecommendationEngine
from .redemption import redemption_guidance_for


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
            Roadmap.objects.select_related('profile__user')
                           .prefetch_related('filters'),
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
            Roadmap.objects.select_related('profile')
                           .prefetch_related('filters'),
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


def _build_quick_rec_response(recommendations):
    """Build the quick-recommendation JSON payload using DRF serializer."""
    serializer = RoadmapRecommendationResponseSerializer({'recommendations': recommendations})
    return serializer.data



def _persist_current_roadmap(request, response_data):
    """Save the just-generated roadmap as the user's "Current Roadmap".

    Runs AFTER `generate_recommendations()`'s always-rolled-back transaction
    has committed nothing, against the user's REAL profile (not the
    serializer's scratch one) so it survives a reload. Anonymous users need
    the durable session created up front in the view (see
    `quick_recommendation_view`) — without it this silently attaches to
    nothing on the next request.
    """
    if request.user.is_authenticated:
        profile, _ = UserSpendingProfile.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            return
        profile, _ = UserSpendingProfile.objects.get_or_create(session_key=session_key)

    roadmap, _ = Roadmap.objects.update_or_create(
        profile=profile,
        name=CURRENT_ROADMAP_NAME,
        defaults={
            'max_recommendations': len(response_data['recommendations']) or 1,
        }
    )
    RoadmapCalculation.objects.update_or_create(
        roadmap=roadmap,
        defaults={
            'total_estimated_rewards': response_data['total_estimated_rewards'],
            'calculation_data': {
                'response': response_data,
                'request': request.data,
                # Reuse the SAME timestamp shown in the live response (set
                # on response_data by the caller) rather than computing a
                # fresh one here — Phase E's calendar-month rendering needs
                # what the user saw and what got persisted to agree exactly.
                'generated_at': response_data.get('generated_at') or timezone.now().isoformat(),
            }
        }
    )


@api_view(['POST'])
def quick_recommendation_view(request):
    """Get quick recommendations without saving a roadmap"""
    # Anonymous users need a durable session BEFORE the generation transaction
    # (which is always rolled back) — otherwise request.session.create() inside
    # that transaction gets rolled back too, and the anon user ends up with no
    # session, so nothing (credit prefs, and now Current Roadmap) can persist.
    if not request.user.is_authenticated and not request.session.session_key:
        request.session.create()

    serializer = GenerateRoadmapSerializer(
        data=request.data,
        context={'request': request}
    )

    if serializer.is_valid():
        try:
            recommendations = serializer.generate_recommendations()
            response_data = _build_quick_rec_response(recommendations)
            # The live POST response didn't carry generated_at before Phase
            # E — only the GET current/shared endpoints did. Sequencing's
            # calendar-month display ("Apply in ~4 months (Nov 2026)") needs
            # a base date on every path, so set it here once and persist
            # the SAME value (see _persist_current_roadmap).
            response_data['generated_at'] = timezone.now().isoformat()

            _persist_current_roadmap(request, response_data)

            return Response(response_data)

        except Exception as e:
            return Response(
                {'error': f'Failed to generate recommendations: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def current_roadmap_view(request):
    """Return the user's most recently generated ("Current Roadmap"), if any.

    Never auto-creates a session/profile — GET is read-only; a 404 means the
    frontend shows its empty state instead of a roadmap.
    """
    roadmap = get_current_roadmap(request)

    if not roadmap:
        return Response({'message': 'No current roadmap found'}, status=status.HTTP_404_NOT_FOUND)

    calculation_data = roadmap.calculation.calculation_data
    return Response({
        **calculation_data.get('response', {}),
        'generated_at': calculation_data.get('generated_at'),
    })


def _roadmap_share_response(roadmap):
    data = {
        'privacy_setting': roadmap.privacy_setting,
        'is_public': roadmap.is_public,
    }
    if roadmap.is_public and roadmap.share_uuid:
        data['share_uuid'] = str(roadmap.share_uuid)
        data['shareable_url'] = roadmap.shareable_url
    return data


@api_view(['GET', 'POST'])
def current_roadmap_share_view(request):
    """Get or update the sharing settings for the visitor's Current Roadmap.

    Mirrors cards.views.get_profile_privacy/update_profile_privacy, but
    anon-capable (session-owned Current Roadmaps are a first-class case here,
    unlike profile sharing which requires auth) — resolved via
    `get_current_roadmap`, the same helper the persistence/read paths use.
    """
    roadmap = get_current_roadmap(request)

    if request.method == 'GET':
        if not roadmap:
            return Response({'privacy_setting': 'private', 'is_public': False})
        return Response(_roadmap_share_response(roadmap))

    # POST
    if not roadmap:
        return Response(
            {'error': 'No current roadmap to share — generate one first'},
            status=status.HTTP_404_NOT_FOUND
        )

    privacy_setting = request.data.get('privacy_setting')
    if privacy_setting not in ('private', 'public'):
        return Response(
            {'error': 'privacy_setting must be "private" or "public"'},
            status=status.HTTP_400_BAD_REQUEST
        )

    roadmap.privacy_setting = privacy_setting
    if privacy_setting == 'public':
        roadmap.generate_share_uuid()
    roadmap.save()

    return Response(_roadmap_share_response(roadmap))


@api_view(['GET'])
def shared_roadmap_data_view(request, share_uuid):
    """Return the stored recommendation payload for a public shared roadmap.

    Public, no auth. Built straight from `calculation_data` — never reuse a
    profile serializer here (see PLAN doc: the profile one has a broken
    `user_cards` field, and this data already IS the exact response the owner
    saw, so there's nothing to re-derive).
    """
    roadmap = get_object_or_404(
        Roadmap.objects.select_related('calculation', 'profile__user'),
        share_uuid=share_uuid,
        privacy_setting='public',
    )
    calculation_data = roadmap.calculation.calculation_data
    owner = roadmap.profile.user
    return Response({
        **calculation_data.get('response', {}),
        'generated_at': calculation_data.get('generated_at'),
        'owner_display_name': owner.username if owner else 'A Credit Card Guru user',
    })


def shared_roadmap_view(request, share_uuid):
    """Public, read-only page for a shared roadmap (mirrors
    cards.views.shared_profile_view). The page itself just loads the shell;
    `shared_roadmap.html` fetches the actual data from
    `shared_roadmap_data_view` and renders it with `roadmap-results.js`.
    """
    roadmap = get_object_or_404(
        Roadmap.objects.select_related('profile__user'),
        share_uuid=share_uuid,
        privacy_setting='public',
    )
    owner = roadmap.profile.user
    context = {
        'share_uuid': share_uuid,
        'owner_display_name': owner.username if owner else 'A Credit Card Guru user',
    }
    return render(request, 'shared_roadmap.html', context)


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