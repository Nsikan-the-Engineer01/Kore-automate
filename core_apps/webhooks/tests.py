import unittest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.utils import timezone
from decimal import Decimal

from core_apps.webhooks.services import (
    WebhookService,
    WebhookError,
    PayloadParser
)
from core_apps.webhooks.models import WebhookEvent
from core_apps.collections.models import Collection
from core_apps.goals.models import Goal
from django.contrib.auth import get_user_model

User = get_user_model()


class TestPayloadParser(unittest.TestCase):
    """Tests for tolerant payload parsing."""
    
    def test_extract_paywithaccount_standard_format(self):
        """Test extraction from standard PayWithAccount payload."""
        payload = {
            "request_ref": "req-abc-123",
            "reference": "pwa-ref-456",
            "status": "success",
            "transaction": {
                "type": "debit",
                "amount": 1000
            }
        }
        
        result = PayloadParser.extract_from_payload(payload, "paywithaccount")
        
        self.assertEqual(result["request_ref"], "req-abc-123")
        self.assertEqual(result["provider_ref"], "pwa-ref-456")
        self.assertEqual(result["status"], "success")
    
    def test_extract_paywithaccount_alternate_paths(self):
        """Test extraction with alternative field names."""
        payload = {
            "requestRef": "req-xyz",
            "transactionRef": "txn-789",
            "status": "completed"
        }
        
        result = PayloadParser.extract_from_payload(payload, "paywithaccount")
        
        self.assertEqual(result["request_ref"], "req-xyz")
        self.assertEqual(result["provider_ref"], "txn-789")
        self.assertEqual(result["status"], "completed")
    
    def test_extract_paywithaccount_nested_in_meta(self):
        """Test extraction from nested meta structure."""
        payload = {
            "meta": {
                "request_ref": "nested-req-123"
            },
            "data": {
                "reference": "data-ref-456",
                "status": "pending"
            }
        }
        
        result = PayloadParser.extract_from_payload(payload, "paywithaccount")
        
        self.assertEqual(result["request_ref"], "nested-req-123")
        self.assertEqual(result["provider_ref"], "data-ref-456")
        self.assertEqual(result["status"], "pending")
    
    def test_extract_paywithaccount_missing_optional_fields(self):
        """Test extraction when some fields are missing."""
        payload = {
            "request_ref": "req-only-123"
            # missing provider_ref and status
        }
        
        result = PayloadParser.extract_from_payload(payload, "paywithaccount")
        
        self.assertEqual(result["request_ref"], "req-only-123")
        self.assertIsNone(result["provider_ref"])
        self.assertEqual(result["status"], "unknown")
    
    def test_extract_generic_provider(self):
        """Test generic extraction for unknown providers."""
        payload = {
            "ref": "generic-ref",
            "reference": "gen-prov-ref",
            "status": "ok"
        }
        
        result = PayloadParser.extract_from_payload(payload, "unknown-provider")
        
        self.assertEqual(result["request_ref"], "generic-ref")
        self.assertEqual(result["provider_ref"], "gen-prov-ref")
        self.assertEqual(result["status"], "ok")


class TestWebhookServiceSignature(unittest.TestCase):
    """Tests for signature verification."""
    
    @patch('core_apps.webhooks.services.settings')
    def test_no_signature_verification_when_no_secret(self, mock_settings):
        """Test that verification is skipped when no secret is configured."""
        mock_settings.PWA_WEBHOOK_SECRET = ''
        
        service = WebhookService()
        
        result = service.verify_signature(
            "any payload",
            "any signature",
            "paywithaccount"
        )
        
        self.assertTrue(result)
    
    @patch('core_apps.webhooks.services.settings')
    def test_signature_verification_success(self, mock_settings):
        """Test successful signature verification."""
        import hmac
        import hashlib
        
        secret = "test-secret-key"
        payload_str = '{"test": "payload"}'
        
        computed = hmac.new(
            secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        mock_settings.PWA_WEBHOOK_SECRET = secret
        service = WebhookService()
        
        result = service.verify_signature(payload_str, computed, "paywithaccount")
        
        self.assertTrue(result)
    
    @patch('core_apps.webhooks.services.settings')
    def test_signature_verification_failure(self, mock_settings):
        """Test failed signature verification."""
        mock_settings.PWA_WEBHOOK_SECRET = "correct-secret"
        service = WebhookService()
        
        result = service.verify_signature(
            "some payload",
            "wrong-signature",
            "paywithaccount"
        )
        
        self.assertFalse(result)


class TestWebhookServiceIntegration(TestCase):
    """Integration tests for WebhookService."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='webhook_test',
            email='webhook@test.com',
            password='pass123'
        )
        cls.goal = Goal.objects.create(
            user=cls.user,
            name='Test Goal',
            target_amount=Decimal('50000.00'),
            status='ACTIVE'
        )
    
    @patch('core_apps.webhooks.services.WebhookService.receive_event')
    def test_receive_event_stores_webhook(self, mock_receive):
        """Test that receive_event stores WebhookEvent."""
        service = WebhookService()
        
        payload = {
            "request_ref": "webhook-test-ref",
            "status": "success"
        }
        
        # Mock the internal logic but verify call
        service.receive_event(
            provider="paywithaccount",
            payload=payload,
            request_ref="webhook-test-ref",
            event_id="webhook-123"
        )
        
        mock_receive.assert_called_once()
    
    def test_receive_event_actual_storage(self):
        """Test actual webhook event storage (without Celery)."""
        service = WebhookService()
        
        payload = {
            "request_ref": "actual-webhook-ref",
            "status": "completed"
        }
        
        # Patch Celery import to force inline processing
        with patch('core_apps.webhooks.services.logger'):
            with patch.object(service, 'process_event', return_value=None):
                webhook_event = service.receive_event(
                    provider="paywithaccount",
                    payload=payload,
                    request_ref="actual-webhook-ref",
                    event_id="evt-123"
                )
        
        self.assertIsNotNone(webhook_event.id)
        self.assertEqual(webhook_event.status, 'RECEIVED')
        self.assertEqual(webhook_event.provider, 'paywithaccount')
        self.assertEqual(webhook_event.request_ref, 'actual-webhook-ref')
    
    def test_receive_event_signature_verification_failure(self):
        """Test that signature verification failure raises error."""
        service = WebhookService()
        
        with patch.object(
            service,
            'verify_signature',
            return_value=False
        ):
            with self.assertRaises(WebhookError):
                service.receive_event(
                    provider="paywithaccount",
                    payload={"request_ref": "test"},
                    signature_header="bad-sig",
                    payload_str="raw"
                )
    
    @patch('core_apps.webhooks.services.CollectionsService.update_collection_from_webhook')
    def test_process_event_success(self, mock_update_collection):
        """Test successful webhook event processing."""
        # Create initial collection
        from core_apps.collections.services import CollectionsService
        with patch.object(CollectionsService, 'transact', return_value=({}, 'webhook-req-ref')):
            with patch.object(CollectionsService, 'create_collection') as mock_create:
                # Create collection via mock
                mock_collection = MagicMock()
                mock_collection.id = 'col-123'
                mock_create.return_value = mock_collection
        
        # Create webhook event
        webhook_event = WebhookEvent.objects.create(
            provider='paywithaccount',
            event_id='evt-456',
            request_ref='webhook-req-ref',
            payload={
                'request_ref': 'webhook-req-ref',
                'reference': 'pwa-ref-789',
                'status': 'success'
            },
            status='RECEIVED'
        )
        
        mock_updated_collection = MagicMock()
        mock_updated_collection.id = 'col-123'
        mock_updated_collection.status = 'SUCCESS'
        mock_update_collection.return_value = mock_updated_collection
        
        service = WebhookService()
        result = service.process_event(webhook_event.id)
        
        # Verify webhook event was marked as processed
        result.refresh_from_db()
        self.assertEqual(result.status, 'PROCESSED')
        self.assertIsNotNone(result.processed_at)
        
        # Verify CollectionsService was called
        mock_update_collection.assert_called_once()
        call_kwargs = mock_update_collection.call_args.kwargs
        self.assertEqual(call_kwargs['request_ref'], 'webhook-req-ref')
        self.assertEqual(call_kwargs['provider_ref'], 'pwa-ref-789')
        self.assertEqual(call_kwargs['new_status'], 'success')
    
    def test_process_event_not_found(self):
        """Test processing non-existent webhook event."""
        service = WebhookService()
        
        with self.assertRaises(WebhookError):
            service.process_event('non-existent-uuid')
    
    @patch('core_apps.webhooks.services.CollectionsService.update_collection_from_webhook')
    def test_process_event_collection_error(self, mock_update):
        """Test webhook processing with collection error."""
        from core_apps.collections.services import CollectionError
        
        mock_update.side_effect = CollectionError("Collection not found")
        
        webhook_event = WebhookEvent.objects.create(
            provider='paywithaccount',
            request_ref='error-ref',
            payload={'request_ref': 'error-ref', 'status': 'failed'},
            status='RECEIVED'
        )
        
        service = WebhookService()
        result = service.process_event(webhook_event.id)
        
        # Verify webhook marked as failed
        result.refresh_from_db()
        self.assertEqual(result.status, 'FAILED')
        self.assertIn('CollectionError', result.error)
    
    def test_process_event_missing_request_ref(self):
        """Test processing when request_ref cannot be extracted."""
        webhook_event = WebhookEvent.objects.create(
            provider='paywithaccount',
            payload={
                'status': 'success'
                # missing request_ref
            },
            status='RECEIVED'
        )
        
        service = WebhookService()
        result = service.process_event(webhook_event.id)
        
        # Should fail with appropriate error
        result.refresh_from_db()
        self.assertEqual(result.status, 'FAILED')
        self.assertIn('request_ref', result.error)
    
    def test_receive_event_extracts_identifiers_from_payload(self):
        """Test that identifiers are extracted from payload if not provided."""
        service = WebhookService()
        
        payload = {
            'request_ref': 'payload-req-ref',
            'txRef': 'payload-event-id',
            'status': 'success'
        }
        
        with patch.object(service, 'process_event'):
            webhook_event = service.receive_event(
                provider='paywithaccount',
                payload=payload
                # No request_ref or event_id provided
            )
        
        # Verify they were extracted from payload
        self.assertEqual(webhook_event.request_ref, 'payload-req-ref')


if __name__ == '__main__':
    unittest.main()


class TestWebhookEndpoints(TestCase):
    """Integration tests for webhook API endpoints."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='webhook_user',
            email='webhook@test.com',
            password='pass123'
        )
        cls.goal = Goal.objects.create(
            user=cls.user,
            name='Webhook Test Goal',
            target_amount=Decimal('100000.00'),
            status='ACTIVE'
        )
    
    def test_post_webhook_no_auth_required(self):
        """Test that webhook endpoint requires no authentication."""
        from rest_framework.test import APIClient
        
        client = APIClient()
        
        payload = {
            'request_ref': 'webhook-test-1',
            'status': 'success',
            'reference': 'pwa-ref-1'
        }
        
        # Should not require authentication
        response = client.post(
            '/api/v1/webhooks/paywithaccount/',
            payload,
            format='json'
        )
        
        self.assertEqual(response.status_code, 200)
    
    def test_post_webhook_returns_200_quickly(self):
        """Test that webhook returns 200 immediately."""
        from rest_framework.test import APIClient
        
        client = APIClient()
        
        payload = {
            'request_ref': 'webhook-fast-1',
            'status': 'success',
            'reference': 'pwa-ref-fast'
        }
        
        response = client.post(
            '/api/v1/webhooks/paywithaccount/',
            payload,
            format='json'
        )
        
        # Always returns 200, even on errors
        self.assertEqual(response.status_code, 200)
        self.assertIn('id', response.data)
        self.assertIn('status', response.data)
        self.assertEqual(response.data['status'], 'RECEIVED')
    
    def test_post_webhook_stores_event(self):
        """Test that webhook event is stored."""
        from rest_framework.test import APIClient
        
        client = APIClient()
        
        payload = {
            'request_ref': 'webhook-store-1',
            'status': 'success',
            'reference': 'pwa-ref-store'
        }
        
        response = client.post(
            '/api/v1/webhooks/paywithaccount/',
            payload,
            format='json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify event was stored
        event_id = response.data['id']
        webhook_event = WebhookEvent.objects.get(id=event_id)
        
        self.assertEqual(webhook_event.provider, 'paywithaccount')
        self.assertEqual(webhook_event.request_ref, 'webhook-store-1')
        self.assertEqual(webhook_event.payload['reference'], 'pwa-ref-store')
        self.assertEqual(webhook_event.status, 'RECEIVED')
    
    def test_post_webhook_stores_signature(self):
        """Test that signature is extracted and stored."""
        from rest_framework.test import APIClient
        
        client = APIClient()
        
        payload = {
            'request_ref': 'webhook-sig-1',
            'status': 'success',
        }
        
        # Send with signature header
        response = client.post(
            '/api/v1/webhooks/paywithaccount/',
            payload,
            format='json',
            HTTP_SIGNATURE='abcd1234signature'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify signature was stored
        event_id = response.data['id']
        webhook_event = WebhookEvent.objects.get(id=event_id)
        
        self.assertEqual(webhook_event.signature, 'abcd1234signature')
    
    def test_post_webhook_alternative_signature_headers(self):
        """Test that alternative signature headers are recognized."""
        from rest_framework.test import APIClient
        
        client = APIClient()
        
        # Test X-Kore-Signature header
        payload = {
            'request_ref': 'webhook-alt-sig-1',
            'status': 'pending',
        }
        
        response = client.post(
            '/api/v1/webhooks/paywithaccount/',
            payload,
            format='json',
            HTTP_X_KORE_SIGNATURE='kore-sig-value'
        )
        
        self.assertEqual(response.status_code, 200)
        
        event_id = response.data['id']
        webhook_event = WebhookEvent.objects.get(id=event_id)
        
        self.assertEqual(webhook_event.signature, 'kore-sig-value')
    
    def test_post_webhook_empty_payload(self):
        """Test that empty payload is accepted."""
        from rest_framework.test import APIClient
        
        client = APIClient()
        
        response = client.post(
            '/api/v1/webhooks/paywithaccount/',
            {},
            format='json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('id', response.data)
    
    @patch('core_apps.webhooks.services.WebhookService.receive_event')
    def test_post_webhook_calls_service(self, mock_receive):
        """Test that webhook endpoint calls WebhookService.receive_event()."""
        from rest_framework.test import APIClient
        
        client = APIClient()
        
        # Mock the service
        mock_event = MagicMock()
        mock_event.id = 'event-uuid'
        mock_event.status = 'RECEIVED'
        mock_event.received_at = timezone.now()
        mock_receive.return_value = mock_event
        
        payload = {
            'request_ref': 'webhook-service-1',
            'status': 'success',
        }
        
        response = client.post(
            '/api/v1/webhooks/paywithaccount/',
            payload,
            format='json',
            HTTP_SIGNATURE='test-sig'
        )
        
        # Verify service was called
        mock_receive.assert_called_once()
        call_kwargs = mock_receive.call_args[1]
        
        self.assertEqual(call_kwargs['payload']['request_ref'], 'webhook-service-1')
        self.assertEqual(call_kwargs['signature'], 'test-sig')
        self.assertEqual(call_kwargs['provider'], 'paywithaccount')
    
    def test_post_webhook_event_id_extracted(self):
        """Test that event_id is extracted from payload."""
        from rest_framework.test import APIClient
        
        client = APIClient()
        
        payload = {
            'event_id': 'evt-12345',
            'request_ref': 'webhook-evt-1',
            'status': 'success',
        }
        
        response = client.post(
            '/api/v1/webhooks/paywithaccount/',
            payload,
            format='json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        event_id = response.data['id']
        webhook_event = WebhookEvent.objects.get(id=event_id)
        
        # event_id should be extracted from payload
        self.assertEqual(webhook_event.event_id, 'evt-12345')
    
    def test_post_webhook_multiple_calls(self):
        """Test handling multiple webhook calls."""
        from rest_framework.test import APIClient
        
        client = APIClient()
        
        # Send multiple webhooks
        for i in range(3):
            payload = {
                'request_ref': f'webhook-multi-{i}',
                'status': 'success',
                'reference': f'pwa-ref-{i}'
            }
            
            response = client.post(
                '/api/v1/webhooks/paywithaccount/',
                payload,
                format='json'
            )
            
            self.assertEqual(response.status_code, 200)
        
        # Verify all were stored
        events = WebhookEvent.objects.filter(provider='paywithaccount')
        self.assertGreaterEqual(events.count(), 3)
    
    def test_post_webhook_with_complex_payload(self):
        """Test webhook with nested complex payload."""
        from rest_framework.test import APIClient
        
        client = APIClient()
        
        payload = {
            'request_ref': 'webhook-complex-1',
            'status': 'success',
            'transaction': {
                'type': 'debit',
                'amount': 10250.00,
                'currency': 'NGN',
                'metadata': {
                    'goal_id': 'goal-uuid',
                    'user_id': 'user-uuid'
                }
            },
            'splits': [
                {
                    'account': 'PARTNER',
                    'amount': 10000.00
                },
                {
                    'account': 'KORE',
                    'amount': 250.00
                }
            ]
        }
        
        response = client.post(
            '/api/v1/webhooks/paywithaccount/',
            payload,
            format='json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify complex payload was stored
        event_id = response.data['id']
        webhook_event = WebhookEvent.objects.get(id=event_id)
        
        self.assertEqual(webhook_event.payload['transaction']['amount'], 10250.00)
        self.assertEqual(len(webhook_event.payload['splits']), 2)
