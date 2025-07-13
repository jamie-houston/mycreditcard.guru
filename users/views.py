from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import UserProfile, UserPreferences
from cards.models import UserCard, UserSpendingProfile, SpendingAmount
from .serializers import (
    UserSerializer, UserProfileSerializer, UserCardSerializer,
    UserSpendingSerializer, UserPreferencesSerializer, UserDataSerializer
)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get or update user profile"""
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


class UserCardListView(generics.ListCreateAPIView):
    """List and add user cards"""
    serializer_class = UserCardSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        profile, _ = UserSpendingProfile.objects.get_or_create(user=self.request.user)
        return UserCard.objects.filter(profile=profile, is_active=True).select_related('card')
    
    def perform_create(self, serializer):
        profile, _ = UserSpendingProfile.objects.get_or_create(user=self.request.user)
        serializer.save(profile=profile)


class UserCardDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Manage individual user cards"""
    serializer_class = UserCardSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        profile, _ = UserSpendingProfile.objects.get_or_create(user=self.request.user)
        return UserCard.objects.filter(profile=profile)


class UserSpendingListView(generics.ListCreateAPIView):
    """List and update user spending"""
    serializer_class = UserSpendingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        profile, _ = UserSpendingProfile.objects.get_or_create(user=self.request.user)
        return SpendingAmount.objects.filter(profile=profile).select_related('category')
    
    def perform_create(self, serializer):
        profile, _ = UserSpendingProfile.objects.get_or_create(user=self.request.user)
        serializer.save(profile=profile)


class UserPreferencesView(generics.RetrieveUpdateAPIView):
    """Get or update user preferences"""
    serializer_class = UserPreferencesSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        prefs, created = UserPreferences.objects.get_or_create(user=self.request.user)
        return prefs


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def user_data_view(request):
    """Bulk get/save user data (spending, cards, preferences)"""
    if request.method == 'GET':
        serializer = UserDataSerializer(instance=None, context={'request': request})
        return Response(serializer.to_representation(None))
    
    elif request.method == 'POST':
        serializer = UserDataSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.create(serializer.validated_data)
            return Response({'success': True, 'message': 'Data saved successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_user_card(request):
    """Add or remove a card from user's collection"""
    try:
        card_id = request.data.get('card_id')
        action = request.data.get('action')  # 'add' or 'remove'
        
        if not card_id or action not in ['add', 'remove']:
            return Response(
                {'error': 'card_id and action (add/remove) required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from cards.models import CreditCard
        try:
            card = CreditCard.objects.get(id=card_id)
        except CreditCard.DoesNotExist:
            return Response(
                {'error': 'Card not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        profile, _ = UserSpendingProfile.objects.get_or_create(user=request.user)
        
        if action == 'add':
            # Always create a new UserCard instance to allow multiple of same card
            nickname = request.data.get('nickname', '')
            opened_date = request.data.get('opened_date')
            
            user_card = UserCard.objects.create(
                profile=profile,
                card=card,
                nickname=nickname,
                opened_date=opened_date,
                is_active=True
            )
            message = 'Card added to your collection'
        else:  # remove
            UserCard.objects.filter(profile=profile, card=card).update(is_active=False)
            message = 'Card removed from your collection'
        
        return Response({
            'success': True,
            'message': message,
            'card_id': card_id,
            'action': action
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_user_card_details(request):
    """Update nickname and opening date for a user's card"""
    try:
        card_id = request.data.get('card_id')
        nickname = request.data.get('nickname', '')
        opened_date = request.data.get('opened_date')
        
        if not card_id:
            return Response(
                {'error': 'card_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from cards.models import CreditCard
        try:
            card = CreditCard.objects.get(id=card_id)
        except CreditCard.DoesNotExist:
            return Response(
                {'error': 'Card not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        profile, _ = UserSpendingProfile.objects.get_or_create(user=request.user)
        
        try:
            user_card = UserCard.objects.get(profile=profile, card=card, is_active=True)
        except UserCard.DoesNotExist:
            return Response(
                {'error': 'Card not in your collection'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update the card details
        user_card.nickname = nickname
        if opened_date:
            user_card.opened_date = opened_date
        user_card.save()
        
        # Return updated card data
        serializer = UserCardSerializer(user_card)
        return Response({
            'success': True,
            'message': 'Card details updated successfully',
            'user_card': serializer.data
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_cards_details(request):
    """Get detailed user cards with nickname and opening date"""
    try:
        profile, _ = UserSpendingProfile.objects.get_or_create(user=request.user)
        user_cards = UserCard.objects.filter(profile=profile, is_active=True).select_related('card', 'card__issuer', 'card__primary_reward_type')
        
        serializer = UserCardSerializer(user_cards, many=True)
        return Response({
            'success': True,
            'user_cards': serializer.data
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def user_status_view(request):
    """Get current user authentication status"""
    if request.user.is_authenticated:
        return Response({
            'authenticated': True,
            'user': UserSerializer(request.user).data
        })
    else:
        return Response({
            'authenticated': False,
            'user': None
        })
