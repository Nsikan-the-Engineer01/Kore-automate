import uuid
from django.db import models
from django.conf import settings
from core_apps.goals.models import Goal
from core_apps.collections.models import Collection


class Transaction(models.Model):
    """Model for append-only transaction ledger."""
    
    TYPE_CHOICES = [
        ('DEBIT', 'Debit'),
        ('CREDIT', 'Credit'),
        ('FEE', 'Fee'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transactions',
        db_index=True
    )
    goal = models.ForeignKey(
        Goal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    collection = models.ForeignKey(
        Collection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    request_ref = models.CharField(max_length=64, db_index=True)
    provider_ref = models.CharField(max_length=64, null=True, blank=True)
    occurred_at = models.DateTimeField()
    metadata = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        # Append-only table - prevent accidental updates
        get_latest_by = 'created_at'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.request_ref} - {self.type} - {self.amount} {self.currency}"
