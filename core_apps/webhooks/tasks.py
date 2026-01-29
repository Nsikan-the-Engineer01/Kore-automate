"""
Celery tasks for webhook processing.

Defines a retrying task that delegates to WebhookService.process_webhook_event.
If Celery isn't used, the service will still function via inline processing.
"""
import logging

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from core_apps.webhooks.services import WebhookService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=5, default_retry_delay=30)
def process_webhook_event_task(self, event_id: str):
    """
    Celery task to process a webhook event by id.

    Retries up to `max_retries` on exceptions. Uses WebhookService.process_webhook_event
    to perform the actual work; that method will mark the WebhookEvent as PROCESSED
    or FAILED as appropriate.
    """
    service = WebhookService()
    try:
        return service.process_webhook_event(event_id)
    except Exception as exc:
        logger.exception("Error processing webhook event %s: %s", event_id, exc)
        try:
            # Retry with the caught exception
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for webhook event %s", event_id)
            # Let the exception bubble so task is recorded as failed
            raise


# Backwards-compatible alias in case other modules import the non-_task name
process_webhook_event = process_webhook_event_task
"""
Optional Celery tasks for async webhook processing.

This module is only imported if Celery is configured in the project.
If Celery is not available, WebhookService falls back to inline processing.
"""

try:
    from celery import shared_task
    
    @shared_task(bind=True, max_retries=3)
    def process_webhook_event_task(self, webhook_event_id: str):
        """
        Async task to process a webhook event.
        
        Retries up to 3 times on failure with exponential backoff.
        
        Args:
            webhook_event_id: UUID of the WebhookEvent to process
        """
        from core_apps.webhooks.services import WebhookService, WebhookError
        
        try:
            service = WebhookService()
            service.process_event(webhook_event_id)
        except WebhookError as e:
            # Retry with exponential backoff
            raise self.retry(exc=e, countdown=2 ** self.request.retries)
        except Exception as e:
            # Log unexpected errors but don't retry indefinitely
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to process webhook {webhook_event_id}: {str(e)}")
            raise self.retry(exc=e, countdown=60, max_retries=2)

except ImportError:
    # Celery not installed; tasks will not be available
    pass
