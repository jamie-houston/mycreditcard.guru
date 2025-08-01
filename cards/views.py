from rest_framework import generics, filters, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.shortcuts import render, get_object_or_404

from .models import (
    Issuer, RewardType, SpendingCategory, CreditCard,
    UserSpendingProfile, SpendingCredit
)
from .serializers import (
    IssuerSerializer, RewardTypeSerializer, SpendingCategorySerializer,
    CreditCardSerializer, CreditCardListSerializer, UserSpendingProfileSerializer,
    CreateSpendingProfileSerializer, SpendingCreditSerializer
)


class IssuerListView(generics.ListAPIView):
    queryset = Issuer.objects.all().order_by('name')
    serializer_class = IssuerSerializer


class RewardTypeListView(generics.ListAPIView):
    queryset = RewardType.objects.all().order_by('name')
    serializer_class = RewardTypeSerializer


class SpendingCategoryListView(generics.ListAPIView):
    queryset = SpendingCategory.objects.all().order_by('name')
    serializer_class = SpendingCategorySerializer


class SpendingCreditListView(generics.ListAPIView):
    queryset = SpendingCredit.objects.all().select_related('category').order_by('category__sort_order', 'sort_order', 'display_name')
    serializer_class = SpendingCreditSerializer


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
    """Landing page - welcome and feature overview"""
    return render(request, 'landing.html')

def index_view(request):
    """Roadmap creation page"""
    context = {
        'user_email': request.user.email if request.user.is_authenticated else None,
        'is_dev_user': request.user.is_authenticated and request.user.email == 'foresterh@gmail.com'
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
def toggle_card_ownership(request):
    """Add or remove a card from user's collection"""
    try:
        card_id = request.data.get('card_id')
        action = request.data.get('action')  # 'add' or 'remove'
        
        if not card_id or action not in ['add', 'remove']:
            return Response(
                {'error': 'card_id and action (add/remove) required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # For now, we'll just return success since we don't have UserCard model
        # In a full implementation, this would manage UserCard records
        return Response({
            'success': True,
            'message': f'Card {"added to" if action == "add" else "removed from"} your collection',
            'card_id': card_id,
            'action': action
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )