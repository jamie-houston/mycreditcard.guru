from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # User authentication status
    path('status/', views.user_status_view, name='user-status'),
    
    # User profile management
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('preferences/', views.UserPreferencesView.as_view(), name='user-preferences'),

    # User cards management moved to cards/ app (Phase F5) — see
    # cards/urls.py user-cards/* and CLAUDE.md's ownership section.

    # User spending management
    path('spending/', views.UserSpendingListView.as_view(), name='user-spending'),
    
    # Bulk user data operations
    path('data/', views.user_data_view, name='user-data'),
]