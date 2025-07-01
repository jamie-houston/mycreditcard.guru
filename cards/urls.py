from django.urls import path
from . import views

app_name = 'cards'

urlpatterns = [
    # Reference data endpoints
    path('issuers/', views.IssuerListView.as_view(), name='issuer-list'),
    path('reward-types/', views.RewardTypeListView.as_view(), name='reward-type-list'),
    path('spending-categories/', views.SpendingCategoryListView.as_view(), name='spending-category-list'),
    path('categories-with-rewards/', views.categories_with_rewards_view, name='categories-with-rewards'),
    path('categories/<int:category_id>/', views.category_detail_view, name='category-detail'),
    
    # Credit card endpoints
    path('cards/', views.CreditCardListView.as_view(), name='card-list'),
    path('cards/<int:pk>/', views.CreditCardDetailView.as_view(), name='card-detail'),
    path('cards/search/', views.card_search_view, name='card-search'),
    
    # User profile endpoints
    path('profile/', views.spending_profile_view, name='spending-profile'),
    
    # Quick recommendations
    path('recommendations/preview/', views.card_recommendations_preview, name='recommendations-preview'),
    
    # Card ownership management
    path('toggle-ownership/', views.toggle_card_ownership, name='toggle-ownership'),
]