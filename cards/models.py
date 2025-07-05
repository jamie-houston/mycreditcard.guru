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
    
    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name_plural = "Spending Categories"
    
    def __str__(self):
        return self.display_name or self.name


class CreditCard(models.Model):
    CARD_TYPES = [
        ('personal', 'Personal'),
        ('business', 'Business'),
    ]
    
    name = models.CharField(max_length=200)
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
    
    # JSON field for additional metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        unique_together = ['name', 'issuer']
    
    def __str__(self):
        return f"{self.issuer.name} {self.name}"


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


class CardOffer(models.Model):
    card = models.ForeignKey(CreditCard, on_delete=models.CASCADE, related_name='offers')
    title = models.CharField(max_length=200)
    description = models.TextField()
    value = models.CharField(max_length=100, blank=True)  # e.g., "$12" or "2 free"
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.card} - {self.title}"


class UserSpendingProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)  # For anonymous users
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['user'], ['session_key']]
    
    def __str__(self):
        if self.user:
            return f"Profile for {self.user.username}"
        return f"Anonymous profile {self.session_key}"


class SpendingAmount(models.Model):
    profile = models.ForeignKey(UserSpendingProfile, on_delete=models.CASCADE, related_name='spending_amounts')
    category = models.ForeignKey(SpendingCategory, on_delete=models.CASCADE)
    monthly_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        unique_together = ['profile', 'category']
    
    def __str__(self):
        return f"{self.profile} - {self.category}: ${self.monthly_amount}"


class UserCard(models.Model):
    profile = models.ForeignKey(UserSpendingProfile, on_delete=models.CASCADE, related_name='user_cards')
    card = models.ForeignKey(CreditCard, on_delete=models.CASCADE)
    nickname = models.CharField(max_length=100, blank=True)
    opened_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['profile', 'card']
    
    def __str__(self):
        name = self.nickname or str(self.card)
        return f"{self.profile} - {name}"
    
    def display_name(self):
        """Return card name with nickname if available"""
        if self.nickname:
            return f"{self.card.name} ({self.nickname})"
        return self.card.name