import unittest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from core_apps.collections.services import (
    CollectionsService,
    CollectionError
)
from core_apps.integrations.paywithaccount.client import TransactionResult
from core_apps.collections.models import Collection
from core_apps.transactions.models import Transaction
from core_apps.goals.models import Goal
from django.contrib.auth import get_user_model

User = get_user_model()


class TestCollectionsServiceFeeCalculation(unittest.TestCase):
    """Tests for fee calculation logic."""
    
    def test_percent_fee_calculation(self):
        """Test percentage-based fee calculation."""
        with patch.dict('os.environ', {'KORE_FEE_PERCENT': '2.5'}):
            service = CollectionsService()
            
            allocation = Decimal('100.00')
            fee = service.compute_fee(allocation)
            
            # 100 * 2.5 / 100 = 2.50
            self.assertEqual(fee, Decimal('2.50'))
    
    def test_flat_fee_calculation(self):
        """Test flat fee calculation."""
        with patch.dict('os.environ', {'KORE_FEE_FLAT': '50.00'}):
            service = CollectionsService()
            
            allocation = Decimal('1000.00')
            fee = service.compute_fee(allocation)
            
            self.assertEqual(fee, Decimal('50.00'))
    
    def test_percent_fee_takes_precedence(self):
        """Test that percent fee takes precedence over flat."""
        with patch.dict('os.environ', {
            'KORE_FEE_PERCENT': '3.0',
            'KORE_FEE_FLAT': '100.00'
        }):
            service = CollectionsService()
            
            allocation = Decimal('1000.00')
            fee = service.compute_fee(allocation)
            
            # Should use percent (3%), not flat (100)
            self.assertEqual(fee, Decimal('30.00'))
    
    def test_no_fee_when_not_configured(self):
        """Test that fee is 0 when not configured."""
        with patch.dict('os.environ', {}, clear=True):
            service = CollectionsService()
            
            allocation = Decimal('100.00')
            fee = service.compute_fee(allocation)
            
            self.assertEqual(fee, Decimal('0.00'))


class TestPayloadBuilding(unittest.TestCase):
    """Tests for PWA payload construction."""
    
    def setUp(self):
        self.service = CollectionsService()
        self.user = MagicMock(id='user-123')
    
    def test_payload_structure(self):
        """Test that payload has correct structure."""
        goal = MagicMock(id='goal-456', name='Emergency Fund')
        
        payload = self.service.build_pwa_payload(
            user=self.user,
            goal=goal,
            amount_allocation=Decimal('500.00'),
            kore_fee=Decimal('12.50'),
            amount_total=Decimal('512.50'),
            currency='NGN',
            narrative='Goal funding'
        )
        
        self.assertIn('request_type', payload)
        self.assertIn('transaction', payload)
        self.assertIn('meta', payload)
        self.assertEqual(payload['request_type'], 'invoice')
    
    def test_payload_includes_goal_info(self):
        """Test that goal info is included in payload."""
        goal = MagicMock(id='goal-789', name='Education Fund')
        
        payload = self.service.build_pwa_payload(
            user=self.user,
            goal=goal,
            amount_allocation=Decimal('1000.00'),
            kore_fee=Decimal('25.00'),
            amount_total=Decimal('1025.00'),
            currency='NGN'
        )
        
        self.assertEqual(payload['meta']['goal_id'], str(goal.id))
        self.assertEqual(payload['meta']['goal_name'], 'Education Fund')
    
    def test_payload_without_goal(self):
        """Test payload when no goal is provided."""
        payload = self.service.build_pwa_payload(
            user=self.user,
            goal=None,
            amount_allocation=Decimal('100.00'),
            kore_fee=Decimal('2.50'),
            amount_total=Decimal('102.50'),
            currency='NGN'
        )
        
        self.assertNotIn('goal_id', payload['meta'])


class TestCollectionsServiceIntegration(TestCase):
    """Integration tests for CollectionsService (requires DB)."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        cls.goal = Goal.objects.create(
            user=cls.user,
            name='Vacation Fund',
            target_amount=Decimal('50000.00'),
            currency='NGN',
            status='ACTIVE'
        )
    
    @patch('core_apps.collections.services.PayWithAccountClient.transact')
    def test_create_collection_success(self, mock_transact):
        """Test successful collection creation."""
        # Mock PWA API response
        mock_transact.return_value = TransactionResult(
            request_ref='request-ref-abc123',
            data={
                'status': 'success',
                'reference': 'pwa-ref-123',
                'transaction_ref': 'pwa-txn-456'
            }
        )
        
        with patch.dict('os.environ', {'KORE_FEE_PERCENT': '2.0'}):
            service = CollectionsService()
            
            collection = service.create_collection(
                user=self.user,
                goal=self.goal,
                amount_allocation=Decimal('10000.00'),
                currency='NGN',
                narrative='Vacation contribution'
            )
        
        # Verify collection was created
        self.assertIsNotNone(collection.id)
        self.assertEqual(collection.status, 'INITIATED')
        self.assertEqual(collection.request_ref, 'request-ref-abc123')
        self.assertEqual(collection.amount_allocation, Decimal('10000.00'))
        self.assertEqual(collection.kore_fee, Decimal('200.00'))
        self.assertEqual(collection.amount_total, Decimal('10200.00'))
    
    @patch('core_apps.collections.services.PayWithAccountClient.transact')
    def test_create_collection_creates_transactions(self, mock_transact):
        """Test that transactions are created with collection."""
        mock_transact.return_value = TransactionResult(
            request_ref='req-ref-xyz',
            data={'status': 'success', 'reference': 'ref-123'}
        )
        
        with patch.dict('os.environ', {'KORE_FEE_PERCENT': '1.5'}):
            service = CollectionsService()
            
            collection = service.create_collection(
                user=self.user,
                goal=self.goal,
                amount_allocation=Decimal('5000.00')
            )
        
        # Verify transactions were created
        transactions = Transaction.objects.filter(collection=collection)
        self.assertEqual(transactions.count(), 2)  # DEBIT + FEE
        
        debit_tx = transactions.get(type='DEBIT')
        self.assertEqual(debit_tx.amount, Decimal('5000.00'))
        self.assertEqual(debit_tx.status, 'PENDING')
        
        fee_tx = transactions.get(type='FEE')
        self.assertEqual(fee_tx.amount, Decimal('75.00'))
        self.assertEqual(fee_tx.status, 'PENDING')
    
    @patch('core_apps.collections.services.PayWithAccountClient.transact')
    def test_create_collection_idempotency(self, mock_transact):
        """Test idempotent collection creation."""
        mock_transact.return_value = TransactionResult(
            request_ref='req-ref-idem',
            data={'status': 'success'}
        )
        
        service = CollectionsService()
        
        # Create first collection
        collection1 = service.create_collection(
            user=self.user,
            goal=self.goal,
            amount_allocation=Decimal('3000.00'),
            idempotency_key='idem-key-123'
        )
        
        # Reset mock to verify it's not called again
        mock_transact.reset_mock()
        
        # Create second with same idempotency key
        collection2 = service.create_collection(
            user=self.user,
            goal=self.goal,
            amount_allocation=Decimal('3000.00'),
            idempotency_key='idem-key-123'
        )
        
        # Should return same collection
        self.assertEqual(collection1.id, collection2.id)
        
        # PWA should not have been called again
        mock_transact.assert_not_called()
    
    def test_create_collection_invalid_amount(self):
        """Test that invalid amount raises error."""
        service = CollectionsService()
        
        with self.assertRaises(CollectionError):
            service.create_collection(
                user=self.user,
                goal=self.goal,
                amount_allocation=Decimal('0.00')
            )
    
    def test_create_collection_goal_not_owned_by_user(self):
        """Test that collection fails if goal doesn't belong to user."""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='pass123'
        )
        
        service = CollectionsService()
        
        with self.assertRaises(CollectionError):
            service.create_collection(
                user=other_user,
                goal=self.goal,  # Belongs to self.user
                amount_allocation=Decimal('1000.00')
            )
    
    @patch('core_apps.collections.services.PayWithAccountClient.transact')
    def test_update_collection_from_webhook_success(self, mock_transact):
        """Test updating collection status from webhook."""
        # Create initial collection
        mock_transact.return_value = TransactionResult(
            request_ref='req-ref-webhook',
            data={'status': 'success'}
        )
        
        service = CollectionsService()
        collection = service.create_collection(
            user=self.user,
            goal=self.goal,
            amount_allocation=Decimal('2000.00')
        )
        
        # Update from webhook
        updated = service.update_collection_from_webhook(
            request_ref=collection.request_ref,
            provider_ref='pwa-webhook-ref-123',
            new_status='success',
            payload={'webhook': 'data'},
            response_body={'final_status': 'success'}
        )
        
        # Verify collection was updated
        self.assertEqual(updated.status, 'SUCCESS')
        self.assertEqual(updated.provider_ref, 'pwa-webhook-ref-123')
        
        # Verify transactions were updated
        transactions = Transaction.objects.filter(collection=collection)
        for tx in transactions:
            self.assertEqual(tx.status, 'SUCCESS')
    
    @patch('core_apps.collections.services.PayWithAccountClient.transact')
    def test_update_collection_from_webhook_failure(self, mock_transact):
        """Test handling failed webhook status."""
        mock_transact.return_value = TransactionResult(
            request_ref='req-ref-fail',
            data={'status': 'success'}
        )
        
        service = CollectionsService()
        collection = service.create_collection(
            user=self.user,
            goal=self.goal,
            amount_allocation=Decimal('1500.00')
        )
        
        # Update with failed status
        updated = service.update_collection_from_webhook(
            request_ref=collection.request_ref,
            provider_ref='pwa-failed-ref',
            new_status='failed',
            payload={'error': 'payment declined'}
        )
        
        self.assertEqual(updated.status, 'FAILED')
        
        # Verify transactions were marked as failed
        transactions = Transaction.objects.filter(collection=collection)
        for tx in transactions:
            self.assertEqual(tx.status, 'FAILED')
    
    def test_update_collection_not_found(self):
        """Test error when updating non-existent collection."""
        service = CollectionsService()
        
        with self.assertRaises(CollectionError):
            service.update_collection_from_webhook(
                request_ref='non-existent-ref',
                provider_ref='pwa-ref',
                new_status='success',
                payload={}
            )


if __name__ == '__main__':
    unittest.main()


class TestCollectionEndpoints(APITestCase):
    """Integration tests for collection API endpoints."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user1 = User.objects.create_user(
            username='apiuser1',
            email='api1@example.com',
            password='pass123'
        )
        cls.user2 = User.objects.create_user(
            username='apiuser2',
            email='api2@example.com',
            password='pass123'
        )
        cls.goal1 = Goal.objects.create(
            user=cls.user1,
            name='API Test Goal 1',
            target_amount=Decimal('100000.00'),
            status='ACTIVE'
        )
        cls.goal2 = Goal.objects.create(
            user=cls.user2,
            name='API Test Goal 2',
            target_amount=Decimal('50000.00'),
            status='ACTIVE'
        )
    
    def setUp(self):
        self.client = APIClient()
    
    def test_post_collections_unauthenticated(self):
        """Test that POST requires authentication."""
        response = self.client.post(
            '/api/v1/collections/',
            {
                'goal_id': str(self.goal1.id),
                'amount_allocation': '10000.00'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    @patch('core_apps.collections.services.PayWithAccountClient.transact')
    def test_post_collections_success(self, mock_transact):
        """Test successful collection creation via API."""
        mock_transact.return_value = TransactionResult(
            request_ref='req-ref-123',
            data={'status': 'success', 'reference': 'pwa-123'}
        )
        
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.post(
            '/api/v1/collections/',
            {
                'goal_id': str(self.goal1.id),
                'amount_allocation': '10000.00',
                'currency': 'NGN',
                'narrative': 'API test contribution'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertIn('request_ref', response.data)
        self.assertIn('kore_fee', response.data)
        self.assertIn('amount_total', response.data)
        self.assertEqual(response.data['status'], 'INITIATED')
        self.assertEqual(response.data['goal_id'], str(self.goal1.id))
    
    @patch('core_apps.collections.services.PayWithAccountClient.transact')
    def test_post_collections_with_defaults(self, mock_transact):
        """Test collection creation with default values."""
        mock_transact.return_value = TransactionResult(
            request_ref='req-ref-defaults',
            data={'status': 'success'}
        )
        
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.post(
            '/api/v1/collections/',
            {
                'goal_id': str(self.goal1.id),
                'amount_allocation': '5000.00'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['currency'], 'NGN')
    
    def test_post_collections_missing_amount(self):
        """Test that amount_allocation is required."""
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.post(
            '/api/v1/collections/',
            {
                'goal_id': str(self.goal1.id)
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('amount_allocation', response.data)
    
    def test_post_collections_invalid_goal(self):
        """Test that invalid goal_id returns 404."""
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.post(
            '/api/v1/collections/',
            {
                'goal_id': '00000000-0000-0000-0000-000000000000',
                'amount_allocation': '10000.00'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_post_collections_goal_ownership(self):
        """Test that user cannot use another user's goal."""
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.post(
            '/api/v1/collections/',
            {
                'goal_id': str(self.goal2.id),  # Belongs to user2
                'amount_allocation': '10000.00'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_post_collections_negative_amount(self):
        """Test that negative amounts are rejected."""
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.post(
            '/api/v1/collections/',
            {
                'goal_id': str(self.goal1.id),
                'amount_allocation': '-1000.00'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    @patch('core_apps.collections.services.PayWithAccountClient.transact')
    def test_get_collections_list(self, mock_transact):
        """Test listing user's collections."""
        mock_transact.return_value = TransactionResult(
            request_ref='req-ref-list-1',
            data={'status': 'success'}
        )
        
        # Create a collection for user1
        self.client.force_authenticate(user=self.user1)
        self.client.post(
            '/api/v1/collections/',
            {
                'goal_id': str(self.goal1.id),
                'amount_allocation': '5000.00'
            },
            format='json'
        )
        
        # List collections
        response = self.client.get('/api/v1/collections/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['user_username'], 'apiuser1')
    
    @patch('core_apps.collections.services.PayWithAccountClient.transact')
    def test_get_collections_list_isolation(self, mock_transact):
        """Test that users only see their own collections."""
        mock_transact.return_value = TransactionResult(
            request_ref='req-ref-isolation',
            data={'status': 'success'}
        )
        
        # User1 creates a collection
        self.client.force_authenticate(user=self.user1)
        self.client.post(
            '/api/v1/collections/',
            {
                'goal_id': str(self.goal1.id),
                'amount_allocation': '3000.00'
            },
            format='json'
        )
        
        # User2 creates a collection
        self.client.force_authenticate(user=self.user2)
        self.client.post(
            '/api/v1/collections/',
            {
                'goal_id': str(self.goal2.id),
                'amount_allocation': '4000.00'
            },
            format='json'
        )
        
        # User1 lists collections - should see only their own
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/v1/collections/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['user_username'], 'apiuser1')
        
        # User2 lists collections
        self.client.force_authenticate(user=self.user2)
        response = self.client.get('/api/v1/collections/')
        
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['user_username'], 'apiuser2')
    
    def test_get_collections_list_unauthenticated(self):
        """Test that list requires authentication."""
        response = self.client.get('/api/v1/collections/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    @patch('core_apps.collections.services.PayWithAccountClient.transact')
    def test_get_collection_detail(self, mock_transact):
        """Test retrieving a single collection."""
        mock_transact.return_value = TransactionResult(
            request_ref='req-ref-detail',
            data={'status': 'success', 'reference': 'pwa-detail'}
        )
        
        # Create collection
        self.client.force_authenticate(user=self.user1)
        create_response = self.client.post(
            '/api/v1/collections/',
            {
                'goal_id': str(self.goal1.id),
                'amount_allocation': '7000.00'
            },
            format='json'
        )
        
        collection_id = create_response.data['id']
        
        # Retrieve collection
        response = self.client.get(f'/api/v1/collections/{collection_id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], collection_id)
        self.assertIn('request_ref', response.data)
        self.assertIn('kore_fee', response.data)
    
    @patch('core_apps.collections.services.PayWithAccountClient.transact')
    def test_get_collection_detail_not_owned(self, mock_transact):
        """Test that users cannot view other users' collections."""
        mock_transact.return_value = TransactionResult(
            request_ref='req-ref-not-owned',
            data={'status': 'success'}
        )
        
        # User1 creates collection
        self.client.force_authenticate(user=self.user1)
        create_response = self.client.post(
            '/api/v1/collections/',
            {
                'goal_id': str(self.goal1.id),
                'amount_allocation': '2000.00'
            },
            format='json'
        )
        
        collection_id = create_response.data['id']
        
        # User2 tries to access it
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(f'/api/v1/collections/{collection_id}/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_get_collection_detail_not_found(self):
        """Test retrieving non-existent collection."""
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.get(
            '/api/v1/collections/00000000-0000-0000-0000-000000000000/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    @patch('core_apps.collections.services.PayWithAccountClient.transact')
    def test_collection_status_endpoint(self, mock_transact):
        """Test the custom status endpoint."""
        mock_transact.return_value = TransactionResult(
            request_ref='req-ref-status',
            data={'status': 'success'}
        )
        
        # Create collection
        self.client.force_authenticate(user=self.user1)
        create_response = self.client.post(
            '/api/v1/collections/',
            {
                'goal_id': str(self.goal1.id),
                'amount_allocation': '1000.00'
            },
            format='json'
        )
        
        collection_id = create_response.data['id']
        
        # Get status
        response = self.client.get(f'/api/v1/collections/{collection_id}/status/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], collection_id)
        self.assertIn('status', response.data)
        self.assertIn('updated_at', response.data)
        self.assertEqual(response.data['status'], 'INITIATED')

