from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import UserProfile, UserPreferences
from cards.models import UserSpendingProfile, SpendingAmount
from .serializers import (
    UserSerializer, UserProfileSerializer,
    UserSpendingSerializer, UserPreferencesSerializer, UserDataSerializer
)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get or update user profile"""
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


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
