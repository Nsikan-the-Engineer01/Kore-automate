from rest_framework import serializers
from core_apps.webhooks.models import WebhookEvent


class WebhookEventSerializer(serializers.ModelSerializer):
    """Serializer for webhook events."""
    
    class Meta:
        model = WebhookEvent
        fields = [
            'id',
            'provider',
            'event_id',
            'request_ref',
            'status',
            'received_at',
            'processed_at',
        ]
        read_only_fields = fields


class WebhookPayloadSerializer(serializers.Serializer):
    """Serializer for incoming webhook payload."""
    
    # Accept any JSON payload dynamically
    def to_internal_value(self, data):
        """Accept any JSON payload."""
        if not isinstance(data, dict):
            raise serializers.ValidationError("Payload must be a JSON object")
        return data
    
    def to_representation(self, instance):
        """Return the payload as-is."""
        return instance
