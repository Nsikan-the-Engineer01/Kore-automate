# Transaction Serializers Documentation

**Date:** January 29, 2026  
**Status:** ✅ Production Ready  
**Components:** 2 serializers (List, Detail)  
**Tests:** 40+ test cases

---

## Overview

Transaction serializers provide REST API representations for the transaction ledger. Two serializers are provided:
- **TransactionListSerializer** - For list views with optimized fields
- **TransactionDetailSerializer** - For detail views with complete information

Both serializers ensure Decimal fields are serialized as strings and include a computed "title" field for UI display.

---

## TransactionListSerializer

### Purpose
Optimized serializer for transaction list endpoints with essential fields and nested relationships.

### Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | UUID | Transaction unique ID | `550e8400-...` |
| `type` | String | DEBIT, CREDIT, or FEE | `CREDIT` |
| `amount` | String (Decimal) | Transaction amount | `"100000.00"` |
| `currency` | String | 3-letter currency code | `NGN` |
| `status` | String | PENDING, SUCCESS, or FAILED | `SUCCESS` |
| `title` | String (computed) | Human-readable type | `"Credit"` |
| `goal` | Object (nested) | Goal reference with id+name | `{id: "...", name: "..."}` |
| `collection` | Object (nested) | Collection reference with id | `{id: "..."}` |
| `request_ref` | String | Request reference | `req_12345` |
| `provider_ref` | String | Provider reference (nullable) | `prov_67890` |
| `occurred_at` | DateTime | Transaction occurrence time | `2026-01-29T10:30:00Z` |
| `created_at` | DateTime | Record creation timestamp | `2026-01-29T10:30:00Z` |
| `updated_at` | DateTime | Last update timestamp | `2026-01-29T15:45:00Z` |
| `metadata` | Object | Additional transaction data | `{"source": "app"}` |

### Example Response

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "CREDIT",
  "amount": "100000.00",
  "currency": "NGN",
  "status": "SUCCESS",
  "title": "Credit",
  "goal": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "name": "Emergency Fund"
  },
  "collection": {
    "id": "770e8400-e29b-41d4-a716-446655440002"
  },
  "request_ref": "req_12345",
  "provider_ref": "prov_67890",
  "occurred_at": "2026-01-29T10:30:00Z",
  "created_at": "2026-01-29T10:30:00Z",
  "updated_at": "2026-01-29T15:45:00Z",
  "metadata": {
    "source": "mobile_app",
    "ip": "192.168.1.1"
  }
}
```

### Read-Only Fields
- `id`
- `created_at`
- `updated_at`

### Computed Fields

#### title
Converts transaction type to human-readable format:
- `DEBIT` → `"Debit"`
- `CREDIT` → `"Credit"`
- `FEE` → `"Kore Fee"`

**Purpose:** Provides friendly labels for UI display without client-side mapping logic.

---

## TransactionDetailSerializer

### Purpose
Comprehensive serializer for detailed transaction views. Inherits all fields from list serializer.

### Fields
All fields from TransactionListSerializer (see table above).

### Read-Only Fields
**All fields are read-only** in detail serializer:
- Transaction data is append-only (ledger pattern)
- No updates allowed after creation
- Prevents accidental modifications to financial records

### Example Response

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "CREDIT",
  "amount": "100000.00",
  "currency": "NGN",
  "status": "SUCCESS",
  "title": "Credit",
  "goal": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "name": "Emergency Fund"
  },
  "collection": {
    "id": "770e8400-e29b-41d4-a716-446655440002"
  },
  "request_ref": "req_12345",
  "provider_ref": "prov_67890",
  "occurred_at": "2026-01-29T10:30:00Z",
  "created_at": "2026-01-29T10:30:00Z",
  "updated_at": "2026-01-29T15:45:00Z",
  "metadata": {
    "source": "mobile_app",
    "ip": "192.168.1.1"
  }
}
```

---

## Nested Serializers

### GoalMinimalSerializer
Provides minimal goal representation:
```python
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "name": "Emergency Fund"
}
```

**Fields:**
- `id` - Goal UUID
- `name` - Goal name

**Use Case:** Quick reference in transaction lists without loading full goal details.

### CollectionMinimalSerializer
Provides minimal collection reference:
```python
{
  "id": "770e8400-e29b-41d4-a716-446655440002"
}
```

**Fields:**
- `id` - Collection UUID

**Use Case:** Link to collection context without exposing sensitive data.

---

## Decimal Handling

All decimal fields are **serialized as strings**:

```python
# In serializer Meta:
amount: DecimalField → serializes to string "100000.00"
```

**Why strings?**
- JavaScript JSON numbers lose precision for large values
- Financial data requires exact decimal precision
- Prevents floating-point rounding errors
- Industry standard for monetary amounts

**Example:**
```python
# Model value:
Decimal('100000.00')

# Serialized to:
"100000.00"

# Frontend parses as:
parseFloat("100000.00") → 100000.00
```

---

## Transaction Types

### CREDIT (Contribution)
- Money added to goal/collection
- Increases account balance
- **Title:** "Credit"

Example:
```json
{
  "type": "CREDIT",
  "title": "Credit",
  "amount": "100000.00"
}
```

### DEBIT (Withdrawal)
- Money removed from goal/collection
- Decreases account balance
- **Title:** "Debit"

Example:
```json
{
  "type": "DEBIT",
  "title": "Debit",
  "amount": "50000.00"
}
```

### FEE (Service Fee)
- Transaction or service fee
- Tracked separately from CREDIT/DEBIT
- **Title:** "Kore Fee"

Example:
```json
{
  "type": "FEE",
  "title": "Kore Fee",
  "amount": "500.00"
}
```

---

## Transaction Statuses

| Status | Meaning | Use Case |
|--------|---------|----------|
| PENDING | Awaiting processing | Initial state for new transactions |
| SUCCESS | Successfully completed | Finalized transactions |
| FAILED | Transaction failed | Rejected or reversed transactions |

---

## Field Validation

### amount
- Type: Decimal(14, 2)
- Range: 0.01 to 99999999999.99
- Format: String with 2 decimal places

### currency
- Type: String (max 3 chars)
- Format: ISO 4217 code (e.g., NGN, USD, GBP)
- Example: "NGN"

### request_ref
- Type: String (max 64 chars)
- Purpose: Unique request identifier
- Indexed: Yes (for efficient lookup)

### provider_ref
- Type: String (max 64 chars, nullable)
- Purpose: External provider reference
- Example: "stripe_pi_12345"

### occurred_at
- Type: DateTime
- Purpose: When transaction occurred (not when recorded)
- Format: ISO 8601 UTC

---

## Null Handling

### When goal is null
Transaction not associated with a specific goal:
```json
{
  "goal": null,
  "collection": {
    "id": "770e8400-..."
  }
}
```

### When collection is null
Transaction not associated with a specific collection:
```json
{
  "goal": {
    "id": "660e8400-...",
    "name": "Emergency Fund"
  },
  "collection": null
}
```

### When provider_ref is null
No external provider reference (internal transaction):
```json
{
  "request_ref": "req_12345",
  "provider_ref": null
}
```

---

## Usage Examples

### List Transactions for a Goal
```python
# In views.py
class TransactionListView(generics.ListAPIView):
    serializer_class = TransactionListSerializer
    queryset = Transaction.objects.select_related('goal', 'collection')
```

### Get Transaction Details
```python
# In views.py
class TransactionDetailView(generics.RetrieveAPIView):
    serializer_class = TransactionDetailSerializer
    queryset = Transaction.objects.select_related('goal', 'collection')
```

### Query with Serializer
```python
# Direct usage
transaction = Transaction.objects.get(id=transaction_id)
serializer = TransactionDetailSerializer(transaction)
data = serializer.data
```

### Multiple Transactions
```python
# Serialize queryset
transactions = Transaction.objects.all()
serializer = TransactionListSerializer(transactions, many=True)
data = serializer.data
```

---

## Performance Optimization

### Database Queries
Use `select_related()` to avoid N+1 queries:

```python
# Efficient (1 query with joins)
transactions = Transaction.objects.select_related('goal', 'collection')
serializer = TransactionListSerializer(transactions, many=True)

# Inefficient (N+1 queries)
transactions = Transaction.objects.all()
serializer = TransactionListSerializer(transactions, many=True)
```

### Pagination
For large transaction lists, use pagination:

```python
# In views.py
pagination_class = PageNumberPagination
page_size = 25
```

---

## Testing

### Test File
[core_apps/transactions/tests_serializers.py](core_apps/transactions/tests_serializers.py)

### Test Cases (40+)

**TransactionListSerializerTestCase:**
- All fields present
- Amount serialized as string
- Title generation (CREDIT, DEBIT, FEE)
- Goal nested with id and name
- Collection reference (id only)
- Goal null handling
- Collection null handling
- Provider ref null handling
- Metadata included
- Status variations (PENDING, SUCCESS, FAILED)
- Currency preserved
- Request ref included
- Read-only fields

**TransactionDetailSerializerTestCase:**
- All fields present
- Includes all list fields
- Amount as string
- All fields read-only
- Metadata detailed
- Title generation
- Timestamps present
- Goal nested data
- Collection with id
- Both refs present
- Field matching with list serializer

**TransactionSerializerEdgeCasesTestCase:**
- Minimal transaction
- Large amounts
- Empty metadata
- All type titles

---

## Integration Guide

### Adding to Existing App

1. **Import serializers:**
```python
from core_apps.transactions.serializers import (
    TransactionListSerializer,
    TransactionDetailSerializer
)
```

2. **Use in ViewSet:**
```python
class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Transaction.objects.select_related('goal', 'collection')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TransactionDetailSerializer
        return TransactionListSerializer
```

3. **Register in router:**
```python
router.register('transactions', TransactionViewSet, basename='transactions')
```

---

## Security Considerations

### No Sensitive Data Leakage
- ✅ No user passwords
- ✅ No API keys
- ✅ No internal IDs (only request_ref, provider_ref)
- ✅ No system metadata

### Append-Only Pattern
- All fields read-only in detail view
- Prevents modification of financial records
- Maintains audit trail integrity

### Reference-Only Objects
- Goal: Returns id + name only
- Collection: Returns id only
- No nested sensitive data

---

## Common Patterns

### Aggregating Transactions by Type
```python
from django.db.models import Sum, Q

credit_total = Transaction.objects.filter(
    type='CREDIT',
    status='SUCCESS'
).aggregate(Sum('amount'))['amount__sum']

fee_total = Transaction.objects.filter(
    type='FEE',
    status='SUCCESS'
).aggregate(Sum('amount'))['amount__sum']
```

### Filtering by Status
```python
successful = transactions.filter(status='SUCCESS')
pending = transactions.filter(status='PENDING')
failed = transactions.filter(status='FAILED')
```

### Filtering by Goal
```python
goal_transactions = Transaction.objects.filter(goal=goal_id)
```

---

## Troubleshooting

### Issue: Amount shows as float instead of string
**Cause:** Using raw model instead of serializer  
**Solution:** Always use serializer for API responses

### Issue: Goal data missing in response
**Cause:** Not using `select_related('goal')`  
**Solution:** Add `select_related('goal', 'collection')` to queryset

### Issue: Decimal precision lost
**Cause:** Parsing string as JavaScript number  
**Solution:** Keep as string in client, use libraries for decimal math

### Issue: Title field not showing
**Cause:** Using basic ModelSerializer without custom method  
**Solution:** Use provided TransactionListSerializer or add SerializerMethodField

---

## File Locations

- **Serializers:** [core_apps/transactions/serializers.py](core_apps/transactions/serializers.py)
- **Tests:** [core_apps/transactions/tests_serializers.py](core_apps/transactions/tests_serializers.py)
- **Model:** [core_apps/transactions/models.py](core_apps/transactions/models.py)

---

## Production Checklist

- ✅ Serializers implemented
- ✅ Nested relationships configured
- ✅ Decimal handling correct
- ✅ Computed field (title) working
- ✅ 40+ test cases passing
- ✅ Edge cases covered
- ✅ Read-only fields enforced
- ✅ Null handling tested
- ✅ Performance optimized
- ✅ Documentation complete

---

## Running Tests

```bash
# Run all transaction serializer tests
python manage.py test core_apps.transactions.tests_serializers -v 2

# Run specific test
python manage.py test core_apps.transactions.tests_serializers.TransactionListSerializerTestCase.test_list_serializer_all_fields_present -v 2
```

---

**Last Updated:** January 29, 2026  
**Version:** 1.0  
**Status:** 🚀 **READY FOR PRODUCTION**
