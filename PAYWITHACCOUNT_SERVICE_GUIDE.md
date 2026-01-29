# PayWithAccountService - Usage Guide

## Overview

`PayWithAccountService` is a thin wrapper around `PayWithAccountClient` that provides:
- Simplified transaction interface returning `dict` format
- Optional KORE metadata builder
- Clean separation of concerns

**Location:** `core_apps/integrations/paywithaccount/service.py`

## Installation

```python
from core_apps.integrations.paywithaccount.service import PayWithAccountService

service = PayWithAccountService()
```

## API Reference

### transact(payload: dict) -> dict

Executes a transaction and returns response with request_ref.

**Parameters:**
- `payload` (dict): Transaction payload with 'transaction' key

**Returns:**
- dict with keys:
  - `request_ref`: Generated UUID hex string for tracking
  - `data`: API response JSON

**Raises:**
- `PayWithAccountError`: On API or network errors

**Example:**
```python
service = PayWithAccountService()

payload = {
    'transaction': {
        'amount': 10000.00,
        'currency': 'NGN',
        'type': 'debit'
    }
}

try:
    response = service.transact(payload)
    print(f"Request Ref: {response['request_ref']}")
    print(f"Status: {response['data']['status']}")
except PayWithAccountError as e:
    print(f"Error: {e.status_code} - {e.response_text}")
```

### build_meta_defaults(user_id: str = None, goal_id: str = None) -> dict

Builds optional KORE metadata fields.

**Parameters:**
- `user_id` (optional): KORE user ID (becomes 'kore_user_id')
- `goal_id` (optional): KORE goal ID (becomes 'kore_goal_id')

**Returns:**
- dict with KORE metadata fields (empty if no args provided)

**Example 1: With both fields**
```python
meta = service.build_meta_defaults(
    user_id='usr-123',
    goal_id='goal-456'
)
# {'kore_user_id': 'usr-123', 'kore_goal_id': 'goal-456'}
```

**Example 2: With user_id only**
```python
meta = service.build_meta_defaults(user_id='usr-789')
# {'kore_user_id': 'usr-789'}
```

**Example 3: With UUIDs (automatically converted to strings)**
```python
import uuid
user_id = uuid.uuid4()
goal_id = uuid.uuid4()

meta = service.build_meta_defaults(
    user_id=user_id,
    goal_id=goal_id
)
# {'kore_user_id': '...uuid...', 'kore_goal_id': '...uuid...'}
```

**Example 4: Empty metadata**
```python
meta = service.build_meta_defaults()
# {}
```

## Complete Workflow Example

```python
from core_apps.integrations.paywithaccount.service import PayWithAccountService
from core_apps.integrations.paywithaccount.client import PayWithAccountError

service = PayWithAccountService()

# Step 1: Build optional metadata
meta = service.build_meta_defaults(
    user_id=str(user.id),
    goal_id=str(goal.id)
)

# Step 2: Create payload
payload = {
    'transaction': {
        'amount': amount_total,
        'currency': 'NGN',
        'type': 'debit'
    },
    'meta': meta  # Optional
}

# Step 3: Execute transaction
try:
    response = service.transact(payload)
    
    request_ref = response['request_ref']
    api_response = response['data']
    
    # Step 4: Process response
    if api_response.get('status') == 'success':
        provider_ref = api_response.get('reference')
        # Handle success
    else:
        # Handle non-success response
        pass
        
except PayWithAccountError as e:
    # Handle error
    print(f"Transaction failed: {e.status_code}")
```

## Integration with CollectionsService

The service is designed to be used by business logic services like `CollectionsService`:

```python
from core_apps.integrations.paywithaccount.service import PayWithAccountService

class CollectionsService:
    def __init__(self):
        self.pwa_service = PayWithAccountService()
    
    def create_collection(self, user, goal, amount_allocation, ...):
        # Build metadata
        meta = self.pwa_service.build_meta_defaults(
            user_id=user.id,
            goal_id=goal.id
        )
        
        # Build payload
        payload = self.build_pwa_payload(..., meta_overrides=meta)
        
        # Execute
        response = self.pwa_service.transact(payload)
        
        # Rest of business logic
        ...
```

## Key Design Decisions

1. **Dict Return Format**: Service returns `dict` instead of `TransactionResult` for convenience
2. **Thin Wrapper**: All business logic remains in service layer (e.g., CollectionsService)
3. **Optional Metadata**: Metadata builder is optional - payload can include custom meta
4. **ID Conversion**: Automatically converts int/UUID to string for meta fields
5. **Error Propagation**: PayWithAccountError bubbles up unchanged for centralized handling

## Testing

```bash
# Run service tests
python manage.py test core_apps.integrations.paywithaccount.service_tests

# Run with coverage
coverage run --source='.' manage.py test core_apps.integrations.paywithaccount.service_tests
coverage report
```

## Error Handling

The service propagates `PayWithAccountError` from the client:

```python
from core_apps.integrations.paywithaccount.client import PayWithAccountError

try:
    response = service.transact(payload)
except PayWithAccountError as e:
    # Access error details
    print(f"Status: {e.status_code}")
    print(f"Message: {e.response_text}")
    print(f"Request Ref: {e.request_ref}")
    
    # Handle specific cases
    if e.status_code == 400:
        # Invalid request
        pass
    elif e.status_code >= 500:
        # Server error
        pass
    elif e.exception:
        # Network error
        pass
```

## Dependencies

- Django 5.2+
- `PayWithAccountClient` (from same package)
- `PayWithAccountError` (from same package)
- Standard library: `logging`, `typing`

## See Also

- [PayWithAccountClient](client.py) - Low-level API client
- [PAYWITHACCOUNT_QUICK_REFERENCE.md](PAYWITHACCOUNT_QUICK_REFERENCE.md) - Settings reference
- [PAYWITHACCOUNT_SETTINGS.md](PAYWITHACCOUNT_SETTINGS.md) - Detailed configuration guide
