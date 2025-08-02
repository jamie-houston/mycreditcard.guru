from django.contrib import admin
from .models import (
    Issuer, RewardType, SpendingCategory, CreditCard,
    RewardCategory, CardCredit, CreditType, UserSpendingProfile,
    SpendingAmount, UserCard, UserCreditPreference
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


class CardCreditInline(admin.TabularInline):
    model = CardCredit
    extra = 1


@admin.register(CreditCard)
class CreditCardAdmin(admin.ModelAdmin):
    list_display = ['name', 'issuer', 'card_type', 'annual_fee', 'signup_bonus_amount', 'is_active']
    list_filter = ['issuer', 'card_type', 'primary_reward_type', 'is_active']
    search_fields = ['name', 'issuer__name']
    inlines = [RewardCategoryInline, CardCreditInline]


@admin.register(RewardCategory)
class RewardCategoryAdmin(admin.ModelAdmin):
    list_display = ['card', 'category', 'reward_rate', 'reward_type', 'start_date', 'end_date']
    list_filter = ['reward_type', 'category', 'is_active']
    

@admin.register(CreditType)
class CreditTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'sort_order']
    list_filter = ['category']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(CardCredit)
class CardCreditAdmin(admin.ModelAdmin):
    list_display = ['card', 'description', 'value', 'weight', 'currency', 'credit_type', 'is_active']
    list_filter = ['is_active', 'currency', 'credit_type']


class SpendingAmountInline(admin.TabularInline):
    model = SpendingAmount
    extra = 1


class UserCreditPreferenceInline(admin.TabularInline):
    model = UserCreditPreference
    extra = 1


@admin.register(UserSpendingProfile)
class UserSpendingProfileAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'user', 'session_key', 'privacy_setting', 'created_at']
    inlines = [SpendingAmountInline, UserCreditPreferenceInline]


@admin.register(UserCard)
class UserCardAdmin(admin.ModelAdmin):
    list_display = ['user', 'card', 'display_name', 'opened_date', 'closed_date', 'is_active']
    list_filter = ['card__issuer', 'opened_date', 'closed_date']
    search_fields = ['user__username', 'card__name', 'nickname']
    date_hierarchy = 'opened_date'
    readonly_fields = ['created_at', 'updated_at']