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
    path('', home_view, name='home'),
    path('admin/', admin.site.urls),
    path('api/cards/', include('cards.urls')),
    path('api/roadmaps/', include('roadmaps.urls')),
]
