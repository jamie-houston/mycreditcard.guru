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
    PRIVACY_CHOICES = [
        ('private', 'Private'),
        ('public', 'Public'),
    ]

    profile = models.ForeignKey(UserSpendingProfile, on_delete=models.CASCADE, related_name='roadmaps')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    filters = models.ManyToManyField(RoadmapFilter, blank=True)
    max_recommendations = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Roadmap sharing settings (mirrors UserSpendingProfile's privacy/share_uuid
    # pattern in cards/models.py, but anon-capable — see roadmaps/views.py)
    privacy_setting = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='private')
    share_uuid = models.UUIDField(default=None, null=True, blank=True, unique=True, help_text="Unique ID for sharing public roadmaps")

    class Meta:
        unique_together = ['profile', 'name']

    def __str__(self):
        return f"{self.profile} - {self.name}"

    def generate_share_uuid(self):
        """Generate a unique UUID for sharing this roadmap"""
        import uuid
        if not self.share_uuid:
            self.share_uuid = uuid.uuid4()
            self.save(update_fields=['share_uuid'])
        return self.share_uuid

    @property
    def shareable_url(self):
        """Get the full shareable URL for this roadmap"""
        if self.privacy_setting == 'public' and self.share_uuid:
            from django.urls import reverse
            return reverse('shared_roadmap', kwargs={'share_uuid': str(self.share_uuid)})
        return None

    @property
    def is_public(self):
        """Check if this roadmap is publicly shareable"""
        return self.privacy_setting == 'public'


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


CURRENT_ROADMAP_NAME = "Current Roadmap"


def get_current_roadmap(request):
    """Return the request's persisted "Current Roadmap" (with `.calculation`
    select_related), or None if there isn't one.

    Read-only — never creates a session or a UserSpendingProfile as a side
    effect, so a fresh anonymous visitor always gets None rather than having
    state fabricated for them. Shared by `roadmaps.views.current_roadmap_view`
    and `cards.views.landing_view`'s roadmap-first redirect.
    """
    if request.user.is_authenticated:
        roadmap = Roadmap.objects.filter(
            profile__user=request.user, name=CURRENT_ROADMAP_NAME
        ).select_related('calculation').first()
    else:
        session_key = request.session.session_key
        roadmap = (
            Roadmap.objects.filter(
                profile__session_key=session_key, name=CURRENT_ROADMAP_NAME
            ).select_related('calculation').first()
            if session_key else None
        )
    return roadmap if roadmap and hasattr(roadmap, 'calculation') else None