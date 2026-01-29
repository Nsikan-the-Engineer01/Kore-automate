# Webhook Idempotency - Quick Reference

## What Was Added

✅ **Event Deduplication** — Detect and skip duplicate webhook events  
✅ **Distributed Locking** — Prevent race conditions during updates  
✅ **Idempotent Updates** — Protect terminal statuses (SUCCESS/FAILED)  
✅ **Comprehensive Tests** — 30+ test cases with full coverage  
✅ **Complete Documentation** — 400+ lines with examples and patterns  

---

## Quick Start

### 1. Event ID Extraction

```python
from core_apps.webhooks.utils import extract_event_id

payload = {'event_id': 'evt_123', 'status': 'success'}
event_id = extract_event_id(payload)  # → 'evt_123'
```

### 2. Processing Lock

```python
from core_apps.webhooks.idempotency import processing_lock

with processing_lock('request_ref_123', timeout=30):
    collection = Collection.objects.get(request_ref='request_ref_123')
    collection.status = 'SUCCESS'
    collection.save()
```

### 3. Status Update Rules

```python
from core_apps.collections.idempotency import IdempotentCollectionUpdate

# Check if update allowed
should_update = IdempotentCollectionUpdate.should_update(
    current_status='SUCCESS',
    new_status='PENDING',
    allow_override=False
)
# → False (would downgrade, blocked)

# Get update fields
fields = IdempotentCollectionUpdate.get_update_fields(
    current_status='INITIATED',
    new_status='SUCCESS'
)
# → {'status': 'SUCCESS'}
```

---

## Status Hierarchy

```
INITIATED (1)
    ↓
PENDING (2)
    ↓
PROCESSING (3)
    ↓
SUCCESS (4) ← Terminal [No further changes]
FAILED (4)  ← Terminal [No further changes]
```

**Rules:**
- ✅ Forward only: INITIATED → PENDING → SUCCESS
- ✅ Same status: SUCCESS → SUCCESS (idempotent)
- ❌ Backward blocked: SUCCESS → PENDING (downgrade)
- ⚠️ Override: `allow_override=True` bypasses all checks

---

## Duplicate Handling

```
First webhook (event_id=evt_abc):
  ✓ Creates WebhookEvent
  ✓ Processes asynchronously

Duplicate webhook (event_id=evt_abc):
  ✓ Returns existing WebhookEvent
  ✓ Skips reprocessing
```

**Implementation:**
- Database unique constraint on `event_id`
- Application-level check before creation
- IntegrityError handling for race conditions

---

## Distributed Lock

```
Multiple webhooks for same collection:

Webhook 1: Acquire lock → Update collection → Release lock
                             ↓
Webhook 2: Wait for lock → Update when ready → Release
                  (up to 10 seconds)
```

**Modes:**
- **Redis:** Fast, distributed, Lua-safe deletion
- **Fallback:** DB-only, always available, slower

---

## Configuration

### Optional: Redis

```python
# settings/base.py
REDIS_URL = 'redis://localhost:6379/0'
```

### Without Redis

```python
# Nothing needed! Uses DB fallback
# Just remove REDIS_URL from settings
```

---

## Logging

### What to Monitor

```
DEBUG: "Acquired Redis lock: webhook_processing:request_ref_123"
INFO:  "Duplicate webhook event detected: event_id=evt_abc"
INFO:  "Skipping status update: already in terminal status SUCCESS"
WARN:  "Failed to acquire Redis lock after 10s"
ERROR: "CollectionError processing webhook"
```

### Check for Duplicates

```bash
# How many webhooks had duplicate event_ids?
python manage.py shell
>>> from core_apps.webhooks.models import WebhookEvent
>>> WebhookEvent.objects.filter(event_id__isnull=False).count()
```

### Check for Skipped Updates

```bash
# Look for idempotency skips in logs
grep "Skipping status update" logs/*.log | wc -l
```

---

## Testing

### Run Tests

```bash
cd api
python manage.py test core_apps.webhooks.idempotency_tests
```

### Test Specific Feature

```bash
# Event extraction
python manage.py test core_apps.webhooks.idempotency_tests.ExtractEventIdTestCase

# Lock functionality
python manage.py test core_apps.webhooks.idempotency_tests.ProcessingLockTestCase

# Status update rules
python manage.py test core_apps.webhooks.idempotency_tests.IdempotentCollectionUpdateTestCase
```

---

## Common Patterns

### Detect Duplicate

```python
from core_apps.webhooks.models import WebhookEvent

try:
    existing = WebhookEvent.objects.get(event_id=event_id)
    # Duplicate detected, return existing
    return existing
except WebhookEvent.DoesNotExist:
    # First occurrence, create new
    webhook_event = WebhookEvent.objects.create(...)
```

### Safe Update with Lock

```python
from core_apps.webhooks.idempotency import processing_lock, LockError

try:
    with processing_lock('request_ref_123'):
        # Update protected by lock
        collection = Collection.objects.select_for_update().get(
            request_ref='request_ref_123'
        )
        collection.status = 'SUCCESS'
        collection.save()
except LockError:
    # Fallback: still safe due to idempotency
    logger.warning("Could not acquire lock, proceeding...")
```

### Idempotent Status Update

```python
from core_apps.collections.idempotency import IdempotentCollectionUpdate

def update_collection(collection, new_status, allow_override=False):
    if not IdempotentCollectionUpdate.should_update(
        collection.status, new_status, allow_override
    ):
        logger.info("Skipped update due to idempotency")
        return
    
    collection.status = new_status
    collection.save()
```

---

## Files Modified

| File | Purpose |
|------|---------|
| `core_apps/webhooks/utils.py` | Added `extract_event_id()` |
| `core_apps/webhooks/idempotency.py` | NEW: Lock, checker, status rules |
| `core_apps/webhooks/services.py` | Added dedup in `receive_event()`, lock in `process_event()` |
| `core_apps/webhooks/idempotency_tests.py` | NEW: 30+ test cases |
| `core_apps/collections/services.py` | Added idempotency in `update_collection_from_webhook()` |
| `core_apps/collections/idempotency.py` | NEW: Status update rules |
| `WEBHOOKS_IDEMPOTENCY.md` | NEW: Full guide |
| `IDEMPOTENCY_IMPLEMENTATION.md` | NEW: Implementation summary |

---

## Troubleshooting

### "Failed to acquire Redis lock"

```
✓ Check Redis is running: redis-cli ping
✓ Increase wait_timeout in processing_lock() call
✓ Fall back to DB-only mode (remove REDIS_URL)
```

### Collection status not updating

```
✓ Check WebhookEvent.status == 'PROCESSED'
✓ Check logs for "Skipping status update"
✓ Verify current collection status: Collection.objects.get(...).status
✓ Use allow_override=True if manual correction needed
```

### Too many duplicate events

```
✓ Check provider webhook retry configuration
✓ Verify extract_event_id() finds correct field
✓ Monitor with: WebhookEvent.objects.filter(event_id__isnull=False).count()
```

---

## Key Benefits

| Feature | Benefit |
|---------|---------|
| **Event Deduplication** | Eliminate wasted processing, reduce API calls |
| **Distributed Lock** | Prevent race conditions safely |
| **Idempotent Updates** | Protect data integrity, handle retries |
| **Optional Redis** | Works without additional infrastructure |
| **DB Fallback** | Always safe, graceful degradation |
| **Comprehensive Tests** | Production-ready with 30+ test cases |

---

## Status Update Examples

### ✅ Allowed Updates

```
INITIATED → SUCCESS     (forward progression)
PENDING → SUCCESS       (forward progression)
SUCCESS → SUCCESS       (idempotent)
FAILED → FAILED         (idempotent)
ANY → ANY (allow_override=True)
```

### ❌ Blocked Updates

```
SUCCESS → PENDING       (downgrade, blocked)
SUCCESS → INITIATED     (downgrade, blocked)
FAILED → PENDING        (downgrade, blocked)
ANY → ANY (without override or forward rule)
```

---

## More Information

📖 **Full Guide:** See [WEBHOOKS_IDEMPOTENCY.md](WEBHOOKS_IDEMPOTENCY.md)  
📋 **Implementation:** See [IDEMPOTENCY_IMPLEMENTATION.md](IDEMPOTENCY_IMPLEMENTATION.md)  
🔍 **Field Extraction:** See [WEBHOOKS_PARSING_HELPERS.md](WEBHOOKS_PARSING_HELPERS.md)  
🌐 **API Reference:** See [WEBHOOKS_API.md](WEBHOOKS_API.md)
