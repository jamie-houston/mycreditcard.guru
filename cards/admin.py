import json
import os

from django.conf import settings
from django.contrib import admin
from django.core.management import call_command
from django.utils import timezone

from .models import (
    Issuer, RewardType, SpendingCategory, CreditCard,
    RewardCategory, CardCredit, UserSpendingProfile,
    SpendingAmount, UserCard, ProfileEntity, PendingCardUpdate
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
    

@admin.register(CardCredit)
class CardCreditAdmin(admin.ModelAdmin):
    list_display = ['card', 'description', 'value', 'weight', 'currency', 'spending_credit', 'is_active']
    list_filter = ['is_active', 'currency', 'spending_credit']


class SpendingAmountInline(admin.TabularInline):
    model = SpendingAmount
    extra = 1


@admin.register(UserSpendingProfile)
class UserSpendingProfileAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'user', 'session_key', 'privacy_setting', 'created_at']
    inlines = [SpendingAmountInline]


@admin.register(UserCard)
class UserCardAdmin(admin.ModelAdmin):
    list_display = ['user', 'card', 'owner', 'display_name', 'opened_date', 'closed_date', 'is_active']
    list_filter = ['card__issuer', 'opened_date', 'closed_date']
    search_fields = ['user__username', 'card__name', 'nickname']
    date_hierarchy = 'opened_date'
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['owner']


@admin.register(ProfileEntity)
class ProfileEntityAdmin(admin.ModelAdmin):
    list_display = ['name', 'profile', 'kind', 'is_primary', 'created_at']
    list_filter = ['kind', 'is_primary']
    search_fields = ['name', 'profile__user__username']


def _approve_pending_updates(modeladmin, request, queryset):
    """Write each approved proposal into its card's JSON file, tag the
    section 'manual' (Jamie is curating by accepting it), and re-import so
    the DB reflects it. Local-dev workflow: review `git diff` and commit
    afterward — see PendingCardUpdate's docstring.

    'credits' is the exception: andenacitelli's flattened shape
    (description/times_per_year=1) can't be reconciled against our curated
    per-credit structure (credit_type/category, times_per_year=12/4/2), so
    approving a credits update only acknowledges the new total — it doesn't
    write anything. Apply the actual dollar change to the right line item
    by hand in the JSON file.
    """
    approved = 0
    acknowledged = 0
    skipped = []
    for update in queryset.filter(status='pending'):
        if update.section == 'credits':
            update.status = 'approved'
            update.resolved_at = timezone.now()
            update.save(update_fields=['status', 'resolved_at'])
            acknowledged += 1
            continue

        path = os.path.join(settings.BASE_DIR, 'data', 'input', 'cards', update.source_file)
        try:
            with open(path) as f:
                cards = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            skipped.append(f'{update.card_label}: could not read {update.source_file} ({e})')
            continue

        target = next((c for c in cards if f"{c.get('issuer')} {c.get('name')}" == update.card_label), None)
        if target is None:
            skipped.append(f'{update.card_label}: not found in {update.source_file} anymore')
            continue

        if update.section == 'annual_fee_waived':
            target.setdefault('metadata', {})['annual_fee_waived_first_year'] = update.proposed_value
        elif update.section == 'signup_bonus':
            bonus = target.get('signup_bonus')
            if not isinstance(bonus, dict):
                bonus = {}
                target['signup_bonus'] = bonus
            bonus.update(update.proposed_value)
        else:
            target[update.section] = update.proposed_value
        target.setdefault('_sources', {})[update.section] = 'manual'

        with open(path, 'w') as f:
            json.dump(cards, f, indent=2, ensure_ascii=False)
            f.write('\n')

        call_command('import_cards', path)

        update.status = 'approved'
        update.resolved_at = timezone.now()
        update.save(update_fields=['status', 'resolved_at'])
        approved += 1

    if approved:
        modeladmin.message_user(request, f'Approved {approved} update(s) — JSON updated and re-imported.')
    if acknowledged:
        modeladmin.message_user(
            request,
            f'Acknowledged {acknowledged} credits update(s) — apply the new total to the '
            'right line item in the JSON file yourself; nothing was written automatically.')
    for msg in skipped:
        modeladmin.message_user(request, msg, level='warning')


_approve_pending_updates.short_description = 'Approve selected updates (writes JSON, re-imports)'


def _reject_pending_updates(modeladmin, request, queryset):
    updated = queryset.filter(status='pending').update(status='rejected', resolved_at=timezone.now())
    modeladmin.message_user(request, f'Rejected {updated} update(s) — identical future proposals will stay suppressed.')


_reject_pending_updates.short_description = 'Reject selected updates'


@admin.register(PendingCardUpdate)
class PendingCardUpdateAdmin(admin.ModelAdmin):
    list_display = ['card_label', 'section', 'current_value', 'proposed_value', 'status', 'created_at']
    list_filter = ['status', 'section', 'source_file']
    search_fields = ['card_label', 'source_file', 'external_card_id']
    readonly_fields = ['created_at', 'resolved_at']
    actions = [_approve_pending_updates, _reject_pending_updates]