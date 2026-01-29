import unittest
from unittest.mock import patch, MagicMock
import json
import uuid
from hashlib import md5
from django.test import TestCase
from django.conf import settings

from .client import (
    PayWithAccountClient,
    PayWithAccountError,
    compute_signature,
    TransactionResult
)


class TestComputeSignature(unittest.TestCase):
    """Tests for compute_signature helper function."""
    
    def test_signature_format(self):
        """Test that signature is computed correctly with correct format."""
        request_ref = "abc123def456"
        client_secret = "secret789"
        expected = md5(f"{request_ref};{client_secret}".encode()).hexdigest()
        
        result = compute_signature(request_ref, client_secret)
        
        self.assertEqual(result, expected)
    
    def test_signature_is_hex(self):
        """Test that signature returns valid hex string."""
        request_ref = uuid.uuid4().hex
        client_secret = "my-secret-key"
        
        result = compute_signature(request_ref, client_secret)
        
        # Should be 32 character hex string
        self.assertEqual(len(result), 32)
        self.assertTrue(all(c in "0123456789abcdef" for c in result))
    
    def test_signature_different_inputs_different_outputs(self):
        """Test that different inputs produce different signatures."""
        secret = "same-secret"
        sig1 = compute_signature("ref1", secret)
        sig2 = compute_signature("ref2", secret)
        
        self.assertNotEqual(sig1, sig2)


class TestPayWithAccountError(unittest.TestCase):
    """Tests for PayWithAccountError exception."""
    
    def test_exception_creation(self):
        """Test exception can be created with all parameters."""
        error = PayWithAccountError(
            status_code=400,
            response_text='{"error": "Invalid request"}',
            request_ref="test-ref-123"
        )
        
        self.assertEqual(error.status_code, 400)
        self.assertEqual(error.response_text, '{"error": "Invalid request"}')
        self.assertEqual(error.request_ref, "test-ref-123")
        self.assertIn("400", str(error))
    
    def test_exception_can_be_raised(self):
        """Test exception can be raised and caught."""
        with self.assertRaises(PayWithAccountError) as ctx:
            raise PayWithAccountError(
                status_code=500,
                response_text="Server error",
                request_ref="ref-xyz"
            )
        
        self.assertEqual(ctx.exception.status_code, 500)
    
    def test_exception_with_original_exception(self):
        """Test exception can wrap another exception."""
        original_error = Exception("Network timeout")
        error = PayWithAccountError(exception=original_error)
        
        self.assertEqual(error.exception, original_error)
        self.assertIn("Network timeout", str(error))


class TestPayWithAccountClient(TestCase):
    """Tests for PayWithAccountClient."""
    
    def setUp(self):
        """Set up test client with mocked settings."""
        self.settings_patcher = patch.dict(
            'django.conf.settings.PAYWITHACCOUNT',
            {
                'base_url': 'https://test-api.example.com',
                'transact_path': '/v2/transact',
                'api_key': 'test-key-123',
                'client_secret': 'test-secret-456',
                'mock_mode': 'false',
                'request_type': 'invoice',
                'timeout_seconds': 30,
                'webhook_secret': 'webhook-secret-789'
            }
        )
        self.settings_patcher.start()
        self.client = PayWithAccountClient()
    
    def tearDown(self):
        self.settings_patcher.stop()
    
    def test_client_initialization(self):
        """Test client initializes with settings."""
        self.assertEqual(self.client.base_url, 'https://test-api.example.com')
        self.assertEqual(self.client.transact_path, '/v2/transact')
        self.assertEqual(self.client.api_key, 'test-key-123')
        self.assertEqual(self.client.client_secret, 'test-secret-456')
        self.assertEqual(self.client.mock_mode, 'false')
        self.assertEqual(self.client.timeout, 30)
    
    def test_build_headers(self):
        """Test that headers are built correctly with signature."""
        request_ref = "test-ref-001"
        headers = self.client.build_headers(request_ref)
        
        self.assertIn("Authorization", headers)
        self.assertIn("Signature", headers)
        self.assertIn("Content-Type", headers)
        self.assertEqual(
            headers["Authorization"],
            "Bearer test-key-123"
        )
        self.assertEqual(
            headers["Content-Type"],
            "application/json"
        )
        # Verify signature matches expected format
        expected_sig = compute_signature(request_ref, 'test-secret-456')
        self.assertEqual(headers["Signature"], expected_sig)
    
    def test_redact_sensitive(self):
        """Test that sensitive data is redacted from logs."""
        text = "API key: test-key-123 and secret: test-secret-456"
        
        redacted = self.client._redact_sensitive(text)
        
        self.assertIn("***REDACTED_API_KEY***", redacted)
        self.assertIn("***REDACTED_SECRET***", redacted)
        self.assertNotIn("test-key-123", redacted)
        self.assertNotIn("test-secret-456", redacted)
    
    @patch('core_apps.integrations.paywithaccount.client.requests.post')
    def test_transact_success(self, mock_post):
        """Test successful transaction request."""
        request_ref = uuid.uuid4().hex
        response_data = {"status": "success", "transaction_id": "txn-123"}
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        mock_post.return_value = mock_response
        
        payload = {
            "transaction": {
                "amount": 100.00,
                "currency": "NGN"
            }
        }
        
        result = self.client.transact(payload, request_ref)
        
        self.assertIsInstance(result, TransactionResult)
        self.assertEqual(result.data, response_data)
        self.assertEqual(result.request_ref, request_ref)
        mock_post.assert_called_once()
        
        # Verify request was made to correct URL
        call_args = mock_post.call_args
        self.assertIn(
            'https://test-api.example.com/v2/transact',
            call_args[0][0]
        )
    
    @patch('core_apps.integrations.paywithaccount.client.requests.post')
    def test_transact_generates_request_ref(self, mock_post):
        """Test that request_ref is generated if not provided."""
        response_data = {"status": "success"}
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        mock_post.return_value = mock_response
        
        payload = {"transaction": {"amount": 50.00}}
        
        result = self.client.transact(payload)
        
        # Verify a ref was generated and returned
        self.assertIsNotNone(result.request_ref)
        self.assertEqual(len(result.request_ref), 32)  # UUID hex is 32 chars
        self.assertTrue(all(c in '0123456789abcdef' for c in result.request_ref))
    
    @patch('core_apps.integrations.paywithaccount.client.requests.post')
    def test_transact_injects_mock_mode(self, mock_post):
        """Test that mock_mode is injected into payload if not present."""
        response_data = {"status": "success"}
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        mock_post.return_value = mock_response
        
        payload = {"transaction": {"amount": 100.00}}
        
        self.client.transact(payload)
        
        # Verify mock_mode was injected
        call_args = mock_post.call_args
        sent_payload = call_args.kwargs['json']
        self.assertIn('mock_mode', sent_payload['transaction'])
        self.assertEqual(sent_payload['transaction']['mock_mode'], 'false')
    
    @patch('core_apps.integrations.paywithaccount.client.requests.post')
    def test_transact_preserves_existing_mock_mode(self, mock_post):
        """Test that existing mock_mode in payload is not overwritten."""
        response_data = {"status": "success"}
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        mock_post.return_value = mock_response
        
        payload = {"transaction": {"amount": 100.00, "mock_mode": "test"}}
        
        self.client.transact(payload)
        
        # Verify mock_mode was not overwritten
        call_args = mock_post.call_args
        sent_payload = call_args.kwargs['json']
        self.assertEqual(sent_payload['transaction']['mock_mode'], "test")
    
    @patch('core_apps.integrations.paywithaccount.client.requests.post')
    def test_transact_error_non_2xx(self, mock_post):
        """Test that non-2xx status raises PayWithAccountError."""
        request_ref = uuid.uuid4().hex
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"error": "Invalid request"}'
        mock_post.return_value = mock_response
        
        payload = {"transaction": {"amount": 100.00}}
        
        with self.assertRaises(PayWithAccountError) as ctx:
            self.client.transact(payload, request_ref)
        
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.request_ref, request_ref)
    
    @patch('core_apps.integrations.paywithaccount.client.requests.post')
    def test_transact_error_500(self, mock_post):
        """Test handling of 500 server error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_post.return_value = mock_response
        
        payload = {"transaction": {"amount": 100.00}}
        
        with self.assertRaises(PayWithAccountError) as ctx:
            self.client.transact(payload)
        
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn('Internal Server Error', ctx.exception.response_text)
    
    @patch('core_apps.integrations.paywithaccount.client.requests.post')
    def test_transact_network_error(self, mock_post):
        """Test handling of network errors."""
        import requests
        
        mock_post.side_effect = requests.ConnectionError("Connection refused")
        
        payload = {"transaction": {"amount": 100.00}}
        
        with self.assertRaises(PayWithAccountError) as ctx:
            self.client.transact(payload)
        
        # When a network error occurs, exception is set
        self.assertIsNotNone(ctx.exception.exception)
        self.assertIn('Connection refused', str(ctx.exception.exception))
    
    @patch('core_apps.integrations.paywithaccount.client.requests.post')
    def test_transact_headers_contain_signature(self, mock_post):
        """Test that request includes correct authorization and signature headers."""
        request_ref = "test-ref-abc123"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_post.return_value = mock_response
        
        payload = {"transaction": {"amount": 100.00}}
        
        self.client.transact(payload, request_ref)
        
        # Verify headers
        call_args = mock_post.call_args
        headers = call_args.kwargs['headers']
        
        self.assertEqual(headers['Authorization'], 'Bearer test-key-123')
        expected_sig = compute_signature(request_ref, 'test-secret-456')
        self.assertEqual(headers['Signature'], expected_sig)
        self.assertEqual(headers['Content-Type'], 'application/json')


if __name__ == '__main__':
    unittest.main()
