import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from core_apps.goals.models import Goal


class Collection(models.Model):
    """Model for tracking money collections/contributions to goals."""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('INITIATED', 'Initiated'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='collections',
        db_index=True
    )
    goal = models.ForeignKey(
        Goal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='collections'
    )
    amount_allocation = models.DecimalField(max_digits=14, decimal_places=2)
    kore_fee = models.DecimalField(max_digits=14, decimal_places=2)
    amount_total = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default='NGN')
    provider = models.CharField(max_length=50, default='paywithaccount')
    request_ref = models.CharField(max_length=64, unique=True, db_index=True)
    provider_ref = models.CharField(max_length=64, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    narrative = models.CharField(max_length=255, blank=True)
    raw_request = models.JSONField()
    raw_response = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['status', 'provider']),
        ]
    
    def clean(self):
        """Validate that amount_total equals sum of allocation and fee."""
        if self.amount_total != self.amount_allocation + self.kore_fee:
            raise ValidationError(
                'amount_total must equal amount_allocation + kore_fee'
            )
    
    def save(self, *args, **kwargs):
        """Save with validation."""
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.request_ref} - {self.user} - {self.status}"
