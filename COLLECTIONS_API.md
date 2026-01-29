# Collections API Documentation

## Overview

The Collections API handles the creation and management of money collections/contributions to financial goals. It integrates with the PayWithAccount payment provider to process transactions.

## Authentication

All endpoints require authentication via Bearer token. Include in request headers:
```
Authorization: Bearer <token>
```

## Endpoints

### 1. Create Collection
**POST** `/api/v1/collections/`

Creates a new collection and initiates payment processing with the PayWithAccount provider.

#### Request Body
```json
{
  "goal_id": "550e8400-e29b-41d4-a716-446655440000",
  "amount_allocation": 10000.00,
  "currency": "NGN",
  "narrative": "Monthly savings contribution"
}
```

#### Request Parameters
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `goal_id` | UUID | Yes | ID of the goal to contribute to |
| `amount_allocation` | Decimal | Yes | Amount to contribute (min 0.01) |
| `currency` | String | No | Currency code (default: "NGN") |
| `narrative` | String | No | Optional description of the contribution |

#### Response (201 Created)
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "user_username": "john_doe",
  "goal_id": "550e8400-e29b-41d4-a716-446655440000",
  "goal_name": "Emergency Fund",
  "amount_allocation": 10000.00,
  "kore_fee": 250.00,
  "amount_total": 10250.00,
  "currency": "NGN",
  "provider": "paywithaccount",
  "request_ref": "req_abc123def456",
  "provider_ref": null,
  "status": "INITIATED",
  "narrative": "Monthly savings contribution",
  "created_at": "2026-01-29T10:30:00Z",
  "updated_at": "2026-01-29T10:30:00Z"
}
```

#### Status Codes
- `201 Created` - Collection successfully created
- `400 Bad Request` - Invalid request body or validation error
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - Goal does not belong to authenticated user
- `404 Not Found` - Goal not found
- `500 Internal Server Error` - Payment processing failed

#### Example Request
```bash
curl -X POST http://localhost:8000/api/v1/collections/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "goal_id": "550e8400-e29b-41d4-a716-446655440000",
    "amount_allocation": 10000.00,
    "narrative": "Emergency fund contribution"
  }'
```

---

### 2. List Collections
**GET** `/api/v1/collections/`

Retrieves all collections created by the authenticated user, ordered by creation date (newest first).

#### Query Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | String | Filter by status (PENDING, INITIATED, SUCCESS, FAILED, CANCELLED) |
| `ordering` | String | Sort order. Options: `-created_at` (default), `created_at`, `status`, `amount_total` |
| `limit` | Integer | Number of results per page |
| `offset` | Integer | Pagination offset |

#### Response (200 OK)
```json
{
  "count": 15,
  "next": "http://localhost:8000/api/v1/collections/?offset=10",
  "previous": null,
  "results": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "user_username": "john_doe",
      "goal_id": "550e8400-e29b-41d4-a716-446655440000",
      "goal_name": "Emergency Fund",
      "amount_allocation": 10000.00,
      "kore_fee": 250.00,
      "amount_total": 10250.00,
      "currency": "NGN",
      "provider": "paywithaccount",
      "request_ref": "req_abc123def456",
      "provider_ref": "pwa_ref_789",
      "status": "SUCCESS",
      "narrative": "Monthly savings contribution",
      "created_at": "2026-01-29T10:30:00Z",
      "updated_at": "2026-01-29T10:35:00Z"
    }
  ]
}
```

#### Status Codes
- `200 OK` - Collections retrieved successfully
- `401 Unauthorized` - Missing or invalid authentication

#### Example Request
```bash
curl -X GET "http://localhost:8000/api/v1/collections/?status=SUCCESS&limit=10" \
  -H "Authorization: Bearer <token>"
```

---

### 3. Retrieve Collection
**GET** `/api/v1/collections/{id}/`

Retrieves details of a specific collection by ID. User must own the collection.

#### URL Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Collection ID |

#### Response (200 OK)
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "user_username": "john_doe",
  "goal_id": "550e8400-e29b-41d4-a716-446655440000",
  "goal_name": "Emergency Fund",
  "amount_allocation": 10000.00,
  "kore_fee": 250.00,
  "amount_total": 10250.00,
  "currency": "NGN",
  "provider": "paywithaccount",
  "request_ref": "req_abc123def456",
  "provider_ref": "pwa_ref_789",
  "status": "SUCCESS",
  "narrative": "Monthly savings contribution",
  "requires_validation": false,
  "validation_fields": {},
  "created_at": "2026-01-29T10:30:00Z",
  "updated_at": "2026-01-29T10:35:00Z"
}
```

#### Status Codes
- `200 OK` - Collection retrieved successfully
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - User does not own the collection
- `404 Not Found` - Collection not found

#### Example Request
```bash
curl -X GET http://localhost:8000/api/v1/collections/660e8400-e29b-41d4-a716-446655440001/ \
  -H "Authorization: Bearer <token>"
```

---

### 4. Get Collection Status (Custom Endpoint)
**GET** `/api/v1/collections/{id}/status/`

Lightweight endpoint to get just the status and last update time of a collection.

#### URL Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | UUID | Collection ID |

#### Response (200 OK)
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "status": "SUCCESS",
  "updated_at": "2026-01-29T10:35:00Z"
}
```

#### Status Codes
- `200 OK` - Status retrieved successfully
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - User does not own the collection
- `404 Not Found` - Collection not found

#### Example Request
```bash
curl -X GET http://localhost:8000/api/v1/collections/660e8400-e29b-41d4-a716-446655440001/status/ \
  -H "Authorization: Bearer <token>"
```

---

### 4. Validate Collection
**POST** `/api/v1/collections/{id}/validate/`

Submits validation data (OTP, challenge response, etc.) for collections awaiting validation.

#### Request Body
```json
{
  "otp": "123456"
}
```

#### Request Parameters
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `otp` | String | Optional | One-time password from user |
| Additional fields | Any | Optional | Provider-specific validation fields |

#### Response (200 OK - Validation Successful)
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

#### Response (200 OK - Still Awaiting Validation)
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

#### Status Codes
- `200 OK` - Validation processed (successful or pending)
- `400 Bad Request` - Invalid request or collection state
- `403 Forbidden` - User does not own collection
- `404 Not Found` - Collection not found
- `500 Internal Server Error` - Provider validation failed

#### Error Response Examples

**Collection Not in Validatable State:**
```json
{
  "error": "Collection status is SUCCESS, must be PENDING to validate"
}
```

**Collection Does Not Require Validation:**
```json
{
  "error": "Collection does not require validation"
}
```

**Provider Validation Failed:**
```json
{
  "error": "Validation failed with provider: PayWithAccount error: Invalid OTP"
}
```

#### Example Request
```bash
curl -X POST http://localhost:8000/api/v1/collections/550e8400-e29b-41d4-a716-446655440000/validate/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "otp": "123456"
  }'
```

#### Behavior
1. Validates that collection is in PENDING state with `requires_validation=true`
2. Calls PayWithAccount validate endpoint with collection context
3. Normalizes provider response status
4. Updates collection status and linked transactions
5. Returns updated collection with current validation state

---

### 5. Query Collection Status
**GET** `/api/v1/collections/{id}/query_status/`

Queries the current status of a collection from the payment provider.

#### Query Parameters
None

#### Response (200 OK - Status Updated)
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

#### Response (200 OK - Status Still Pending)
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
    "validation_ref": "val_ref_123",
    "session_id": "sess_456"
  },
  "created_at": "2026-01-29T10:30:00Z",
  "updated_at": "2026-01-29T12:00:00Z"
}
```

#### Status Codes
- `200 OK` - Status queried successfully
- `400 Bad Request` - Cannot query (no provider_ref or request_ref)
- `403 Forbidden` - User does not own collection
- `404 Not Found` - Collection not found
- `500 Internal Server Error` - Provider query failed

#### Error Response Examples

**Cannot Query Without References:**
```json
{
  "error": "Cannot query status: no provider_ref or request_ref available"
}
```

**Provider Query Failed:**
```json
{
  "error": "Query failed with provider: PayWithAccount error: Invalid request reference"
}
```

#### Example Request
```bash
curl -X GET http://localhost:8000/api/v1/collections/550e8400-e29b-41d4-a716-446655440000/query_status/ \
  -H "Authorization: Bearer <token>"
```

#### Behavior
1. Uses best-effort approach with provider_ref or request_ref
2. Calls PayWithAccount query endpoint
3. Normalizes provider response status
4. Updates collection status and transactions if status changed
5. Returns updated collection with current status

---

## Collection Status Flow

Collections progress through the following statuses:

```
INITIATED -> PENDING (with requires_validation=true) -> POST /validate/ -> SUCCESS
         \-> PENDING (no validation needed)             \-> GET /query_status/ -> SUCCESS
         \-> SUCCESS                                                      \-> FAILED
         \-> FAILED
         \-> CANCELLED
```

| Status | Description |
|--------|-------------|
| `INITIATED` | Collection sent to PayWithAccount, awaiting processing |
| `PENDING` | Awaiting validation input (OTP) or query for status update |
| `SUCCESS` | Payment completed successfully |
| `FAILED` | Payment processing failed |
| `CANCELLED` | Collection was cancelled by user |

#### Validation Flows

**Flow 1: Immediate Success (No Validation)**
1. Create collection → Status: INITIATED
2. Provider processes immediately → Status: SUCCESS

**Flow 2: OTP Required (Requires Validation)**
1. Create collection → Status: INITIATED
2. Provider requires OTP → Status: PENDING, requires_validation: true
3. Call POST /validate/ with OTP → Status: SUCCESS (or PENDING if new validation needed)

**Flow 3: Status Query (Best Effort)**
1. Create collection → Status: INITIATED
2. Call GET /query_status/ at any time → Status updated if provider has new info
3. Repeat until Status: SUCCESS or FAILED

#### Validation Fields

When `requires_validation=true`, the `validation_fields` object contains provider-specific data:

| Field | Purpose |
|-------|---------|
| `validation_ref` | Reference for validation submission |
| `session_id` | Session identifier for OTP |
| `otp_reference` | Provider's OTP reference ID |
| `challenge_ref` | Challenge reference for challenge-response auth |
| `auth_token` | Token for authentication challenge |

---

## Fee Calculation

Fees are calculated based on server configuration:

- **Percentage-based** (if `KORE_FEE_PERCENT` is set): `fee = amount_allocation * (KORE_FEE_PERCENT / 100)`
- **Flat fee** (if `KORE_FEE_FLAT` is set): `fee = KORE_FEE_FLAT`
- **Precedence**: Percentage fee takes precedence over flat fee
- **Default**: 0% if neither is configured

The `amount_total` sent to the payment provider is: `amount_allocation + kore_fee`

---

## Error Responses

All error responses follow this format:

```json
{
  "error": "Detailed error message"
}
```

### Common Error Scenarios

#### 400 Bad Request - Invalid Amount
```json
{
  "error": "Amount must be greater than zero."
}
```

#### 403 Forbidden - Goal Not Owned
```json
{
  "error": "You do not have permission to use this goal"
}
```

#### 404 Not Found - Goal Missing
```json
{
  "error": "Goal does not exist."
}
```

#### 500 Internal Server Error - Payment Provider Issue
```json
{
  "error": "Failed to create collection: <provider error details>"
}
```

---

## Security Considerations

1. **Ownership Enforcement**: All endpoints verify that the authenticated user owns the accessed collections/goals
2. **Atomic Transactions**: Collection creation is atomic - either fully succeeds or fully fails
3. **Idempotency**: Multiple requests with the same `idempotency_key` will return the same collection
4. **Audit Trail**: All collections and their history are stored for audit purposes

---

## Integration with Payment Provider

Collections are processed through the PayWithAccount API:

- **Request Reference**: Unique ID (`request_ref`) generated per collection
- **Provider Reference**: Merchant's transaction reference from PayWithAccount (`provider_ref`)
- **Status Reconciliation**: Webhook events update collection status based on provider feedback
- **Fee Handling**: Fees are separately tracked in the double-entry ledger

---

## Testing

Run the test suite:

```bash
python manage.py test core_apps.collections.tests.TestCollectionEndpoints
```

Key test scenarios covered:
- Collection creation with and without optional fields
- Permission enforcement (ownership checks)
- Authentication requirements
- List and detail retrieval
- Status filtering
- Custom status endpoint
- Error handling for invalid inputs
