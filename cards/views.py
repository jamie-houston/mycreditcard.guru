from rest_framework import generics, filters, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.shortcuts import render

from .models import (
    Issuer, RewardType, SpendingCategory, CreditCard,
    UserSpendingProfile
)
from .serializers import (
    IssuerSerializer, RewardTypeSerializer, SpendingCategorySerializer,
    CreditCardSerializer, CreditCardListSerializer, UserSpendingProfileSerializer,
    CreateSpendingProfileSerializer
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


class CreditCardListView(generics.ListAPIView):
    queryset = CreditCard.objects.filter(is_active=True).select_related(
        'issuer', 'primary_reward_type', 'signup_bonus_type'
    ).prefetch_related(
        'reward_categories__category',
        'reward_categories__reward_type',
        'offers'
    )
    serializer_class = CreditCardSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'issuer__name': ['exact', 'icontains'],
        'primary_reward_type__name': ['exact', 'icontains'],
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
        'offers'
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
def index_view(request):
    """Main profile page"""
    return render(request, 'index.html')

def cards_list_view(request):
    """Credit cards listing page"""
    return render(request, 'cards_list.html')

def categories_list_view(request):
    """Spending categories listing page"""
    return render(request, 'categories_list.html')

def issuers_list_view(request):
    """Issuers listing page"""
    return render(request, 'issuers_list.html')


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