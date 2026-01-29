import uuid
from django.db import models


class WebhookEvent(models.Model):
    """Model for storing incoming webhook events."""
    
    STATUS_CHOICES = [
        ('RECEIVED', 'Received'),
        ('PROCESSED', 'Processed'),
        ('FAILED', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=50, default='paywithaccount')
    event_id = models.CharField(max_length=64, null=True, blank=True, unique=True)
    request_ref = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    payload = models.JSONField()
    signature = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='RECEIVED'
    )
    error = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-received_at']
    
    def __str__(self):
        return f"{self.provider} - {self.event_id} - {self.status}"
