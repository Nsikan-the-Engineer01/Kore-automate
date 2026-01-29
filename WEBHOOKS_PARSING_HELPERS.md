# Webhook Parsing Helpers - Implementation Guide

## Overview

The webhook parsing utilities in `core_apps/webhooks/utils.py` provide defensive extraction functions that work with diverse provider payload formats. These helpers handle the complexity of different nesting patterns, field name variants (snake_case, camelCase), and missing/invalid data.

## Functions

### `extract_request_ref(payload) -> Optional[str]`

Extracts the application's internal request reference from a webhook payload.

**Tried paths (in order):**
- Top-level: `request_ref`, `requestRef`, `request_reference`, `requestReference`, `ref`
- Nested: `transaction.*`, `data.*`, `meta.*`, `event.*`, `payload.*`
- Variants: Both snake_case and camelCase

**Returns:** String if found, None otherwise

**Example:**
```python
extract_request_ref({'request_ref': 'req_1001_abc'})  # → 'req_1001_abc'
extract_request_ref({'data': {'requestRef': 'req_2002_def'}})  # → 'req_2002_def'
extract_request_ref({'transaction': {'request_ref': 'req_3003'}})  # → 'req_3003'
```

### `extract_provider_ref(payload) -> Optional[str]`

Extracts the provider's transaction identifier (varies by payment provider).

**Tried paths (in order):**
- Top-level variants: `provider_ref`, `providerRef`, `transaction_ref`, `transactionRef`, `txRef`, `tx_ref`, `reference`, `ref`
- Provider-specific: `flutterwave_ref`, `flutterwaveRef`, `paystack_ref`, `paystackRef`, `monnify_ref`, `monnifyRef`
- Nested: `transaction.*`, `data.*`, `meta.*`, `event.*`

**Returns:** String if found, None otherwise

**Example:**
```python
extract_provider_ref({'txRef': 'tx_12345'})  # → 'tx_12345'
extract_provider_ref({'flutterwaveRef': 'FLW9876543210'})  # → 'FLW9876543210'
extract_provider_ref({'data': {'transaction_ref': 'txn_001'}})  # → 'txn_001'
```

### `extract_status(payload) -> Optional[str]`

Extracts transaction status (e.g., "SUCCESS", "PENDING", "FAILED", "successful", "completed").

**Tried paths (in order):**
- Top-level: `status`, `transaction_status`, `transactionStatus`, `payment_status`, `paymentStatus`, `state`
- Nested: `transaction.*`, `data.*`, `event.*`, `meta.*`, `response.*`

**Returns:** Status string (as-is, case-sensitive) if found, None otherwise

**Important:** Status strings are **case-sensitive** and may vary by provider. The normalization layer (`normalize_provider_status()`) in the Collections service handles mapping these to internal enums.

**Example:**
```python
extract_status({'status': 'SUCCESS'})  # → 'SUCCESS'
extract_status({'data': {'transaction_status': 'completed'}})  # → 'completed'
extract_status({'event': {'state': 'PAID'}})  # → 'PAID'
```

### `extract_amount(payload) -> Optional[Union[float, int]]`

Extracts transaction amount as a numeric value.

**Tried paths (in order):**
- Top-level: `amount`, `value`, `total`, `total_amount`, `totalAmount`, `transaction_amount`, `transactionAmount`, `payable_amount`, `payableAmount`
- Nested: `transaction.*`, `data.*`, `meta.*`, `body.*`

**Returns:** Numeric value (int or float) if found and parseable, None otherwise

**Parsing behavior:**
- Accepts int, float, Decimal types directly
- Parses strings as float (e.g., "25000.50" → 25000.5)
- Returns None for non-numeric strings (e.g., "not_a_number")
- Handles zero, negative amounts (refunds)

**Example:**
```python
extract_amount({'amount': 50000})  # → 50000
extract_amount({'amount': '25000.50'})  # → 25000.5
extract_amount({'data': {'total': 75000}})  # → 75000
extract_amount({'amount': Decimal('99999.99')})  # → 99999.99
```

### `extract_currency(payload) -> Optional[str]`

Extracts currency code (typically 3-letter ISO code like "NGN", "USD", "GBP").

**Tried paths (in order):**
- Top-level: `currency`, `currency_code`, `currencyCode`, `currency_type`, `currencyType`, `curr`
- Nested: `transaction.*`, `data.*`, `meta.*`, `body.*`

**Returns:** Currency code string if found, None otherwise

**Parsing behavior:**
- Returns string as-is (preserves case: "NGN", "ngn", "Ngn" are all valid)
- Converts numeric codes to string (though rare)
- Strips whitespace

**Example:**
```python
extract_currency({'currency': 'NGN'})  # → 'NGN'
extract_currency({'data': {'currency_code': 'USD'}})  # → 'USD'
extract_currency({'currencyCode': 'EUR'})  # → 'EUR'
```

## Helper Functions

### `_get_by_path(payload: Dict, path: List[str]) -> Optional[Any]`

Safely traverse nested dict by a list of keys.

**Behavior:**
- Returns None if any key in path is missing
- Returns None if any intermediate value is not a dict
- Returns the final value if path traversal succeeds

**Example:**
```python
_get_by_path({'a': {'b': {'c': 42}}}, ['a', 'b', 'c'])  # → 42
_get_by_path({'a': {'b': {'c': 42}}}, ['a', 'x', 'c'])  # → None
_get_by_path({'a': None}, ['a', 'b'])  # → None
```

### `_first_non_empty(payload: Dict, paths: List[List[str]]) -> Optional[str]`

Return the first non-empty string value found following a list of candidate paths.

**Behavior:**
- Tries each path in order
- Converts values to string (int/UUID/etc)
- Rejects empty strings and non-convertible values
- Returns None if no path yields a non-empty string

**Example:**
```python
payload = {'a': '', 'b': {'c': 'found'}, 'd': None}
_first_non_empty(payload, [['a'], ['b', 'c'], ['d']])  # → 'found' (skips empty 'a')
```

### `_first_numeric(payload: Dict, paths: List[List[str]]) -> Optional[Union[float, int]]`

Return the first numeric value found following a list of candidate paths.

**Behavior:**
- Tries each path in order
- Accepts int, float, Decimal types
- Parses numeric strings as float
- Returns None if no path yields a numeric value

**Example:**
```python
payload = {'a': 'text', 'b': {'c': 50000}, 'd': '25000.50'}
_first_numeric(payload, [['a'], ['b', 'c'], ['d']])  # → 50000
```

## Supported Payload Shapes

The extraction helpers are designed to work with four common provider webhook payload shapes:

### 1. OnePipe-Style: Nested Transaction Structure

```json
{
  "request_ref": "req_1001_abc",
  "webhook_id": "wh_123",
  "event_type": "transaction.completed",
  "transaction": {
    "transaction_ref": "txn_server_2024_001",
    "amount": 50000,
    "currency": "NGN",
    "status": "SUCCESS"
  },
  "data": {
    "reference": "ref_xyz789"
  }
}
```

**Extractors find:**
- `extract_request_ref()` → "req_1001_abc"
- `extract_provider_ref()` → "txn_server_2024_001"
- `extract_status()` → "SUCCESS"
- `extract_amount()` → 50000
- `extract_currency()` → "NGN"

### 2. Flat-Style: All Fields at Top Level

```json
{
  "request_ref": "req_2002_def",
  "provider_ref": "prov_ghi_888",
  "txRef": "tx_flat_9999",
  "status": "COMPLETED",
  "amount": 25000.50,
  "currency": "USD",
  "timestamp": "2024-01-15T11:00:00Z"
}
```

**Extractors find:**
- `extract_request_ref()` → "req_2002_def"
- `extract_provider_ref()` → "prov_ghi_888"
- `extract_status()` → "COMPLETED"
- `extract_amount()` → 25000.5
- `extract_currency()` → "USD"

### 3. Meta-Wrapped: Fields in Data/Meta Containers

```json
{
  "event": "payment.complete",
  "data": {
    "id": "evt_metadata",
    "reference": "req_3003_ghi",
    "transactionRef": "tx_meta_5555",
    "transaction_status": "PAID",
    "total": "75000",
    "currency_code": "NGN"
  },
  "meta": {
    "request_ref": "req_3003_ghi_meta",
    "provider_ref": "prov_meta_777"
  }
}
```

**Extractors find:**
- `extract_request_ref()` → "req_3003_ghi" or "req_3003_ghi_meta" (first match in candidate_paths)
- `extract_provider_ref()` → "tx_meta_5555" or "prov_meta_777"
- `extract_status()` → "PAID"
- `extract_amount()` → 75000.0
- `extract_currency()` → "NGN"

### 4. Provider-Wrapped: Event/Response Wrapper Style

```json
{
  "event": {
    "type": "charge.success",
    "data": {
      "id": "evt_flutterwave",
      "txRef": "tx_fw_6666",
      "flutterwaveRef": "FLW1234567890",
      "amount": 10000,
      "currency": "NGN",
      "status": "successful",
      "reference": "req_4004_jkl"
    }
  },
  "body": {
    "amount": 10000,
    "value": 10000,
    "payable_amount": 10000
  }
}
```

**Extractors find:**
- `extract_request_ref()` → "req_4004_jkl"
- `extract_provider_ref()` → "tx_fw_6666" or "FLW1234567890"
- `extract_status()` → "successful"
- `extract_amount()` → 10000
- `extract_currency()` → "NGN"

## Usage in Webhook Handler

The parsing helpers are designed to be used in the webhook event processing task:

```python
from core_apps.webhooks.utils import (
    extract_request_ref,
    extract_provider_ref,
    extract_status,
    extract_amount,
    extract_currency,
)

def process_webhook_event_task(event_id):
    event = WebhookEvent.objects.get(id=event_id)
    payload = event.payload
    
    # Extract all fields defensively
    request_ref = extract_request_ref(payload)
    provider_ref = extract_provider_ref(payload)
    status = extract_status(payload)
    amount = extract_amount(payload)
    currency = extract_currency(payload)
    
    # Log extracted values
    logger.info(f"Webhook event {event_id}: request_ref={request_ref}, "
                f"provider_ref={provider_ref}, status={status}, "
                f"amount={amount}, currency={currency}")
    
    # Handle the webhook event based on extracted values
    if not request_ref:
        logger.warning(f"Webhook {event_id}: No request_ref found")
        return
    
    # Find collection by request_ref
    try:
        collection = Collection.objects.get(request_ref=request_ref)
        
        # Update collection status if status is present
        if status:
            from core_apps.integrations.paywithaccount.normalization import normalize_provider_status
            normalized_status, needs_validation = normalize_provider_status(status)
            collection.status = normalized_status
            collection.save()
            logger.info(f"Updated collection {collection.id} status to {normalized_status}")
            
    except Collection.DoesNotExist:
        logger.warning(f"Webhook {event_id}: No collection found for request_ref={request_ref}")
```

## Error Handling

All extraction functions are defensive and never raise exceptions:

- **Non-dict input:** Returns None (handles None, strings, lists, etc.)
- **Missing keys:** Returns None (gracefully continues to next path candidate)
- **Type mismatches:** Returns None (e.g., amount="text" cannot be parsed as number)
- **Empty strings/values:** Returns None (rejects empty results)
- **Nested path errors:** Returns None if any intermediate key is missing or non-dict

## Testing

Comprehensive test suite in `core_apps/webhooks/utils_tests.py` includes:

- **Per-function tests:** 10-15 test cases per extractor covering normal cases, edge cases, and error scenarios
- **Payload shape tests:** 5 different payload formats (OnePipe, Flat, Meta-wrapped, Provider-wrapped, Minimal, Empty)
- **Integration tests:** All extractors working together on each payload shape
- **Edge cases:** Whitespace, case sensitivity, numeric strings, missing fields, invalid types

**Run tests:**
```bash
python manage.py test core_apps.webhooks.utils_tests
```

## Future Enhancements

Potential improvements:

1. **Custom path patterns:** Allow passing additional candidate paths to handle new provider formats
2. **Logging:** Optional debug logging for extraction attempts (help with troubleshooting new providers)
3. **Validation:** Validate extracted values against expected ranges/formats (e.g., amount > 0)
4. **Caching:** Cache extraction path candidates by provider type to avoid repeated searches
5. **Type hints:** More specific return type hints (e.g., `PositiveFloat` for amounts)

## References

- [WEBHOOK_QUICK_REFERENCE.md](WEBHOOK_QUICK_REFERENCE.md) - Quick webhook integration guide
- [WEBHOOKS_API.md](WEBHOOKS_API.md) - Full webhook API documentation
- [PAYWITHACCOUNT_QUICK_REFERENCE.md](PAYWITHACCOUNT_QUICK_REFERENCE.md) - PayWithAccount integration guide
