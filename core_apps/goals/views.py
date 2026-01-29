from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Sum, F
from decimal import Decimal
from .models import Goal
from core_apps.transactions.models import Transaction
from .serializers import (
    GoalCreateSerializer,
    GoalUpdateSerializer,
    GoalDetailSerializer
)
from .permissions import IsOwner


class GoalViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Goal CRUD operations and custom status actions.
    
    Provides standard CRUD operations (Create, Retrieve, Update) plus
    custom actions for pausing and resuming goals.
    
    Routes:
    - GET/POST /api/v1/goals/
    - GET/PATCH /api/v1/goals/{id}/
    - POST /api/v1/goals/{id}/pause/
    - POST /api/v1/goals/{id}/resume/
    
    Permissions:
    - IsAuthenticated: User must be logged in
    - IsOwner: User must own the goal
    
    Serializers:
    - create/post: GoalCreateSerializer
    - update/patch: GoalUpdateSerializer
    - retrieve/list: GoalDetailSerializer
    """
    
    permission_classes = [IsAuthenticated, IsOwner]
    lookup_field = 'id'
    ordering = ['-created_at']  # Newest first
    
    def get_queryset(self):
        """
        Return goals filtered to current user only.
        
        Returns:
            QuerySet: Goals belonging to the authenticated user
        """
        return Goal.objects.filter(user=self.request.user).order_by(*self.ordering)
    
    def get_serializer_class(self):
        """
        Return the appropriate serializer class based on the action.
        
        Returns:
            Serializer class: One of Create, Update, or Detail serializers
        """
        if self.action == 'create':
            return GoalCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return GoalUpdateSerializer
        else:  # retrieve, list, pause, resume, etc.
            return GoalDetailSerializer
    
    def get_serializer_context(self):
        """
        Add request to serializer context (required for GoalCreateSerializer).
        
        Returns:
            dict: Context dict with request object
        """
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsOwner])
    def pause(self, request, id=None):
        """
        Pause a goal (only if currently ACTIVE).
        
        Sets goal status to PAUSED. Only works if goal is in ACTIVE state.
        
        Args:
            request: HTTP request object
            id: Goal ID (UUID)
            
        Returns:
            Response: Updated goal detail serialized, or error message
            
        Status Codes:
            200 OK: Goal paused successfully
            400 Bad Request: Goal not in ACTIVE state
            403 Forbidden: User does not own goal
            404 Not Found: Goal not found
        """
        goal = self.get_object()
        
        if goal.status != 'ACTIVE':
            return Response(
                {
                    'detail': f"Can only pause ACTIVE goals. Current status: {goal.status}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        goal.status = 'PAUSED'
        goal.save()
        
        serializer = self.get_serializer(goal)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsOwner])
    def resume(self, request, id=None):
        """
        Resume a goal (only if currently PAUSED).
        
        Sets goal status back to ACTIVE. Only works if goal is in PAUSED state.
        
        Args:
            request: HTTP request object
            id: Goal ID (UUID)
            
        Returns:
            Response: Updated goal detail serialized, or error message
            
        Status Codes:
            200 OK: Goal resumed successfully
            400 Bad Request: Goal not in PAUSED state
            403 Forbidden: User does not own goal
            404 Not Found: Goal not found
        """
        goal = self.get_object()
        
        if goal.status != 'PAUSED':
            return Response(
                {
                    'detail': f"Can only resume PAUSED goals. Current status: {goal.status}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        goal.status = 'ACTIVE'
        goal.save()
        
        serializer = self.get_serializer(goal)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsOwner])
    def summary(self, request, id=None):
        """
        Get goal summary with transaction aggregations.
        
        Returns goal details plus aggregated transaction data:
        - total_contributed: Sum of successful CREDIT transactions
        - total_debited: Sum of successful DEBIT transactions
        - total_fees: Sum of successful FEE transactions
        - progress_percent: (total_contributed / target_amount) * 100, capped at 100
        
        Args:
            request: HTTP request object
            id: Goal ID (UUID)
            
        Returns:
            Response: Goal detail with transaction summaries
            
        Status Codes:
            200 OK: Summary retrieved successfully
            403 Forbidden: User does not own goal
            404 Not Found: Goal not found
        """
        goal = self.get_object()
        
        # Aggregate transactions efficiently with single database query
        transaction_summary = Transaction.objects.filter(
            goal=goal,
            status='SUCCESS'
        ).aggregate(
            total_contributed=Sum('amount', filter=Q(type='CREDIT')),
            total_debited=Sum('amount', filter=Q(type='DEBIT')),
            total_fees=Sum('amount', filter=Q(type='FEE'))
        )
        
        # Handle null values (no transactions)
        total_contributed = transaction_summary['total_contributed'] or Decimal('0.00')
        total_debited = transaction_summary['total_debited'] or Decimal('0.00')
        total_fees = transaction_summary['total_fees'] or Decimal('0.00')
        
        # Calculate progress percent (capped at 100)
        if goal.target_amount > 0:
            progress_percent = min(
                int((total_contributed / goal.target_amount) * 100),
                100
            )
        else:
            progress_percent = 0
        
        # Get goal detail serializer data
        serializer = self.get_serializer(goal)
        data = serializer.data
        
        # Add transaction summary fields
        data['total_contributed'] = str(total_contributed)
        data['total_debited'] = str(total_debited)
        data['total_fees'] = str(total_fees)
        data['progress_percent'] = progress_percent
        
        return Response(data, status=status.HTTP_200_OK)

