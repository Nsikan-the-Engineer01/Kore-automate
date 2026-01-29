# Collections Service - Validation Handling Implementation

## Overview
The Collections Service now detects and handles PayWithAccount validation cases (OTP, challenge, etc.) automatically when creating collections.

## Changes Made

### 1. **CollectionsService.create_collection()**
**File:** `core_apps/collections/services.py`

- Added import: `from core_apps.integrations.paywithaccount.normalization import normalize_provider_status`
- After `PayWithAccountClient.transact()` call, added validation handling:
  - Extracts `status` from response JSON (defensive: checks both `status` and `transaction_status`)
  - Normalizes status using `normalize_provider_status()` → `(status, needs_validation)`
  - Sets collection status based on validation requirement:
    - `needs_validation=True` → status = `"PENDING"`
    - `normalized_status == "SUCCESS"` → status = `"SUCCESS"`
    - `normalized_status == "FAILED"` → status = `"FAILED"`
    - Otherwise → status = `"PENDING"`
  - Stores validation metadata:
    - `metadata['needs_validation']`: Boolean flag
    - `metadata['normalized_status']`: Normalized internal status
    - `metadata['validation_fields']`: Dict of extracted validation identifiers (validation_ref, session_id, otp_reference, challenge_ref, auth_token)
  - Transaction status aligned with collection status (PENDING if collection is PENDING, SUCCESS if SUCCESS, FAILED if FAILED)
  - All extraction is defensive — missing fields won't crash

### 2. **CollectionCreateResponseSerializer**
**File:** `core_apps/collections/serializers.py`

New response serializer that extends `CollectionSerializer`:
- Added field: `requires_validation` — SerializerMethodField reading from `metadata['needs_validation']`
- Added field: `validation_fields` — SerializerMethodField extracting `metadata['validation_fields']` or empty dict
- Handles None metadata gracefully (returns False/empty dict)

### 3. **CollectionViewSet.create()**
**File:** `core_apps/collections/views.py`

Updated response serialization:
- Changed from `CollectionSerializer` to `CollectionCreateResponseSerializer` for create response
- Frontend now receives `requires_validation` flag and `validation_fields` in response

### 4. **Test Coverage**
**File:** `core_apps/collections/tests_validation.py`

New test suite with 10+ test cases:
- `test_collection_with_validation_required()` — OTP validation case
- `test_collection_with_success_status()` — Success case
- `test_collection_with_failed_status()` — Failed case
- `test_collection_with_pending_status()` — Pending without validation
- `test_collection_with_missing_status_field()` — Defensive handling
- `test_collection_with_multiple_validation_fields()` — Extraction of all field types
- `test_collection_with_case_insensitive_status()` — Case handling
- `test_transaction_status_follows_collection_status()` — Status propagation

### 5. **Documentation**
**File:** `PAYWITHACCOUNT_QUICK_REFERENCE.md`

Added "Collections API - Validation Handling" section with:
- Example response JSON showing validation case
- Field descriptions
- Frontend flow for handling validation
- Behavior details

## Response Example

**Request:**
```bash
POST /api/v1/collections/
{
    "goal_id": "uuid",
    "amount_allocation": 50000.00,
    "narrative": "Payment"
}
```

**Response (Validation Required):**
```json
{
    "id": "collection-uuid",
    "status": "PENDING",
    "requires_validation": true,
    "validation_fields": {
        "validation_ref": "val_123",
        "session_id": "sess_456"
    },
    "amount_allocation": 50000.00,
    "kore_fee": 500.00,
    "amount_total": 50500.00,
    "currency": "NGN",
    "request_ref": "request_uuid",
    "provider_ref": "provider_ref_123"
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
    "provider_ref": "provider_ref_123"
}
```

## Key Properties

✅ **Defensive:** Missing fields in provider response don't crash — defaults applied  
✅ **Configurable:** Status mappings editable via `PAYWITHACCOUNT_STATUS_MAP` setting  
✅ **Non-Breaking:** Adds fields to response; existing code unaffected  
✅ **Audit Trail:** Validation fields stored in metadata for debugging  
✅ **Consistent:** Transaction status mirrors collection status  

## Testing

Run tests locally:
```bash
docker compose -f local.yml exec api python manage.py test core_apps.collections.tests_validation
```

Or test a single case:
```bash
docker compose -f local.yml exec api python manage.py test core_apps.collections.tests_validation.CollectionsServiceValidationTest.test_collection_with_validation_required
```

## Integration Notes

- Collections webhook handler (`update_collection_from_webhook`) will update status when provider sends final validation result
- Frontend should check `requires_validation` flag and prompt user accordingly
- `validation_fields` contains identifiers needed for follow-up OTP submission to provider (out of scope for this API)
