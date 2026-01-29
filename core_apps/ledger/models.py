import uuid
from django.db import models
from django.core.exceptions import ValidationError


class LedgerAccount(models.Model):
    """Model for general ledger accounts."""
    
    TYPE_CHOICES = [
        ('ASSET', 'Asset'),
        ('LIABILITY', 'Liability'),
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
    ]
    
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=120)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    
    class Meta:
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class JournalEntry(models.Model):
    """Model for journal entries in the ledger."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=64, db_index=True)
    memo = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.reference} - {self.created_at.strftime('%Y-%m-%d')}"


class LedgerLine(models.Model):
    """Model for individual ledger entry lines."""
    
    journal_entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name='lines'
    )
    account = models.ForeignKey(
        LedgerAccount,
        on_delete=models.PROTECT,
        related_name='ledger_lines'
    )
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    
    class Meta:
        ordering = ['journal_entry', 'account']
    
    def clean(self):
        """Validate that exactly one of debit or credit is > 0."""
        debit_positive = self.debit > 0
        credit_positive = self.credit > 0
        
        # XOR: exactly one should be positive
        if not (debit_positive ^ credit_positive):
            raise ValidationError(
                'Exactly one of debit or credit must be greater than 0.'
            )
    
    def save(self, *args, **kwargs):
        """Save with validation."""
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.journal_entry.reference} - {self.account.code} - D:{self.debit} C:{self.credit}"
