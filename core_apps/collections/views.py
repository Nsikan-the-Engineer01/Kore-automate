from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction

from core_apps.collections.models import Collection
from core_apps.collections.serializers import (
    CollectionCreateSerializer,
    CollectionSerializer,
    CollectionCreateResponseSerializer,
    CollectionValidateSerializer,
    CollectionStatusResponseSerializer
)
from core_apps.collections.services import CollectionsService, CollectionError
from core_apps.goals.models import Goal


class IsOwner(permissions.BasePermission):
    """Permission to check if user owns the collection."""
    
    def has_object_permission(self, request, view, obj):
        """Allow access only if user owns the collection."""
        return obj.user == request.user


class CollectionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing collections.
    
    Endpoints:
    - POST /api/v1/collections/ - Create collection
    - GET /api/v1/collections/ - List user's collections
    - GET /api/v1/collections/{id}/ - Retrieve collection details
    """
    
    serializer_class = CollectionSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    lookup_field = 'id'
    
    def get_queryset(self):
        """Return collections for the authenticated user."""
        return Collection.objects.filter(user=self.request.user).order_by('-created_at')
    
    def get_serializer_class(self):
        """Use different serializer for create requests."""
        if self.action == 'create':
            return CollectionCreateSerializer
        return CollectionSerializer
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Create a new collection.
        
        Request body:
        {
            "goal_id": "uuid",
            "amount_allocation": 10000.00,
            "currency": "NGN",  # optional, defaults to NGN
            "narrative": "Monthly savings"  # optional
        }
        
        Response: Collection object with request_ref, status, and fees
        """
        # Validate input
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Extract validated data
        goal_id = serializer.validated_data.get('goal_id')
        amount_allocation = serializer.validated_data['amount_allocation']
        currency = serializer.validated_data.get('currency', 'NGN')
        narrative = serializer.validated_data.get('narrative', '')
        
        # Resolve goal if provided
        goal = None
        if goal_id:
            try:
                goal = Goal.objects.get(id=goal_id)
            except Goal.DoesNotExist:
                return Response({'error': 'Goal not found'}, status=status.HTTP_404_NOT_FOUND)

            # Verify user owns the goal
            if goal.user != request.user:
                return Response({'error': 'You do not have permission to use this goal'}, status=status.HTTP_403_FORBIDDEN)
        
        # Call service to create collection
        try:
            service = CollectionsService()
            collection = service.create_collection(
                user=request.user,
                goal=goal,
                amount_allocation=amount_allocation,
                currency=currency,
                narrative=narrative
            )
        except CollectionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to create collection: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Serialize and return using response serializer (includes validation flag)
        output_serializer = CollectionCreateResponseSerializer(collection)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)
    
    def list(self, request, *args, **kwargs):
        """
        List all collections for the authenticated user.
        
        Query parameters:
        - status: Filter by status (PENDING, INITIATED, SUCCESS, FAILED, CANCELLED)
        - ordering: -created_at (default), created_at, status, amount_total
        """
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single collection by ID.
        
        Returns full collection details including request_ref, provider info, and raw request/response.
        """
        return super().retrieve(request, *args, **kwargs)
    
    @action(detail=True, methods=['get'])
    def status(self, request, id=None):
        """
        Get the current status of a collection.
        
        Returns minimal response with just id, status, and updated_at.
        """
        collection = self.get_object()
        return Response({
            'id': collection.id,
            'status': collection.status,
            'updated_at': collection.updated_at
        })    
    @transaction.atomic
    @action(detail=True, methods=['post'])
    def validate(self, request, id=None):
        """
        Submit validation (OTP, challenge response, etc.) for a collection.
        
        Request body:
        {
            "otp": "123456",
            // Additional provider-specific fields as needed
        }
        
        Response: Updated Collection with current status and validation state
        
        Only available for collections in PENDING state with requires_validation=true.
        """
        collection = self.get_object()
        
        # Parse and validate input
        serializer = CollectionValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        otp = serializer.validated_data.get('otp')
        # Additional fields can be extracted from request.data for provider-specific needs
        extra_fields = {k: v for k, v in request.data.items() if k != 'otp'}
        
        try:
            service = CollectionsService()
            updated_collection = service.validate_collection(
                collection=collection,
                otp=otp,
                extra_fields=extra_fields
            )
        except CollectionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Validation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Serialize and return updated collection
        output_serializer = CollectionStatusResponseSerializer(updated_collection)
        return Response(output_serializer.data, status=status.HTTP_200_OK)
    
    @transaction.atomic
    @action(detail=True, methods=['get'])
    def query_status(self, request, id=None):
        """
        Query current status of a collection from provider.
        
        Makes best-effort query using collection's provider_ref or request_ref.
        Updates collection if status has changed.
        
        Response: Updated Collection with latest status from provider
        """
        collection = self.get_object()
        
        try:
            service = CollectionsService()
            updated_collection = service.query_collection_status(collection)
        except CollectionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Status query failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Serialize and return updated collection
        output_serializer = CollectionStatusResponseSerializer(updated_collection)
        return Response(output_serializer.data, status=status.HTTP_200_OK)