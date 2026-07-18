from rest_framework import generics, filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, ProtectedError, RestrictedError
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
from django.utils import timezone

from .models import (
    Issuer, RewardType, SpendingCategory, CreditCard,
    UserSpendingProfile, SpendingCredit, UserCard,
    UserSpendingCreditPreference, ProfileEntity
)
from .serializers import (
    IssuerSerializer, RewardTypeSerializer, SpendingCategorySerializer,
    CreditCardSerializer, CreditCardListSerializer, UserSpendingProfileSerializer,
    CreateSpendingProfileSerializer, SpendingCreditSerializer, UserCardSerializer,
    UserCardCreateUpdateSerializer, ProfileEntitySerializer
)


class IssuerListView(generics.ListAPIView):
    queryset = Issuer.objects.all().order_by('name')
    serializer_class = IssuerSerializer
    pagination_class = None  # Disable pagination for reference data


class RewardTypeListView(generics.ListAPIView):
    queryset = RewardType.objects.all().order_by('name')
    serializer_class = RewardTypeSerializer
    pagination_class = None  # Disable pagination for reference data


class SpendingCategoryListView(generics.ListAPIView):
    queryset = SpendingCategory.objects.all().order_by('sort_order', 'name')
    serializer_class = SpendingCategorySerializer
    pagination_class = None  # Disable pagination for reference data


class SpendingCreditListView(generics.ListAPIView):
    queryset = SpendingCredit.objects.all().select_related('category').order_by('category__sort_order', 'sort_order', 'display_name')
    serializer_class = SpendingCreditSerializer
    pagination_class = None  # Disable pagination for reference data


class CreditCardListView(generics.ListAPIView):
    queryset = CreditCard.objects.filter(is_active=True).select_related(
        'issuer', 'primary_reward_type', 'signup_bonus_type'
    ).prefetch_related(
        'reward_categories__category',
        'reward_categories__reward_type',
        'credits'
    )
    serializer_class = CreditCardSerializer
    pagination_class = None  # Disable pagination for this view
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'issuer__name': ['exact', 'icontains'],
        'primary_reward_type__name': ['exact', 'icontains'],
        'card_type': ['exact'],
        'annual_fee': ['exact', 'lte', 'gte'],
        'signup_bonus_amount': ['gte', 'lte'],
    }
    search_fields = ['name', 'issuer__name']
    ordering_fields = ['name', 'annual_fee', 'signup_bonus_amount']
    ordering = ['issuer__name', 'name']


class CreditCardDetailView(generics.RetrieveAPIView):
    queryset = CreditCard.objects.filter(is_active=True).select_related(
        'issuer', 'primary_reward_type', 'signup_bonus_type'
    ).prefetch_related(
        'reward_categories__category',
        'reward_categories__reward_type',
        'credits'
    )
    serializer_class = CreditCardSerializer


@api_view(['GET', 'POST'])
def spending_profile_view(request):
    """Get or create/update user spending profile"""
    
    if request.method == 'GET':
        # Get existing profile
        if request.user.is_authenticated:
            try:
                profile = UserSpendingProfile.objects.get(user=request.user)
            except UserSpendingProfile.DoesNotExist:
                return Response({'message': 'No profile found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            session_key = request.session.session_key
            if not session_key:
                return Response({'message': 'No profile found'}, status=status.HTTP_404_NOT_FOUND)
            try:
                profile = UserSpendingProfile.objects.get(session_key=session_key)
            except UserSpendingProfile.DoesNotExist:
                return Response({'message': 'No profile found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = UserSpendingProfileSerializer(profile)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Create or update profile
        serializer = CreateSpendingProfileSerializer(
            data=request.data, 
            context={'request': request}
        )
        if serializer.is_valid():
            profile = serializer.save()
            response_serializer = UserSpendingProfileSerializer(profile)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def _serialize_credit_preferences(profile):
    return {
        pref.spending_credit.slug: pref.values_credit
        for pref in profile.spending_credit_preferences.select_related('spending_credit')
    }


@api_view(['GET', 'PUT'])
def credit_preferences_view(request):
    """Get or set which spending credits the user values (auth + anon via session).

    Absent slugs are untouched/unchecked; only rows that exist are returned.
    """
    if request.method == 'GET':
        if request.user.is_authenticated:
            profile = UserSpendingProfile.objects.filter(user=request.user).first()
        else:
            session_key = request.session.session_key
            profile = (
                UserSpendingProfile.objects.filter(session_key=session_key).first()
                if session_key else None
            )

        if not profile:
            return Response({'preferences': {}})

        return Response({'preferences': _serialize_credit_preferences(profile)})

    # PUT
    preferences = request.data.get('preferences')
    if not isinstance(preferences, dict):
        return Response(
            {'error': 'preferences must be an object of {credit_slug: bool}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if request.user.is_authenticated:
        profile, _created = UserSpendingProfile.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        profile, _created = UserSpendingProfile.objects.get_or_create(
            session_key=request.session.session_key
        )

    valid_credits = {c.slug: c for c in SpendingCredit.objects.all()}
    for slug, values_credit in preferences.items():
        credit = valid_credits.get(slug)
        if not credit:
            continue
        UserSpendingCreditPreference.objects.update_or_create(
            profile=profile,
            spending_credit=credit,
            defaults={'values_credit': bool(values_credit)}
        )

    return Response({'preferences': _serialize_credit_preferences(profile)})


@api_view(['GET'])
def card_search_view(request):
    """Advanced card search with multiple filters"""
    queryset = CreditCard.objects.filter(is_active=True).select_related(
        'issuer', 'primary_reward_type', 'signup_bonus_type'
    )
    
    # Filter by issuer
    issuer = request.GET.get('issuer')
    if issuer:
        queryset = queryset.filter(issuer__name__icontains=issuer)
    
    # Filter by reward type
    reward_type = request.GET.get('reward_type')
    if reward_type:
        queryset = queryset.filter(primary_reward_type__name__icontains=reward_type)
    
    # Filter by card type
    card_type = request.GET.get('card_type')
    if card_type:
        queryset = queryset.filter(card_type=card_type)
    
    # Filter by annual fee range
    min_fee = request.GET.get('min_fee')
    max_fee = request.GET.get('max_fee')
    if min_fee:
        queryset = queryset.filter(annual_fee__gte=min_fee)
    if max_fee:
        queryset = queryset.filter(annual_fee__lte=max_fee)
    
    # Filter by signup bonus
    min_bonus = request.GET.get('min_bonus')
    if min_bonus:
        queryset = queryset.filter(signup_bonus_amount__gte=min_bonus)
    
    # Filter by reward category
    category = request.GET.get('category')
    if category:
        queryset = queryset.filter(
            reward_categories__category__slug__icontains=category,
            reward_categories__is_active=True
        ).distinct()
    
    # Search by name
    search = request.GET.get('search')
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) | Q(issuer__name__icontains=search)
        )
    
    # Ordering
    order_by = request.GET.get('order_by', 'issuer__name')
    if order_by in ['name', 'annual_fee', 'signup_bonus_amount', 'issuer__name']:
        if request.GET.get('order') == 'desc':
            order_by = f'-{order_by}'
        queryset = queryset.order_by(order_by)
    
    # Pagination
    from rest_framework.pagination import PageNumberPagination
    paginator = PageNumberPagination()
    paginator.page_size = 20
    
    page = paginator.paginate_queryset(queryset, request)
    if page is not None:
        serializer = CreditCardListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    serializer = CreditCardListSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def category_detail_view(request, category_slug):
    """Get detailed information about a spending category including top reward rates and cards"""
    try:
        from cards.models import SpendingCategory, RewardCategory
        from django.db.models import Max
        
        # Get the category
        category = get_object_or_404(SpendingCategory, slug=category_slug)
        
        # Get all reward categories for this spending category with reward rate > 1%
        reward_categories = RewardCategory.objects.filter(
            category=category,
            is_active=True,
            reward_rate__gt=1.0
        ).select_related('card', 'card__issuer').order_by('-reward_rate')
        
        # Get top reward rate for this category
        top_rate = reward_categories.aggregate(max_rate=Max('reward_rate'))['max_rate'] or 0
        
        # Build response
        category_data = {
            'id': category.id,
            'name': category.name,
            'display_name': category.display_name,
            'description': category.description,
            'icon': category.icon,
            'slug': category.slug,
            'sort_order': category.sort_order,
            'top_reward_rate': float(top_rate),
            'cards_with_rewards': [
                {
                    'id': rc.card.id,
                    'name': rc.card.name,
                    'issuer': rc.card.issuer.name,
                    'reward_rate': float(rc.reward_rate),
                    'annual_fee': float(rc.card.annual_fee),
                    'max_annual_spend': float(rc.max_annual_spend) if rc.max_annual_spend else None,
                    'signup_bonus_amount': rc.card.signup_bonus_amount
                }
                for rc in reward_categories
            ]
        }
        
        return Response(category_data)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to get category details: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def categories_with_rewards_view(request):
    """Get all categories with their top reward rates"""
    try:
        from cards.models import SpendingCategory, RewardCategory
        from django.db.models import Max
        
        # Get all categories with their top reward rates
        categories = SpendingCategory.objects.all().order_by('sort_order', 'name')
        
        categories_data = []
        for category in categories:
            # Get top reward rate for this category
            top_rate = RewardCategory.objects.filter(
                category=category,
                is_active=True
            ).aggregate(max_rate=Max('reward_rate'))['max_rate'] or 0
            
            # Count cards with rewards > 1% for this category
            cards_count = RewardCategory.objects.filter(
                category=category,
                is_active=True,
                reward_rate__gt=1.0
            ).count()
            
            categories_data.append({
                'id': category.id,
                'name': category.name,
                'display_name': category.display_name or category.name,
                'description': category.description,
                'icon': category.icon,
                'slug': category.slug,
                'sort_order': category.sort_order,
                'top_reward_rate': float(top_rate),
                'cards_with_rewards_count': cards_count
            })
        
        return Response(categories_data)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to get categories: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def card_recommendations_preview(request):
    """Preview card recommendations without saving"""
    from roadmaps.serializers import GenerateRoadmapSerializer
    
    serializer = GenerateRoadmapSerializer(
        data=request.data if request.method == 'POST' else request.GET.dict(),
        context={'request': request}
    )
    
    if serializer.is_valid():
        try:
            recommendations = serializer.generate_recommendations()
            return Response({
                'recommendations': [
                    {
                        'card_id': rec['card'].id,
                        'card_slug': rec['card'].slug,
                        'card_name': str(rec['card']),
                        'action': rec['action'],
                        'estimated_rewards': float(rec['estimated_rewards']),
                        'reasoning': rec['reasoning'],
                        'priority': rec['priority']
                    }
                    for rec in recommendations
                ]
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to generate recommendations: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Template Views
def landing_view(request):
    """Landing page - welcome and feature overview.

    Skips straight to /roadmap/ for visitors (auth or anon-via-session) who
    already have a persisted Current Roadmap — Home is meant as an entry
    point into the roadmap, not a page returning users need to pass through.
    Read-only check: never creates a session for a fresh anonymous visitor.
    """
    from roadmaps.models import get_current_roadmap
    if get_current_roadmap(request):
        return redirect('roadmap')
    return render(request, 'landing.html')

def index_view(request):
    """Roadmap creation page"""
    from roadmaps.strategies import ui_presets
    from roadmaps.models import get_current_roadmap
    context = {
        'user_email': request.user.email if request.user.is_authenticated else None,
        'is_dev_user': request.user.is_authenticated and request.user.email == 'foresterh@gmail.com',
        'strategies': ui_presets(),
        'has_current_roadmap': get_current_roadmap(request) is not None,
    }
    return render(request, 'index.html', context)

def cards_list_view(request):
    """Credit cards listing page"""
    return render(request, 'cards_list.html')

def categories_list_view(request):
    """Spending categories listing page"""
    return render(request, 'categories_list.html')

def category_detail_page_view(request, category_slug):
    """Category detail page"""
    return render(request, 'category_detail.html', {'category_slug': category_slug})

def issuers_list_view(request):
    """Issuers listing page"""
    return render(request, 'issuers_list.html')

def profile_view(request):
    """User profile page showing card collection and category optimization"""
    return render(request, 'profile.html')


@api_view(['POST'])
def update_profile_privacy(request):
    """Update the privacy setting for a user's profile"""
    try:
        # Get or create user profile
        if request.user.is_authenticated:
            profile, created = UserSpendingProfile.objects.get_or_create(
                user=request.user,
                defaults={'privacy_setting': 'private'}
            )
        else:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        privacy_setting = request.data.get('privacy_setting')
        if privacy_setting not in ['private', 'public']:
            return Response(
                {'error': 'privacy_setting must be "private" or "public"'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        profile.privacy_setting = privacy_setting
        
        # Generate share UUID if making public
        if privacy_setting == 'public':
            profile.generate_share_uuid()
        
        profile.save()
        
        # Build response data
        response_data = {
            'privacy_setting': profile.privacy_setting,
            'is_public': profile.is_public,
        }
        
        # Include shareable URL if public
        if profile.is_public and profile.share_uuid:
            response_data['share_uuid'] = str(profile.share_uuid)
            response_data['shareable_url'] = f'/profile/shared/{profile.share_uuid}/'
        
        return Response(response_data)
        
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_profile_privacy(request):
    """Get the current privacy setting for a user's profile"""
    try:
        if request.user.is_authenticated:
            profile = UserSpendingProfile.objects.filter(user=request.user).first()
            if profile:
                response_data = {
                    'privacy_setting': profile.privacy_setting,
                    'is_public': profile.is_public,
                }
                
                # Include shareable URL if public
                if profile.is_public and profile.share_uuid:
                    response_data['share_uuid'] = str(profile.share_uuid)
                    response_data['shareable_url'] = f'/profile/shared/{profile.share_uuid}/'
                
                return Response(response_data)
            else:
                return Response({
                    'privacy_setting': 'private',
                    'is_public': False,
                })
        else:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def shared_profile_view(request, share_uuid):
    """Display a read-only public profile"""
    try:
        profile = get_object_or_404(
            UserSpendingProfile, 
            share_uuid=share_uuid,
            privacy_setting='public'
        )
        
        # Pass the profile to the template with a flag indicating it's a shared view
        context = {
            'profile': profile,
            'is_shared_view': True,
            'profile_owner': profile.user.username if profile.user else 'Anonymous User'
        }
        
        return render(request, 'shared_profile.html', context)
        
    except (ValueError, UserSpendingProfile.DoesNotExist):
        raise Http404("Profile not found or not public")


@api_view(['GET'])
def shared_profile_data_view(request, share_uuid):
    """Get profile data for a shared public profile"""
    try:
        profile = get_object_or_404(
            UserSpendingProfile, 
            share_uuid=share_uuid,
            privacy_setting='public'
        )
        
        # Get the profile data using the existing serializer
        from .serializers import UserSpendingProfileSerializer
        profile_data = UserSpendingProfileSerializer(profile).data
        
        # Add profile owner information
        profile_data['profile_owner'] = profile.user.username if profile.user else 'Anonymous User'
        
        # Add portfolio summary information (without revealing specific cards)
        if profile.user:
            user_cards = profile.user.owned_cards.filter(closed_date__isnull=True)
            total_cards = user_cards.count()
            total_annual_fees = sum(float(card.card.annual_fee or 0) for card in user_cards)
            
            profile_data['portfolio_summary'] = {
                'total_cards': total_cards,
                'total_annual_fees': total_annual_fees,
                'has_cards': total_cards > 0
            }
        else:
            profile_data['portfolio_summary'] = {
                'total_cards': 0,
                'total_annual_fees': 0,
                'has_cards': False
            }
        
        # Generate card-to-category recommendations based on actual owned cards
        card_recommendations = []
        
        if profile.user:
            user_cards = profile.user.owned_cards.filter(closed_date__isnull=True)
            spending_amounts = profile.spending_amounts.all().order_by('-monthly_amount')
            
            # Create a mapping of categories to best cards
            for spending in spending_amounts:
                if float(spending.monthly_amount) < 50:  # Skip very small spending categories
                    continue
                    
                category_name = spending.category.display_name
                category_slug = spending.category.slug
                monthly_amount = float(spending.monthly_amount)
                
                # Determine best card for this category based on Jamie's actual cards
                best_card = None
                reward_rate = "1x"
                
                # Check each card for this category
                for user_card in user_cards:
                    card = user_card.card
                    
                    # Check if this card has rewards for this category
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
                
                # If no specific category match, assign based on card specialties
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
        
        profile_data['card_recommendations'] = card_recommendations
        
        return Response(profile_data)
        
    except (ValueError, UserSpendingProfile.DoesNotExist):
        return Response(
            {'error': 'Profile not found or not public'}, 
            status=status.HTTP_404_NOT_FOUND
        )


def _resolve_owner_entity(profile, owner_id):
    """Resolve an 'owner' request param to a ProfileEntity, or the profile's
    primary entity if none was given. Returns (entity, error_response) —
    error_response is None on success. Phase K owner-CRUD helper."""
    if owner_id in (None, ''):
        return profile.primary_entity(), None
    entity = ProfileEntity.objects.filter(id=owner_id, profile=profile).first()
    if entity is None:
        return None, Response(
            {'error': 'owner must be one of your own household entities'},
            status=status.HTTP_400_BAD_REQUEST)
    return entity, None


def _get_or_create_owned_card(user, card, owner_entity, defaults):
    """get_or_create for (user, card, owner_entity) that also matches a
    legacy NULL-owner row when owner_entity is the primary — NULL and the
    primary entity are the same row conceptually (UserCard.owner=NULL means
    "the primary entity"), but the DB unique constraint treats them as
    distinct values, so a plain get_or_create(owner=owner_entity) would
    create a duplicate instead of reopening a pre-Phase-K row."""
    lookup = Q(user=user, card=card, owner=owner_entity)
    if owner_entity.is_primary:
        lookup |= Q(user=user, card=card, owner__isnull=True)
    existing = UserCard.objects.filter(lookup).first()
    if existing:
        return existing, False
    return UserCard.objects.create(user=user, card=card, owner=owner_entity, **defaults), True


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def profile_entities_view(request):
    """List or create the household's ProfileEntities (Phase K).

    GET lazily creates the primary entity if it doesn't exist yet — this is
    the entry point that brings a household's first entity into being.
    POST creates an additional (never-primary) entity: {"name", "kind"}.
    """
    profile, _ = UserSpendingProfile.objects.get_or_create(user=request.user)

    if request.method == 'GET':
        profile.primary_entity()
        entities = profile.entities.all()
        return Response(ProfileEntitySerializer(entities, many=True).data)

    profile.primary_entity()

    name = (request.data.get('name') or '').strip()
    if not name:
        return Response({'error': 'name is required'}, status=status.HTTP_400_BAD_REQUEST)
    kind = request.data.get('kind', 'personal')
    if kind not in dict(ProfileEntity.KIND_CHOICES):
        return Response({'error': 'invalid kind'}, status=status.HTTP_400_BAD_REQUEST)

    if profile.entities.filter(name=name).exists():
        return Response({'error': 'an entity with this name already exists'},
                         status=status.HTTP_400_BAD_REQUEST)

    entity = ProfileEntity.objects.create(profile=profile, name=name, kind=kind)
    return Response(ProfileEntitySerializer(entity).data, status=status.HTTP_201_CREATED)


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def profile_entity_detail_view(request, entity_id):
    """Rename or remove a single ProfileEntity (Phase K)."""
    profile, _ = UserSpendingProfile.objects.get_or_create(user=request.user)
    entity = get_object_or_404(ProfileEntity, id=entity_id, profile=profile)

    if request.method == 'PATCH':
        name = request.data.get('name')
        if name is not None:
            name = name.strip()
            if not name:
                return Response({'error': 'name cannot be blank'}, status=status.HTTP_400_BAD_REQUEST)
            if profile.entities.filter(name=name).exclude(pk=entity.pk).exists():
                return Response({'error': 'an entity with this name already exists'},
                                 status=status.HTTP_400_BAD_REQUEST)
            entity.name = name
            entity.save(update_fields=['name'])
        return Response(ProfileEntitySerializer(entity).data)

    # DELETE
    if entity.is_primary:
        return Response({'error': 'the primary entity cannot be removed'},
                         status=status.HTTP_400_BAD_REQUEST)
    try:
        entity.delete()
    except (ProtectedError, RestrictedError):
        card_count = entity.cards.count()
        return Response(
            {'error': f'reassign or remove this player\'s {card_count} card(s) first'},
            status=status.HTTP_400_BAD_REQUEST
        )
    return Response({'message': 'entity removed'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_cards(request):
    """Get all cards owned by the current user"""
    try:
        user_cards = UserCard.objects.filter(user=request.user).order_by('-opened_date', '-created_at')
        serializer = UserCardSerializer(user_cards, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_user_card(request):
    """Add or update a card in user's collection"""
    try:
        card_id = request.data.get('card_id')
        if not card_id:
            return Response(
                {'error': 'card_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if card exists
        try:
            card = CreditCard.objects.get(id=card_id)
        except CreditCard.DoesNotExist:
            return Response(
                {'error': 'Card not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        profile, _ = UserSpendingProfile.objects.get_or_create(user=request.user)
        owner_entity, error = _resolve_owner_entity(profile, request.data.get('owner'))
        if error:
            return error

        # Check if user already owns this card (as this owner)
        user_card, created = _get_or_create_owned_card(
            request.user, card, owner_entity,
            defaults={
                'nickname': request.data.get('nickname', ''),
                'opened_date': request.data.get('opened_date'),
                'closed_date': request.data.get('closed_date'),
                'notes': request.data.get('notes', '')
            }
        )
        
        if not created:
            # Found an existing row for this user+card (unique_together) —
            # this happens for genuine edits, but also when re-adding a
            # card that was previously soft-closed via remove_user_card.
            # 'add' always means "I currently own this card", so reopen it
            # unless the caller explicitly wants to set/keep a closed_date.
            if 'closed_date' not in request.data and user_card.closed_date is not None:
                user_card.closed_date = None
                user_card.save(update_fields=['closed_date'])

            # Update existing card
            serializer = UserCardCreateUpdateSerializer(
                user_card, data=request.data, partial=True,
                context={'request': request})
            if serializer.is_valid():
                serializer.save()
                user_card.refresh_from_db()
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Return the updated/created card
        response_serializer = UserCardSerializer(user_card)
        return Response({
            'user_card': response_serializer.data,
            'created': created,
            'message': 'Card added to your collection' if created else 'Card details updated'
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_user_card(request, user_card_id):
    """Update details of a user's card"""
    try:
        user_card = get_object_or_404(UserCard, id=user_card_id, user=request.user)
        
        serializer = UserCardCreateUpdateSerializer(
            user_card,
            data=request.data,
            partial=(request.method == 'PATCH'),
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            response_serializer = UserCardSerializer(user_card)
            return Response({
                'user_card': response_serializer.data,
                'message': 'Card details updated successfully'
            })
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_user_card(request, user_card_id):
    """Remove a card from user's collection.

    Soft-close rather than delete — eligibility rules (Chase 5/24, BofA
    2/3/4, Amex lifetime, Citi 48-month) evaluate against closed cards'
    opened/closed/bonus_earned dates, so a hard delete would erase history
    the engine still needs.
    """
    try:
        user_card = get_object_or_404(UserCard, id=user_card_id, user=request.user)
        card_name = user_card.display_name
        user_card.closed_date = timezone.now().date()
        user_card.save(update_fields=['closed_date'])

        return Response({
            'message': f'Removed {card_name} from your collection'
        })

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_user_card(request):
    """Add or remove a card from the user's collection in one call — the
    single add/remove ergonomics some callers (the card-detail modal's
    ownership toggle, roadmap results' "Remove from my cards") want instead
    of a two-step add-then-delete flow. Reopens a soft-closed row on 'add'
    (see add_user_card's docstring-adjacent comment for why) and soft-closes
    on 'remove' — never hard-deletes."""
    card_id = request.data.get('card_id')
    action = request.data.get('action')

    if not card_id or action not in ('add', 'remove'):
        return Response(
            {'error': 'card_id and action (add/remove) required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    card = get_object_or_404(CreditCard, id=card_id)
    profile, _ = UserSpendingProfile.objects.get_or_create(user=request.user)

    if action == 'add':
        owner_entity, error = _resolve_owner_entity(profile, request.data.get('owner'))
        if error:
            return error
        user_card, created = _get_or_create_owned_card(
            request.user, card, owner_entity,
            defaults={
                'nickname': request.data.get('nickname', ''),
                'opened_date': request.data.get('opened_date'),
            }
        )
        if not created:
            if user_card.closed_date is not None:
                user_card.closed_date = None
            if 'nickname' in request.data:
                user_card.nickname = request.data.get('nickname', '')
            if 'opened_date' in request.data:
                user_card.opened_date = request.data.get('opened_date')
            user_card.save()
        message = 'Card added to your collection'
    else:
        owner_id = request.data.get('owner')
        open_rows = UserCard.objects.filter(
            user=request.user, card=card, closed_date__isnull=True)
        if owner_id not in (None, ''):
            target = open_rows.filter(owner_id=owner_id).first()
        else:
            primary = profile.primary_entity()
            target = open_rows.filter(Q(owner__isnull=True) | Q(owner=primary)).first()
            if target is None and open_rows.count() == 1:
                target = open_rows.first()
        if target is None:
            if open_rows.count() > 1:
                return Response(
                    {'error': 'multiple household members hold this card — specify owner'},
                    status=status.HTTP_400_BAD_REQUEST)
            return Response({
                'success': True,
                'message': 'Card was not in your collection',
                'card_id': card_id,
                'action': action
            })
        target.closed_date = timezone.now().date()
        target.save(update_fields=['closed_date'])
        message = 'Card removed from your collection'

    return Response({
        'success': True,
        'message': message,
        'card_id': card_id,
        'action': action
    })


@api_view(['GET'])
def check_card_ownership(request, card_id):
    """Check if user owns a specific card"""
    if not request.user.is_authenticated:
        return Response({'owned': False})
    
    try:
        user_card = UserCard.objects.filter(user=request.user, card_id=card_id).first()
        if user_card:
            serializer = UserCardSerializer(user_card)
            return Response({
                'owned': True,
                'user_card': serializer.data
            })
        else:
            return Response({'owned': False})
            
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )