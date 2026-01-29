# Collections API - Validation & Query Endpoints

## Overview

Two new endpoints enable collecting validation input and querying transaction status after collection creation.

## Endpoints

### 1. POST /api/v1/collections/{id}/validate/

**Purpose:** Submit validation data (OTP, challenge response, etc.) for collections awaiting validation.

**Request Body:**
```json
{
    "otp": "123456"
}
```

**Request Fields:**
- `otp` (string, optional): One-time password from user (if provider requires)
- Additional fields: Any provider-specific validation fields can be included in the request; they will be passed through to the provider API

**Response (Validation Successful):**
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
    "request_ref": "abc123def456...",
    "provider_ref": "prov_ref_123...",
    "status": "SUCCESS",
    "narrative": "Monthly savings",
    "requires_validation": false,
    "validation_fields": {},
    "updated_at": "2026-01-29T12:00:00Z"
}
```

**Response (Still Awaiting Validation):**
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
    "request_ref": "abc123def456...",
    "provider_ref": "prov_ref_123...",
    "status": "PENDING",
    "narrative": "Monthly savings",
    "requires_validation": true,
    "validation_fields": {
        "validation_ref": "val_new_ref",
        "session_id": "sess_updated"
    },
    "updated_at": "2026-01-29T12:00:00Z"
}
```

**Error Responses:**

1. Collection not in validatable state (400 Bad Request):
```json
{
    "error": "Collection status is SUCCESS, must be PENDING to validate"
}
```

2. Collection does not require validation (400 Bad Request):
```json
{
    "error": "Collection does not require validation"
}
```

3. Provider validation failed (400 Bad Request):
```json
{
    "error": "Validation failed with provider: PayWithAccount error: ..."
}
```

4. Permission denied (403 Forbidden):
```json
{
    "error": "You do not have permission to perform this action."
}
```

**Status Codes:**
- `200 OK` — Validation processed (successful or pending)
- `400 Bad Request` — Invalid request or collection state
- `403 Forbidden` — User does not own collection
- `404 Not Found` — Collection not found
- `500 Internal Server Error` — Server error

**Behavior:**
1. Validates that collection is in PENDING state with `requires_validation=true`
2. Calls `PayWithAccountClient.validate(payload)` with collection context
3. Normalizes provider response status
4. Updates collection status and transactions based on normalized status
5. Returns updated collection with current validation state
6. Transaction statuses updated to match collection status

---

### 2. GET /api/v1/collections/{id}/query_status/

**Purpose:** Query the current status of a collection from the payment provider.

**Query Parameters:** None

**Request Body:** None

**Response (Status Updated):**
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
    "request_ref": "abc123def456...",
    "provider_ref": "prov_ref_123...",
    "status": "SUCCESS",
    "narrative": "Monthly savings",
    "requires_validation": false,
    "validation_fields": {},
    "updated_at": "2026-01-29T12:00:00Z"
}
```

**Response (Status Still Pending):**
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
    "request_ref": "abc123def456...",
    "provider_ref": "prov_ref_123...",
    "status": "PENDING",
    "narrative": "Monthly savings",
    "requires_validation": true,
    "validation_fields": {
        "validation_ref": "val_ref_123",
        "session_id": "sess_456"
    },
    "updated_at": "2026-01-29T12:00:00Z"
}
```

**Error Responses:**

1. Cannot query without references (400 Bad Request):
```json
{
    "error": "Cannot query status: no provider_ref or request_ref available"
}
```

2. Provider query failed (400 Bad Request):
```json
{
    "error": "Query failed with provider: PayWithAccount error: ..."
}
```

3. Permission denied (403 Forbidden):
```json
{
    "error": "You do not have permission to perform this action."
}
```

**Status Codes:**
- `200 OK` — Status queried successfully (returns updated collection)
- `400 Bad Request` — Cannot query or provider error
- `403 Forbidden` — User does not own collection
- `404 Not Found` — Collection not found
- `500 Internal Server Error` — Server error

**Behavior:**
1. Uses collection's `provider_ref` (preferred) or `request_ref` for lookup
2. Calls `PayWithAccountClient.query(payload)` with collection reference
3. Normalizes provider response status
4. Updates collection and transactions only if status changed
5. Returns collection with latest status
6. Non-blocking: even if provider returns same status, collection is returned successfully

---

## Frontend Integration Example

### Validation Flow

```javascript
// 1. Create collection (may require validation)
const createResponse = await fetch('/api/v1/collections/', {
    method: 'POST',
    headers: {'Authorization': `Bearer ${token}`},
    body: JSON.stringify({
        goal_id: 'goal-uuid',
        amount_allocation: 50000.00
    })
});
const collection = await createResponse.json();

// 2. Check if validation required
if (collection.requires_validation) {
    // Show OTP prompt to user
    const otp = await getUserOTP();
    
    // 3. Submit validation
    const validateResponse = await fetch(`/api/v1/collections/${collection.id}/validate/`, {
        method: 'POST',
        headers: {'Authorization': `Bearer ${token}`},
        body: JSON.stringify({otp: otp})
    });
    const updatedCollection = await validateResponse.json();
    
    // 4. Check updated status
    if (updatedCollection.status === 'SUCCESS') {
        showSuccess('Payment completed!');
    } else if (updatedCollection.requires_validation) {
        showError('OTP incorrect, please try again');
    } else if (updatedCollection.status === 'FAILED') {
        showError('Payment failed');
    }
}
```

### Status Query Flow

```javascript
// Poll for status updates (e.g., after webhook delay)
const statusResponse = await fetch(`/api/v1/collections/${collectionId}/query_status/`, {
    method: 'GET',
    headers: {'Authorization': `Bearer ${token}`}
});
const updatedCollection = await statusResponse.json();

console.log(`Collection status: ${updatedCollection.status}`);
```

---

## Implementation Notes

**Service Methods:**
- `CollectionsService.validate_collection(collection, otp, extra_fields)` — Submits validation
- `CollectionsService.query_collection_status(collection)` — Queries current status

**Serializers:**
- `CollectionValidateSerializer` — Input validation for OTP request
- `CollectionStatusResponseSerializer` — Output format for both validation and query responses

**ViewSet Actions:**
- `@action(detail=True, methods=['post']) validate()` — Handles POST /collections/{id}/validate/
- `@action(detail=True, methods=['get']) query_status()` — Handles GET /collections/{id}/query_status/

**Atomic Transactions:**
- Both endpoints wrapped in `@transaction.atomic`
- Collection and related transactions updated together
- On error, entire operation rolled back

**Error Handling:**
- Defensive extraction of fields (missing fields don't crash)
- `CollectionError` for business logic errors
- `PayWithAccountError` for provider API errors
- Graceful 400/403/500 responses to frontend

