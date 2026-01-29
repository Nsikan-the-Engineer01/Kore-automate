# Webhook Idempotency & Deduplication Guide

## Overview

This guide documents the idempotency and deduplication mechanisms for webhook processing in the PayWithAccount integration. These features ensure that:

1. **Duplicate events are detected and skipped** (via event_id deduplication)
2. **Race conditions are prevented** (via distributed locking)
3. **Collection status updates are idempotent** (prevent overwrites of terminal states)

## Architecture

### 1. Event Deduplication (Event ID)

**Problem:** Payment providers may deliver the same webhook event multiple times due to retry logic or network issues.

**Solution:** Store `event_id` from provider and enforce unique constraint in database.

```
Provider sends webhook → Extract event_id → Check DB → If exists, return existing → If new, create & process
```

**Database Level:**
- `WebhookEvent.event_id` field with `unique=True`
- Prevents duplicate entries at database constraint level
- Handles rare race conditions via IntegrityError handling

**Application Level:**
- Before creating `WebhookEvent`, query for existing `event_id`
- Return existing event immediately (no reprocessing)
- Reduces CPU/API calls by skipping reprocessing

**Event ID Extraction:**
The `extract_event_id()` helper tries multiple paths to find provider event identifiers:

```python
from core_apps.webhooks.utils import extract_event_id

payload = {
    'event_id': 'evt_123',
    'data': {'id': 'evt_456'},
    'event': {'id': 'evt_789'}
}

event_id = extract_event_id(payload)  # → 'evt_123' (first match)
```

**Supported field names:**
- Top-level: `event_id`, `eventId`, `event`, `id`, `webhook_id`, `webhookId`
- Provider-specific: `flutterwave_event_id`, `paystack_reference`, `monnify_transaction_ref`
- Nested: `event.id`, `data.event_id`, `meta.event_id`

**Flow:**
1. Provider sends webhook with `event_id`
2. `receive_event()` extracts `event_id` via `extract_event_id(payload)`
3. Checks if `WebhookEvent.objects.filter(event_id=event_id).exists()`
4. If exists: return existing `WebhookEvent` (no database create)
5. If new: create `WebhookEvent` and process normally
6. If race condition (IntegrityError): catch and return existing (rare)

### 2. Distributed Processing Lock

**Problem:** Multiple webhook events for same collection may arrive simultaneously, causing race conditions in status updates.

**Solution:** Use Redis-based distributed lock or DB fallback.

```
Lock acquired → Update collection → Release lock
   ↓
Multiple webhooks wait for lock
   ↓
Each processes in sequence (safe)
```

**Lock Implementation:**

The `ProcessingLock` class handles both Redis and fallback:

```python
from core_apps.webhooks.idempotency import processing_lock

# Context manager approach (recommended)
with processing_lock('request_ref_123', timeout=30):
    collection = Collection.objects.get(request_ref='request_ref_123')
    collection.status = 'SUCCESS'
    collection.save()
```

**Redis Mode (if available):**
- Uses Redis SET with NX (only if not exists) and EX (expiry)
- Lua script ensures safe deletion (only own lock)
- Automatic cleanup via TTL

**Database Fallback (if Redis not configured):**
- Skips lock acquisition (no-op)
- Relies on idempotent status update logic (see section 3)
- Still safe due to status hierarchy validation

**Configuration:**
```python
# settings/base.py
REDIS_URL = 'redis://localhost:6379/0'  # Optional
# OR use Django CACHES
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

**Timeout Parameters:**
- `timeout=30` — Lock TTL in seconds (Redis only)
- `wait_timeout=10` — Max time to wait for lock before proceeding without lock

### 3. Idempotent Status Updates

**Problem:** Once a collection reaches SUCCESS or FAILED, we shouldn't overwrite it with PENDING.

**Solution:** Enforce status hierarchy and terminal state rules.

```
Status progression:
INITIATED → PENDING → PROCESSING → SUCCESS
                                  → FAILED

Terminal states: SUCCESS, FAILED (no further changes unless idempotent)
```

**Rules:**
1. **Same status is always allowed** (idempotent re-delivery)
   - Collection is SUCCESS, webhook says SUCCESS → No change (allowed)
2. **Terminal states are protected** (no downgrade)
   - Collection is SUCCESS, webhook says PENDING → Blocked
   - Collection is FAILED, webhook says PENDING → Blocked
3. **Forward progression is allowed** (on first update)
   - Collection is INITIATED, webhook says SUCCESS → Allowed
   - Collection is PENDING, webhook says FAILED → Allowed
4. **Override available** (for manual corrections)
   - `allow_override=True` parameter bypasses all checks

**Implementation:**

```python
from core_apps.collections.idempotency import IdempotentCollectionUpdate

# Check if update should proceed
should_update = IdempotentCollectionUpdate.should_update(
    current_status='SUCCESS',
    new_status='PENDING',
    allow_override=False
)
# → False (don't update, would be downgrade)

# Get update fields
update_fields = IdempotentCollectionUpdate.get_update_fields(
    current_status='INITIATED',
    new_status='SUCCESS',
    allow_override=False
)
# → {'status': 'SUCCESS'} (allow forward progression)
```

**Status Hierarchy:**
```python
{
    'INITIATED': 1,      # Initial state
    'PENDING': 2,        # Payment processing
    'PROCESSING': 3,     # Additional validation
    'SUCCESS': 4,        # Terminal: payment successful
    'FAILED': 4,         # Terminal: payment failed (same level)
}
```

**Webhook Service Integration:**

The `update_collection_from_webhook()` method in `CollectionsService` automatically enforces idempotency:

```python
def update_collection_from_webhook(
    self,
    request_ref: str,
    provider_ref: str,
    new_status: str,
    payload: Dict[str, Any],
    response_body: Optional[Dict[str, Any]] = None,
    allow_override: bool = False  # ← Idempotency control
) -> Collection:
    # ...
    should_update = IdempotentCollectionUpdate.should_update(
        collection.status,
        normalized_status,
        allow_override=allow_override
    )
    
    if should_update:
        collection.status = normalized_status  # Update
    else:
        logger.info(f"Skipped status update due to idempotency rules")
    
    # Only update transactions if collection status was updated
    if should_update:
        # Update transactions
    else:
        logger.info("Skipped transaction update (idempotency)")
```

## Complete Flow

### Receiving a Webhook

```
1. POST /api/v1/webhooks/paywithaccount/
   ↓
2. PayWithAccountWebhookView.post()
   - Extract signature from headers
   - Call WebhookService.receive_paywithaccount_event()
   ↓
3. WebhookService.receive_event()
   - Extract event_id via extract_event_id(payload)
   - Check if WebhookEvent with this event_id exists
     - YES: Return existing event (no database create)
     - NO: Create new WebhookEvent with event_id
   ↓
4. Enqueue async processing (Celery or sync fallback)
   ↓
5. Return 200 OK immediately
```

### Processing a Webhook

```
1. WebhookService.process_event(webhook_event_id)
   ↓
2. Parse payload, extract request_ref, provider_ref, status
   ↓
3. Acquire processing lock for request_ref
   with processing_lock('webhook_processing:request_ref_123'):
   ↓
4. Call CollectionsService.update_collection_from_webhook(
     request_ref=request_ref,
     new_status=status,
     allow_override=False  # Standard mode
   )
   ↓
5. Inside update_collection_from_webhook():
   - Find collection by request_ref
   - Check idempotency:
     if IdempotentCollectionUpdate.should_update(
       current_status, new_status, allow_override=False
     ):
       - Update collection.status
       - Update transaction statuses (if PENDING)
     else:
       - Log skip, no changes
   ↓
6. Release processing lock
   ↓
7. Mark WebhookEvent as PROCESSED
   ↓
8. Return collection (updated or unchanged)
```

## Code Examples

### Handling Duplicate Webhook (Same event_id)

```python
# First delivery
event1 = webhook_service.receive_event(
    provider='paywithaccount',
    payload={'event_id': 'evt_abc123', 'status': 'success', ...}
)
# → Creates new WebhookEvent
# → Status: RECEIVED
# → Processes async

# Second delivery (same event)
event2 = webhook_service.receive_event(
    provider='paywithaccount',
    payload={'event_id': 'evt_abc123', 'status': 'success', ...}  # Identical
)
# → Returns existing WebhookEvent (event1.id == event2.id)
# → No database create (IntegrityError prevented)
# → No reprocessing (service returns existing)
```

### Idempotent Status Updates

```python
# Scenario 1: Normal update (first success)
collection = Collection(status='INITIATED')
result = update_collection_from_webhook(
    request_ref='req_123',
    new_status='SUCCESS',
    ...
)
# → collection.status = 'SUCCESS' ✓ (allowed, forward progression)

# Scenario 2: Duplicate success webhook (idempotent)
collection = Collection(status='SUCCESS')
result = update_collection_from_webhook(
    request_ref='req_123',
    new_status='SUCCESS',  # Same as current
    ...
)
# → collection.status = 'SUCCESS' (unchanged) ✓ (idempotent, no change)
# → Skips transaction updates
# → Logged as "Skipped status update" at INFO level

# Scenario 3: Webhook says PENDING after SUCCESS (blocked)
collection = Collection(status='SUCCESS')
result = update_collection_from_webhook(
    request_ref='req_123',
    new_status='PENDING',  # Would be downgrade
    ...
)
# → collection.status = 'SUCCESS' (unchanged) ✓ (idempotency protection)
# → Logged as "Skipping status update: already in terminal status"
# → Skips transaction updates

# Scenario 4: Force update (manual correction)
collection = Collection(status='SUCCESS')
result = update_collection_from_webhook(
    request_ref='req_123',
    new_status='FAILED',
    allow_override=True  # ← Override idempotency
)
# → collection.status = 'FAILED' ✓ (allowed due to override)
# → Updates transactions
```

### Processing Lock Usage

```python
from core_apps.webhooks.idempotency import processing_lock, LockError

try:
    with processing_lock('request_ref_123', timeout=30, wait_timeout=5):
        # This block executes with exclusive lock
        collection = Collection.objects.get(request_ref='request_ref_123')
        
        # Safe to update knowing no other process is here
        collection.status = 'SUCCESS'
        collection.save()
        
except LockError as e:
    logger.error(f"Could not acquire processing lock: {e}")
    # Fallback: still safe due to idempotency checks
    # Proceed without lock (db-level checks protect us)
```

### Checking Redis Availability

```python
from core_apps.webhooks.idempotency import has_redis, get_redis_client

# Check if Redis configured
if has_redis():
    logger.info("Redis available for distributed locking")
    redis_client = get_redis_client()
else:
    logger.info("Redis not configured, using DB fallback for locking")
```

## Configuration

### Settings

```python
# settings/base.py or settings/local.py

# Optional: Configure Redis for distributed locking
REDIS_URL = 'redis://localhost:6379/0'

# OR use Django caching Redis
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Webhook processing settings (optional)
WEBHOOK_CONFIG = {
    'LOCK_TIMEOUT': 30,  # Lock TTL in seconds
    'LOCK_WAIT_TIMEOUT': 10,  # Max wait for lock
    'EVENT_ID_CACHE_TTL': 3600,  # Event result cache duration (seconds)
}
```

### Environment Variables

```bash
# Optional Redis configuration
REDIS_URL=redis://localhost:6379/0
# OR
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

## Monitoring & Logging

### Log Levels

The idempotency system produces logs at different levels:

**DEBUG:**
- Lock acquisition/release: `"Acquired Redis lock: request_ref_123"`
- Event extraction: `"Parsed webhook: request_ref=..., status=..."`

**INFO:**
- Duplicate detection: `"Duplicate webhook event detected: event_id=..., existing_event=..."`
- Skipped updates: `"Skipping status update: collection already in terminal status SUCCESS"`
- Successful processing: `"Successfully processed webhook: collection=..., status=..."`

**WARNING:**
- Lock failures: `"Failed to acquire Redis lock after 10s: request_ref_123"`
- Race conditions: `"Race condition: IntegrityError creating webhook event with event_id=..."`

**ERROR:**
- Processing errors: `"CollectionError processing webhook ..."`
- Lock release failures: `"Error releasing Redis lock: ..."`

### Metrics to Monitor

1. **Duplicate Rate:** `WebhookEvent.objects.filter(event_id__isnull=False).count()` vs total events
2. **Lock Contention:** Count of "Failed to acquire..." log messages
3. **Idempotency Skips:** Count of "Skipping status update" log messages
4. **Processing Time:** Time from RECEIVED to PROCESSED status

## Testing

### Test Idempotency Checker

```python
from core_apps.webhooks.idempotency import IdempotencyChecker

checker = IdempotencyChecker()

# Cache event result
checker.cache_event_result(
    event_id='evt_123',
    result={'collection_id': 'col_456', 'status': 'SUCCESS'},
    ttl=3600
)

# Retrieve cached result
cached = checker.get_cached_event_id('evt_123')
assert cached['status'] == 'SUCCESS'
```

### Test Processing Lock

```python
from core_apps.webhooks.idempotency import processing_lock

# Single-threaded test
with processing_lock('test_key'):
    # Lock acquired
    assert True

# Lock released after context exit
```

### Test Idempotent Updates

```python
from core_apps.collections.idempotency import IdempotentCollectionUpdate

# Should allow same status
assert IdempotentCollectionUpdate.should_update('SUCCESS', 'SUCCESS') == True

# Should block downgrade
assert IdempotentCollectionUpdate.should_update('SUCCESS', 'PENDING') == False

# Should allow forward progression
assert IdempotentCollectionUpdate.should_update('INITIATED', 'SUCCESS') == True

# Should allow with override
assert IdempotentCollectionUpdate.should_update(
    'SUCCESS', 'PENDING', allow_override=True
) == True
```

## Troubleshooting

### "Failed to acquire Redis lock"

**Cause:** Redis is configured but unavailable, or timeout is too short.

**Solution:**
1. Check Redis is running: `redis-cli ping`
2. Increase `wait_timeout` in `processing_lock()` call
3. Fall back to DB-only mode by removing `REDIS_URL` (will still work, just slower)

### "Duplicate webhook event detected" appearing too often

**Cause:** Provider is retrying excessively, or same event_id format for different events.

**Solution:**
1. Check provider webhook configuration for retry settings
2. Verify `extract_event_id()` is finding correct field (may need custom path)
3. Monitor webhook event creation rate

### Collection status not updating

**Cause:** Idempotency rules are preventing update (e.g., trying to downgrade from SUCCESS).

**Solution:**
1. Check webhook payload status matches expected progression
2. Verify collection's current status with: `Collection.objects.get(id=...).status`
3. If override needed: set `allow_override=True` in `update_collection_from_webhook()`

## References

- [Webhook Parsing Helpers](WEBHOOKS_PARSING_HELPERS.md) — Extract fields from diverse payloads
- [Webhooks API](WEBHOOKS_API.md) — Full webhook endpoint documentation
- [Collections Validation](COLLECTIONS_VALIDATION_HANDLING.md) — OTP/validation flows
- [PayWithAccount Quick Reference](PAYWITHACCOUNT_QUICK_REFERENCE.md) — Integration guide
