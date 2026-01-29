# Quick Reference - Webhook Endpoint

## 📍 Endpoint
```
POST /api/v1/webhooks/paywithaccount/
```

## 🔓 Authentication
**None required** (AllowAny)

## ⚡ Response
**Always 200 OK** (even on errors)

Returns within **<100ms** after storing event.

## 📨 Request Example
```bash
curl -X POST http://localhost:8000/api/v1/webhooks/paywithaccount/ \
  -H "Content-Type: application/json" \
  -H "Signature: hash_value" \
  -d '{
    "request_ref": "req_123",
    "reference": "pwa_ref_456",
    "status": "success",
    "event_id": "evt_789"
  }'
```

## 📤 Response Example
```json
{
  "id": "webhook-uuid",
  "provider": "paywithaccount",
  "event_id": "evt_789",
  "request_ref": "req_123",
  "status": "RECEIVED",
  "received_at": "2026-01-29T10:30:00Z",
  "processed_at": null
}
```

## 🔐 Signature Headers Checked
1. `Signature`
2. `X-Kore-Signature`
3. `X-Signature`

Any of these can be provided or omitted.

## 📊 Processing Flow
```
1. POST webhook → 2. Store event (status=RECEIVED)
3. Return 200 → 4. (Background) Process async
5. Verify signature (if spec available)
6. Update Collection status → 7. Mark event PROCESSED/FAILED
```

## 🧪 Test Endpoint
```bash
python manage.py test core_apps.webhooks.tests.TestWebhookEndpoints -v 2
```

## 📋 Payload Field Names (Tolerant)
Supports multiple formats:
- `request_ref`, `requestRef`, `ref`
- `reference`, `transactionRef`, `transaction_ref`
- `status`, `payment_status`, `transaction_status`
- `event_id`, `eventId`, `event_reference`

## 📂 Files Created
```
core_apps/webhooks/
├── serializers.py        (Serializers)
├── views.py              (WebhookView)
├── urls.py               (URLs)
└── tests.py              (11 tests added)

config/urls.py            (Updated)
WEBHOOKS_API.md           (Documentation)
```

## 🔍 Monitor Events
```
Admin Dashboard → Webhooks → Webhook Events
```

Filter by status, provider, request_ref, or date.

## ✅ Key Features
- ✅ No authentication needed
- ✅ Signature extraction + optional verification
- ✅ 200 response immediately (async processing)
- ✅ Full payload stored for audit
- ✅ Integration with CollectionsService
- ✅ Tolerant field name parsing
- ✅ Error handling: always returns 200
- ✅ 11 comprehensive test cases

## 🚀 Ready For
- ✅ PayWithAccount webhook configuration
- ✅ Payment status updates
- ✅ Collection status synchronization
- ✅ Production deployment

## 📝 Notes
- Event stored with `status=RECEIVED` immediately
- Processing happens asynchronously
- Failed signature verification → `status=FAILED` (still returns 200)
- All errors stored in WebhookEvent.error field
- Signature stored in WebhookEvent.signature field
- Payload stored in WebhookEvent.payload field
