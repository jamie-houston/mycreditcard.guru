from django.db import models
from django.contrib.auth.models import User
from cards.models import CreditCard, UserSpendingProfile, Issuer, RewardType


class RoadmapFilter(models.Model):
    FILTER_TYPES = [
        ('issuer', 'Issuer'),
        ('reward_type', 'Reward Type'),
        ('card_type', 'Card Type'),
        ('annual_fee', 'Annual Fee'),
        ('signup_bonus', 'Signup Bonus'),
    ]
    
    name = models.CharField(max_length=100)
    filter_type = models.CharField(max_length=20, choices=FILTER_TYPES)
    value = models.CharField(max_length=200)  # JSON string for complex filters
    
    def __str__(self):
        return f"{self.name} ({self.filter_type})"


class Roadmap(models.Model):
    profile = models.ForeignKey(UserSpendingProfile, on_delete=models.CASCADE, related_name='roadmaps')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    filters = models.ManyToManyField(RoadmapFilter, blank=True)
    max_recommendations = models.IntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['profile', 'name']
    
    def __str__(self):
        return f"{self.profile} - {self.name}"


class RoadmapRecommendation(models.Model):
    ACTION_TYPES = [
        ('apply', 'Apply for new card'),
        ('keep', 'Keep current card'),
        ('cancel', 'Cancel card'),
        ('upgrade', 'Upgrade card'),
        ('downgrade', 'Downgrade card'),
    ]
    
    roadmap = models.ForeignKey(Roadmap, on_delete=models.CASCADE, related_name='recommendations')
    card = models.ForeignKey(CreditCard, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    priority = models.IntegerField(default=1)  # 1 = highest priority
    estimated_rewards = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reasoning = models.TextField()
    recommended_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['roadmap', 'card', 'action']
        ordering = ['priority', 'estimated_rewards']
    
    def __str__(self):
        return f"{self.roadmap} - {self.action.title()} {self.card}"


class RoadmapCalculation(models.Model):
    roadmap = models.OneToOneField(Roadmap, on_delete=models.CASCADE, related_name='calculation')
    total_estimated_rewards = models.DecimalField(max_digits=12, decimal_places=2)
    calculation_data = models.JSONField(default=dict)  # Store detailed breakdown
    calculated_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Calculation for {self.roadmap}"