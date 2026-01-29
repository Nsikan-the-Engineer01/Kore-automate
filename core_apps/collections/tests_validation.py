"""
Tests for Collections Service validation handling.

Tests verify:
- Collection status set to PENDING when validation required
- Validation fields extracted and stored in metadata
- Transaction status aligned with collection status
- SUCCESS and FAILED statuses handled correctly
- Defensive extraction of provider status
"""

from decimal import Decimal
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import Mock, patch

from core_apps.collections.models import Collection
from core_apps.collections.services import CollectionsService
from core_apps.goals.models import Goal
from core_apps.transactions.models import Transaction
from core_apps.integrations.paywithaccount.client import TransactionResult

User = get_user_model()


@override_settings(PAYWITHACCOUNT={
    'base_url': 'https://api.test.onepipe.io',
    'api_key': 'test_key',
    'client_secret': 'test_secret',
    'timeout_seconds': 5,
    'mock_mode': 'inspect',
    'request_type': 'invoice',
    'request_type_invoice': 'invoice',
    'transact_path': '/v2/transact',
})
class CollectionsServiceValidationTest(TestCase):
    """Tests for validation handling in collections service"""
    
    def setUp(self):
        """Set up test user and goal"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )
        self.goal = Goal.objects.create(
            user=self.user,
            name='Test Goal',
            target_amount=Decimal('100000.00')
        )
    
    @patch('core_apps.collections.services.PayWithAccountClient.transact')
    def test_collection_with_validation_required(self, mock_transact):
        """Test that collection status is PENDING when OTP validation required"""
        # Mock response indicating validation required
        mock_transact.return_value = TransactionResult(
            request_ref='test_ref_123',
            data={
                'status': 'WaitingForOTP',
                'reference': 'provider_ref_123',
                'validation_ref': 'val_ref_456',
                'session_id': 'sess_789'
            }
        )
        
        service = CollectionsService()
        collection = service.create_collection(
            user=self.user,
            goal=self.goal,
            amount_allocation=Decimal('50000.00')
        )
        
        # Verify collection status is PENDING
        assert collection.status == 'PENDING'
        assert collection.request_ref == 'test_ref_123'
        assert collection.provider_ref == 'provider_ref_123'
        
        # Verify metadata contains validation flags
        assert collection.metadata.get('needs_validation') is True
        assert 'validation_fields' in collection.metadata
        assert collection.metadata['validation_fields']['validation_ref'] == 'val_ref_456'
        assert collection.metadata['validation_fields']['session_id'] == 'sess_789'
        
        # Verify transactions have PENDING status
        transactions = Transaction.objects.filter(collection=collection)
        assert transactions.count() == 2  # DEBIT + FEE
        assert all(t.status == 'PENDING' for t in transactions)
    
    @patch('core_apps.collections.services.PayWithAccountClient.transact')
    def test_collection_with_success_status(self, mock_transact):
        """Test that collection status is SUCCESS when provider returns success"""
        mock_transact.return_value = TransactionResult(
            request_ref='test_ref_123',
            data={
                'status': 'SUCCESS',
                'reference': 'provider_ref_123'
            }
        )
        
        service = CollectionsService()
        collection = service.create_collection(
            user=self.user,
            goal=self.goal,
            amount_allocation=Decimal('50000.00')
        )
        
        # Verify collection status is SUCCESS
        assert collection.status == 'SUCCESS'
        
        # Verify metadata indicates no validation required
        assert collection.metadata.get('needs_validation') is False
        assert 'validation_fields' not in collection.metadata or not collection.metadata.get('validation_fields')
        
        # Verify transactions have SUCCESS status
        transactions = Transaction.objects.filter(collection=collection)
        assert all(t.status == 'SUCCESS' for t in transactions)
    
    @patch('core_apps.collections.services.PayWithAccountClient.transact')
    def test_collection_with_failed_status(self, mock_transact):
        """Test that collection status is FAILED when provider returns failure"""
        mock_transact.return_value = TransactionResult(
            request_ref='test_ref_123',
            data={
                'status': 'DECLINED',
                'reference': 'provider_ref_123',
                'error': 'Insufficient funds'
            }
        )
        
        service = CollectionsService()
        collection = service.create_collection(
            user=self.user,
            goal=self.goal,
            amount_allocation=Decimal('50000.00')
        )
        
        # Verify collection status is FAILED
        assert collection.status == 'FAILED'
        assert collection.metadata.get('needs_validation') is False
        
        # Verify transactions have FAILED status
        transactions = Transaction.objects.filter(collection=collection)
        assert all(t.status == 'FAILED' for t in transactions)
    
    @patch('core_apps.collections.services.PayWithAccountClient.transact')
    def test_collection_with_pending_status(self, mock_transact):
        """Test that collection status is PENDING when provider returns pending (no validation)"""
        mock_transact.return_value = TransactionResult(
            request_ref='test_ref_123',
            data={
                'status': 'PROCESSING',
                'reference': 'provider_ref_123'
            }
        )
        
        service = CollectionsService()
        collection = service.create_collection(
            user=self.user,
            goal=self.goal,
            amount_allocation=Decimal('50000.00')
        )
        
        # Verify collection status is PENDING
        assert collection.status == 'PENDING'
        assert collection.metadata.get('needs_validation') is False
        
        # Verify transactions have PENDING status
        transactions = Transaction.objects.filter(collection=collection)
        assert all(t.status == 'PENDING' for t in transactions)
    
    @patch('core_apps.collections.services.PayWithAccountClient.transact')
    def test_collection_with_missing_status_field(self, mock_transact):
        """Test defensive behavior when status field is missing"""
        # Response without status field
        mock_transact.return_value = TransactionResult(
            request_ref='test_ref_123',
            data={
                'reference': 'provider_ref_123',
                'message': 'Processing'
            }
        )
        
        service = CollectionsService()
        collection = service.create_collection(
            user=self.user,
            goal=self.goal,
            amount_allocation=Decimal('50000.00')
        )
        
        # Defensive: should default to PENDING
        assert collection.status == 'PENDING'
        assert collection.metadata.get('needs_validation') is False
    
    @patch('core_apps.collections.services.PayWithAccountClient.transact')
    def test_collection_with_multiple_validation_fields(self, mock_transact):
        """Test extraction of multiple validation field types"""
        mock_transact.return_value = TransactionResult(
            request_ref='test_ref_123',
            data={
                'status': 'OTP_PENDING',
                'reference': 'provider_ref_123',
                'validation_ref': 'val_ref_1',
                'session_id': 'sess_123',
                'otp_reference': 'otp_456',
                'challenge_ref': 'chal_789',
                'auth_token': 'token_abc'
            }
        )
        
        service = CollectionsService()
        collection = service.create_collection(
            user=self.user,
            goal=self.goal,
            amount_allocation=Decimal('50000.00')
        )
        
        # Verify all validation fields are extracted
        validation_fields = collection.metadata.get('validation_fields', {})
        assert validation_fields.get('validation_ref') == 'val_ref_1'
        assert validation_fields.get('session_id') == 'sess_123'
        assert validation_fields.get('otp_reference') == 'otp_456'
        assert validation_fields.get('challenge_ref') == 'chal_789'
        assert validation_fields.get('auth_token') == 'token_abc'
    
    @patch('core_apps.collections.services.PayWithAccountClient.transact')
    def test_collection_with_case_insensitive_status(self, mock_transact):
        """Test that status normalization is case-insensitive"""
        # Provider returns lowercase/mixed case status
        mock_transact.return_value = TransactionResult(
            request_ref='test_ref_123',
            data={
                'status': 'waitingforotp',
                'reference': 'provider_ref_123',
                'validation_ref': 'val_ref_1'
            }
        )
        
        service = CollectionsService()
        collection = service.create_collection(
            user=self.user,
            goal=self.goal,
            amount_allocation=Decimal('50000.00')
        )
        
        # Should still detect validation requirement despite case
        assert collection.status == 'PENDING'
        assert collection.metadata.get('needs_validation') is True
    
    @patch('core_apps.collections.services.PayWithAccountClient.transact')
    def test_transaction_status_follows_collection_status(self, mock_transact):
        """Test that transaction status reflects collection status"""
        test_cases = [
            ('SUCCESS', 'SUCCESS'),
            ('DECLINED', 'FAILED'),
            ('PROCESSING', 'PENDING'),
            ('WaitingForOTP', 'PENDING'),  # validation case
        ]
        
        for provider_status, expected_tx_status in test_cases:
            mock_transact.return_value = TransactionResult(
                request_ref=f'ref_{provider_status}',
                data={'status': provider_status, 'reference': 'provider_ref'}
            )
            
            service = CollectionsService()
            collection = service.create_collection(
                user=self.user,
                goal=self.goal,
                amount_allocation=Decimal('50000.00')
            )
            
            transactions = Transaction.objects.filter(collection=collection)
            for tx in transactions:
                assert tx.status == expected_tx_status, \
                    f"Provider status {provider_status} should map to TX status {expected_tx_status}"
            
            # Clean up for next iteration
            collection.delete()
