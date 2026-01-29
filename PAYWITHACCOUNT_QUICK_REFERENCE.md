# PayWithAccount Settings - Quick Reference

## Settings Dictionary

All PayWithAccount configuration is available in a single dictionary:

```python
from django.conf import settings

config = settings.PAYWITHACCOUNT
# {
#     'base_url': 'https://api.dev.onepipe.io',
#     'transact_path': '/v2/transact',
#     'api_key': '...',
#     'client_secret': '...',
#     'webhook_secret': '...',
#     'mock_mode': 'inspect',
#     'request_type': 'invoice',
#     'timeout_seconds': 30,
# }
```

## Environment Variables

| Variable | Default | Required |
|----------|---------|----------|
| `PWA_BASE_URL` | `https://api.dev.onepipe.io` | No |
| `PWA_TRANSACT_PATH` | `/v2/transact` | No |
| `PWA_QUERY_PATH` | `/transact/query` | No |
| `PWA_VALIDATE_PATH` | `/transact/validate` | No |
| `PWA_API_KEY` | `` | Yes |
| `PWA_CLIENT_SECRET` | `` | Yes |
| `PWA_WEBHOOK_SECRET` | `` | No |
| `PWA_MOCK_MODE` | `inspect` | No |
| `PWA_REQUEST_TYPE` | `invoice` | No |
| `PWA_REQUEST_TYPE_INVOICE` | `invoice` | No |
| `PWA_REQUEST_TYPE_DISBURSE` | `disburse` | No |
| `PWA_REQUEST_TYPE_SUBSCRIPTION` | `subscription` | No |
| `PWA_REQUEST_TYPE_INSTALMENT` | `instalment` | No |
| `PWA_TIMEOUT_SECONDS` | `30` | No |

## Usage in Code

### Get Configuration
```python
from django.conf import settings
config = settings.PAYWITHACCOUNT
```

### Get Specific Value
```python
base_url = settings.PAYWITHACCOUNT['base_url']
timeout = settings.PAYWITHACCOUNT['timeout_seconds']
api_key = settings.PAYWITHACCOUNT['api_key']
```

### Use in Initialization
```python
class PayWithAccountClient:
    def __init__(self):
        config = settings.PAYWITHACCOUNT
        self.base_url = config['base_url']
        self.api_key = config['api_key']
        self.timeout = config['timeout_seconds']
```

### Using Payload Builders
```python
from core_apps.integrations.paywithaccount.payloads import (
    build_invoice_payload,
    build_disburse_payload,
    build_subscription_payload,
    build_instalment_payload
)

# Invoice (payment collection)
payload = build_invoice_payload(
    amount_total=50000.00,
    customer_email="user@example.com",
    customer_name="John Doe",
    meta={"order_id": "12345"}
)
result = client.transact(payload)

# Disbursement (payout)
payload = build_disburse_payload(
    amount=25000.00,
    beneficiary_account="0123456789",
    beneficiary_bank_code="058",
    meta={"payout_id": "PO-001"}
)
result = client.transact(payload)

# Subscription
payload = build_subscription_payload(
    amount_total=120000.00,
    schedule={'frequency': 'monthly', 'interval': 1, 'duration': 12},
    meta={"subscription_id": "SUB-001"}
)
result = client.transact(payload)

# Installment
payload = build_instalment_payload(
    amount_total=300000.00,
    down_payment=100000.00,
    schedule={'frequency': 'monthly', 'num_installments': 3, 'interval': 1},
    meta={"instalment_id": "INST-001"}
)
result = client.transact(payload)
```

### Status Normalization
```python
from core_apps.integrations.paywithaccount.normalization import normalize_provider_status

# Normalize provider status strings to internal enums (SUCCESS, FAILED, PENDING)
# Returns tuple of (status, needs_validation)

status, needs_validation = normalize_provider_status("SUCCESS")
# status == "SUCCESS", needs_validation == False

status, needs_validation = normalize_provider_status("WaitingForOTP")
# status == "PENDING", needs_validation == True (OTP/validation required)

status, needs_validation = normalize_provider_status("DECLINED")
# status == "FAILED", needs_validation == False

# Case-insensitive and handles None gracefully
status, needs_validation = normalize_provider_status(None)
# status == "PENDING", needs_validation == False
```

## Status Normalization

Maps diverse provider status strings to internal enum values and detects validation requirements.

**Supported Internal Statuses:**
- `SUCCESS` — Transaction completed successfully
- `FAILED` — Transaction failed (error, declined, rejected, etc.)
- `PENDING` — Transaction in progress (processing, awaiting confirmation)

**Validation Detection:**
Automatically flags statuses that require OTP or additional validation:
- Examples: "WaitingForOTP", "PENDING_VALIDATION", "OTP_REQUIRED"
- Returns `needs_validation=True` for these cases

**Configurable Mapping:**
Customize status mappings via settings without code changes:

```python
# In settings or .env
PAYWITHACCOUNT_STATUS_MAP = {
    "CUSTOM_SUCCESS": ("SUCCESS", False),
    "CUSTOM_PENDING": ("PENDING", True),
    "CUSTOM_FAILED": ("FAILED", False),
}
```

## Collections API - Validation Handling

When creating a collection via `POST /api/v1/collections/`, the response automatically handles validation cases:

```json
{
    "id": "collection-uuid",
    "status": "PENDING",
    "requires_validation": true,
    "validation_fields": {
        "validation_ref": "val_ref_123",
        "session_id": "sess_456",
        "otp_reference": "otp_789"
    },
    "amount_allocation": 50000.00,
    "kore_fee": 500.00,
    "amount_total": 50500.00,
    "request_ref": "request_uuid"
}
```

**Response Fields:**
- `status`: Collection status (PENDING, SUCCESS, FAILED, etc.)
  - `PENDING` — Transaction processing or waiting for validation
  - `SUCCESS` — Transaction completed successfully
  - `FAILED` — Transaction failed
- `requires_validation`: Boolean flag indicating OTP/validation needed
- `validation_fields`: Dict of validation identifiers to use in follow-up requests
  - Contains: validation_ref, session_id, otp_reference, challenge_ref, auth_token (as available)

**Frontend Flow for Validation Cases:**
1. Receive response with `requires_validation=true`
2. Display OTP/validation prompt using fields in `validation_fields`
3. Collect user input (OTP, challenge response, etc.)
4. Send validation to provider endpoint (out of scope for Collections API)
5. Provider updates collection status via webhook

**Behavior Details:**
- Collection status automatically set to `PENDING` if validation required
- Transactions linked to collection inherit collection status
- Validation fields stored in collection metadata for audit/debugging
- All extraction is defensive — missing fields won't crash; response remains valid

## Collections API - Validation Endpoints

### Submit Validation (OTP)

**Endpoint:** `POST /api/v1/collections/{id}/validate/`

**Request:**
```json
{
    "otp": "123456"
}
```

**Response (Success):**
```json
{
    "id": "collection-uuid",
    "status": "SUCCESS",
    "requires_validation": false,
    "validation_fields": {},
    "amount_allocation": 50000.00,
    "kore_fee": 500.00,
    "amount_total": 50500.00,
    "currency": "NGN",
    "request_ref": "request_uuid",
    "provider_ref": "provider_ref_123",
    "updated_at": "2026-01-29T12:00:00Z"
}
```

**Response (Validation Required - Multiple Attempts):**
```json
{
    "id": "collection-uuid",
    "status": "PENDING",
    "requires_validation": true,
    "validation_fields": {
        "validation_ref": "val_ref_updated",
        "session_id": "sess_new"
    },
    "amount_allocation": 50000.00,
    "kore_fee": 500.00,
    "amount_total": 50500.00,
    "currency": "NGN",
    "request_ref": "request_uuid",
    "provider_ref": "provider_ref_123",
    "updated_at": "2026-01-29T12:00:00Z"
}
```

**Error Response (Collection Not in Validation State):**
```json
{
    "error": "Collection status is SUCCESS, must be PENDING to validate"
}
```

**Status Code:** 200 (Success/Pending), 400 (Validation Error), 403 (Permission Denied), 500 (Server Error)

---

### Query Collection Status

**Endpoint:** `GET /api/v1/collections/{id}/query_status/`

**Description:**
Queries the current status of a collection from the payment provider. Uses collection's `provider_ref` or `request_ref` to lookup the transaction status. Updates the collection if status has changed.

**Request:**
No request body. Authentication via JWT token.

**Response (Status Updated):**
```json
{
    "id": "collection-uuid",
    "status": "SUCCESS",
    "requires_validation": false,
    "validation_fields": {},
    "amount_allocation": 50000.00,
    "kore_fee": 500.00,
    "amount_total": 50500.00,
    "currency": "NGN",
    "request_ref": "request_uuid",
    "provider_ref": "provider_ref_123",
    "narrative": "Monthly payment",
    "updated_at": "2026-01-29T12:00:00Z"
}
```

**Response (Status Unchanged):**
```json
{
    "id": "collection-uuid",
    "status": "PENDING",
    "requires_validation": true,
    "validation_fields": {
        "validation_ref": "val_ref_123",
        "session_id": "sess_456"
    },
    "amount_allocation": 50000.00,
    "kore_fee": 500.00,
    "amount_total": 50500.00,
    "currency": "NGN",
    "request_ref": "request_uuid",
    "provider_ref": "provider_ref_123",
    "narrative": "Monthly payment",
    "updated_at": "2026-01-29T12:00:00Z"
}
```

**Error Response (Cannot Query):**
```json
{
    "error": "Cannot query status: no provider_ref or request_ref available"
}
```

**Status Code:** 200 (Success), 400 (Query Error), 403 (Permission Denied), 500 (Server Error)

## Security
- `api_key`
- `client_secret`
- `webhook_secret`

```python
# ❌ DON'T: Logs entire config including secrets
logger.info(settings.PAYWITHACCOUNT)

# ✅ DO: Log only non-sensitive values
logger.info(f"PWA timeout: {settings.PAYWITHACCOUNT['timeout_seconds']}")
```

## Local Development (.env.local)

```bash
PWA_BASE_URL=https://api.dev.onepipe.io
PWA_API_KEY=your_key_here
PWA_CLIENT_SECRET=your_secret_here
PWA_WEBHOOK_SECRET=optional_webhook_secret
PWA_MOCK_MODE=inspect
PWA_REQUEST_TYPE=invoice
PWA_TIMEOUT_SECONDS=30
```

## Production

```bash
PWA_BASE_URL=https://api.onepipe.io
PWA_API_KEY=prod_api_key
PWA_CLIENT_SECRET=prod_client_secret
PWA_WEBHOOK_SECRET=prod_webhook_secret
PWA_MOCK_MODE=false
PWA_REQUEST_TYPE=invoice
PWA_TIMEOUT_SECONDS=30
```

## Testing

```python
from django.test import override_settings

@override_settings(
    PAYWITHACCOUNT={
        'base_url': 'https://api.test.onepipe.io',
        'api_key': 'test_key',
        'client_secret': 'test_secret',
        'timeout_seconds': 5,
        'mock_mode': 'true',
        'request_type': 'invoice',
        'transact_path': '/v2/transact',
        'webhook_secret': 'test_webhook_secret',
    }
)
def test_something():
    pass
```

## Collection Validation Endpoints

Two new endpoints handle OTP validation and status queries:

### POST /api/v1/collections/{id}/validate/

Submit validation data (OTP) for collections awaiting validation:

```bash
curl -X POST http://localhost:8000/api/v1/collections/550e8400-e29b-41d4-a716-446655440000/validate/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "otp": "123456"
  }'
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "SUCCESS",
  "requires_validation": false,
  "request_ref": "abc123def456",
  "provider_ref": "prov_ref_123",
  "validation_fields": {}
}
```

Or if still awaiting validation:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PENDING",
  "requires_validation": true,
  "request_ref": "abc123def456",
  "provider_ref": "prov_ref_123",
  "validation_fields": {
    "validation_ref": "val_new_ref",
    "session_id": "sess_updated",
    "otp_reference": "otp_ref_456"
  }
}
```

### GET /api/v1/collections/{id}/query_status/

Query the current status from the payment provider:

```bash
curl -X GET http://localhost:8000/api/v1/collections/550e8400-e29b-41d4-a716-446655440000/query_status/ \
  -H "Authorization: Bearer <token>"
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "SUCCESS",
  "requires_validation": false,
  "request_ref": "abc123def456",
  "provider_ref": "prov_ref_123",
  "updated_at": "2026-01-29T12:00:00Z"
}
```

### Key Fields

| Field | Meaning |
|-------|---------|
| `status` | Current normalized status (INITIATED, PENDING, SUCCESS, FAILED) |
| `requires_validation` | Whether OTP/validation input is needed |
| `request_ref` | Your transaction reference (use for query_status) |
| `provider_ref` | PayWithAccount's transaction reference |
| `validation_fields` | Provider-specific validation metadata (validation_ref, session_id, otp_reference, etc.) |

### Workflow

**OTP Required:**
1. Create collection → `status: INITIATED`
2. Provider returns OTP required → `status: PENDING, requires_validation: true`
3. POST /validate/ with OTP → `status: SUCCESS` (or PENDING if new validation needed)

**Status Query:**
1. Create collection → `status: INITIATED`
2. GET /query_status/ at any time → Status updated from provider
3. Repeat until `status: SUCCESS` or `FAILED`

---

## Notes

- All defaults are safe for development
- `PWA_API_KEY` and `PWA_CLIENT_SECRET` must be configured in production
- Old env var name `PWA_SECRET_KEY` is still supported as fallback
- Timeout is in seconds (default 30)
- Mock mode options: `inspect`, `true`, `false`
