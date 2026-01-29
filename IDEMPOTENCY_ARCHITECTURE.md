# Webhook Idempotency - Architecture Diagrams

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          PAYMENT PROVIDER                             │
│                   (PayWithAccount, Flutterwave, etc)                 │
└─────────────────────┬──────────────────────────────────────┬──────────┘
                      │                                      │
                      │ Webhook (with event_id)             │ Retry (same event)
                      ↓                                      ↓
┌──────────────────────────────────────────────────────────────────────┐
│                    WEBHOOK ENDPOINT                                   │
│              POST /api/v1/webhooks/paywithaccount/                  │
└──────────────────┬───────────────────────────────────────────────────┘
                   │
                   ↓
        ┌──────────────────────┐
        │ Extract event_id     │ ← NEW: extract_event_id()
        │ from payload         │
        └──────┬───────────────┘
               │
               ↓
        ┌──────────────────────────────┐
        │ Check DB for event_id        │ ← NEW: Deduplication
        │ WebhookEvent.event_id=?      │
        └──────┬────────────┬──────────┘
               │            │
        Found  │            │ Not found
               ↓            ↓
        ┌─────────────┐  ┌──────────────────┐
        │ Return      │  │ Create           │
        │ existing    │  │ WebhookEvent     │
        │ (no create) │  │ (first time)     │
        └─────────────┘  └──────┬───────────┘
               │                │
               └────────┬───────┘
                        ↓
               ┌────────────────────┐
               │ Enqueue async      │
               │ processing or      │
               │ process inline     │
               └────────┬───────────┘
                        ↓
                  Return 200 OK
```

## Processing Flow with Idempotency

```
START: Webhook received

    Extract event_id ──→ Check for duplicate
         ↓                     ↓ (found)
    Parse payload         Return existing
         ↓                (no reprocessing)
    Get request_ref
         │
         ↓
    Acquire lock ←─────── NEW: ProcessingLock
    (Redis or DB)        - Prevents race conditions
         │
         ↓
    Find collection
         │
         ↓
    Check idempotency ←── NEW: IdempotentCollectionUpdate
    should_update()?      - Protects terminal states
         ↓
      YES  │  NO
         ↓  └──→ Log skip, return collection
         ↓       (e.g., SUCCESS→PENDING blocked)
    Update status
         │
         ↓
    Update transactions
         │
         ↓
    Release lock
         │
         ↓
    Mark PROCESSED
         │
         ↓
    Return collection

END: Webhook processed (or skipped)
```

## Duplicate Detection Sequence

```
Webhook 1: event_id=evt_abc
├─ Extract event_id
├─ Query DB: WebhookEvent.objects.get(event_id='evt_abc')
│  └─ DoesNotExist: Create new
├─ Create WebhookEvent (status=RECEIVED)
├─ Enqueue processing
└─ Return 200 OK

Webhook 2: event_id=evt_abc (DUPLICATE)
├─ Extract event_id
├─ Query DB: WebhookEvent.objects.get(event_id='evt_abc')
│  └─ Found: Return existing
├─ Skip WebhookEvent creation (IntegrityError prevented)
├─ Skip reprocessing
└─ Return 200 OK (same event ID)

Webhook 3: event_id=evt_def (DIFFERENT)
├─ Extract event_id
├─ Query DB: WebhookEvent.objects.get(event_id='evt_def')
│  └─ DoesNotExist: Create new
├─ Create WebhookEvent (status=RECEIVED)
├─ Enqueue processing
└─ Return 200 OK
```

## Distributed Lock Mechanism

```
Multiple webhooks for same collection (request_ref=req_123):

Timeline:
─────────────────────────────────────────────────────────────

Request 1: webhook (status=success)
│
├─ Try: processing_lock('req_123')
│  └─ Redis: SET lock:req_123 = uuid_1 (NX, EX=30) → Success
│  └─ DB: no-op (always success)
├─ Acquired ✓
│
├─ Update collection
│  └─ collection.status = SUCCESS
│
├─ Release lock
│  └─ Redis: DEL lock:req_123 (if owner=uuid_1)
│  └─ DB: no-op
│
└─ Webhook 1 done

                  Request 2: webhook (status=pending)
                  │
                  ├─ Try: processing_lock('req_123')
                  │  └─ Redis: SET lock:req_123 (NX) → Locked by req1
                  │  └─ Wait up to 10 seconds...
                  │
                  ├─ (Webhook 1 finishes, releases lock)
                  │
                  ├─ Acquired ✓
                  │
                  ├─ Update collection
                  │  └─ Idempotency check: SUCCESS→PENDING? NO (blocked)
                  │  └─ collection.status = SUCCESS (unchanged)
                  │
                  ├─ Release lock
                  │
                  └─ Webhook 2 done
```

## Status Update Decision Tree

```
                    Webhook received
                    new_status=?
                           │
                           ↓
                Get current collection status
                           │
                           ↓
    ┌───────────────────────────────────────────────────┐
    │ Is new_status == current_status?                  │
    └────────┬────────────────────────────────┬─────────┘
             │ YES                            │ NO
             │                                │
             ↓                                ↓
        ┌─────────────┐            ┌─────────────────────┐
        │ ✓ ALLOWED   │            │ Is override=True?   │
        │ Idempotent  │            └────┬─────────┬──────┘
        │ redeliver   │                 │ YES    │ NO
        └─────────────┘                 │        │
                                        ↓        ↓
                                    ┌──────┐  ┌────────────────┐
                                    │✓ALLOW│  │Is current in   │
                                    │      │  │terminal state? │
                                    └──────┘  │(SUCCESS/FAILED)│
                                             └────┬──────┬────┘
                                                  │ YES  │ NO
                                                  │      │
                                                  ↓      ↓
                                            ┌──────┐  ┌──────┐
                                            │✗BLOCK│  │ Check│
                                            │      │  │ forward?
                                            └──────┘  └─┬──┬──┘
                                                      │  │
                                           Hierarchy level
                                           comparison
                                           new > current
                                                      │  │
                                                   YES │  │ NO
                                                      │  │
                                                      ↓  ↓
                                                   ✓    ✗
                                                  ALLOW BLOCK
```

## Status Hierarchy Levels

```
                    Terminal States
                   (No further changes)
                   ────────────────
INITIATED          PENDING          PROCESSING      SUCCESS
   (1)               (2)               (3)           (4)
                                                      │
                                                      │
                                                    FAILED
                                                     (4)

Forward direction (allowed):  → → → → → ↘
                                         ↘ (both to 4)
                                         ↙
Backward direction (blocked):  ← ← ← ← ← (not allowed)

Within same level (idempotent):  =  (always allowed)
```

## Database Constraints

```
WebhookEvent table:
┌─────────────────────────────────────────────┐
│ id (UUID, PK)                               │
│ provider (string, 50)                       │
│ event_id (string, 64, UNIQUE, nullable)     │← NEW: Deduplication
│ request_ref (string, 64, indexed)           │
│ payload (JSON)                              │
│ signature (string, 255)                     │
│ status (choice: RECEIVED/PROCESSED/FAILED)  │
│ error (text)                                │
│ received_at (datetime, auto_now_add)        │
│ processed_at (datetime, nullable)           │
└─────────────────────────────────────────────┘

Unique constraint:
- event_id: UNIQUE (allows multiple NULL)
  ↓
  Prevents duplicate: 'evt_abc' cannot exist twice
  Allows multiple NULL: Old webhooks without event_id
```

## Configuration Options

```
settings.base.py:

┌────────────────────────────────────────────────┐
│ REDIS_URL (optional)                           │
│ = 'redis://localhost:6379/0'                   │
│                                                │
│ If present:                                    │
│   ✓ Use Redis for distributed locking         │
│   ✓ Lua script for safe deletion               │
│   ✓ ~1-5ms lock acquisition                    │
│                                                │
│ If absent:                                     │
│   ✓ Use DB fallback (no-op lock)               │
│   ✓ Still safe due to idempotency rules       │
│   ✓ ~0ms lock acquisition                      │
└────────────────────────────────────────────────┘

WEBHOOK_CONFIG (optional):
└────────────────────────────────────────────────┐
│ LOCK_TIMEOUT = 30          (Lock TTL in sec)   │
│ LOCK_WAIT_TIMEOUT = 10     (Max wait in sec)   │
│ EVENT_ID_CACHE_TTL = 3600  (Cache in sec)      │
└────────────────────────────────────────────────┘
```

## Error Handling Paths

```
Webhook received

    ↓ Extract event_id fails?
    → Log warning, continue (event_id is optional)
    
    ↓ Duplicate event_id detected?
    → Return existing WebhookEvent (no error)
    
    ↓ IntegrityError on create? (race condition)
    → Catch and fetch existing (handles rare race)
    
    ↓ Lock acquisition fails?
    → Log warning, proceed without lock (safe)
    
    ↓ Collection not found?
    → Save as FAILED, log error
    
    ↓ Status update blocked by idempotency?
    → Log info, continue (not an error)
    
    ↓ Transaction update fails?
    → Rollback (atomic transaction), save as FAILED
    
    ↓ Processing completed?
    → Mark WebhookEvent as PROCESSED
```

## Monitoring Checkpoints

```
Webhook processing pipeline with observation points:

Webhook received ─────────────┐
                              ↓ METRIC: Total webhooks
Event ID extracted ───────────┐
                              ↓ METRIC: Extraction success rate
Duplicate check ──────────────┐
                              ├─→ (Duplicate) ──┐ METRIC: Duplicate rate
                              ├─→ (New)         ↓
Lock acquired ────────────────┐ METRIC: Lock acquisition rate
                              ├─→ (Success)     ─┐
                              ├─→ (Timeout)  ─┐  ↓
                              │               ↓
Collection found ─────────────┐
                              ├─→ (Not found) → FAILED
                              ├─→ (Found)     ↓
Idempotency check ────────────┐
                              ├─→ (Blocked) ──┐ METRIC: Idempotency skips
                              ├─→ (Allowed)   ↓
Status updated ───────────────┐
Transactions updated ─────────┐
Lock released ────────────────┐
Event marked PROCESSED ───────┐
                              ↓
                        Webhook complete
                        
METRIC: Processing time (RECEIVED to PROCESSED)
METRIC: Success rate
METRIC: Error rate by type
```

---

## Component Interactions

```
                  ┌─────────────────────────────┐
                  │  Webhook Service            │
                  │  ───────────────────        │
                  │  • receive_event()          │
                  │  • process_event()          │
                  └────┬──────────────┬─────────┘
                       │              │
                       │ uses         │ uses
                       ↓              ↓
            ┌──────────────────┐  ┌────────────────────┐
            │ Webhook Utils    │  │ Collections        │
            │ ──────────────── │  │ Service            │
            │ • extract_event_ │  │ ────────────────── │
            │   id()           │  │ • update_collection│
            │ • extract_request│  │   _from_webhook()  │
            │   _ref()         │  │ • validate_collect │
            │ • extract_status │  │   ion()            │
            │ • extract_amount │  │ • query_collection │
            │ • extract_curren │  │   _status()        │
            │   cy()           │  └────┬────────────────┘
            └──────────────────┘       │
                                       │ uses
                                       ↓
                          ┌────────────────────────┐
                          │ Collections            │
                          │ Idempotency            │
                          │ ───────────────────── │
                          │ • IdempotentCollectionU│
                          │   pdate.should_update()│
                          │ • IdempotentCollectionU│
                          │   pdate.get_update_    │
                          │   fields()             │
                          └────────────────────────┘


        ┌──────────────────────────────────┐
        │ Webhooks Idempotency             │
        │ ──────────────────────────────── │
        │ • ProcessingLock                 │
        │ • IdempotencyChecker             │
        │ • IdempotentCollectionUpdate    │
        │ • processing_lock()              │
        │ • has_redis()                    │
        │ • get_redis_client()             │
        └──────────────────────────────────┘
                       ↓ uses (optional)
                ┌─────────────┐
                │   Redis     │
                │             │
                │ Distributed │
                │ Lock        │
                │ Store       │
                └─────────────┘


        ┌────────────────────────────┐
        │ Django Database            │
        │ ────────────────────────── │
        │ • WebhookEvent table       │
        │   - event_id UNIQUE        │
        │ • Collection table         │
        │ • Transaction table        │
        └────────────────────────────┘
```

---

## Deployment Topology

```
Production Setup:

┌─────────────────────────────────────┐
│     Payment Provider (PWA)          │
│  (Sends webhooks with event_id)     │
└────────────────┬────────────────────┘
                 │ HTTPS POST
                 ↓
         ┌───────────────┐
         │  Load Balancer│
         └───────┬───────┘
                 │
    ┌────────────┴────────────┐
    ↓                         ↓
┌────────┐               ┌────────┐
│ Django │               │ Django │
│ App 1  │               │ App 2  │
│        │               │        │
└────┬───┘               └────┬───┘
     │                        │
     │ (both use Redis lock)  │
     │                        │
     └──────────┬─────────────┘
                ↓
        ┌──────────────┐
        │   Redis      │
        │   Cluster    │
        │   (Optional) │
        └──────────────┘
        
        │────────────────────────────│
        │ If no Redis available:     │
        │ - Lock becomes no-op       │
        │ - Idempotency rules still  │
        │   protect data             │
        │────────────────────────────│

     ┌──────────────────────┐
     │   PostgreSQL         │
     │   Database           │
     │                      │
     │ WebhookEvent table:  │
     │ - Stores all events  │
     │ - event_id UNIQUE    │
     │ - Deduplication      │
     │   at DB level        │
     │                      │
     │ Collection table:    │
     │ - Updated by webhooks│
     │ - Status protected   │
     │   by idempotency     │
     └──────────────────────┘
```

---

See related documentation for detailed specifications:
- [WEBHOOKS_IDEMPOTENCY.md](WEBHOOKS_IDEMPOTENCY.md)
- [IDEMPOTENCY_IMPLEMENTATION.md](IDEMPOTENCY_IMPLEMENTATION.md)
- [IDEMPOTENCY_QUICK_REFERENCE.md](IDEMPOTENCY_QUICK_REFERENCE.md)
