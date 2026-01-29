"""
Tests for Transaction serializers.

Tests TransactionListSerializer and TransactionDetailSerializer with various
scenarios including nested goal/collection data, computed fields, and edge cases.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework import serializers
from decimal import Decimal
from datetime import datetime, timezone
from core_apps.transactions.models import Transaction
from core_apps.transactions.serializers import (
    TransactionListSerializer,
    TransactionDetailSerializer
)
from core_apps.goals.models import Goal
from core_apps.collections.models import Collection


class TransactionListSerializerTestCase(TestCase):
    """Test suite for TransactionListSerializer."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test goal
        self.goal = Goal.objects.create(
            user=self.user,
            name='Emergency Fund',
            target_amount=Decimal('500000.00'),
            currency='NGN',
            status='ACTIVE'
        )
        
        # Create test collection
        self.collection = Collection.objects.create(
            name='Test Collection',
            user=self.user,
            frequency='ONCE'
        )
        
        # Create test transaction
        self.transaction = Transaction.objects.create(
            user=self.user,
            goal=self.goal,
            collection=self.collection,
            type='CREDIT',
            amount=Decimal('100000.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req_12345',
            provider_ref='prov_67890',
            occurred_at=datetime.now(timezone.utc),
            metadata={'source': 'mobile_app'}
        )
    
    def test_list_serializer_all_fields_present(self):
        """Test that list serializer includes all required fields."""
        serializer = TransactionListSerializer(self.transaction)
        data = serializer.data
        
        # Check all fields present
        required_fields = [
            'id', 'type', 'amount', 'currency', 'status', 'title',
            'goal', 'collection', 'request_ref', 'provider_ref',
            'occurred_at', 'created_at', 'updated_at', 'metadata'
        ]
        for field in required_fields:
            self.assertIn(field, data)
    
    def test_list_serializer_amount_as_string(self):
        """Test that amount is serialized as string."""
        serializer = TransactionListSerializer(self.transaction)
        data = serializer.data
        
        self.assertIsInstance(data['amount'], str)
        self.assertEqual(data['amount'], '100000.00')
    
    def test_list_serializer_credit_title(self):
        """Test that CREDIT type generates 'Credit' title."""
        serializer = TransactionListSerializer(self.transaction)
        data = serializer.data
        
        self.assertEqual(data['title'], 'Credit')
    
    def test_list_serializer_debit_title(self):
        """Test that DEBIT type generates 'Debit' title."""
        debit_transaction = Transaction.objects.create(
            user=self.user,
            goal=self.goal,
            type='DEBIT',
            amount=Decimal('50000.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req_debit_001',
            occurred_at=datetime.now(timezone.utc)
        )
        
        serializer = TransactionListSerializer(debit_transaction)
        data = serializer.data
        
        self.assertEqual(data['title'], 'Debit')
    
    def test_list_serializer_fee_title(self):
        """Test that FEE type generates 'Kore Fee' title."""
        fee_transaction = Transaction.objects.create(
            user=self.user,
            goal=self.goal,
            type='FEE',
            amount=Decimal('500.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req_fee_001',
            occurred_at=datetime.now(timezone.utc)
        )
        
        serializer = TransactionListSerializer(fee_transaction)
        data = serializer.data
        
        self.assertEqual(data['title'], 'Kore Fee')
    
    def test_list_serializer_goal_nested(self):
        """Test that goal is nested with id and name."""
        serializer = TransactionListSerializer(self.transaction)
        data = serializer.data
        
        self.assertIn('goal', data)
        self.assertIn('id', data['goal'])
        self.assertIn('name', data['goal'])
        self.assertEqual(str(data['goal']['id']), str(self.goal.id))
        self.assertEqual(data['goal']['name'], 'Emergency Fund')
    
    def test_list_serializer_collection_reference(self):
        """Test that collection includes id reference."""
        serializer = TransactionListSerializer(self.transaction)
        data = serializer.data
        
        self.assertIn('collection', data)
        self.assertIn('id', data['collection'])
        self.assertEqual(str(data['collection']['id']), str(self.collection.id))
    
    def test_list_serializer_goal_none(self):
        """Test serialization when goal is None."""
        transaction = Transaction.objects.create(
            user=self.user,
            collection=self.collection,
            type='CREDIT',
            amount=Decimal('100000.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req_no_goal',
            occurred_at=datetime.now(timezone.utc)
        )
        
        serializer = TransactionListSerializer(transaction)
        data = serializer.data
        
        self.assertIsNone(data['goal'])
    
    def test_list_serializer_collection_none(self):
        """Test serialization when collection is None."""
        transaction = Transaction.objects.create(
            user=self.user,
            goal=self.goal,
            type='CREDIT',
            amount=Decimal('100000.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req_no_collection',
            occurred_at=datetime.now(timezone.utc)
        )
        
        serializer = TransactionListSerializer(transaction)
        data = serializer.data
        
        self.assertIsNone(data['collection'])
    
    def test_list_serializer_provider_ref_null(self):
        """Test serialization when provider_ref is null."""
        transaction = Transaction.objects.create(
            user=self.user,
            goal=self.goal,
            type='CREDIT',
            amount=Decimal('100000.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req_no_provider',
            occurred_at=datetime.now(timezone.utc)
        )
        
        serializer = TransactionListSerializer(transaction)
        data = serializer.data
        
        self.assertIsNone(data['provider_ref'])
    
    def test_list_serializer_metadata_included(self):
        """Test that metadata is included in serialization."""
        serializer = TransactionListSerializer(self.transaction)
        data = serializer.data
        
        self.assertIn('metadata', data)
        self.assertEqual(data['metadata'], {'source': 'mobile_app'})
    
    def test_list_serializer_pending_status(self):
        """Test serialization with PENDING status."""
        pending_transaction = Transaction.objects.create(
            user=self.user,
            goal=self.goal,
            type='CREDIT',
            amount=Decimal('100000.00'),
            currency='NGN',
            status='PENDING',
            request_ref='req_pending',
            occurred_at=datetime.now(timezone.utc)
        )
        
        serializer = TransactionListSerializer(pending_transaction)
        data = serializer.data
        
        self.assertEqual(data['status'], 'PENDING')
    
    def test_list_serializer_failed_status(self):
        """Test serialization with FAILED status."""
        failed_transaction = Transaction.objects.create(
            user=self.user,
            goal=self.goal,
            type='DEBIT',
            amount=Decimal('50000.00'),
            currency='NGN',
            status='FAILED',
            request_ref='req_failed',
            occurred_at=datetime.now(timezone.utc)
        )
        
        serializer = TransactionListSerializer(failed_transaction)
        data = serializer.data
        
        self.assertEqual(data['status'], 'FAILED')
    
    def test_list_serializer_currency_preserved(self):
        """Test that currency is correctly preserved."""
        serializer = TransactionListSerializer(self.transaction)
        data = serializer.data
        
        self.assertEqual(data['currency'], 'NGN')
    
    def test_list_serializer_request_ref_included(self):
        """Test that request_ref is included."""
        serializer = TransactionListSerializer(self.transaction)
        data = serializer.data
        
        self.assertEqual(data['request_ref'], 'req_12345')
    
    def test_list_serializer_read_only_fields(self):
        """Test that certain fields are read-only."""
        serializer = TransactionListSerializer()
        
        # Check that id, created_at, updated_at are read-only
        self.assertTrue(serializer.fields['id'].read_only)
        self.assertTrue(serializer.fields['created_at'].read_only)
        self.assertTrue(serializer.fields['updated_at'].read_only)


class TransactionDetailSerializerTestCase(TestCase):
    """Test suite for TransactionDetailSerializer."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test goal
        self.goal = Goal.objects.create(
            user=self.user,
            name='Emergency Fund',
            target_amount=Decimal('500000.00'),
            currency='NGN',
            status='ACTIVE'
        )
        
        # Create test collection
        self.collection = Collection.objects.create(
            name='Test Collection',
            user=self.user,
            frequency='ONCE'
        )
        
        # Create test transaction
        self.transaction = Transaction.objects.create(
            user=self.user,
            goal=self.goal,
            collection=self.collection,
            type='CREDIT',
            amount=Decimal('100000.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='req_12345',
            provider_ref='prov_67890',
            occurred_at=datetime.now(timezone.utc),
            metadata={'source': 'mobile_app', 'ip': '192.168.1.1'}
        )
    
    def test_detail_serializer_all_fields_present(self):
        """Test that detail serializer includes all required fields."""
        serializer = TransactionDetailSerializer(self.transaction)
        data = serializer.data
        
        required_fields = [
            'id', 'type', 'amount', 'currency', 'status', 'title',
            'goal', 'collection', 'request_ref', 'provider_ref',
            'occurred_at', 'created_at', 'updated_at', 'metadata'
        ]
        for field in required_fields:
            self.assertIn(field, data)
    
    def test_detail_serializer_includes_list_fields(self):
        """Test that detail serializer includes all list serializer fields."""
        list_serializer = TransactionListSerializer(self.transaction)
        detail_serializer = TransactionDetailSerializer(self.transaction)
        
        list_data = list_serializer.data
        detail_data = detail_serializer.data
        
        # Detail should have all list fields
        for field in list_data.keys():
            self.assertIn(field, detail_data)
    
    def test_detail_serializer_amount_as_string(self):
        """Test that amount is serialized as string in detail."""
        serializer = TransactionDetailSerializer(self.transaction)
        data = serializer.data
        
        self.assertIsInstance(data['amount'], str)
        self.assertEqual(data['amount'], '100000.00')
    
    def test_detail_serializer_all_fields_read_only(self):
        """Test that all fields are read-only in detail serializer."""
        serializer = TransactionDetailSerializer()
        
        # All listed fields should be read-only
        for field_name in serializer.fields.keys():
            if field_name not in ['title']:  # title is computed
                self.assertTrue(
                    serializer.fields[field_name].read_only,
                    f"Field {field_name} should be read-only"
                )
    
    def test_detail_serializer_metadata_detailed(self):
        """Test that metadata with multiple keys is preserved."""
        serializer = TransactionDetailSerializer(self.transaction)
        data = serializer.data
        
        self.assertEqual(data['metadata'], {
            'source': 'mobile_app',
            'ip': '192.168.1.1'
        })
    
    def test_detail_serializer_title_credit(self):
        """Test that detail serializer generates correct title."""
        serializer = TransactionDetailSerializer(self.transaction)
        data = serializer.data
        
        self.assertEqual(data['title'], 'Credit')
    
    def test_detail_serializer_timestamps_present(self):
        """Test that timestamps are included."""
        serializer = TransactionDetailSerializer(self.transaction)
        data = serializer.data
        
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)
        self.assertIsNotNone(data['created_at'])
        self.assertIsNotNone(data['updated_at'])
    
    def test_detail_serializer_goal_with_nested_data(self):
        """Test that goal nested data is included."""
        serializer = TransactionDetailSerializer(self.transaction)
        data = serializer.data
        
        self.assertIsNotNone(data['goal'])
        self.assertEqual(data['goal']['name'], 'Emergency Fund')
    
    def test_detail_serializer_collection_with_id(self):
        """Test that collection has id reference."""
        serializer = TransactionDetailSerializer(self.transaction)
        data = serializer.data
        
        self.assertIsNotNone(data['collection'])
        self.assertIn('id', data['collection'])
    
    def test_detail_serializer_both_refs_present(self):
        """Test that both request_ref and provider_ref are present."""
        serializer = TransactionDetailSerializer(self.transaction)
        data = serializer.data
        
        self.assertEqual(data['request_ref'], 'req_12345')
        self.assertEqual(data['provider_ref'], 'prov_67890')
    
    def test_detail_serializer_matches_list_serializer_for_common_fields(self):
        """Test that common fields match between detail and list."""
        list_serializer = TransactionListSerializer(self.transaction)
        detail_serializer = TransactionDetailSerializer(self.transaction)
        
        list_data = list_serializer.data
        detail_data = detail_serializer.data
        
        # For common fields, values should match
        common_fields = [
            'id', 'type', 'amount', 'currency', 'status', 'title',
            'request_ref', 'provider_ref', 'occurred_at'
        ]
        for field in common_fields:
            self.assertEqual(
                list_data[field], detail_data[field],
                f"Field {field} should match between list and detail"
            )


class TransactionSerializerEdgeCasesTestCase(TestCase):
    """Test edge cases and special scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.goal = Goal.objects.create(
            user=self.user,
            name='Test Goal',
            target_amount=Decimal('100000.00'),
            currency='NGN'
        )
    
    def test_minimal_transaction_serialization(self):
        """Test serialization with minimal required fields."""
        transaction = Transaction.objects.create(
            user=self.user,
            type='CREDIT',
            amount=Decimal('1000.00'),
            currency='NGN',
            status='PENDING',
            request_ref='minimal_ref',
            occurred_at=datetime.now(timezone.utc)
        )
        
        serializer = TransactionListSerializer(transaction)
        data = serializer.data
        
        self.assertEqual(data['type'], 'CREDIT')
        self.assertEqual(data['amount'], '1000.00')
        self.assertIsNone(data['goal'])
        self.assertIsNone(data['collection'])
    
    def test_large_amount_serialization(self):
        """Test serialization with large amounts."""
        transaction = Transaction.objects.create(
            user=self.user,
            type='CREDIT',
            amount=Decimal('999999999999.99'),
            currency='NGN',
            status='SUCCESS',
            request_ref='large_amount',
            occurred_at=datetime.now(timezone.utc)
        )
        
        serializer = TransactionListSerializer(transaction)
        data = serializer.data
        
        self.assertEqual(data['amount'], '999999999999.99')
    
    def test_empty_metadata_serialization(self):
        """Test serialization with empty metadata."""
        transaction = Transaction.objects.create(
            user=self.user,
            type='CREDIT',
            amount=Decimal('1000.00'),
            currency='NGN',
            status='SUCCESS',
            request_ref='no_metadata',
            occurred_at=datetime.now(timezone.utc),
            metadata={}
        )
        
        serializer = TransactionListSerializer(transaction)
        data = serializer.data
        
        self.assertEqual(data['metadata'], {})
    
    def test_all_transaction_types_titles(self):
        """Test title generation for all transaction types."""
        types_and_titles = [
            ('CREDIT', 'Credit'),
            ('DEBIT', 'Debit'),
            ('FEE', 'Kore Fee')
        ]
        
        for trans_type, expected_title in types_and_titles:
            transaction = Transaction.objects.create(
                user=self.user,
                type=trans_type,
                amount=Decimal('100.00'),
                currency='NGN',
                status='SUCCESS',
                request_ref=f'ref_{trans_type}',
                occurred_at=datetime.now(timezone.utc)
            )
            
            serializer = TransactionListSerializer(transaction)
            data = serializer.data
            
            self.assertEqual(
                data['title'], expected_title,
                f"Title for {trans_type} should be {expected_title}"
            )
