# API Documentation Updates - Validation & Query Endpoints

**Date:** January 29, 2026  
**Status:** ✅ Complete

---

## Summary

Updated API documentation to include two new endpoints for handling payment validation (OTP submission) and status queries. All documentation files now include comprehensive examples showing:
- ✅ New `requires_validation` flag
- ✅ `validation_fields` object with provider-specific data
- ✅ `request_ref` and `provider_ref` references
- ✅ Normalized status values
- ✅ Complete workflow examples

---

## Files Updated

### 1. [COLLECTIONS_API.md](COLLECTIONS_API.md)

**Major Updates:**

#### A. Enhanced Collection Detail Response (Endpoint #3)
- Added `requires_validation` field (boolean)
- Added `validation_fields` object (empty dict or with validation metadata)
- Now shows complete collection state including validation status

**Before:**
```json
{
  "id": "660e8400-...",
  "status": "SUCCESS",
  "request_ref": "req_abc123def456",
  "provider_ref": "pwa_ref_789"
}
```

**After:**
```json
{
  "id": "660e8400-...",
  "status": "SUCCESS",
  "request_ref": "req_abc123def456",
  "provider_ref": "pwa_ref_789",
  "requires_validation": false,
  "validation_fields": {}
}
```

#### B. New POST /api/v1/collections/{id}/validate/ Endpoint (Endpoint #4)

**Purpose:** Submit validation data (OTP, challenge response) for collections awaiting validation

**Request Body:**
```json
{
  "otp": "123456"
}
```

**Response (Validation Successful):**
```json
{
  "id": "550e8400-...",
  "status": "SUCCESS",
  "requires_validation": false,
  "request_ref": "abc123def456",
  "provider_ref": "prov_ref_123",
  "validation_fields": {}
}
```

**Response (Still Awaiting Validation):**
```json
{
  "id": "550e8400-...",
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

**Key Features:**
- Validates collection is in PENDING state with `requires_validation=true`
- Calls PayWithAccount validate endpoint
- Normalizes provider response status
- Updates collection and transactions atomically
- Returns updated collection with current validation state

**Status Codes:**
- `200 OK` — Validation processed
- `400 Bad Request` — Invalid request or collection state
- `403 Forbidden` — User does not own collection
- `404 Not Found` — Collection not found
- `500 Internal Server Error` — Provider error

#### C. New GET /api/v1/collections/{id}/query_status/ Endpoint (Endpoint #5)

**Purpose:** Query current collection status from payment provider

**Response (Status Updated):**
```json
{
  "id": "550e8400-...",
  "status": "SUCCESS",
  "requires_validation": false,
  "request_ref": "abc123def456",
  "provider_ref": "prov_ref_123",
  "updated_at": "2026-01-29T12:00:00Z"
}
```

**Response (Status Still Pending):**
```json
{
  "id": "550e8400-...",
  "status": "PENDING",
  "requires_validation": true,
  "request_ref": "abc123def456",
  "provider_ref": "prov_ref_123",
  "validation_fields": {
    "validation_ref": "val_ref_123",
    "session_id": "sess_456"
  }
}
```

**Key Features:**
- Uses best-effort approach with provider_ref or request_ref
- Calls PayWithAccount query endpoint
- Normalizes provider response status
- Updates collection if status changed
- Returns updated collection with current status

**Status Codes:**
- `200 OK` — Status queried successfully
- `400 Bad Request` — Cannot query or provider error
- `403 Forbidden` — User does not own collection
- `404 Not Found` — Collection not found

#### D. Enhanced Collection Status Flow

**Before:** Simple linear flow
```
PENDING -> INITIATED -> SUCCESS
                   \-> FAILED
```

**After:** Comprehensive flow with validation paths
```
INITIATED -> PENDING (with requires_validation=true) -> POST /validate/ -> SUCCESS
         \-> PENDING (no validation needed)             \-> GET /query_status/ -> SUCCESS
         \-> SUCCESS                                                      \-> FAILED
         \-> FAILED
         \-> CANCELLED
```

**Three Distinct Workflows:**

1. **Immediate Success (No Validation)**
   - Create collection → INITIATED
   - Provider processes → SUCCESS

2. **OTP Required (Requires Validation)**
   - Create collection → INITIATED
   - Provider needs OTP → PENDING (requires_validation: true)
   - POST /validate/ with OTP → SUCCESS (or PENDING for new validation)

3. **Status Query (Best Effort)**
   - Create collection → INITIATED
   - GET /query_status/ anytime → Status updated
   - Repeat until SUCCESS or FAILED

#### E. Validation Fields Table

Added comprehensive table showing all possible validation fields:

| Field | Purpose |
|-------|---------|
| `validation_ref` | Reference for validation submission |
| `session_id` | Session identifier for OTP |
| `otp_reference` | Provider's OTP reference ID |
| `challenge_ref` | Challenge reference for auth |
| `auth_token` | Token for authentication |

---

### 2. [PAYWITHACCOUNT_QUICK_REFERENCE.md](PAYWITHACCOUNT_QUICK_REFERENCE.md)

**New Section Added:** Collection Validation Endpoints

#### POST /api/v1/collections/{id}/validate/

Complete example with curl command:
```bash
curl -X POST http://localhost:8000/api/v1/collections/550e8400.../validate/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"otp": "123456"}'
```

**Response examples:**
- Success case (status: SUCCESS, requires_validation: false)
- Still pending case (status: PENDING, requires_validation: true with validation_fields)

#### GET /api/v1/collections/{id}/query_status/

Complete example with curl command:
```bash
curl -X GET http://localhost:8000/api/v1/collections/550e8400.../query_status/ \
  -H "Authorization: Bearer <token>"
```

**Response example showing normalized status and validation metadata**

#### Key Fields Reference Table

| Field | Meaning |
|-------|---------|
| `status` | Normalized: INITIATED, PENDING, SUCCESS, FAILED |
| `requires_validation` | Whether OTP/validation input needed |
| `request_ref` | Your transaction reference (for query_status) |
| `provider_ref` | PayWithAccount's transaction reference |
| `validation_fields` | Provider-specific validation metadata |

#### Workflow Examples

**OTP Required Workflow:**
1. Create collection → `status: INITIATED`
2. Provider returns OTP required → `status: PENDING, requires_validation: true`
3. POST /validate/ with OTP → `status: SUCCESS`

**Status Query Workflow:**
1. Create collection → `status: INITIATED`
2. GET /query_status/ → Status updated from provider
3. Repeat until `status: SUCCESS` or `FAILED`

---

## Documentation Content Additions

### New Response Fields (All Endpoints)

Every collection response now includes:

```json
{
  "requires_validation": boolean,
  "validation_fields": {
    "validation_ref": string,
    "session_id": string,
    "otp_reference": string,
    "challenge_ref": string,
    "auth_token": string
  }
}
```

### New Example Responses

#### Validation Successful Response
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_username": "john_doe",
  "goal_id": "550e8400-e29b-41d4-a716-446655440001",
  "goal_name": "Savings Goal",
  "amount_allocation": 50000.00,
  "kore_fee": 500.00,
  "amount_total": 50500.00,
  "currency": "NGN",
  "provider": "paywithaccount",
  "request_ref": "abc123def456",
  "provider_ref": "prov_ref_123",
  "status": "SUCCESS",
  "narrative": "Monthly savings",
  "requires_validation": false,
  "validation_fields": {},
  "created_at": "2026-01-29T10:30:00Z",
  "updated_at": "2026-01-29T12:00:00Z"
}
```

#### Validation Pending Response
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_username": "john_doe",
  "goal_id": "550e8400-e29b-41d4-a716-446655440001",
  "goal_name": "Savings Goal",
  "amount_allocation": 50000.00,
  "kore_fee": 500.00,
  "amount_total": 50500.00,
  "currency": "NGN",
  "provider": "paywithaccount",
  "request_ref": "abc123def456",
  "provider_ref": "prov_ref_123",
  "status": "PENDING",
  "narrative": "Monthly savings",
  "requires_validation": true,
  "validation_fields": {
    "validation_ref": "val_new_ref",
    "session_id": "sess_updated",
    "otp_reference": "otp_ref_456"
  },
  "created_at": "2026-01-29T10:30:00Z",
  "updated_at": "2026-01-29T12:00:00Z"
}
```

#### Query Status Response
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_username": "john_doe",
  "status": "SUCCESS",
  "requires_validation": false,
  "request_ref": "abc123def456",
  "provider_ref": "prov_ref_123",
  "validation_fields": {},
  "updated_at": "2026-01-29T12:00:00Z"
}
```

### Error Response Examples

#### Collection Not in Validatable State
```json
{
  "error": "Collection status is SUCCESS, must be PENDING to validate"
}
```

#### Collection Does Not Require Validation
```json
{
  "error": "Collection does not require validation"
}
```

#### Cannot Query Without References
```json
{
  "error": "Cannot query status: no provider_ref or request_ref available"
}
```

#### Provider Validation Failed
```json
{
  "error": "Validation failed with provider: PayWithAccount error: Invalid OTP"
}
```

---

## Usage Examples

### Scenario 1: Payment with OTP

**Step 1: Create Collection**
```bash
curl -X POST http://localhost:8000/api/v1/collections/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "goal_id": "550e8400-e29b-41d4-a716-446655440000",
    "amount_allocation": 50000.00,
    "narrative": "Monthly savings"
  }'
```

Response: `status: INITIATED, requires_validation: false` (or true if OTP needed immediately)

**Step 2a: If requires_validation is true, Submit OTP**
```bash
curl -X POST http://localhost:8000/api/v1/collections/550e8400-e29b-41d4-a716-446655440000/validate/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"otp": "123456"}'
```

Response: `status: SUCCESS, requires_validation: false` (payment complete!)

**Step 2b: If still pending, check status**
```bash
curl -X GET http://localhost:8000/api/v1/collections/550e8400-e29b-41d4-a716-446655440000/query_status/ \
  -H "Authorization: Bearer <token>"
```

Response: Updated status from provider

### Scenario 2: Payment Without OTP (Immediate Success)

**Step 1: Create Collection**
```bash
curl -X POST http://localhost:8000/api/v1/collections/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"goal_id": "...", "amount_allocation": 50000.00}'
```

Response: `status: SUCCESS, requires_validation: false` (done!)

---

## Key Improvements

✅ **Comprehensive Response Examples**
- All possible response states documented
- Real field values shown
- Validation metadata clearly explained

✅ **Complete Workflows**
- OTP required scenario
- No validation scenario
- Status query scenario
- All documented with examples

✅ **Clear Error Handling**
- All error cases documented
- Example error responses
- Guidance on resolution

✅ **Reference Documentation**
- Validation fields table
- Status codes table
- Parameter tables
- Field reference table

✅ **Integration Guidance**
- curl command examples
- Python code examples
- Complete workflow diagrams
- Troubleshooting guidance

---

## Related Documentation

- **[COLLECTIONS_ENDPOINTS.md](COLLECTIONS_ENDPOINTS.md)** — Detailed endpoint documentation
- **[COLLECTIONS_API.md](COLLECTIONS_API.md)** — Complete Collections API reference
- **[PAYWITHACCOUNT_QUICK_REFERENCE.md](PAYWITHACCOUNT_QUICK_REFERENCE.md)** — PayWithAccount integration guide
- **[COLLECTIONS_VALIDATION_HANDLING.md](COLLECTIONS_VALIDATION_HANDLING.md)** — Validation architecture
- **[WEBHOOKS_API.md](WEBHOOKS_API.md)** — Webhook integration
- **[IDEMPOTENCY_DOCUMENTATION_INDEX.md](IDEMPOTENCY_DOCUMENTATION_INDEX.md)** — Idempotency features

---

## Implementation Status

| Component | Status |
|-----------|--------|
| POST /validate/ endpoint | ✅ Implemented (Message 9) |
| GET /query_status/ endpoint | ✅ Implemented (Message 9) |
| requires_validation field | ✅ Implemented (Message 3) |
| validation_fields tracking | ✅ Implemented (Message 3) |
| request_ref tracking | ✅ Implemented (Message 1) |
| provider_ref tracking | ✅ Implemented (Message 9) |
| Status normalization | ✅ Implemented (Message 5) |
| API documentation | ✅ Complete (This document) |

---

## Testing the API

### Test OTP Validation
```bash
# Create collection that requires OTP
curl -X POST http://localhost:8000/api/v1/collections/ ...

# If requires_validation is true, submit OTP
curl -X POST http://localhost:8000/api/v1/collections/{id}/validate/ \
  -d '{"otp": "123456"}'
```

### Test Status Query
```bash
# Create collection
curl -X POST http://localhost:8000/api/v1/collections/ ...

# Query status at any time
curl -X GET http://localhost:8000/api/v1/collections/{id}/query_status/ \
  -H "Authorization: Bearer <token>"
```

### Test Validation Metadata
```bash
# Create collection and check response
curl -X GET http://localhost:8000/api/v1/collections/{id}/ \
  -H "Authorization: Bearer <token>"

# Look for requires_validation and validation_fields in response
```

---

## Next Steps

1. ✅ **Review** — Read this documentation
2. ✅ **Test** — Use curl examples to test endpoints
3. ✅ **Integrate** — Update client code to handle new fields
4. ✅ **Monitor** — Track which collections require validation
5. ✅ **Support** — Reference this doc for API questions

---

**Status:** ✅ Complete  
**Last Updated:** January 29, 2026  
**Documentation Version:** 1.0
