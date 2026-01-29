"""
Tests for Transaction ViewSet.

Tests list and retrieve endpoints with filtering, permissions, and pagination.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from core_apps.transactions.models import Transaction
from core_apps.goals.models import Goal
from core_apps.collections.models import Collection


class TransactionListViewSetTestCase(TestCase):
    """Test suite for Transaction list endpoint."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        
        # Create test users
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        # Authenticate as test user
        self.client.force_authenticate(user=self.user)
        
        # Create test goals
        self.goal1 = Goal.objects.create(
            user=self.user,
            name='Emergency Fund',
            target_amount=Decimal('500000.00'),
            currency='NGN'
        )
        
        self.goal2 = Goal.objects.create(
            user=self.user,
            name='Vacation Fund',
            target_amount=Decimal('200000.00'),
            currency='NGN'
        )
        
        # Create test collection
        self.collection = Collection.objects.create(
            name='Test Collection',
            user=self.user,
            frequency='ONCE'
        )
        
        # Create test transactions
        now = datetime.now(timezone.utc)
        
        self.txn_credit_success = Transaction.objects.create(
            user=self.user,
            goal=self.goal1,
            type='CREDIT',
            amount=Decimal('100000.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req_001',
            occurred_at=now - timedelta(days=2)
        )
        
        self.txn_debit_success = Transaction.objects.create(
            user=self.user,
            goal=self.goal1,
            type='DEBIT',
            amount=Decimal('50000.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req_002',
            occurred_at=now - timedelta(days=1)
        )
        
        self.txn_fee_success = Transaction.objects.create(
            user=self.user,
            goal=self.goal2,
            type='FEE',
            amount=Decimal('500.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req_003',
            occurred_at=now
        )
        
        self.txn_pending = Transaction.objects.create(
            user=self.user,
            goal=self.goal2,
            type='CREDIT',
            amount=Decimal('100000.00'),
            currency='NGN',
            status='PENDING',
            request_ref='req_004',
            occurred_at=now
        )
        
        # Other user's transaction (should not appear)
        self.other_txn = Transaction.objects.create(
            user=self.other_user,
            goal=None,
            type='CREDIT',
            amount=Decimal('100000.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req_other',
            occurred_at=now
        )
    
    def test_list_authenticated_user_transactions(self):
        """Test listing transactions for authenticated user."""
        response = self.client.get('/api/v1/transactions/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have 4 transactions (not other user's)
        self.assertEqual(response.data['count'], 4)
    
    def test_list_unauthenticated(self):
        """Test that unauthenticated users cannot list transactions."""
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/v1/transactions/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_list_filtered_by_user(self):
        """Test that list only returns user's own transactions."""
        response = self.client.get('/api/v1/transactions/')
        
        txn_ids = [txn['id'] for txn in response.data['results']]
        
        # Should contain user's transactions
        self.assertIn(str(self.txn_credit_success.id), txn_ids)
        self.assertIn(str(self.txn_debit_success.id), txn_ids)
        # Should not contain other user's transaction
        self.assertNotIn(str(self.other_txn.id), txn_ids)
    
    def test_list_default_ordering_newest_first(self):
        """Test that default ordering is newest first (occurred_at desc)."""
        response = self.client.get('/api/v1/transactions/')
        
        results = response.data['results']
        # Fee transaction (newest)
        self.assertEqual(str(results[0]['id']), str(self.txn_fee_success.id))
        # Debit transaction
        self.assertEqual(str(results[1]['id']), str(self.txn_debit_success.id))
        # Credit transaction (oldest)
        self.assertEqual(str(results[2]['id']), str(self.txn_credit_success.id))
    
    def test_list_filter_by_status_success(self):
        """Test filtering by SUCCESS status."""
        response = self.client.get('/api/v1/transactions/?status=SUCCESS')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        
        statuses = [txn['status'] for txn in response.data['results']]
        self.assertTrue(all(s == 'SUCCESS' for s in statuses))
    
    def test_list_filter_by_status_pending(self):
        """Test filtering by PENDING status."""
        response = self.client.get('/api/v1/transactions/?status=PENDING')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['status'], 'PENDING')
    
    def test_list_filter_by_type_credit(self):
        """Test filtering by CREDIT type."""
        response = self.client.get('/api/v1/transactions/?type=CREDIT')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        
        types = [txn['type'] for txn in response.data['results']]
        self.assertTrue(all(t == 'CREDIT' for t in types))
    
    def test_list_filter_by_type_debit(self):
        """Test filtering by DEBIT type."""
        response = self.client.get('/api/v1/transactions/?type=DEBIT')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['type'], 'DEBIT')
    
    def test_list_filter_by_type_fee(self):
        """Test filtering by FEE type."""
        response = self.client.get('/api/v1/transactions/?type=FEE')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['type'], 'FEE')
    
    def test_list_filter_by_goal(self):
        """Test filtering by goal_id."""
        response = self.client.get(f'/api/v1/transactions/?goal_id={self.goal1.id}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        
        goal_ids = [txn['goal']['id'] for txn in response.data['results']]
        self.assertTrue(all(gid == str(self.goal1.id) for gid in goal_ids))
    
    def test_list_filter_by_goal_returns_none_for_other_goal(self):
        """Test filtering by goal shows correct transactions."""
        response = self.client.get(f'/api/v1/transactions/?goal_id={self.goal2.id}')
        
        self.assertEqual(response.data['count'], 2)  # Fee and Pending
        txn_ids = [txn['id'] for txn in response.data['results']]
        self.assertIn(str(self.txn_fee_success.id), txn_ids)
        self.assertIn(str(self.txn_pending.id), txn_ids)
    
    def test_list_filter_by_from_date(self):
        """Test filtering by from_date."""
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        response = self.client.get(f'/api/v1/transactions/?from_date={yesterday}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return fee and pending transactions (from yesterday onwards)
        self.assertGreaterEqual(response.data['count'], 2)
    
    def test_list_filter_by_to_date(self):
        """Test filtering by to_date."""
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        response = self.client.get(f'/api/v1/transactions/?to_date={yesterday}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return only old transactions
        self.assertLess(response.data['count'], 4)
    
    def test_list_filter_by_date_range(self):
        """Test filtering by date range."""
        three_days_ago = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        today = datetime.now(timezone.utc).isoformat()
        
        response = self.client.get(
            f'/api/v1/transactions/?from_date={three_days_ago}&to_date={today}'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 4)
    
    def test_list_combined_filters(self):
        """Test combining multiple filters."""
        response = self.client.get(
            f'/api/v1/transactions/?goal_id={self.goal1.id}&status=SUCCESS&type=CREDIT'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(str(response.data['results'][0]['id']), str(self.txn_credit_success.id))
    
    def test_list_pagination(self):
        """Test that list endpoint supports pagination."""
        response = self.client.get('/api/v1/transactions/')
        
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
    
    def test_list_serializer_used(self):
        """Test that TransactionListSerializer is used."""
        response = self.client.get('/api/v1/transactions/')
        
        # Check for list serializer fields
        txn = response.data['results'][0]
        self.assertIn('title', txn)
        self.assertIn('goal', txn)
        self.assertIn('collection', txn)
        self.assertIsInstance(txn['amount'], str)


class TransactionRetrieveViewSetTestCase(TestCase):
    """Test suite for Transaction retrieve endpoint."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        
        # Create test users
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        # Authenticate as test user
        self.client.force_authenticate(user=self.user)
        
        # Create test goal
        self.goal = Goal.objects.create(
            user=self.user,
            name='Test Goal',
            target_amount=Decimal('100000.00'),
            currency='NGN'
        )
        
        # Create test transaction
        self.transaction = Transaction.objects.create(
            user=self.user,
            goal=self.goal,
            type='CREDIT',
            amount=Decimal('100000.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req_001',
            metadata={'source': 'app'},
            occurred_at=datetime.now(timezone.utc)
        )
        
        # Other user's transaction
        self.other_transaction = Transaction.objects.create(
            user=self.other_user,
            type='CREDIT',
            amount=Decimal('50000.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req_other',
            occurred_at=datetime.now(timezone.utc)
        )
    
    def test_retrieve_own_transaction(self):
        """Test retrieving a transaction that belongs to the user."""
        response = self.client.get(f'/api/v1/transactions/{self.transaction.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data['id']), str(self.transaction.id))
        self.assertEqual(response.data['type'], 'CREDIT')
    
    def test_retrieve_other_user_transaction_forbidden(self):
        """Test that users cannot retrieve other users' transactions."""
        response = self.client.get(f'/api/v1/transactions/{self.other_transaction.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_retrieve_nonexistent_transaction(self):
        """Test retrieving a transaction that doesn't exist."""
        fake_id = '00000000-0000-0000-0000-000000000000'
        response = self.client.get(f'/api/v1/transactions/{fake_id}/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_retrieve_unauthenticated(self):
        """Test that unauthenticated users cannot retrieve transactions."""
        self.client.force_authenticate(user=None)
        response = self.client.get(f'/api/v1/transactions/{self.transaction.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_retrieve_serializer_used(self):
        """Test that TransactionDetailSerializer is used."""
        response = self.client.get(f'/api/v1/transactions/{self.transaction.id}/')
        
        # Check for detail serializer fields
        self.assertIn('id', response.data)
        self.assertIn('type', response.data)
        self.assertIn('amount', response.data)
        self.assertIn('status', response.data)
        self.assertIn('title', response.data)
        self.assertIn('goal', response.data)
        self.assertIn('metadata', response.data)
        self.assertEqual(response.data['metadata'], {'source': 'app'})
    
    def test_retrieve_includes_all_fields(self):
        """Test that retrieve returns all fields."""
        response = self.client.get(f'/api/v1/transactions/{self.transaction.id}/')
        
        required_fields = [
            'id', 'type', 'amount', 'currency', 'status', 'title',
            'goal', 'collection', 'request_ref', 'provider_ref',
            'occurred_at', 'created_at', 'updated_at', 'metadata'
        ]
        
        for field in required_fields:
            self.assertIn(field, response.data)
    
    def test_retrieve_amount_as_string(self):
        """Test that amount is serialized as string."""
        response = self.client.get(f'/api/v1/transactions/{self.transaction.id}/')
        
        self.assertIsInstance(response.data['amount'], str)
        self.assertEqual(response.data['amount'], '100000.00')


class TransactionSummaryViewSetTestCase(TestCase):
    """Test suite for Transaction summary endpoint."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        
        # Create test users
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        # Authenticate as test user
        self.client.force_authenticate(user=self.user)
        
        # Create test goals
        self.goal1 = Goal.objects.create(
            user=self.user,
            name='Emergency Fund',
            target_amount=Decimal('500000.00'),
            currency='NGN'
        )
        
        self.goal2 = Goal.objects.create(
            user=self.user,
            name='Vacation Fund',
            target_amount=Decimal('200000.00'),
            currency='NGN'
        )
        
        # Create successful transactions for goal1
        Transaction.objects.create(
            user=self.user,
            goal=self.goal1,
            type='CREDIT',
            amount=Decimal('100000.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req_001',
            occurred_at=datetime.now(timezone.utc)
        )
        
        Transaction.objects.create(
            user=self.user,
            goal=self.goal1,
            type='DEBIT',
            amount=Decimal('50000.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req_002',
            occurred_at=datetime.now(timezone.utc)
        )
        
        # Create successful transactions for goal2
        Transaction.objects.create(
            user=self.user,
            goal=self.goal2,
            type='CREDIT',
            amount=Decimal('150000.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req_003',
            occurred_at=datetime.now(timezone.utc)
        )
        
        Transaction.objects.create(
            user=self.user,
            goal=self.goal2,
            type='FEE',
            amount=Decimal('500.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req_004',
            occurred_at=datetime.now(timezone.utc)
        )
        
        # Create pending transaction (should not be in summary)
        Transaction.objects.create(
            user=self.user,
            goal=self.goal1,
            type='CREDIT',
            amount=Decimal('200000.00'),
            currency='NGN',
            status='PENDING',
            request_ref='req_pending',
            occurred_at=datetime.now(timezone.utc)
        )
        
        # Other user's successful transaction (should not appear)
        Transaction.objects.create(
            user=self.other_user,
            goal=None,
            type='CREDIT',
            amount=Decimal('100000.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req_other',
            occurred_at=datetime.now(timezone.utc)
        )
    
    def test_summary_returns_correct_totals(self):
        """Test that summary returns correct aggregated totals."""
        response = self.client.get('/api/v1/transactions/summary/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Total credits: 100000 + 150000 = 250000
        self.assertEqual(str(response.data['total_credits_success']), '250000')
        # Total debits: 50000
        self.assertEqual(str(response.data['total_debits_success']), '50000')
        # Total fees: 500
        self.assertEqual(str(response.data['total_fees_success']), '500')
    
    def test_summary_excludes_pending_transactions(self):
        """Test that summary only includes SUCCESS status transactions."""
        response = self.client.get('/api/v1/transactions/summary/')
        
        # Pending transaction (200000) should not be included
        self.assertEqual(str(response.data['total_credits_success']), '250000')
    
    def test_summary_excludes_other_users_transactions(self):
        """Test that summary only includes own transactions."""
        response = self.client.get('/api/v1/transactions/summary/')
        
        # Other user's transaction should not be included
        self.assertEqual(str(response.data['total_credits_success']), '250000')
    
    def test_summary_filter_by_goal(self):
        """Test filtering summary by goal_id."""
        response = self.client.get(f'/api/v1/transactions/summary/?goal_id={self.goal1.id}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Goal1 totals: 1 credit (100000) + 1 debit (50000)
        self.assertEqual(str(response.data['total_credits_success']), '100000')
        self.assertEqual(str(response.data['total_debits_success']), '50000')
        self.assertEqual(str(response.data['total_fees_success']), '0')
    
    def test_summary_filter_by_goal2(self):
        """Test filtering summary by different goal."""
        response = self.client.get(f'/api/v1/transactions/summary/?goal_id={self.goal2.id}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Goal2 totals: 1 credit (150000) + 1 fee (500)
        self.assertEqual(str(response.data['total_credits_success']), '150000')
        self.assertEqual(str(response.data['total_debits_success']), '0')
        self.assertEqual(str(response.data['total_fees_success']), '500')
    
    def test_summary_unauthenticated(self):
        """Test that unauthenticated users cannot access summary."""
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/v1/transactions/summary/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_summary_returns_zero_for_empty_type(self):
        """Test that missing transaction types return 0."""
        # Create a user with only credit transactions
        user_credit_only = User.objects.create_user(
            username='creditonly',
            email='creditonly@example.com',
            password='pass123'
        )
        goal_credit = Goal.objects.create(
            user=user_credit_only,
            name='Test Goal',
            target_amount=Decimal('100000.00'),
            currency='NGN'
        )
        Transaction.objects.create(
            user=user_credit_only,
            goal=goal_credit,
            type='CREDIT',
            amount=Decimal('50000.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req_credit_only',
            occurred_at=datetime.now(timezone.utc)
        )
        
        self.client.force_authenticate(user=user_credit_only)
        response = self.client.get('/api/v1/transactions/summary/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data['total_credits_success']), '50000')
        self.assertEqual(str(response.data['total_debits_success']), '0')
        self.assertEqual(str(response.data['total_fees_success']), '0')
