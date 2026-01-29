# PayWithAccount Settings Configuration

## Overview

PayWithAccount (OnePipe) settings are now consolidated in a clean dictionary format accessible throughout the application.

## Settings Dictionary

Access configuration via:
```python
from django.conf import settings

# Get entire config
config = settings.PAYWITHACCOUNT

# Get specific value
base_url = settings.PAYWITHACCOUNT['base_url']
timeout = settings.PAYWITHACCOUNT['timeout_seconds']
```

## Configuration

### Environment Variables

| Variable | Default | Required | Notes |
|----------|---------|----------|-------|
| `PWA_BASE_URL` | `https://api.dev.onepipe.io` | No | OnePipe API base URL |
| `PWA_TRANSACT_PATH` | `/v2/transact` | No | Payment endpoint path |
| `PWA_API_KEY` | `` | Yes | API key for authentication |
| `PWA_CLIENT_SECRET` | `` | Yes | Client secret for signature (legacy: PWA_SECRET_KEY) |
| `PWA_WEBHOOK_SECRET` | `` | No | Webhook signature verification secret |
| `PWA_MOCK_MODE` | `inspect` | No | Mock mode setting (e.g., "inspect", "true", "false") |
| `PWA_REQUEST_TYPE` | `invoice` | No | Payment request type |
| `PWA_TIMEOUT_SECONDS` | `30` | No | HTTP request timeout in seconds |

### Settings Dictionary Structure

```python
PAYWITHACCOUNT = {
    'base_url': 'https://api.dev.onepipe.io',              # Default
    'transact_path': '/v2/transact',                       # Default
    'api_key': '',                                         # From PWA_API_KEY env
    'client_secret': '',                                   # From PWA_CLIENT_SECRET env
    'webhook_secret': '',                                  # From PWA_WEBHOOK_SECRET env
    'mock_mode': 'inspect',                                # Default
    'request_type': 'invoice',                             # Default
    'timeout_seconds': 30,                                 # Default
}
```

## Usage Examples

### In PayWithAccountClient

```python
from django.conf import settings

class PayWithAccountClient:
    def __init__(self):
        config = settings.PAYWITHACCOUNT
        self.base_url = config['base_url']
        self.api_key = config['api_key']
        self.client_secret = config['client_secret']
        self.timeout = config['timeout_seconds']
```

### In Service Layer

```python
from django.conf import settings

class CollectionsService:
    def __init__(self):
        self.pwa_config = settings.PAYWITHACCOUNT
    
    def build_pwa_payload(self, ...):
        return {
            'request_type': self.pwa_config['request_type'],
            'mock_mode': self.pwa_config['mock_mode'],
            ...
        }
```

## Security Notes

### Secrets Not Logged

The following are sensitive and should never be logged:
- `api_key`
- `client_secret`
- `webhook_secret`

When logging configuration:
```python
# ✅ SAFE: Only log non-sensitive values
logger.info(f"PWA base_url: {settings.PAYWITHACCOUNT['base_url']}")
logger.info(f"PWA timeout: {settings.PAYWITHACCOUNT['timeout_seconds']}")

# ❌ UNSAFE: Never log secrets
logger.info(f"API Key: {settings.PAYWITHACCOUNT['api_key']}")  # BAD
logger.info(settings.PAYWITHACCOUNT)  # BAD - contains secrets
```

### Environment Variable Fallback

The client secret supports two env var names for backwards compatibility:
```python
PWA_CLIENT_SECRET = getenv("PWA_CLIENT_SECRET") or getenv("PWA_SECRET_KEY", "")
```

Prefer `PWA_CLIENT_SECRET` in new configurations.

## Local Development

Add to `.envs/.env.local`:
```bash
# OnePipe PayWithAccount API
PWA_BASE_URL=https://api.dev.onepipe.io
PWA_TRANSACT_PATH=/v2/transact
PWA_API_KEY=your_api_key_here
PWA_CLIENT_SECRET=your_client_secret_here
PWA_WEBHOOK_SECRET=optional_webhook_secret
PWA_MOCK_MODE=inspect
PWA_REQUEST_TYPE=invoice
PWA_TIMEOUT_SECONDS=30
```

## Production Configuration

For production, ensure all sensitive values are set:
```bash
PWA_API_KEY=production_api_key
PWA_CLIENT_SECRET=production_secret
PWA_WEBHOOK_SECRET=production_webhook_secret
PWA_MOCK_MODE=false          # Disable mock mode
PWA_BASE_URL=https://api.onepipe.io  # Use production endpoint
```

## Testing

In tests, override settings:
```python
from django.test import override_settings

@override_settings(
    PAYWITHACCOUNT={
        'base_url': 'https://api.test.onepipe.io',
        'api_key': 'test_key',
        'client_secret': 'test_secret',
        'timeout_seconds': 5,
        ...
    }
)
def test_pwa_integration():
    # Test code here
    pass
```

## Accessing Individual Variables

Individual variables are still available for backwards compatibility:
```python
from django.conf import settings

# These still work (but PAYWITHACCOUNT dict is preferred)
base_url = settings.PWA_BASE_URL
api_key = settings.PWA_API_KEY
timeout = settings.PWA_TIMEOUT_SECONDS
```

## Default Values Summary

| Setting | Default |
|---------|---------|
| Base URL | `https://api.dev.onepipe.io` |
| Transact Path | `/v2/transact` |
| Mock Mode | `inspect` |
| Request Type | `invoice` |
| Timeout | 30 seconds |
| API Key | Required (empty) |
| Client Secret | Required (empty) |
| Webhook Secret | Optional (empty) |
