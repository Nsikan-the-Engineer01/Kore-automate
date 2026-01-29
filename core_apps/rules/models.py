import uuid
from django.db import models
from django.conf import settings
from core_apps.goals.models import Goal


class Rule(models.Model):
    """Model for automated goal contribution rules."""
    
    FREQUENCY_CHOICES = [
        ('MANUAL', 'Manual'),
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rules',
        db_index=True
    )
    goal = models.ForeignKey(
        Goal,
        on_delete=models.CASCADE,
        related_name='rules'
    )
    frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default='MANUAL'
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    enabled = models.BooleanField(default=True, db_index=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['goal']),
            models.Index(fields=['enabled']),
        ]
    
    def __str__(self):
        return f"{self.goal.name} - {self.frequency} - {self.amount}"
