import logging
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes

from core_apps.webhooks.models import WebhookEvent
from core_apps.webhooks.services import WebhookService, WebhookError
from core_apps.webhooks.serializers import WebhookEventSerializer

logger = logging.getLogger(__name__)


class PayWithAccountWebhookView(APIView):
    """
    Webhook endpoint for PayWithAccount payment provider.
    
    Accepts webhook payloads without authentication.
    Verifies signature if spec is available, otherwise stores header for manual verification.
    Returns 200 immediately after storing event, processing happens asynchronously.
    
    POST /api/v1/webhooks/paywithaccount/
    Headers:
        - Signature: HMAC-SHA256 signature (optional)
        - X-Kore-Signature: Alternative signature header (optional)
    
    Request Body:
        {
            "request_ref": "abc123",
            "status": "success",
            "reference": "pwa123",
            ...other fields
        }
    
    Response:
        200 OK
        {
            "id": "webhook-event-uuid",
            "status": "RECEIVED",
            "received_at": "2026-01-29T10:30:00Z"
        }
    """
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        """
        Receive webhook event from PayWithAccount.
        
        Steps:
        1. Extract signature from headers (if available)
        2. Store raw payload and signature in WebhookEvent
        3. Call WebhookService.receive_event() for async processing
        4. Return 200 immediately
        
        The actual event processing (signature verification, status update)
        happens asynchronously via Celery or sync fallback.
        """
        # Get signature from multiple possible header names
        signature = (
            request.headers.get('Signature') or
            request.headers.get('X-Kore-Signature') or
            request.headers.get('X-Signature') or
            ''
        )
        
        # Extract request body as JSON
        payload = request.data or {}

        # Initialize webhook service and store/enqueue processing
        service = WebhookService()

        try:
            # Use the convenience method for PayWithAccount events. It stores the
            # event and enqueues processing (or falls back). We do not wait for
            # processing here — return immediately to acknowledge receipt.
            service.receive_paywithaccount_event(payload=payload, signature=signature)
        except Exception as e:
            # Log but do not block or fail the request — return 200 to the provider
            # so they don't retry excessively. The service will record the event
            # and any error for later inspection.
            logger.exception("Error receiving PayWithAccount webhook: %s", e)

        # Acknowledge receipt immediately
        return Response({"status": "received"}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def webhook_paywithaccount(request):
    """
    Function-based view alternative for webhook endpoint.
    
    This is simpler alternative to the class-based view.
    Can be used if preferred.
    """
    view = PayWithAccountWebhookView()
    return view.post(request)
