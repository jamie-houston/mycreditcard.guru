from django.contrib import admin
from .models import RoadmapFilter, Roadmap, RoadmapRecommendation, RoadmapCalculation


@admin.register(RoadmapFilter)
class RoadmapFilterAdmin(admin.ModelAdmin):
    list_display = ['name', 'filter_type', 'value']
    list_filter = ['filter_type']
    search_fields = ['name', 'value']


class RoadmapRecommendationInline(admin.TabularInline):
    model = RoadmapRecommendation
    extra = 0
    readonly_fields = ['created_at']


class RoadmapCalculationInline(admin.StackedInline):
    model = RoadmapCalculation
    extra = 0
    readonly_fields = ['calculated_at']


@admin.register(Roadmap)
class RoadmapAdmin(admin.ModelAdmin):
    list_display = ['name', 'profile', 'max_recommendations', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name', 'profile__user__username']
    filter_horizontal = ['filters']
    inlines = [RoadmapRecommendationInline, RoadmapCalculationInline]


@admin.register(RoadmapRecommendation)
class RoadmapRecommendationAdmin(admin.ModelAdmin):
    list_display = ['roadmap', 'card', 'action', 'priority', 'estimated_rewards', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['roadmap__name', 'card__name']


@admin.register(RoadmapCalculation)
class RoadmapCalculationAdmin(admin.ModelAdmin):
    list_display = ['roadmap', 'total_estimated_rewards', 'calculated_at']
    readonly_fields = ['calculated_at']