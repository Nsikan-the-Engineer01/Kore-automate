"""
ViewSets for Transaction model.

Provides read-only API for transaction ledger with filtering, pagination, and proper serialization.
"""

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Prefetch, Sum, Q, DecimalField
from django.db.models.functions import Coalesce
from .models import Transaction
from .serializers import (
    TransactionListSerializer,
    TransactionDetailSerializer
)
from .filters import TransactionFilter, TransactionFilterBackend

try:
    from django_filters.rest_framework import DjangoFilterBackend
    HAS_DJANGO_FILTER = True
except ImportError:
    HAS_DJANGO_FILTER = False


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Transaction model (read-only, append-only ledger).
    
    Provides list and retrieve endpoints for transactions with:
    - User-scoped filtering (only see own transactions)
    - Advanced filtering (goal, status, type, date range)
    - Pagination (DRF settings)
    - Proper serialization (list vs detail)
    
    Endpoints:
    - GET /api/v1/transactions/ - List user's transactions
    - GET /api/v1/transactions/{id}/ - Get transaction details
    
    Query Parameters:
    - goal_id: Filter by goal UUID
    - status: Filter by status (PENDING, SUCCESS, FAILED)
    - type: Filter by type (CREDIT, DEBIT, FEE)
    - from_date: Filter from date (ISO format)
    - to_date: Filter to date (ISO format)
    - collection_id: Filter by collection UUID
    - ordering: Order results (-occurred_at default)
    
    Example Requests:
    - GET /api/v1/transactions/
    - GET /api/v1/transactions/?status=SUCCESS
    - GET /api/v1/transactions/?goal_id=550e8400-...
    - GET /api/v1/transactions/?type=CREDIT&status=SUCCESS
    - GET /api/v1/transactions/?from_date=2026-01-01&to_date=2026-01-31
    """
    
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    ordering = ['-occurred_at']  # Newest first
    ordering_fields = ['occurred_at', 'amount', 'created_at']
    
    # Setup filtering backends
    if HAS_DJANGO_FILTER:
        filter_backends = [DjangoFilterBackend]
        filterset_class = TransactionFilter
    else:
        filter_backends = [TransactionFilterBackend]
    
    def get_queryset(self):
        """
        Return transactions filtered to current user.
        
        Optimizes with select_related for goal and collection to avoid N+1 queries.
        
        Returns:
            QuerySet: Transactions belonging to authenticated user
        """
        return Transaction.objects.filter(
            user=self.request.user
        ).select_related(
            'goal',
            'collection'
        ).order_by(*self.ordering)
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        
        Returns:
            Serializer class: List serializer for list, detail for retrieve
        """
        if self.action == 'retrieve':
            return TransactionDetailSerializer
        return TransactionListSerializer
    
    def list(self, request, *args, **kwargs):
        """
        List transactions with filtering and pagination.
        
        Applies filters from query parameters and returns paginated results.
        
        Args:
            request: HTTP request
            
        Returns:
            Response: Paginated list of transactions
        """
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single transaction.
        
        Returns full transaction details with all fields.
        
        Args:
            request: HTTP request
            
        Returns:
            Response: Transaction details
            
        Status Codes:
            200 OK: Transaction retrieved
            404 Not Found: Transaction not found
        """
        return super().retrieve(request, *args, **kwargs)    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def summary(self, request):
        """
        Get transaction summary for authenticated user.
        
        Returns aggregated totals for successful transactions:
        - total_debits_success: Sum of all successful DEBIT transactions
        - total_credits_success: Sum of all successful CREDIT transactions
        - total_fees_success: Sum of all successful FEE transactions
        
        Optionally group by goal if goal_id query parameter provided.
        
        Query Parameters:
        - goal_id: Optional UUID to get summary for specific goal
        
        Returns:
            Response: Summary with aggregated amounts
            
        Example:
            GET /api/v1/transactions/summary/
            GET /api/v1/transactions/summary/?goal_id=550e8400-...
        """
        queryset = self.get_queryset().filter(status='SUCCESS')
        
        # Filter by goal if provided
        goal_id = request.query_params.get('goal_id')
        if goal_id:
            queryset = queryset.filter(goal_id=goal_id)
        
        # Aggregate by type
        summary = queryset.aggregate(
            total_debits_success=Coalesce(
                Sum('amount', filter=Q(type='DEBIT'), output_field=DecimalField()),
                0,
                output_field=DecimalField()
            ),
            total_credits_success=Coalesce(
                Sum('amount', filter=Q(type='CREDIT'), output_field=DecimalField()),
                0,
                output_field=DecimalField()
            ),
            total_fees_success=Coalesce(
                Sum('amount', filter=Q(type='FEE'), output_field=DecimalField()),
                0,
                output_field=DecimalField()
            )
        )
        
        return Response(summary, status=status.HTTP_200_OK)