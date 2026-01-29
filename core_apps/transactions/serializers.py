"""
Serializers for Transaction model.

Provides TransactionListSerializer for list views and TransactionDetailSerializer
for detail views. Both include computed fields for UI and proper decimal handling.
"""

from rest_framework import serializers
from decimal import Decimal
from .models import Transaction


class GoalMinimalSerializer(serializers.Serializer):
    """Minimal Goal serializer for nested representation."""
    id = serializers.UUIDField()
    name = serializers.CharField()


class CollectionMinimalSerializer(serializers.Serializer):
    """Minimal Collection serializer for reference."""
    id = serializers.UUIDField()


class TransactionListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing transactions.
    
    Includes core transaction fields, nested goal/collection references,
    and a computed 'title' field for UI display.
    
    Fields:
    - id: Transaction UUID
    - type: DEBIT, CREDIT, or FEE
    - amount: Decimal as string
    - currency: 3-letter currency code
    - status: PENDING, SUCCESS, or FAILED
    - title: Human-readable type label (computed)
    - goal: Nested minimal goal object with id and name
    - collection: Minimal collection reference (id only)
    - request_ref: Request reference identifier
    - provider_ref: Provider reference (if available)
    - occurred_at: Timestamp when transaction occurred
    - created_at: Record creation timestamp
    - updated_at: Last update timestamp
    - metadata: Additional transaction metadata
    """
    
    # Nested serializers
    goal = GoalMinimalSerializer(read_only=True)
    collection = CollectionMinimalSerializer(read_only=True)
    
    # Computed field for UI
    title = serializers.SerializerMethodField()
    
    class Meta:
        model = Transaction
        fields = [
            'id',
            'type',
            'amount',
            'currency',
            'status',
            'title',
            'goal',
            'collection',
            'request_ref',
            'provider_ref',
            'occurred_at',
            'created_at',
            'updated_at',
            'metadata'
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at'
        ]
    
    def get_title(self, obj):
        """
        Generate human-readable title from transaction type.
        
        Args:
            obj: Transaction instance
            
        Returns:
            str: Human-readable title ("Debit", "Credit", or "Kore Fee")
        """
        type_map = {
            'DEBIT': 'Debit',
            'CREDIT': 'Credit',
            'FEE': 'Kore Fee'
        }
        return type_map.get(obj.type, obj.type)


class TransactionDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for transaction detail view.
    
    Includes all list fields plus additional context for detail pages.
    Does not expose sensitive information like secrets or internal references.
    
    Inherits from TransactionListSerializer to include all list fields.
    """
    
    # Nested serializers
    goal = GoalMinimalSerializer(read_only=True)
    collection = CollectionMinimalSerializer(read_only=True)
    
    # Computed field for UI
    title = serializers.SerializerMethodField()
    
    class Meta:
        model = Transaction
        fields = [
            'id',
            'type',
            'amount',
            'currency',
            'status',
            'title',
            'goal',
            'collection',
            'request_ref',
            'provider_ref',
            'occurred_at',
            'created_at',
            'updated_at',
            'metadata'
        ]
        read_only_fields = [
            'id',
            'type',
            'amount',
            'currency',
            'status',
            'goal',
            'collection',
            'request_ref',
            'provider_ref',
            'occurred_at',
            'created_at',
            'updated_at',
            'metadata'
        ]
    
    def get_title(self, obj):
        """
        Generate human-readable title from transaction type.
        
        Args:
            obj: Transaction instance
            
        Returns:
            str: Human-readable title ("Debit", "Credit", or "Kore Fee")
        """
        type_map = {
            'DEBIT': 'Debit',
            'CREDIT': 'Credit',
            'FEE': 'Kore Fee'
        }
        return type_map.get(obj.type, obj.type)
