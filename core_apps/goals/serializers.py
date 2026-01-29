from decimal import Decimal
from rest_framework import serializers
from .models import Goal


class GoalCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new goals."""
    
    currency = serializers.CharField(default='NGN', required=False)
    metadata = serializers.JSONField(default=dict, required=False)
    
    class Meta:
        model = Goal
        fields = ['name', 'target_amount', 'currency', 'metadata']
    
    def validate_target_amount(self, value):
        """Ensure target_amount is greater than 0."""
        if value <= 0:
            raise serializers.ValidationError("Target amount must be greater than 0.")
        return value
    
    def validate_name(self, value):
        """Ensure name is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Goal name cannot be empty.")
        return value.strip()
    
    def validate_currency(self, value):
        """Ensure currency is a valid 3-character code."""
        if not value or len(value) != 3:
            raise serializers.ValidationError("Currency must be a 3-character code (e.g., 'NGN').")
        return value.upper()
    
    def create(self, validated_data):
        """Create goal with current user and default status of ACTIVE."""
        validated_data['user'] = self.context['request'].user
        validated_data['status'] = 'ACTIVE'
        return super().create(validated_data)


class GoalUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating goals (partial updates only)."""
    
    class Meta:
        model = Goal
        fields = ['name', 'target_amount', 'currency', 'metadata']
    
    def validate_target_amount(self, value):
        """Ensure target_amount is greater than 0 if provided."""
        if value is not None and value <= 0:
            raise serializers.ValidationError("Target amount must be greater than 0.")
        return value
    
    def validate_name(self, value):
        """Ensure name is not empty if provided."""
        if value is not None:
            if not value or not value.strip():
                raise serializers.ValidationError("Goal name cannot be empty.")
            return value.strip()
        return value
    
    def validate_currency(self, value):
        """Ensure currency is a valid 3-character code if provided."""
        if value is not None:
            if not value or len(value) != 3:
                raise serializers.ValidationError("Currency must be a 3-character code (e.g., 'NGN').")
            return value.upper()
        return value
    
    def update(self, instance, validated_data):
        """Update goal, explicitly preventing user and status changes."""
        # Never allow user changes
        validated_data.pop('user', None)
        # Never allow status changes (must use dedicated endpoint if needed)
        validated_data.pop('status', None)
        return super().update(instance, validated_data)


class GoalDetailSerializer(serializers.ModelSerializer):
    """Serializer for retrieving detailed goal information."""
    
    # Decimals as strings (DRF standard)
    target_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        coerce_to_string=True
    )
    total_contributed = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()
    
    class Meta:
        model = Goal
        fields = [
            'id',
            'name',
            'target_amount',
            'currency',
            'status',
            'metadata',
            'total_contributed',
            'progress_percent',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'total_contributed',
            'progress_percent',
            'created_at',
            'updated_at'
        ]
    
    def get_total_contributed(self, obj):
        """
        Calculate total amount contributed to this goal.
        
        Returns decimal as string.
        Placeholder: returns "0.00" for now (waiting for ledger aggregation).
        
        TODO: Once ledger aggregation is implemented, query the ledger
        to sum all debit entries for this goal.
        
        Example implementation:
        ```python
        from core_apps.ledger.models import LedgerEntry
        total = LedgerEntry.objects.filter(
            goal=obj,
            entry_type='DEBIT'
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        return str(total)
        ```
        """
        return "0.00"
    
    def get_progress_percent(self, obj):
        """
        Calculate progress as percentage of target.
        
        Formula: (total_contributed / target_amount) * 100
        
        Returns: integer 0-100 (clamped at 100 if over-contributed)
        
        TODO: Update to use actual total_contributed once ledger aggregation is available.
        """
        total_contributed = Decimal(self.get_total_contributed(obj))
        
        if obj.target_amount <= 0:
            return 0
        
        progress = (total_contributed / obj.target_amount) * 100
        
        # Clamp between 0 and 100
        progress_percent = int(min(100, max(0, progress)))
        return progress_percent
