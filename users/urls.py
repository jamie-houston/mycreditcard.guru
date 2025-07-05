from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # User authentication status
    path('status/', views.user_status_view, name='user-status'),
    
    # User profile management
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('preferences/', views.UserPreferencesView.as_view(), name='user-preferences'),
    
    # User cards management
    path('cards/', views.UserCardListView.as_view(), name='user-cards'),
    path('cards/<int:pk>/', views.UserCardDetailView.as_view(), name='user-card-detail'),
    path('cards/toggle/', views.toggle_user_card, name='toggle-user-card'),
    path('cards/update-details/', views.update_user_card_details, name='update-user-card-details'),
    path('cards/details/', views.get_user_cards_details, name='get-user-cards-details'),
    
    # User spending management
    path('spending/', views.UserSpendingListView.as_view(), name='user-spending'),
    
    # Bulk user data operations
    path('data/', views.user_data_view, name='user-data'),
]