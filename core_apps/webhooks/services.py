import logging
import hashlib
import hmac
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

from django.utils import timezone
from django.conf import settings
from django.db import IntegrityError

from .models import WebhookEvent
from .idempotency import IdempotencyChecker, processing_lock, IdempotentCollectionUpdate
from .utils import extract_event_id
from core_apps.collections.services import CollectionsService, CollectionError
from core_apps.integrations.paywithaccount.client import PayWithAccountError

logger = logging.getLogger(__name__)


class WebhookError(Exception):
    """Exception raised for webhook-related errors."""
    pass


class PayloadParser:
    """
    Tolerant parser for extracting transaction data from various provider payloads.
    
    Supports:
    - PayWithAccount (OnePipe) response structure
    - Generic transaction webhooks
    """
    
    @staticmethod
    def extract_from_payload(
        payload: Dict[str, Any],
        provider: str = "paywithaccount"
    ) -> Dict[str, Optional[str]]:
        """
        Extract request_ref, provider_ref, and status from webhook payload.
        
        Tolerant parsing: tries multiple paths for each field.
        
        Args:
            payload: Webhook payload dictionary
            provider: Provider name (affects path lookup)
            
        Returns:
            Dict with keys: request_ref, provider_ref, status
        """
        
        if provider.lower() in ["paywithaccount", "onepipe"]:
            return PayloadParser._extract_paywithaccount(payload)
        else:
            # Generic extraction
            return PayloadParser._extract_generic(payload)
    
    @staticmethod
    def _extract_paywithaccount(payload: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """Extract from PayWithAccount/OnePipe payload."""
        
        # request_ref can be in multiple places
        request_ref = (
            payload.get("request_ref")
            or payload.get("requestRef")
            or payload.get("ref")
            or payload.get("reference")
            or payload.get("meta", {}).get("request_ref")
        )
        
        # provider_ref (transaction reference from provider)
        provider_ref = (
            payload.get("provider_ref")
            or payload.get("providerRef")
            or payload.get("transaction_ref")
            or payload.get("transactionRef")
            or payload.get("reference")
            or payload.get("txRef")
            or payload.get("data", {}).get("reference")
        )
        
        # status
        status = (
            payload.get("status")
            or payload.get("transaction", {}).get("status")
            or payload.get("data", {}).get("status")
            or "unknown"
        )
        
        return {
            "request_ref": request_ref,
            "provider_ref": provider_ref,
            "status": status
        }
    
    @staticmethod
    def _extract_generic(payload: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """Generic extraction for unknown providers."""
        
        request_ref = (
            payload.get("request_ref")
            or payload.get("requestRef")
            or payload.get("ref")
            or payload.get("id")
        )
        
        provider_ref = (
            payload.get("provider_ref")
            or payload.get("providerRef")
            or payload.get("transaction_ref")
            or payload.get("reference")
        )
        
        status = payload.get("status", "unknown")
        
        return {
            "request_ref": request_ref,
            "provider_ref": provider_ref,
            "status": status
        }


class WebhookService:
    """Service for handling incoming webhook events."""
    
    def __init__(self):
        self.collections_service = CollectionsService()
        self.webhook_secret = getattr(settings, 'PWA_WEBHOOK_SECRET', '')
    
    def verify_signature(
        self,
        payload_str: str,
        signature_header: str,
        provider: str = "paywithaccount"
    ) -> bool:
        """
        Verify webhook signature (if configured).
        
        Args:
            payload_str: Raw payload string
            signature_header: Signature from webhook header
            provider: Provider name (for signature scheme selection)
            
        Returns:
            True if signature valid or no secret configured; False if invalid
        """
        
        if not self.webhook_secret:
            logger.debug("No webhook secret configured; skipping signature verification")
            return True
        
        if provider.lower() in ["paywithaccount", "onepipe"]:
            # OnePipe uses HMAC-SHA256 typically
            computed = hmac.new(
                self.webhook_secret.encode(),
                payload_str.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(computed, signature_header)
        
        return True
    
    def receive_event(
        self,
        provider: str,
        payload: Dict[str, Any],
        signature_header: Optional[str] = None,
        request_ref: Optional[str] = None,
        event_id: Optional[str] = None,
        payload_str: Optional[str] = None
    ) -> WebhookEvent:
        """
        Receive and store incoming webhook event.
        
        Implements deduplication: if event_id is present and already processed,
        returns existing WebhookEvent without reprocessing.
        
        Stores event as RECEIVED, then enqueues async processing if Celery is
        available; otherwise processes inline.
        
        Args:
            provider: Provider name (e.g., "paywithaccount")
            payload: Webhook payload dictionary
            signature_header: Optional signature for verification
            request_ref: Optional request reference (may also be in payload)
            event_id: Optional event ID (may also be in payload)
            payload_str: Raw payload string for signature verification
            
        Returns:
            WebhookEvent instance (existing if duplicate, new if first occurrence)
            
        Raises:
            WebhookError: If signature verification fails
        """
        
        # Verify signature if provided
        if signature_header and payload_str:
            if not self.verify_signature(payload_str, signature_header, provider):
                logger.error(f"Webhook signature verification failed for provider={provider}")
                raise WebhookError("Webhook signature verification failed")
        
        # Extract identifiers from payload if not provided
        extracted = PayloadParser.extract_from_payload(payload, provider)
        if not request_ref and extracted["request_ref"]:
            request_ref = extracted["request_ref"]
        if not event_id:
            event_id = extract_event_id(payload)  # Try to extract event_id
        
        logger.info(
            f"Receiving webhook: provider={provider}, request_ref={request_ref}, "
            f"event_id={event_id}"
        )
        
        # Check for duplicate event_id (idempotency)
        if event_id:
            try:
                existing_event = WebhookEvent.objects.get(event_id=event_id)
                logger.info(
                    f"Duplicate webhook event detected: event_id={event_id}, "
                    f"existing_event={existing_event.id}, status={existing_event.status}"
                )
                return existing_event
            except WebhookEvent.DoesNotExist:
                pass  # First occurrence, proceed normally
        
        # Store webhook event
        try:
            webhook_event = WebhookEvent.objects.create(
                provider=provider,
                event_id=event_id,
                request_ref=request_ref,
                payload=payload,
                signature=signature_header or '',
                status='RECEIVED'
            )
        except IntegrityError as e:
            # Rare race condition: event_id uniqueness violation
            # This can happen if two identical events arrive simultaneously
            if event_id:
                logger.warning(
                    f"Race condition: IntegrityError creating webhook event with "
                    f"event_id={event_id}: {str(e)}"
                )
                # Try to fetch the existing event
                try:
                    webhook_event = WebhookEvent.objects.get(event_id=event_id)
                    return webhook_event
                except WebhookEvent.DoesNotExist:
                    raise
            else:
                raise
        
        logger.info(f"Stored webhook event: {webhook_event.id}")
        
        # Try to process async with Celery, fall back to sync
        try:
            from core_apps.webhooks.tasks import process_webhook_event_task
            
            logger.debug(f"Enqueueing async webhook processing: {webhook_event.id}")
            process_webhook_event_task.delay(webhook_event.id)
        except (ImportError, AttributeError):
            logger.debug(
                "Celery not configured or task not found; processing webhook inline"
            )
            self.process_event(webhook_event.id)
        
        return webhook_event

    def receive_paywithaccount_event(
        self,
        payload: Dict[str, Any],
        signature: Optional[str] = None
    ) -> WebhookEvent:
        """
        Receive a PayWithAccount webhook event (specialized convenience method).

        This is a thin wrapper that extracts a best-effort `request_ref`, stores
        the `WebhookEvent` with provider="paywithaccount" and enqueues processing
        via Celery if available, otherwise processes inline.
        """
        # Best-effort extraction of request_ref from payload
        extracted = PayloadParser._extract_paywithaccount(payload)
        request_ref = extracted.get("request_ref")

        # Create event
        webhook_event = WebhookEvent.objects.create(
            provider="paywithaccount",
            request_ref=request_ref,
            payload=payload,
            signature=signature or '',
            status='RECEIVED'
        )

        logger.info(f"Stored PayWithAccount webhook event: {webhook_event.id}")

        # Enqueue or process inline
        try:
            from core_apps.webhooks.tasks import process_webhook_event_task
            logger.debug(f"Enqueueing async webhook processing: {webhook_event.id}")
            process_webhook_event_task.delay(webhook_event.id)
        except (ImportError, AttributeError):
            logger.debug("Celery not configured; processing PayWithAccount webhook inline")
            # Call the processing method inline
            try:
                self.process_webhook_event(webhook_event.id)
            except Exception:
                # process_webhook_event will handle marking FAILED and logging
                pass

        return webhook_event
    
    def process_event(self, webhook_event_id: str) -> WebhookEvent:
        """
        Process stored webhook event: parse payload, update collection, mark processed.
        
        Implements idempotency:
        1. Acquires processing lock (Redis or DB fallback) for the request_ref
        2. Validates that status update won't overwrite terminal states (SUCCESS/FAILED)
        3. Skips update if collection already in terminal state with different status
        
        Args:
            webhook_event_id: WebhookEvent primary key (UUID)
            
        Returns:
            Updated WebhookEvent instance
            
        Raises:
            WebhookError: If event not found or processing fails
        """
        
        try:
            webhook_event = WebhookEvent.objects.get(id=webhook_event_id)
        except WebhookEvent.DoesNotExist:
            raise WebhookError(f"WebhookEvent not found: {webhook_event_id}")
        
        logger.info(f"Processing webhook event: {webhook_event.id}")
        
        try:
            # Parse payload
            payload = webhook_event.payload
            extracted = PayloadParser.extract_from_payload(payload, webhook_event.provider)
            
            request_ref = extracted.get("request_ref")
            provider_ref = extracted.get("provider_ref")
            status = extracted.get("status")
            
            logger.debug(
                f"Parsed webhook: request_ref={request_ref}, "
                f"provider_ref={provider_ref}, status={status}"
            )
            
            # Validate required fields
            if not request_ref:
                raise WebhookError("Could not extract request_ref from webhook payload")
            
            if not status:
                logger.warning("Could not extract status from webhook; defaulting to 'pending'")
                status = "pending"
            
            # Acquire processing lock to prevent race conditions
            lock_key = f"webhook_processing:{request_ref}"
            try:
                with processing_lock(lock_key, timeout=30, wait_timeout=10):
                    # Update collection via CollectionsService (with idempotency checks)
                    collection = self.collections_service.update_collection_from_webhook(
                        request_ref=request_ref,
                        provider_ref=provider_ref or "",
                        new_status=status,
                        payload=payload,
                        response_body=None
                    )
                    
                    logger.info(
                        f"Successfully processed webhook: collection={collection.id}, "
                        f"status={collection.status}"
                    )
            except Exception as lock_err:
                logger.warning(f"Lock acquisition failed, proceeding without lock: {lock_err}")
                # Proceed without lock (DB fallback will still protect via idempotency)
                collection = self.collections_service.update_collection_from_webhook(
                    request_ref=request_ref,
                    provider_ref=provider_ref or "",
                    new_status=status,
                    payload=payload,
                    response_body=None
                )
            
            # Mark webhook event as processed
            webhook_event.status = 'PROCESSED'
            webhook_event.processed_at = timezone.now()
            webhook_event.save(update_fields=['status', 'processed_at'])

            return webhook_event

        except CollectionError as e:
            logger.error(f"CollectionError processing webhook {webhook_event.id}: {str(e)}")
            webhook_event.status = 'FAILED'
            webhook_event.error = f"CollectionError: {str(e)}"
            webhook_event.processed_at = timezone.now()
            webhook_event.save(update_fields=['status', 'error', 'processed_at'])
            return webhook_event

        except PayWithAccountError as e:
            logger.error(f"PayWithAccountError processing webhook {webhook_event.id}: {str(e)}")
            webhook_event.status = 'FAILED'
            webhook_event.error = f"PayWithAccountError: {str(e)}"
            webhook_event.processed_at = timezone.now()
            webhook_event.save(update_fields=['status', 'error', 'processed_at'])
            return webhook_event

        except Exception as e:
            logger.error(
                f"Unexpected error processing webhook {webhook_event.id}: {str(e)}",
                exc_info=True
            )
            webhook_event.status = 'FAILED'
            webhook_event.error = f"Unexpected error: {str(e)}"
            webhook_event.processed_at = timezone.now()
            webhook_event.save(update_fields=['status', 'error', 'processed_at'])
            return webhook_event

    def process_webhook_event(self, event_id: str) -> WebhookEvent:
        """
        Process a webhook event by id.

        Loads the WebhookEvent, parses payload tolerantly for `request_ref`,
        `provider_ref`, and status, calls into the collections service to update
        the collection, and marks the WebhookEvent as PROCESSED (or FAILED on error).
        """
        # Delegate to existing processing implementation
        return self.process_event(event_id)
