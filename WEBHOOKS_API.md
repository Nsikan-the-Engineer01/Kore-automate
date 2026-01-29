# Webhook API Documentation

## Overview

The Webhook API receives and processes payment events from the PayWithAccount provider. Webhooks are configured to allow no authentication but verify signatures when available for security.

## Endpoint

### POST /api/v1/webhooks/paywithaccount/

Receives webhook events from PayWithAccount payment provider.

**Authentication**: Not required (AllowAny)
**Method**: POST
**Response Time**: < 100ms (processing happens asynchronously)

---

## Request Format

### Headers (Optional)

```
Signature: HMAC-SHA256-hash
X-Kore-Signature: alternative-signature-header
X-Signature: another-alternative-signature
```

At least one signature header may be provided for verification, but it's optional.

### Request Body

Send any JSON payload that PayWithAccount sends. Common fields:

```json
{
  "request_ref": "abc123def456",
  "reference": "pwa-transaction-ref",
  "event_id": "evt-789",
  "status": "success",
  "transaction": {
    "type": "debit",
    "amount": 10250.00,
    "currency": "NGN"
  }
}
```

### Supported Field Names

The webhook parser is tolerant and supports multiple field name formats:

| Standard | Alternatives |
|----------|--------------|
| `request_ref` | `requestRef`, `request_reference`, `ref` |
| `reference` | `transactionRef`, `transaction_ref`, `txn_ref`, `provider_ref` |
| `status` | `payment_status`, `transaction_status` |
| `event_id` | `eventId`, `event_reference` |

---

## Response

### 200 OK

Always returns 200, even on errors. This prevents the payment provider from retrying.

```json
{
  "id": "e1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6",
  "provider": "paywithaccount",
  "event_id": "evt-789",
  "request_ref": "abc123def456",
  "status": "RECEIVED",
  "received_at": "2026-01-29T10:30:00Z",
  "processed_at": null
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique webhook event ID |
| `provider` | String | Always "paywithaccount" |
| `event_id` | String | Event ID from payload (if present) |
| `request_ref` | String | Request reference (extracted or provided) |
| `status` | String | Event status (RECEIVED, PROCESSED, FAILED) |
| `received_at` | DateTime | When event was received |
| `processed_at` | DateTime | When event was processed (async) |

---

## Processing Flow

```
1. Receive webhook POST
   ↓
2. Extract signature from headers (optional)
   ↓
3. Store payload + signature in WebhookEvent (status=RECEIVED)
   ↓
4. Return 200 immediately
   ↓
5. (Async) Call WebhookService.process_event()
   ↓
6. (Async) Parse payload, verify signature if configured
   ↓
7. (Async) Call CollectionsService.update_collection_from_webhook()
   ↓
8. (Async) Update WebhookEvent status to PROCESSED or FAILED
```

---

## Signature Verification

### When Verification Happens

If PayWithAccount signature specification is available:
- Signature is verified against payload
- Stored in WebhookEvent
- If verification fails, event status = FAILED

If specification is NOT available:
- Signature header is stored as-is
- No verification performed
- Event proceeds normally

### Signature Headers Checked (in order)

1. `Signature` header
2. `X-Kore-Signature` header
3. `X-Signature` header
4. Falls back to empty string if none present

---

## Error Handling

### All Webhooks Return 200

To prevent payment providers from retrying due to server errors, all responses return 200 OK.

Errors are:
- Logged for monitoring
- Stored in WebhookEvent with status=FAILED and error message
- Available in admin for manual review

### Common Scenarios

**Malformed JSON**
```
Request: invalid json string
Response: 200 OK
Details: Stored as failed event
```

**Duplicate Event**
```
Request: Same event_id sent twice
Response: 200 OK
Details: First stored, second creates separate event or fails unique constraint
```

**Missing Required Fields**
```
Request: {} (empty object)
Response: 200 OK
Details: Event stored with empty/null fields
```

---

## Example Requests

### Simple Success Webhook

```bash
curl -X POST http://localhost:8000/api/v1/webhooks/paywithaccount/ \
  -H "Content-Type: application/json" \
  -H "Signature: signature123hash" \
  -d '{
    "request_ref": "req_abc123",
    "reference": "pwa_ref_xyz",
    "status": "success",
    "transaction": {
      "amount": 10250.00,
      "currency": "NGN",
      "type": "debit"
    }
  }'
```

**Response:**
```json
{
  "id": "webhook-event-uuid",
  "provider": "paywithaccount",
  "event_id": null,
  "request_ref": "req_abc123",
  "status": "RECEIVED",
  "received_at": "2026-01-29T10:30:00Z",
  "processed_at": null
}
```

### Webhook with Event ID

```bash
curl -X POST http://localhost:8000/api/v1/webhooks/paywithaccount/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "evt_12345",
    "request_ref": "req_def456",
    "status": "success",
    "reference": "pwa_ref_abc"
  }'
```

### Webhook with Alternative Header

```bash
curl -X POST http://localhost:8000/api/v1/webhooks/paywithaccount/ \
  -H "Content-Type: application/json" \
  -H "X-Kore-Signature: signature_value" \
  -d '{
    "requestRef": "req_ghi789",
    "transactionRef": "pwa_ref_def",
    "status": "completed"
  }'
```

---

## Webhook Event Statuses

| Status | Meaning | Next Step |
|--------|---------|-----------|
| `RECEIVED` | Webhook stored, processing started | Async processing |
| `PROCESSED` | Webhook processed successfully | Collection updated |
| `FAILED` | Processing failed (see error field) | Manual review in admin |

---

## Monitoring & Debugging

### View Webhook Events

In Django Admin:
```
Admin → Webhooks → Webhook Events
```

Filter by:
- Provider: paywithaccount
- Status: RECEIVED, PROCESSED, FAILED
- Request Ref: search by collection request_ref
- Date Range: received_at

### View Failed Events

```
Admin → Webhooks → Webhook Events
Filter: Status = FAILED
```

See error message explaining why processing failed.

### Manual Retry

For failed events:
1. View event in admin
2. Check error field for details
3. Resolve issue in code/configuration
4. Manually process via admin action or API

---

## Integration with Collections

When webhook is processed, it:

1. Extracts `request_ref` from payload
2. Finds Collection with matching request_ref
3. Calls `CollectionsService.update_collection_from_webhook()`
4. Updates Collection status based on webhook status
5. Updates related Transaction records

---

## Security Considerations

### Signature Verification

- Signature is verified if PayWithAccount specification is available
- Verification prevents spoofed webhooks
- Failed verification results in FAILED status but still returns 200

### No Authentication Required

- Endpoint allows unauthenticated requests (AllowAny)
- This is standard for webhooks (provider sends events)
- Signature verification provides security instead

### Payload Storage

- Full payload stored in WebhookEvent for audit trail
- Raw signature header stored for verification
- All data available for forensics if issues occur

### Rate Limiting (Future)

Could add rate limiting by provider IP if needed:
```python
from throttle import ScopedRateThrottle
```

---

## Testing the Endpoint

### Run Tests

```bash
python manage.py test core_apps.webhooks.tests.TestWebhookEndpoints -v 2
```

### Manual Testing

Using curl or Postman:

```bash
# Test 1: Simple success webhook
curl -X POST http://localhost:8000/api/v1/webhooks/paywithaccount/ \
  -H "Content-Type: application/json" \
  -d '{"request_ref": "test123", "status": "success"}'

# Test 2: With signature
curl -X POST http://localhost:8000/api/v1/webhooks/paywithaccount/ \
  -H "Content-Type: application/json" \
  -H "Signature: test_sig" \
  -d '{"request_ref": "test456", "status": "success"}'

# Test 3: Empty payload
curl -X POST http://localhost:8000/api/v1/webhooks/paywithaccount/ \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## Configuration

### Environment Variables

No special configuration needed. The endpoint works with default settings.

Optional future configuration:
```bash
# Webhook signature secret (if available)
WEBHOOK_SIGNATURE_SECRET=your_secret_here

# Max payload size
WEBHOOK_MAX_PAYLOAD_SIZE=1048576  # 1MB
```

---

## Troubleshooting

### Webhook Not Being Processed

Check:
1. POST request going to correct URL: `/api/v1/webhooks/paywithaccount/`
2. Content-Type header is `application/json`
3. Look in admin → WebhookEvent for received event
4. Check event status (RECEIVED vs PROCESSED)

### Event Stuck in RECEIVED Status

Means async processing hasn't completed yet. Check:
1. Celery is running (if async is enabled)
2. Check logs for processing errors
3. Event will show FAILED status if processing failed

### Collection Not Updated

Check:
1. WebhookEvent has correct request_ref
2. Collection exists with that request_ref
3. WebhookEvent status = PROCESSED (not FAILED)
4. Check error field in WebhookEvent for details

---

## API Reference Summary

| Endpoint | Method | Auth | Speed | Returns |
|----------|--------|------|-------|---------|
| `/api/v1/webhooks/paywithaccount/` | POST | No | <100ms | 200 + event data |

**Status Code**: Always 200 (even on errors)
**Processing**: Async via Celery or sync fallback
**Storage**: Full payload + signature stored for audit
