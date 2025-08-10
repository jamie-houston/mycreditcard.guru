from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import json


class Issuer(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    max_cards_per_period = models.IntegerField(default=5)
    period_months = models.IntegerField(default=24)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name


class RewardType(models.Model):
    name = models.CharField(max_length=50, unique=True)  # points, miles, cashback, hotel_nights
    slug = models.SlugField(unique=True)
    
    def __str__(self):
        return self.name


class SpendingCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    display_name = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    sort_order = models.IntegerField(default=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    
    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name_plural = "Spending Categories"
    
    def __str__(self):
        return self.display_name or self.name
    
    @property
    def is_parent_category(self):
        """Returns True if this is a parent category (has subcategories)"""
        return self.subcategories.exists()
    
    @property
    def is_subcategory(self):
        """Returns True if this is a subcategory (has a parent)"""
        return self.parent is not None


class CreditCard(models.Model):
    CARD_TYPES = [
        ('personal', 'Personal'),
        ('business', 'Business'),
    ]
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    issuer = models.ForeignKey(Issuer, on_delete=models.CASCADE)
    card_type = models.CharField(max_length=20, choices=CARD_TYPES, default='personal')
    annual_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    signup_bonus_amount = models.IntegerField(null=True, blank=True)
    signup_bonus_type = models.ForeignKey(RewardType, on_delete=models.CASCADE, related_name='signup_bonus_cards')
    signup_bonus_requirement = models.CharField(max_length=500, blank=True)
    primary_reward_type = models.ForeignKey(RewardType, on_delete=models.CASCADE, related_name='primary_reward_cards')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # URL fields for referral links
    url = models.URLField(max_length=500, blank=True, help_text="Primary card application URL")
    
    # JSON field for additional metadata (including signup_bonus.referral_url)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        unique_together = ['name', 'issuer']
    
    def __str__(self):
        return f"{self.issuer.name} {self.name}"
    
    @property
    def referral_url(self):
        """
        Get the referral URL with priority:
        1. signup_bonus.referral_url from metadata
        2. url field
        """
        # First try to get referral_url from signup_bonus in metadata
        signup_bonus = self.metadata.get('signup_bonus', {})
        if isinstance(signup_bonus, dict) and signup_bonus.get('referral_url'):
            return signup_bonus['referral_url']
        
        # Fallback to the main url field
        return self.url if self.url else None
    
    @property 
    def apply_url(self):
        """Alias for referral_url for template clarity"""
        return self.referral_url


class RewardCategory(models.Model):
    card = models.ForeignKey(CreditCard, on_delete=models.CASCADE, related_name='reward_categories')
    category = models.ForeignKey(SpendingCategory, on_delete=models.CASCADE)
    reward_rate = models.DecimalField(max_digits=5, decimal_places=2)  # e.g., 5.00 for 5x points
    reward_type = models.ForeignKey(RewardType, on_delete=models.CASCADE)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    max_annual_spend = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['card', 'category', 'start_date']
    
    def __str__(self):
        period = ""
        if self.start_date and self.end_date:
            period = f" ({self.start_date} to {self.end_date})"
        return f"{self.card} - {self.reward_rate}x {self.category}{period}"


class CreditType(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    category = models.CharField(max_length=100, blank=True)  # e.g., 'travel', 'dining', 'misc'
    sort_order = models.IntegerField(default=100)
    
    class Meta:
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name


class SpendingCredit(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    display_name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    category = models.ForeignKey(SpendingCategory, on_delete=models.CASCADE, related_name='spending_credits')
    icon = models.CharField(max_length=50, blank=True)
    sort_order = models.IntegerField(default=100)
    
    class Meta:
        ordering = ['sort_order', 'display_name']
    
    def __str__(self):
        return self.display_name


class CardCredit(models.Model):
    card = models.ForeignKey(CreditCard, on_delete=models.CASCADE, related_name='credits')
    credit_type = models.ForeignKey(CreditType, on_delete=models.CASCADE, related_name='card_credits', null=True, blank=True)
    spending_credit = models.ForeignKey(SpendingCredit, on_delete=models.CASCADE, related_name='card_credits', null=True, blank=True)
    category = models.ForeignKey(SpendingCategory, on_delete=models.CASCADE, null=True, blank=True)  # For category-based credits
    description = models.CharField(max_length=500)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    times_per_year = models.IntegerField(default=1)
    weight = models.FloatField(default=1.0)
    currency = models.CharField(max_length=20, default='USD', blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.card} - {self.description}"
    
    @property
    def annual_value(self):
        """Calculate the total annual value of this credit"""
        return float(self.value) * self.times_per_year


class UserSpendingProfile(models.Model):
    PRIVACY_CHOICES = [
        ('private', 'Private'),
        ('public', 'Public'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)  # For anonymous users
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Profile sharing settings
    privacy_setting = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='private')
    share_uuid = models.UUIDField(default=None, null=True, blank=True, unique=True, help_text="Unique ID for sharing public profiles")
    
    class Meta:
        unique_together = [['user'], ['session_key']]
    
    def __str__(self):
        if self.user:
            return f"Profile for {self.user.username}"
        return f"Anonymous profile {self.session_key}"
    
    def generate_share_uuid(self):
        """Generate a unique UUID for sharing this profile"""
        import uuid
        if not self.share_uuid:
            self.share_uuid = uuid.uuid4()
            self.save(update_fields=['share_uuid'])
        return self.share_uuid
    
    @property
    def shareable_url(self):
        """Get the full shareable URL for this profile"""
        if self.privacy_setting == 'public' and self.share_uuid:
            from django.urls import reverse
            return reverse('shared_profile', kwargs={'share_uuid': str(self.share_uuid)})
        return None
    
    @property
    def is_public(self):
        """Check if this profile is publicly shareable"""
        return self.privacy_setting == 'public'


class SpendingAmount(models.Model):
    profile = models.ForeignKey(UserSpendingProfile, on_delete=models.CASCADE, related_name='spending_amounts')
    category = models.ForeignKey(SpendingCategory, on_delete=models.CASCADE)
    monthly_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        unique_together = ['profile', 'category']
    
    def __str__(self):
        return f"{self.profile} - {self.category}: ${self.monthly_amount}"


class UserCard(models.Model):
    """Tracks detailed information about cards owned by users"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_cards')
    card = models.ForeignKey(CreditCard, on_delete=models.CASCADE, related_name='user_ownerships')
    
    # Card details
    nickname = models.CharField(max_length=100, blank=True, help_text="Optional nickname for this card")
    opened_date = models.DateField(null=True, blank=True, help_text="Date when the card was opened/approved")
    closed_date = models.DateField(null=True, blank=True, help_text="Date when the card was closed (if applicable)")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, help_text="Additional notes about this card")
    
    class Meta:
        unique_together = ['user', 'card']
        ordering = ['-opened_date', '-created_at']
    
    def __str__(self):
        card_name = self.nickname if self.nickname else str(self.card)
        status = " (Closed)" if self.closed_date else ""
        return f"{self.user.username}'s {card_name}{status}"
    
    @property
    def is_active(self):
        """Check if the card is currently active (not closed)"""
        return self.closed_date is None
    
    @property
    def display_name(self):
        """Get the display name (nickname if available, otherwise card name)"""
        return self.nickname if self.nickname else str(self.card)



class UserCreditPreference(models.Model):
    profile = models.ForeignKey(UserSpendingProfile, on_delete=models.CASCADE, related_name='credit_preferences')
    credit_type = models.ForeignKey(CreditType, on_delete=models.CASCADE)
    values_credit = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['profile', 'credit_type']
    
    def __str__(self):
        return f"{self.profile} - {self.credit_type.name}: {self.values_credit}"


class UserSpendingCreditPreference(models.Model):
    """Tracks which spending credits the user values/uses"""
    profile = models.ForeignKey(UserSpendingProfile, on_delete=models.CASCADE, related_name='spending_credit_preferences')
    spending_credit = models.ForeignKey(SpendingCredit, on_delete=models.CASCADE)
    values_credit = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['profile', 'spending_credit']
    
    def __str__(self):
        return f"{self.profile} - {self.spending_credit.display_name}: {self.values_credit}"