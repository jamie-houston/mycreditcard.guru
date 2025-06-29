from django.db import models
from django.contrib.auth.models import User
from cards.models import CreditCard, SpendingCategory


class UserProfile(models.Model):
    """Extended user profile for storing preferences and settings"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # User preferences
    preferred_issuer = models.CharField(max_length=100, blank=True, null=True)
    preferred_reward_type = models.CharField(max_length=50, blank=True, null=True)
    max_annual_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    class Meta:
        db_table = 'user_profiles'
    
    def __str__(self):
        return f"{self.user.email}'s Profile"



class UserPreferences(models.Model):
    """User's saved preferences and filters"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    
    # Saved filter preferences
    default_issuer_filter = models.CharField(max_length=100, blank=True)
    default_reward_type_filter = models.CharField(max_length=50, blank=True)
    default_max_fee_filter = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    default_max_recommendations = models.IntegerField(default=5)
    
    # UI preferences
    theme = models.CharField(max_length=20, default='light', choices=[('light', 'Light'), ('dark', 'Dark')])
    email_notifications = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_preferences'
    
    def __str__(self):
        return f"{self.user.email}'s Preferences"
