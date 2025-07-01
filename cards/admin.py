from django.contrib import admin
from .models import (
    Issuer, RewardType, SpendingCategory, CreditCard,
    RewardCategory, CardOffer, UserSpendingProfile,
    SpendingAmount, UserCard
)


@admin.register(Issuer)
class IssuerAdmin(admin.ModelAdmin):
    list_display = ['name', 'max_cards_per_period', 'period_months', 'created_at']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(RewardType)
class RewardTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(SpendingCategory)
class SpendingCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


class RewardCategoryInline(admin.TabularInline):
    model = RewardCategory
    extra = 1


class CardOfferInline(admin.TabularInline):
    model = CardOffer
    extra = 1


@admin.register(CreditCard)
class CreditCardAdmin(admin.ModelAdmin):
    list_display = ['name', 'issuer', 'card_type', 'annual_fee', 'signup_bonus_amount', 'is_active']
    list_filter = ['issuer', 'card_type', 'primary_reward_type', 'is_active']
    search_fields = ['name', 'issuer__name']
    inlines = [RewardCategoryInline, CardOfferInline]


@admin.register(RewardCategory)
class RewardCategoryAdmin(admin.ModelAdmin):
    list_display = ['card', 'category', 'reward_rate', 'reward_type', 'start_date', 'end_date']
    list_filter = ['reward_type', 'category', 'is_active']
    

@admin.register(CardOffer)
class CardOfferAdmin(admin.ModelAdmin):
    list_display = ['card', 'title', 'value', 'start_date', 'end_date', 'is_active']
    list_filter = ['is_active']


class SpendingAmountInline(admin.TabularInline):
    model = SpendingAmount
    extra = 1


class UserCardInline(admin.TabularInline):
    model = UserCard
    extra = 1


@admin.register(UserSpendingProfile)
class UserSpendingProfileAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'user', 'session_key', 'created_at']
    inlines = [SpendingAmountInline, UserCardInline]