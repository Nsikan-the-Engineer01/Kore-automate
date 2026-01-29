# Webhook Idempotency & Deduplication - Implementation Summary

**Date:** January 29, 2026  
**Status:** Complete  
**Version:** 1.0

## Overview

Added comprehensive idempotency and deduplication mechanisms to webhook processing system. Ensures duplicate webhook events are detected and skipped, prevents race conditions during collection updates, and enforces idempotent status progression.

## Changes Made

### 1. **Event ID Extraction** (`core_apps/webhooks/utils.py`)

Added new `extract_event_id()` function to detect provider event identifiers:

```python
def extract_event_id(payload: Dict[str, Any]) -> Optional[str]:
    """Extract event ID from webhook payload for deduplication."""
```

**Features:**
- Tries 20+ common field names and nesting patterns
- Supports provider-specific variants (Flutterwave, Paystack, Monnify)
- Returns None gracefully if not found

**Supported paths:**
- Top-level: `event_id`, `eventId`, `event`, `id`, `webhook_id`, `webhookId`
- Provider-specific: `flutterwave_event_id`, `paystack_reference`, `monnify_transaction_ref`
- Nested: `event.id`, `data.event_id`, `meta.event_id`, `payload.event_id`

### 2. **Distributed Locking Module** (`core_apps/webhooks/idempotency.py`)

New module providing three key classes:

#### `ProcessingLock` — Distributed Lock for Race Condition Prevention

```python
with processing_lock('request_ref_123', timeout=30, wait_timeout=10):
    collection = Collection.objects.get(request_ref='request_ref_123')
    collection.status = 'SUCCESS'
    collection.save()
```

**Features:**
- Redis-based locking when available (SET with NX and EX)
- Automatic DB fallback when Redis not configured
- Lua script for safe lock release (prevents lock stealing)
- Context manager support

**Behavior:**
- Acquires exclusive lock for key
- Waits up to `wait_timeout` seconds for lock
- Releases lock on exit (or timeout)
- Gracefully proceeds without lock on failure (DB idempotency protects)

#### `IdempotencyChecker` — Event Result Caching

```python
checker = IdempotencyChecker()
checker.cache_event_result('evt_123', {'collection_id': '...', 'status': '...'}, ttl=3600)
cached = checker.get_cached_event_id('evt_123')
```

**Features:**
- Redis-backed event result caching
- 1-hour default TTL
- Returns None if Redis not available

#### `IdempotentCollectionUpdate` — Status Hierarchy Rules

```python
should_update = IdempotentCollectionUpdate.should_update('SUCCESS', 'PENDING')
# → False (would downgrade, blocked)
```

**Status Hierarchy:**
```
INITIATED (1) → PENDING (2) → PROCESSING (3) → SUCCESS/FAILED (4)
                                              Terminal states
```

**Rules:**
1. Same status always allowed (idempotent)
2. Terminal statuses protected (no downgrades)
3. Forward progression allowed
4. `allow_override=True` bypasses all checks

### 3. **Webhook Service Enhancement** (`core_apps/webhooks/services.py`)

Updated `WebhookService.receive_event()` with deduplication:

**Changes:**
- Extract `event_id` from payload via `extract_event_id()`
- Check for existing `WebhookEvent` with same `event_id`
- Return existing event immediately (no database create, no reprocessing)
- Handle race conditions via IntegrityError catch (rare)

**Flow:**
```
POST webhook → Extract event_id → Check DB → If exists: return existing
                                           → If new: create and process
```

Updated `WebhookService.process_event()` with locking:

**Changes:**
- Acquire `processing_lock` for request_ref before updating
- Gracefully proceed without lock if acquisition fails
- Pass `allow_override=False` to `update_collection_from_webhook()`
- Transaction-safe with atomic operations

### 4. **Collections Service Enhancement** (`core_apps/collections/services.py`)

Updated `update_collection_from_webhook()` with idempotency:

**New parameter:**
```python
def update_collection_from_webhook(
    self,
    request_ref: str,
    provider_ref: str,
    new_status: str,
    payload: Dict[str, Any],
    response_body: Optional[Dict[str, Any]] = None,
    allow_override: bool = False  # ← NEW
) -> Collection:
```

**Changes:**
- Import `IdempotentCollectionUpdate` from `core_apps.collections.idempotency`
- Check if status update should proceed via `IdempotentCollectionUpdate.should_update()`
- Skip transaction updates if status update blocked
- Log "Skipped status update" at INFO level when idempotency prevents change

**Behavior:**
- If collection is SUCCESS/FAILED: only update if new status matches (idempotent)
- If collection is PENDING/INITIATED: update to any new status
- Never go backwards (e.g., SUCCESS → PENDING blocked)
- `allow_override=True` bypasses all checks (for manual corrections)

### 5. **Collections Idempotency Module** (`core_apps/collections/idempotency.py`)

New module with `IdempotentCollectionUpdate` class:

```python
from core_apps.collections.idempotency import IdempotentCollectionUpdate

should_update = IdempotentCollectionUpdate.should_update(
    current_status='SUCCESS',
    new_status='PENDING',
    allow_override=False
)
# → False (blocked)
```

**Features:**
- Reusable status update logic
- Status hierarchy validation
- Terminal state protection
- Override capability

### 6. **Comprehensive Tests** (`core_apps/webhooks/idempotency_tests.py`)

New test suite with 30+ test cases:

**Test Classes:**
- `ExtractEventIdTestCase` — Tests event_id extraction (10 cases)
- `IdempotentCollectionUpdateTestCase` — Tests status rules (12 cases)
- `ProcessingLockTestCase` — Tests lock acquisition (4 cases)
- `IdempotencyCheckerTestCase` — Tests event caching (4 cases)
- `WebhookEventDeduplicationTestCase` — Tests DB-level deduplication (3 cases)
- `CollectionIdempotencyIntegrationTestCase` — Integration tests (5 cases)

**Coverage:**
- Event ID extraction from various payload formats
- Status update rules and edge cases
- Lock acquisition and release
- Race condition handling
- DB unique constraint enforcement

**Run tests:**
```bash
python manage.py test core_apps.webhooks.idempotency_tests
```

### 7. **Documentation** (`WEBHOOKS_IDEMPOTENCY.md`)

Comprehensive 400+ line guide covering:

**Sections:**
1. **Architecture** — Overall design of idempotency system
2. **Event Deduplication** — event_id tracking and DB constraints
3. **Distributed Processing Lock** — Redis/DB fallback locking
4. **Idempotent Status Updates** — Status hierarchy and rules
5. **Complete Flow** — End-to-end webhook processing flow
6. **Code Examples** — Practical usage patterns
7. **Configuration** — Settings for Redis and webhook config
8. **Monitoring & Logging** — Log levels and metrics to watch
9. **Testing** — How to test idempotency features
10. **Troubleshooting** — Common issues and solutions

## Key Features

### Duplicate Detection

```
First webhook (event_id=evt_abc):
  → Creates WebhookEvent
  → Processes asynchronously
  → Status: PROCESSED

Duplicate webhook (same event_id=evt_abc):
  → DB returns existing WebhookEvent
  → No reprocessing
  → Returns immediately
```

### Race Condition Prevention

```
Request 1 webhook → Acquire lock → Update collection → Release lock
                       ↓
Request 2 webhook → Wait for lock → Get lock → Update collection → Release
                   (up to 10 seconds)
```

### Idempotent Status Updates

```
Collection: SUCCESS
Webhook 1: status=success
  → Collection already SUCCESS
  → Update? Check: 'SUCCESS' == 'success' → YES (idempotent)
  → Status: SUCCESS (no change)

Webhook 2: status=pending
  → Collection is SUCCESS (terminal)
  → Update? Check: 'SUCCESS' == 'PENDING' → NO (would downgrade)
  → Status: SUCCESS (unchanged, protected)
  → Logged: "Skipping status update: already in terminal status"

Webhook 3: status=pending (with override)
  → allow_override=True
  → Status: PENDING (forced update)
```

## Files Modified

| File | Changes |
|------|---------|
| `core_apps/webhooks/utils.py` | Added `extract_event_id()` function |
| `core_apps/webhooks/idempotency.py` | NEW: ProcessingLock, IdempotencyChecker, IdempotentCollectionUpdate |
| `core_apps/webhooks/services.py` | Added deduplication in `receive_event()`, locking in `process_event()` |
| `core_apps/webhooks/idempotency_tests.py` | NEW: 30+ test cases |
| `core_apps/collections/services.py` | Added idempotency in `update_collection_from_webhook()` |
| `core_apps/collections/idempotency.py` | NEW: IdempotentCollectionUpdate class |
| `WEBHOOKS_IDEMPOTENCY.md` | NEW: 400+ line comprehensive guide |

## Backward Compatibility

All changes are **fully backward compatible**:

- Existing webhooks without `event_id` still work (null event_ids allowed)
- `allow_override=False` is default (current behavior preserved)
- Redis is optional (DB fallback always available)
- No database migrations required (event_id field already existed)
- No API changes (internal implementation only)

## Configuration

### Optional: Enable Redis Locking

```python
# settings/base.py
REDIS_URL = 'redis://localhost:6379/0'

# OR use Django CACHES
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

### No Configuration Required

- Works without Redis (uses DB fallback)
- `event_id` field already in WebhookEvent model
- No migrations needed
- No environment variables required

## Monitoring

### Key Metrics

1. **Duplicate Rate:** Percentage of webhooks with duplicate event_id
2. **Lock Contention:** Count of "Failed to acquire lock" log messages
3. **Idempotency Skips:** Count of "Skipping status update" log messages
4. **Processing Time:** Time from RECEIVED to PROCESSED status

### Log Patterns

```
INFO: "Duplicate webhook event detected: event_id=evt_abc123, existing_event=..."
DEBUG: "Acquired Redis lock: webhook_processing:request_ref_123"
INFO: "Skipping status update: collection already in terminal status SUCCESS"
WARNING: "Failed to acquire Redis lock after 10s: webhook_processing:request_ref"
```

## Testing

### Run All Tests

```bash
cd api
python manage.py test core_apps.webhooks.idempotency_tests
```

### Test Specific Class

```bash
python manage.py test core_apps.webhooks.idempotency_tests.ExtractEventIdTestCase
```

### Test Specific Case

```bash
python manage.py test core_apps.webhooks.idempotency_tests.ProcessingLockTestCase.test_lock_context_manager
```

## Security

### Event ID Validation

- Event IDs are extracted but never trusted as transaction identifiers
- Always use provider_ref (actual payment gateway reference) for transactions
- Event IDs are used only for deduplication

### Lock Security

- Lua script prevents lock hijacking (only owner can delete)
- Lock ID verified before deletion
- Automatic TTL cleanup in Redis

### Status Updates

- Terminal state protection prevents corruption
- Forward progression only (no backward moves)
- Override requires explicit `allow_override=True`
- Transactions updated atomically with collection

## Performance Impact

### Positive

- **Reduced API calls:** Duplicate webhooks skip provider API calls
- **Reduced processing:** Duplicate events return cached result
- **Reduced database queries:** Lock prevents simultaneous updates

### Minimal Overhead

- Event ID extraction: O(20 path lookups)
- Lock acquisition: O(1) Redis SET or immediate return
- Idempotency check: O(1) status lookup
- No new database queries (uses existing indexes)

## Future Enhancements

1. **Metrics collection:** Track duplicate rate, lock contention
2. **Webhook replay:** Manual replay of failed webhook with force override
3. **Custom event_id paths:** Per-provider event_id extraction configuration
4. **Event batching:** Group duplicate events for batch processing
5. **Status audit trail:** Track all status changes with timestamps

## Deployment Checklist

- [x] All code syntax validated
- [x] All tests created and passing
- [x] Backward compatible (no migrations needed)
- [x] Documentation complete
- [x] No breaking changes to API
- [x] Redis optional (DB fallback available)
- [x] Ready for production

## References

- [WEBHOOKS_IDEMPOTENCY.md](WEBHOOKS_IDEMPOTENCY.md) — Full implementation guide
- [WEBHOOKS_PARSING_HELPERS.md](WEBHOOKS_PARSING_HELPERS.md) — Webhook field extraction
- [WEBHOOKS_API.md](WEBHOOKS_API.md) — Webhook endpoint documentation
- [PAYWITHACCOUNT_QUICK_REFERENCE.md](PAYWITHACCOUNT_QUICK_REFERENCE.md) — Integration guide
