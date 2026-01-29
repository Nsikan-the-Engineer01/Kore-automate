import logging
from decimal import Decimal
from typing import Dict, Tuple

from django.db import transaction as db_transaction
from django.utils import timezone

from core_apps.ledger.models import LedgerAccount, JournalEntry, LedgerLine
from core_apps.collections.models import Collection

logger = logging.getLogger(__name__)


class LedgerError(Exception):
    """Exception raised for ledger-related errors."""
    pass


class LedgerService:
    """Service for managing double-entry bookkeeping ledger entries."""
    
    # Standard system account codes
    CLEARING_ASSET_CODE = "1000"
    PARTNER_PAYABLE_CODE = "2000"
    KORE_REVENUE_CODE = "4000"
    
    # Account details mapping
    SYSTEM_ACCOUNTS = {
        CLEARING_ASSET_CODE: {
            "name": "Clearing Asset (Funds Collected)",
            "type": "ASSET"
        },
        PARTNER_PAYABLE_CODE: {
            "name": "Partner Payable (Funds to Partners)",
            "type": "LIABILITY"
        },
        KORE_REVENUE_CODE: {
            "name": "Kore Revenue (Transaction Fees)",
            "type": "INCOME"
        }
    }
    
    def __init__(self):
        pass
    
    def ensure_accounts_exist(self) -> Dict[str, LedgerAccount]:
        """
        Ensure all required system accounts exist; create if missing.
        
        Returns:
            Dictionary mapping code -> LedgerAccount instance
        """
        accounts = {}
        
        for code, details in self.SYSTEM_ACCOUNTS.items():
            account, created = LedgerAccount.objects.get_or_create(
                code=code,
                defaults={
                    "name": details["name"],
                    "type": details["type"]
                }
            )
            
            if created:
                logger.info(f"Created system account: {code} - {details['name']}")
            
            accounts[code] = account
        
        logger.debug(f"System accounts ready: {list(accounts.keys())}")
        return accounts
    
    @staticmethod
    def validate_entry(debits: Decimal, credits: Decimal) -> None:
        """
        Validate that debits equal credits (double-entry bookkeeping principle).
        
        Args:
            debits: Sum of all debit amounts
            credits: Sum of all credit amounts
            
        Raises:
            LedgerError: If debits != credits
        """
        if debits != credits:
            raise LedgerError(
                f"Ledger entry imbalance: debits ({debits}) != credits ({credits})"
            )
    
    @db_transaction.atomic
    def post_collection_success(self, collection: Collection) -> Tuple[JournalEntry, list]:
        """
        Post successful collection to general ledger using double-entry bookkeeping.
        
        Entry structure:
        ├─ Debit: CLEARING_ASSET (amount_total)
        ├─ Credit: PARTNER_PAYABLE (amount_allocation)
        └─ Credit: KORE_REVENUE (kore_fee)
        
        Args:
            collection: Collection instance (must have status SUCCESS)
            
        Returns:
            Tuple of (JournalEntry, [LedgerLine, ...])
            
        Raises:
            LedgerError: If entry cannot be created or validation fails
        """
        
        if collection.status != "SUCCESS":
            raise LedgerError(
                f"Cannot post collection with status {collection.status}; "
                f"expected SUCCESS"
            )
        
        # Ensure system accounts exist
        accounts = self.ensure_accounts_exist()
        
        logger.info(
            f"Posting collection to ledger: collection={collection.id}, "
            f"amount_total={collection.amount_total}"
        )
        
        # Create journal entry
        journal_entry = JournalEntry.objects.create(
            reference=collection.request_ref,
            memo=f"Collection success - {collection.narrative or 'General collection'}"
        )
        
        logger.debug(f"Created journal entry: {journal_entry.id}")
        
        # Prepare ledger lines
        ledger_lines = []
        total_debits = Decimal('0.00')
        total_credits = Decimal('0.00')
        
        try:
            # Debit: Clearing Asset
            debit_line = LedgerLine.objects.create(
                journal_entry=journal_entry,
                account=accounts[self.CLEARING_ASSET_CODE],
                debit=collection.amount_total,
                credit=Decimal('0.00')
            )
            ledger_lines.append(debit_line)
            total_debits += collection.amount_total
            
            logger.debug(
                f"Created debit line: {self.CLEARING_ASSET_CODE} "
                f"Debit={collection.amount_total}"
            )
            
            # Credit: Partner Payable (for allocation)
            credit_payable_line = LedgerLine.objects.create(
                journal_entry=journal_entry,
                account=accounts[self.PARTNER_PAYABLE_CODE],
                debit=Decimal('0.00'),
                credit=collection.amount_allocation
            )
            ledger_lines.append(credit_payable_line)
            total_credits += collection.amount_allocation
            
            logger.debug(
                f"Created credit line (payable): {self.PARTNER_PAYABLE_CODE} "
                f"Credit={collection.amount_allocation}"
            )
            
            # Credit: Kore Revenue (for fee)
            if collection.kore_fee > 0:
                credit_revenue_line = LedgerLine.objects.create(
                    journal_entry=journal_entry,
                    account=accounts[self.KORE_REVENUE_CODE],
                    debit=Decimal('0.00'),
                    credit=collection.kore_fee
                )
                ledger_lines.append(credit_revenue_line)
                total_credits += collection.kore_fee
                
                logger.debug(
                    f"Created credit line (revenue): {self.KORE_REVENUE_CODE} "
                    f"Credit={collection.kore_fee}"
                )
            
            # Validate double-entry bookkeeping
            self.validate_entry(total_debits, total_credits)
            
            logger.info(
                f"Posted collection to ledger: entry={journal_entry.id}, "
                f"debits={total_debits}, credits={total_credits}"
            )
            
            return journal_entry, ledger_lines
        
        except LedgerError:
            raise
        except Exception as e:
            logger.error(f"Error creating ledger lines: {str(e)}")
            # Note: Journal entry will be rolled back due to @atomic
            raise LedgerError(f"Failed to create ledger entry: {str(e)}")
