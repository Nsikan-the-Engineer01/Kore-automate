"""
Filters for Transaction model.

Provides filtering by goal, status, type, and date range.
Supports both django-filter backend and manual filtering.
"""

from django_filters import rest_framework as filters
from django.db.models import Q
from datetime import datetime
from .models import Transaction


class TransactionFilter(filters.FilterSet):
    """
    FilterSet for Transaction model.
    
    Supports filtering by:
    - goal_id: UUID of associated goal
    - status: PENDING, SUCCESS, or FAILED
    - type: CREDIT, DEBIT, or FEE
    - from_date: ISO datetime or date (inclusive)
    - to_date: ISO datetime or date (inclusive)
    
    Default ordering: -occurred_at (newest first)
    """
    
    # Goal filter by UUID
    goal_id = filters.UUIDFilter(
        field_name='goal__id',
        label='Goal ID',
        help_text='Filter by goal UUID'
    )
    
    # Status filter
    status = filters.ChoiceFilter(
        choices=Transaction.STATUS_CHOICES,
        label='Transaction Status',
        help_text='Filter by status: PENDING, SUCCESS, FAILED'
    )
    
    # Type filter
    type = filters.ChoiceFilter(
        choices=Transaction.TYPE_CHOICES,
        label='Transaction Type',
        help_text='Filter by type: CREDIT, DEBIT, FEE'
    )
    
    # Date range filters
    from_date = filters.IsoDateTimeFilter(
        field_name='occurred_at',
        lookup_expr='gte',
        label='From Date',
        help_text='ISO datetime or date (inclusive)'
    )
    
    to_date = filters.IsoDateTimeFilter(
        field_name='occurred_at',
        lookup_expr='lte',
        label='To Date',
        help_text='ISO datetime or date (inclusive)'
    )
    
    # Collection filter by UUID
    collection_id = filters.UUIDFilter(
        field_name='collection__id',
        label='Collection ID',
        help_text='Filter by collection UUID'
    )
    
    class Meta:
        model = Transaction
        fields = ['goal_id', 'status', 'type', 'from_date', 'to_date', 'collection_id']
    
    class ordering:
        """Default ordering by occurred_at descending (newest first)."""
        fields = [
            ('occurred_at', 'Newest First'),
            ('-occurred_at', 'Oldest First'),
            ('amount', 'Amount Low to High'),
            ('-amount', 'Amount High to Low'),
            ('created_at', 'Created Oldest First'),
            ('-created_at', 'Created Newest First'),
        ]
        fields_map = {
            'occurred_at': 'occurred_at',
        }


class TransactionFilterBackend:
    """
    Manual filter backend for Transaction model (fallback if django-filter not available).
    
    Supports filtering by:
    - goal_id: UUID
    - status: PENDING, SUCCESS, FAILED
    - type: CREDIT, DEBIT, FEE
    - from_date: ISO datetime
    - to_date: ISO datetime
    - collection_id: UUID
    """
    
    def filter_queryset(self, request, queryset, view):
        """
        Apply filters from query parameters.
        
        Args:
            request: HTTP request object
            queryset: Initial queryset
            view: View instance
            
        Returns:
            QuerySet: Filtered queryset
        """
        params = request.query_params
        
        # Filter by goal_id
        if 'goal_id' in params:
            goal_id = params.get('goal_id')
            queryset = queryset.filter(goal__id=goal_id)
        
        # Filter by status
        if 'status' in params:
            status = params.get('status').upper()
            if status in dict(Transaction.STATUS_CHOICES):
                queryset = queryset.filter(status=status)
        
        # Filter by type
        if 'type' in params:
            type_val = params.get('type').upper()
            if type_val in dict(Transaction.TYPE_CHOICES):
                queryset = queryset.filter(type=type_val)
        
        # Filter by from_date
        if 'from_date' in params:
            try:
                from_date = datetime.fromisoformat(params.get('from_date'))
                queryset = queryset.filter(occurred_at__gte=from_date)
            except (ValueError, TypeError):
                pass  # Invalid date format, skip filter
        
        # Filter by to_date
        if 'to_date' in params:
            try:
                to_date = datetime.fromisoformat(params.get('to_date'))
                queryset = queryset.filter(occurred_at__lte=to_date)
            except (ValueError, TypeError):
                pass  # Invalid date format, skip filter
        
        # Filter by collection_id
        if 'collection_id' in params:
            collection_id = params.get('collection_id')
            queryset = queryset.filter(collection__id=collection_id)
        
        return queryset
