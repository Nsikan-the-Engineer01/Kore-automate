import unittest
from decimal import Decimal
from django.test import TestCase

from core_apps.ledger.services import LedgerService, LedgerError
from core_apps.ledger.models import LedgerAccount, JournalEntry, LedgerLine
from core_apps.collections.models import Collection
from core_apps.goals.models import Goal
from django.contrib.auth import get_user_model

User = get_user_model()


class TestLedgerServiceAccountInitialization(TestCase):
    """Tests for system account creation and management."""
    
    def setUp(self):
        self.service = LedgerService()
        # Clear accounts before each test
        LedgerAccount.objects.all().delete()
    
    def test_ensure_accounts_exist_creates_all_accounts(self):
        """Test that all three system accounts are created."""
        accounts = self.service.ensure_accounts_exist()
        
        self.assertEqual(len(accounts), 3)
        self.assertIn(self.service.CLEARING_ASSET_CODE, accounts)
        self.assertIn(self.service.PARTNER_PAYABLE_CODE, accounts)
        self.assertIn(self.service.KORE_REVENUE_CODE, accounts)
    
    def test_ensure_accounts_exist_with_correct_types(self):
        """Test that accounts are created with correct types."""
        accounts = self.service.ensure_accounts_exist()
        
        self.assertEqual(accounts[self.service.CLEARING_ASSET_CODE].type, "ASSET")
        self.assertEqual(accounts[self.service.PARTNER_PAYABLE_CODE].type, "LIABILITY")
        self.assertEqual(accounts[self.service.KORE_REVENUE_CODE].type, "INCOME")
    
    def test_ensure_accounts_exist_idempotent(self):
        """Test that ensure_accounts_exist is idempotent."""
        # First call creates accounts
        accounts1 = self.service.ensure_accounts_exist()
        count_after_first = LedgerAccount.objects.count()
        
        # Second call should not create duplicates
        accounts2 = self.service.ensure_accounts_exist()
        count_after_second = LedgerAccount.objects.count()
        
        self.assertEqual(count_after_first, count_after_second)
        self.assertEqual(count_after_first, 3)
        self.assertEqual(accounts1[self.service.CLEARING_ASSET_CODE].id,
                        accounts2[self.service.CLEARING_ASSET_CODE].id)
    
    def test_ensure_accounts_exist_returns_dict(self):
        """Test that ensure_accounts_exist returns dictionary keyed by code."""
        accounts = self.service.ensure_accounts_exist()
        
        self.assertIsInstance(accounts, dict)
        self.assertEqual(accounts["1000"].code, "1000")
        self.assertEqual(accounts["2000"].code, "2000")
        self.assertEqual(accounts["4000"].code, "4000")


class TestLedgerValidation(unittest.TestCase):
    """Tests for ledger entry validation."""
    
    def setUp(self):
        self.service = LedgerService()
    
    def test_validate_entry_balanced(self):
        """Test validation passes when debits equal credits."""
        debits = Decimal('1000.00')
        credits = Decimal('1000.00')
        
        # Should not raise
        self.service.validate_entry(debits, credits)
    
    def test_validate_entry_unbalanced_debit_greater(self):
        """Test validation fails when debits > credits."""
        debits = Decimal('1100.00')
        credits = Decimal('1000.00')
        
        with self.assertRaises(LedgerError) as ctx:
            self.service.validate_entry(debits, credits)
        
        self.assertIn('imbalance', str(ctx.exception).lower())
    
    def test_validate_entry_unbalanced_credit_greater(self):
        """Test validation fails when credits > debits."""
        debits = Decimal('900.00')
        credits = Decimal('1000.00')
        
        with self.assertRaises(LedgerError) as ctx:
            self.service.validate_entry(debits, credits)
        
        self.assertIn('imbalance', str(ctx.exception).lower())
    
    def test_validate_entry_zero_values(self):
        """Test validation with zero amounts."""
        debits = Decimal('0.00')
        credits = Decimal('0.00')
        
        # Should not raise
        self.service.validate_entry(debits, credits)


class TestLedgerServiceCollectionPosting(TestCase):
    """Integration tests for posting collections to ledger."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='ledger_test',
            email='ledger@test.com',
            password='pass123'
        )
        cls.goal = Goal.objects.create(
            user=cls.user,
            name='Ledger Test Goal',
            target_amount=Decimal('100000.00'),
            status='ACTIVE'
        )
    
    def setUp(self):
        self.service = LedgerService()
        # Clear entries before each test
        JournalEntry.objects.all().delete()
        LedgerLine.objects.all().delete()
    
    def test_post_collection_success_creates_journal_entry(self):
        """Test that posting creates a journal entry with correct reference."""
        collection = Collection.objects.create(
            user=self.user,
            goal=self.goal,
            amount_allocation=Decimal('10000.00'),
            kore_fee=Decimal('250.00'),
            amount_total=Decimal('10250.00'),
            currency='NGN',
            request_ref='je-test-ref-123',
            status='SUCCESS',
            raw_request={},
            raw_response={}
        )
        
        journal_entry, lines = self.service.post_collection_success(collection)
        
        self.assertIsNotNone(journal_entry.id)
        self.assertEqual(journal_entry.reference, 'je-test-ref-123')
        self.assertIn('Collection success', journal_entry.memo)
    
    def test_post_collection_success_creates_ledger_lines(self):
        """Test that three ledger lines are created."""
        collection = Collection.objects.create(
            user=self.user,
            goal=self.goal,
            amount_allocation=Decimal('5000.00'),
            kore_fee=Decimal('100.00'),
            amount_total=Decimal('5100.00'),
            currency='NGN',
            request_ref='je-lines-test',
            status='SUCCESS',
            raw_request={},
            raw_response={}
        )
        
        journal_entry, lines = self.service.post_collection_success(collection)
        
        # Should have 3 lines: 1 debit + 2 credits
        self.assertEqual(len(lines), 3)
        
        # Verify line types
        debit_lines = [l for l in lines if l.debit > 0]
        credit_lines = [l for l in lines if l.credit > 0]
        
        self.assertEqual(len(debit_lines), 1)
        self.assertEqual(len(credit_lines), 2)
    
    def test_post_collection_success_debit_clearing_asset(self):
        """Test that debit line goes to clearing asset."""
        collection = Collection.objects.create(
            user=self.user,
            goal=self.goal,
            amount_allocation=Decimal('8000.00'),
            kore_fee=Decimal('200.00'),
            amount_total=Decimal('8200.00'),
            currency='NGN',
            request_ref='je-debit-test',
            status='SUCCESS',
            raw_request={},
            raw_response={}
        )
        
        journal_entry, lines = self.service.post_collection_success(collection)
        
        debit_line = next(l for l in lines if l.debit > 0)
        
        self.assertEqual(debit_line.account.code, self.service.CLEARING_ASSET_CODE)
        self.assertEqual(debit_line.debit, Decimal('8200.00'))
        self.assertEqual(debit_line.credit, Decimal('0.00'))
    
    def test_post_collection_success_credits_partner_payable(self):
        """Test that partner payable credit is created."""
        collection = Collection.objects.create(
            user=self.user,
            goal=self.goal,
            amount_allocation=Decimal('7500.00'),
            kore_fee=Decimal('187.50'),
            amount_total=Decimal('7687.50'),
            currency='NGN',
            request_ref='je-credit-payable-test',
            status='SUCCESS',
            raw_request={},
            raw_response={}
        )
        
        journal_entry, lines = self.service.post_collection_success(collection)
        
        payable_line = next(
            l for l in lines
            if l.account.code == self.service.PARTNER_PAYABLE_CODE
        )
        
        self.assertEqual(payable_line.credit, Decimal('7500.00'))
        self.assertEqual(payable_line.debit, Decimal('0.00'))
    
    def test_post_collection_success_credits_kore_revenue(self):
        """Test that kore revenue credit is created."""
        collection = Collection.objects.create(
            user=self.user,
            goal=self.goal,
            amount_allocation=Decimal('6000.00'),
            kore_fee=Decimal('300.00'),
            amount_total=Decimal('6300.00'),
            currency='NGN',
            request_ref='je-credit-revenue-test',
            status='SUCCESS',
            raw_request={},
            raw_response={}
        )
        
        journal_entry, lines = self.service.post_collection_success(collection)
        
        revenue_line = next(
            l for l in lines
            if l.account.code == self.service.KORE_REVENUE_CODE
        )
        
        self.assertEqual(revenue_line.credit, Decimal('300.00'))
        self.assertEqual(revenue_line.debit, Decimal('0.00'))
    
    def test_post_collection_success_balances(self):
        """Test that debits equal credits."""
        collection = Collection.objects.create(
            user=self.user,
            goal=self.goal,
            amount_allocation=Decimal('10000.00'),
            kore_fee=Decimal('250.00'),
            amount_total=Decimal('10250.00'),
            currency='NGN',
            request_ref='je-balance-test',
            status='SUCCESS',
            raw_request={},
            raw_response={}
        )
        
        journal_entry, lines = self.service.post_collection_success(collection)
        
        total_debits = sum(l.debit for l in lines)
        total_credits = sum(l.credit for l in lines)
        
        self.assertEqual(total_debits, Decimal('10250.00'))
        self.assertEqual(total_credits, Decimal('10250.00'))
    
    def test_post_collection_success_zero_fee(self):
        """Test posting when kore fee is zero."""
        collection = Collection.objects.create(
            user=self.user,
            goal=self.goal,
            amount_allocation=Decimal('5000.00'),
            kore_fee=Decimal('0.00'),
            amount_total=Decimal('5000.00'),
            currency='NGN',
            request_ref='je-zero-fee-test',
            status='SUCCESS',
            raw_request={},
            raw_response={}
        )
        
        journal_entry, lines = self.service.post_collection_success(collection)
        
        # Should have only 2 lines (debit + payable credit, no revenue line)
        self.assertEqual(len(lines), 2)
        
        total_debits = sum(l.debit for l in lines)
        total_credits = sum(l.credit for l in lines)
        
        self.assertEqual(total_debits, total_credits)
        self.assertEqual(total_debits, Decimal('5000.00'))
    
    def test_post_collection_non_success_status_fails(self):
        """Test that posting collection with non-SUCCESS status raises error."""
        collection = Collection.objects.create(
            user=self.user,
            goal=self.goal,
            amount_allocation=Decimal('1000.00'),
            kore_fee=Decimal('25.00'),
            amount_total=Decimal('1025.00'),
            currency='NGN',
            request_ref='je-fail-test',
            status='INITIATED',  # Not SUCCESS
            raw_request={},
            raw_response={}
        )
        
        with self.assertRaises(LedgerError) as ctx:
            self.service.post_collection_success(collection)
        
        self.assertIn('SUCCESS', str(ctx.exception))
    
    def test_post_collection_idempotent_by_reference(self):
        """Test that posting same collection twice creates separate entries."""
        collection = Collection.objects.create(
            user=self.user,
            goal=self.goal,
            amount_allocation=Decimal('3000.00'),
            kore_fee=Decimal('75.00'),
            amount_total=Decimal('3075.00'),
            currency='NGN',
            request_ref='je-idem-test',
            status='SUCCESS',
            raw_request={},
            raw_response={}
        )
        
        # Post same collection twice
        entry1, _ = self.service.post_collection_success(collection)
        entry2, _ = self.service.post_collection_success(collection)
        
        # Each call creates a new entry (reference can be duplicated)
        self.assertNotEqual(entry1.id, entry2.id)
        
        # But both have same reference
        self.assertEqual(entry1.reference, entry2.reference)
    
    def test_post_collection_with_narrative(self):
        """Test that collection narrative is included in journal memo."""
        collection = Collection.objects.create(
            user=self.user,
            goal=self.goal,
            amount_allocation=Decimal('2000.00'),
            kore_fee=Decimal('50.00'),
            amount_total=Decimal('2050.00'),
            currency='NGN',
            request_ref='je-narrative-test',
            narrative='Monthly contribution for education fund',
            status='SUCCESS',
            raw_request={},
            raw_response={}
        )
        
        journal_entry, _ = self.service.post_collection_success(collection)
        
        self.assertIn('Monthly contribution for education fund', journal_entry.memo)


if __name__ == '__main__':
    unittest.main()
