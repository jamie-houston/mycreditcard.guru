from django.urls import path
from . import views

app_name = 'roadmaps'

urlpatterns = [
    # Roadmap filters
    path('filters/', views.RoadmapFilterListView.as_view(), name='filter-list'),
    
    # Roadmaps CRUD
    path('', views.RoadmapListView.as_view(), name='roadmap-list'),
    path('create/', views.create_roadmap_view, name='roadmap-create'),
    path('<int:pk>/', views.RoadmapDetailView.as_view(), name='roadmap-detail'),
    
    # Roadmap generation
    path('<int:roadmap_id>/generate/', views.generate_roadmap_view, name='roadmap-generate'),
    path('quick-recommendation/', views.quick_recommendation_view, name='quick-recommendation'),
    
    # Stats
    path('stats/', views.roadmap_stats_view, name='roadmap-stats'),
    
    # Debug/Development
    path('export-scenario/', views.export_scenario_view, name='export-scenario'),
]