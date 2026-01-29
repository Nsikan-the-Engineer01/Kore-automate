from rest_framework import serializers
from core_apps.collections.models import Collection
from core_apps.goals.models import Goal


class CollectionCreateSerializer(serializers.Serializer):
    """Serializer for creating collections."""

    # goal_id is optional; if omitted the collection is not tied to a goal
    goal_id = serializers.UUIDField(required=False, allow_null=True)
    amount_allocation = serializers.DecimalField(
        max_digits=14, 
        decimal_places=2, 
        min_value=0.01,
        required=True
    )
    currency = serializers.CharField(
        max_length=3,
        default='NGN',
        required=False
    )
    narrative = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True
    )
    
    def validate_goal_id(self, value):
        """Validate that goal exists."""
        # If goal_id is None or not provided, skip validation here
        if value in (None, ''):
            return value
        try:
            Goal.objects.get(id=value)
        except Goal.DoesNotExist:
            raise serializers.ValidationError("Goal does not exist.")
        return value
    
    def validate_amount_allocation(self, value):
        """Validate that amount is positive."""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value


class CollectionSerializer(serializers.ModelSerializer):
    """Serializer for collection responses."""
    
    goal_name = serializers.CharField(
        source='goal.name',
        read_only=True,
        allow_null=True
    )
    user_username = serializers.CharField(
        source='user.username',
        read_only=True
    )
    
    class Meta:
        model = Collection
        fields = [
            'id',
            'user_username',
            'goal_id',
            'goal_name',
            'amount_allocation',
            'kore_fee',
            'amount_total',
            'currency',
            'provider',
            'request_ref',
            'provider_ref',
            'status',
            'narrative',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'user_username',
            'goal_name',
            'kore_fee',
            'amount_total',
            'provider',
            'request_ref',
            'provider_ref',
            'status',
            'created_at',
            'updated_at',
        ]

class CollectionCreateResponseSerializer(serializers.ModelSerializer):
    """Extended response serializer for collection creation that includes validation flags."""
    
    goal_name = serializers.CharField(
        source='goal.name',
        read_only=True,
        allow_null=True
    )
    user_username = serializers.CharField(
        source='user.username',
        read_only=True
    )
    requires_validation = serializers.SerializerMethodField()
    validation_fields = serializers.SerializerMethodField()
    
    class Meta:
        model = Collection
        fields = [
            'id',
            'user_username',
            'goal_id',
            'goal_name',
            'amount_allocation',
            'kore_fee',
            'amount_total',
            'currency',
            'provider',
            'request_ref',
            'provider_ref',
            'status',
            'narrative',
            'requires_validation',
            'validation_fields',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'user_username',
            'goal_name',
            'kore_fee',
            'amount_total',
            'provider',
            'request_ref',
            'provider_ref',
            'status',
            'requires_validation',
            'validation_fields',
            'created_at',
            'updated_at',
        ]
    
    def get_requires_validation(self, obj) -> bool:
        """
        Extract validation requirement from metadata.
        
        Returns True if collection status indicates OTP/validation is required.
        """
        if obj.metadata:
            return obj.metadata.get('needs_validation', False)
        return False
    
    def get_validation_fields(self, obj) -> dict:
        """
        Extract validation fields from metadata for frontend use.
        
        Contains validation_ref, session_id, otp_reference, etc.
        Returns empty dict if not applicable.
        """
        if obj.metadata and obj.metadata.get('needs_validation'):
            return obj.metadata.get('validation_fields', {})
        return {}


class CollectionValidateSerializer(serializers.Serializer):
    """Serializer for submitting validation (OTP, challenge, etc.) to a collection."""
    
    otp = serializers.CharField(
        max_length=10,
        required=False,
        allow_blank=True,
        help_text="One-time password from user (if provider requires)"
    )


class CollectionStatusResponseSerializer(serializers.ModelSerializer):
    """Response serializer for collection status queries."""
    
    goal_name = serializers.CharField(
        source='goal.name',
        read_only=True,
        allow_null=True
    )
    user_username = serializers.CharField(
        source='user.username',
        read_only=True
    )
    requires_validation = serializers.SerializerMethodField()
    validation_fields = serializers.SerializerMethodField()
    
    class Meta:
        model = Collection
        fields = [
            'id',
            'user_username',
            'goal_id',
            'goal_name',
            'amount_allocation',
            'kore_fee',
            'amount_total',
            'currency',
            'provider',
            'request_ref',
            'provider_ref',
            'status',
            'narrative',
            'requires_validation',
            'validation_fields',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'user_username',
            'goal_name',
            'amount_allocation',
            'kore_fee',
            'amount_total',
            'currency',
            'provider',
            'request_ref',
            'provider_ref',
            'status',
            'narrative',
            'requires_validation',
            'validation_fields',
            'updated_at',
        ]
    
    def get_requires_validation(self, obj) -> bool:
        """Extract validation requirement from metadata."""
        if obj.metadata:
            return obj.metadata.get('needs_validation', False)
        return False
    
    def get_validation_fields(self, obj) -> dict:
        """Extract validation fields from metadata."""
        if obj.metadata and obj.metadata.get('needs_validation'):
            return obj.metadata.get('validation_fields', {})
        return {}