"""
URL configuration for creditcard_guru project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.shortcuts import render
from cards.views import index_view, cards_list_view, categories_list_view, category_detail_page_view, issuers_list_view, profile_view

def home_view(request):
    if 'text/html' in request.META.get('HTTP_ACCEPT', ''):
        return render(request, 'index.html')
    
    return JsonResponse({
        'message': 'Credit Card Guru API',
        'version': '1.0',
        'endpoints': {
            'cards': '/api/cards/',
            'roadmaps': '/api/roadmaps/',
            'admin': '/admin/',
            'docs': {
                'cards': '/api/cards/ - List all credit cards',
                'card_search': '/api/cards/search/ - Advanced card search',
                'spending_profile': '/api/cards/profile/ - User spending profile',
                'roadmaps': '/api/roadmaps/ - User roadmaps',
                'quick_recommendation': '/api/roadmaps/quick-recommendation/ - Get quick recommendations'
            }
        }
    })

urlpatterns = [
    # Template pages
    path('', index_view, name='index'),
    path('cards/', cards_list_view, name='cards_list'),
    path('categories/', categories_list_view, name='categories_list'),
    path('categories/<slug:category_slug>/', category_detail_page_view, name='category_detail'),
    path('issuers/', issuers_list_view, name='issuers_list'),
    path('profile/', profile_view, name='profile'),
    
    # Authentication
    path('accounts/', include('allauth.urls')),
    
    # API endpoints
    path('api/', home_view, name='api_home'),
    path('admin/', admin.site.urls),
    path('api/cards/', include('cards.urls')),
    path('api/roadmaps/', include('roadmaps.urls')),
    path('api/users/', include('users.urls')),
]
