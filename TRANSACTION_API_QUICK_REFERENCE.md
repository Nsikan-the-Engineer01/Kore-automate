# Transaction API - Quick Reference

**Status:** ✅ Production Ready

---

## Endpoints

```
GET  /api/v1/transactions/           # List (with filters)
GET  /api/v1/transactions/{id}/      # Retrieve
```

Both require: `Authorization: Bearer <token>`

---

## Query Parameters

| Param | Type | Values | Example |
|-------|------|--------|---------|
| `goal_id` | UUID | Goal UUID | 550e8400-... |
| `status` | String | PENDING, SUCCESS, FAILED | SUCCESS |
| `type` | String | CREDIT, DEBIT, FEE | CREDIT |
| `from_date` | ISO DateTime | YYYY-MM-DDTHH:MM:SSZ | 2026-01-01T00:00:00Z |
| `to_date` | ISO DateTime | YYYY-MM-DDTHH:MM:SSZ | 2026-01-31T23:59:59Z |
| `collection_id` | UUID | Collection UUID | 770e8400-... |
| `ordering` | String | -occurred_at (default), occurred_at, -amount, amount, -created_at, created_at | -occurred_at |
| `page` | Integer | Page number | 1 |

---

## Usage Examples

### List All
```bash
curl http://localhost:8000/api/v1/transactions/ \
  -H "Authorization: Bearer <token>"
```

### By Status
```bash
curl "http://localhost:8000/api/v1/transactions/?status=SUCCESS" \
  -H "Authorization: Bearer <token>"
```

### By Goal
```bash
curl "http://localhost:8000/api/v1/transactions/?goal_id=550e8400-..." \
  -H "Authorization: Bearer <token>"
```

### By Type
```bash
curl "http://localhost:8000/api/v1/transactions/?type=CREDIT" \
  -H "Authorization: Bearer <token>"
```

### Date Range
```bash
curl "http://localhost:8000/api/v1/transactions/?from_date=2026-01-01&to_date=2026-01-31" \
  -H "Authorization: Bearer <token>"
```

### Combined Filters
```bash
curl "http://localhost:8000/api/v1/transactions/?goal_id=550e8400-...&status=SUCCESS&type=CREDIT" \
  -H "Authorization: Bearer <token>"
```

### Retrieve One
```bash
curl http://localhost:8000/api/v1/transactions/550e8400-.../ \
  -H "Authorization: Bearer <token>"
```

---

## Response Fields

```json
{
  "id": "UUID",
  "type": "CREDIT|DEBIT|FEE",
  "amount": "string (decimal)",
  "currency": "NGN",
  "status": "PENDING|SUCCESS|FAILED",
  "title": "Credit|Debit|Kore Fee",
  "goal": {
    "id": "UUID",
    "name": "string"
  },
  "collection": {
    "id": "UUID"
  },
  "request_ref": "string",
  "provider_ref": "string|null",
  "occurred_at": "datetime",
  "created_at": "datetime",
  "updated_at": "datetime",
  "metadata": "object"
}
```

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 401 | Unauthorized |
| 404 | Not found |
| 500 | Server error |

---

## Testing

```bash
# All tests
python manage.py test core_apps.transactions -v 2

# ViewSet tests only
python manage.py test core_apps.transactions.tests_viewset -v 2
```

---

## Common Patterns

### User's Goal Transactions (This Month)
```bash
curl "http://localhost:8000/api/v1/transactions/?goal_id=550e8400-...&from_date=2026-01-01&to_date=2026-01-31" \
  -H "Authorization: Bearer <token>"
```

### All Credits (Successful)
```bash
curl "http://localhost:8000/api/v1/transactions/?type=CREDIT&status=SUCCESS" \
  -H "Authorization: Bearer <token>"
```

### Recent Transactions (Newest First)
```bash
curl "http://localhost:8000/api/v1/transactions/?ordering=-occurred_at" \
  -H "Authorization: Bearer <token>"
```

### Fees This Month
```bash
curl "http://localhost:8000/api/v1/transactions/?type=FEE&from_date=2026-01-01&to_date=2026-01-31" \
  -H "Authorization: Bearer <token>"
```

---

## Features

✅ User-scoped (only own transactions)  
✅ Advanced filtering  
✅ Date range support  
✅ Pagination  
✅ Newest first ordering  
✅ Read-only (append-only ledger)  
✅ Optimized queries  
✅ Full test coverage

---

**Status:** 🚀 Ready for Production
