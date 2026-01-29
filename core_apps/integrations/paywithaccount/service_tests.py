"""
Tests for PayWithAccountService.
"""

import unittest
from unittest.mock import patch, MagicMock
from django.test import TestCase

from .service import PayWithAccountService
from .client import TransactionResult, PayWithAccountError


class TestPayWithAccountService(TestCase):
    """Tests for PayWithAccountService wrapper."""
    
    def setUp(self):
        """Set up test service."""
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
        self.service = PayWithAccountService()
    
    def tearDown(self):
        self.settings_patcher.stop()
    
    @patch('core_apps.integrations.paywithaccount.service.PayWithAccountClient.transact')
    def test_transact_wraps_client_result(self, mock_transact):
        """Test that transact wraps client.transact() result into dict."""
        mock_result = TransactionResult(
            request_ref='req-abc123',
            data={'status': 'success', 'transaction_id': 'txn-456'}
        )
        mock_transact.return_value = mock_result
        
        payload = {'transaction': {'amount': 1000.00}}
        response = self.service.transact(payload)
        
        # Verify response is dict format
        self.assertIsInstance(response, dict)
        self.assertEqual(response['request_ref'], 'req-abc123')
        self.assertEqual(response['data']['status'], 'success')
        self.assertEqual(response['data']['transaction_id'], 'txn-456')
    
    @patch('core_apps.integrations.paywithaccount.service.PayWithAccountClient.transact')
    def test_transact_passes_payload_to_client(self, mock_transact):
        """Test that transact passes payload to client unchanged."""
        mock_result = TransactionResult(
            request_ref='req-xyz',
            data={'status': 'success'}
        )
        mock_transact.return_value = mock_result
        
        payload = {
            'transaction': {
                'amount': 5000.00,
                'currency': 'NGN',
                'type': 'debit'
            },
            'meta': {
                'custom_field': 'value'
            }
        }
        
        self.service.transact(payload)
        
        # Verify client was called with exact payload
        mock_transact.assert_called_once_with(payload)
    
    @patch('core_apps.integrations.paywithaccount.service.PayWithAccountClient.transact')
    def test_transact_propagates_errors(self, mock_transact):
        """Test that transact propagates PayWithAccountError from client."""
        mock_transact.side_effect = PayWithAccountError(
            status_code=400,
            response_text='Invalid request',
            request_ref='req-fail'
        )
        
        payload = {'transaction': {'amount': 100.00}}
        
        with self.assertRaises(PayWithAccountError) as ctx:
            self.service.transact(payload)
        
        self.assertEqual(ctx.exception.status_code, 400)
    
    def test_build_meta_defaults_with_both_fields(self):
        """Test building meta with both user_id and goal_id."""
        meta = self.service.build_meta_defaults(
            user_id='user-123',
            goal_id='goal-456'
        )
        
        self.assertEqual(meta['kore_user_id'], 'user-123')
        self.assertEqual(meta['kore_goal_id'], 'goal-456')
        self.assertEqual(len(meta), 2)
    
    def test_build_meta_defaults_with_user_id_only(self):
        """Test building meta with only user_id."""
        meta = self.service.build_meta_defaults(user_id='user-789')
        
        self.assertEqual(meta['kore_user_id'], 'user-789')
        self.assertNotIn('kore_goal_id', meta)
        self.assertEqual(len(meta), 1)
    
    def test_build_meta_defaults_with_goal_id_only(self):
        """Test building meta with only goal_id."""
        meta = self.service.build_meta_defaults(goal_id='goal-999')
        
        self.assertEqual(meta['kore_goal_id'], 'goal-999')
        self.assertNotIn('kore_user_id', meta)
        self.assertEqual(len(meta), 1)
    
    def test_build_meta_defaults_empty(self):
        """Test building meta with no arguments."""
        meta = self.service.build_meta_defaults()
        
        self.assertEqual(meta, {})
        self.assertEqual(len(meta), 0)
    
    def test_build_meta_defaults_converts_to_string(self):
        """Test that build_meta_defaults converts IDs to strings."""
        meta = self.service.build_meta_defaults(
            user_id=123,  # Integer
            goal_id=456   # Integer
        )
        
        self.assertEqual(meta['kore_user_id'], '123')
        self.assertEqual(meta['kore_goal_id'], '456')
        self.assertIsInstance(meta['kore_user_id'], str)
        self.assertIsInstance(meta['kore_goal_id'], str)
    
    def test_build_meta_defaults_with_uuid_objects(self):
        """Test that build_meta_defaults handles UUID objects."""
        import uuid
        
        user_uuid = uuid.uuid4()
        goal_uuid = uuid.uuid4()
        
        meta = self.service.build_meta_defaults(
            user_id=user_uuid,
            goal_id=goal_uuid
        )
        
        self.assertEqual(meta['kore_user_id'], str(user_uuid))
        self.assertEqual(meta['kore_goal_id'], str(goal_uuid))
    
    def test_build_meta_defaults_ignores_none(self):
        """Test that explicit None values are ignored."""
        meta = self.service.build_meta_defaults(
            user_id='user-123',
            goal_id=None
        )
        
        self.assertEqual(meta['kore_user_id'], 'user-123')
        self.assertNotIn('kore_goal_id', meta)
    
    @patch('core_apps.integrations.paywithaccount.service.PayWithAccountClient.transact')
    def test_full_workflow_with_meta(self, mock_transact):
        """Test complete workflow: build meta, then transact."""
        mock_result = TransactionResult(
            request_ref='req-workflow',
            data={'status': 'success'}
        )
        mock_transact.return_value = mock_result
        
        # Build meta defaults
        meta = self.service.build_meta_defaults(
            user_id='usr-123',
            goal_id='goal-456'
        )
        
        # Create payload with meta
        payload = {
            'transaction': {
                'amount': 10000.00,
                'currency': 'NGN'
            },
            'meta': meta
        }
        
        # Execute transaction
        response = self.service.transact(payload)
        
        # Verify result
        self.assertEqual(response['request_ref'], 'req-workflow')
        self.assertEqual(response['data']['status'], 'success')
        
        # Verify payload was passed with meta
        call_args = mock_transact.call_args
        passed_payload = call_args[0][0]
        self.assertEqual(passed_payload['meta']['kore_user_id'], 'usr-123')
        self.assertEqual(passed_payload['meta']['kore_goal_id'], 'goal-456')


if __name__ == '__main__':
    unittest.main()
