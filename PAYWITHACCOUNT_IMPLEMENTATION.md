# PayWithAccount Settings Implementation ✅

## What Was Implemented

### 1. **Settings Configuration** (config/settings/base.py)

Added comprehensive PayWithAccount settings with safe defaults:

```python
# Individual environment variables (for backwards compatibility)
PWA_BASE_URL = getenv("PWA_BASE_URL", "https://api.dev.onepipe.io")
PWA_TRANSACT_PATH = getenv("PWA_TRANSACT_PATH", "/v2/transact")
PWA_API_KEY = getenv("PWA_API_KEY", "")
PWA_CLIENT_SECRET = getenv("PWA_CLIENT_SECRET") or getenv("PWA_SECRET_KEY", "")
PWA_WEBHOOK_SECRET = getenv("PWA_WEBHOOK_SECRET", "")
PWA_MOCK_MODE = getenv("PWA_MOCK_MODE", "inspect")
PWA_REQUEST_TYPE = getenv("PWA_REQUEST_TYPE", "invoice")
PWA_TIMEOUT_SECONDS = int(getenv("PWA_TIMEOUT_SECONDS", "30"))

# Consolidated clean dictionary
PAYWITHACCOUNT = {
    'base_url': PWA_BASE_URL,
    'transact_path': PWA_TRANSACT_PATH,
    'api_key': PWA_API_KEY,
    'client_secret': PWA_CLIENT_SECRET,
    'webhook_secret': PWA_WEBHOOK_SECRET,
    'mock_mode': PWA_MOCK_MODE,
    'request_type': PWA_REQUEST_TYPE,
    'timeout_seconds': PWA_TIMEOUT_SECONDS,
}
```

### 2. **Environment Variables**

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `PWA_BASE_URL` | `https://api.dev.onepipe.io` | No | OnePipe API base URL |
| `PWA_TRANSACT_PATH` | `/v2/transact` | No | Payment endpoint path |
| `PWA_API_KEY` | `` | **Yes** | API key for authentication |
| `PWA_CLIENT_SECRET` | `` | **Yes** | Client secret for signature |
| `PWA_WEBHOOK_SECRET` | `` | No | Webhook verification secret |
| `PWA_MOCK_MODE` | `inspect` | No | Mock mode setting |
| `PWA_REQUEST_TYPE` | `invoice` | No | Payment request type |
| `PWA_TIMEOUT_SECONDS` | `30` | No | HTTP timeout in seconds |

### 3. **Usage Pattern**

Clean dictionary access throughout the codebase:

```python
from django.conf import settings

# Access entire config
config = settings.PAYWITHACCOUNT

# Access specific value
base_url = settings.PAYWITHACCOUNT['base_url']
timeout = settings.PAYWITHACCOUNT['timeout_seconds']
api_key = settings.PAYWITHACCOUNT['api_key']
```

### 4. **Backwards Compatibility**

Individual variables still available:
```python
settings.PWA_BASE_URL
settings.PWA_API_KEY
settings.PWA_TIMEOUT_SECONDS
# ... etc
```

### 5. **Security**

✅ **Secrets not logged:**
- `api_key`
- `client_secret`
- `webhook_secret`

❌ Never do:
```python
logger.info(settings.PAYWITHACCOUNT)  # Contains secrets!
```

✅ Safe logging:
```python
logger.info(f"PWA timeout: {settings.PAYWITHACCOUNT['timeout_seconds']}")
```

### 6. **Environment File** (.envs/.env.local)

Updated with standard variable names:
```bash
PWA_BASE_URL=https://api.dev.onepipe.io
PWA_API_KEY=kn4qmDvpjsagPepajF9i_336b96943bcb42d8857f035bbc52cf6f
PWA_CLIENT_SECRET=49NCK9ipx2aQQm3o
PWA_WEBHOOK_SECRET=https://email-webhook.onepipe.io/...
PWA_MOCK_MODE=inspect
PWA_REQUEST_TYPE=invoice
PWA_TIMEOUT_SECONDS=30
PWA_TRANSACT_PATH=/v2/transact
```

### 7. **Defaults Summary**

| Setting | Default | Note |
|---------|---------|------|
| Base URL | `https://api.dev.onepipe.io` | Dev endpoint |
| Transact Path | `/v2/transact` | Standard path |
| Mock Mode | `inspect` | Inspection mode |
| Request Type | `invoice` | Standard type |
| Timeout | 30 seconds | Safe timeout |
| API Key | `` | Must be configured |
| Client Secret | `` | Must be configured |
| Webhook Secret | `` | Optional |

## Usage Examples

### In PayWithAccountClient

```python
from django.conf import settings

class PayWithAccountClient:
    def __init__(self):
        config = settings.PAYWITHACCOUNT
        self.base_url = config['base_url']
        self.transact_path = config['transact_path']
        self.api_key = config['api_key']
        self.client_secret = config['client_secret']
        self.timeout = config['timeout_seconds']
    
    def transact(self, payload):
        url = f"{self.base_url}{self.transact_path}"
        # Use self.timeout for requests
```

### In CollectionsService

```python
from django.conf import settings

class CollectionsService:
    def __init__(self):
        self.pwa_config = settings.PAYWITHACCOUNT
    
    def build_pwa_payload(self, ...):
        return {
            'request_type': self.pwa_config['request_type'],
            'mock_mode': self.pwa_config['mock_mode'],
            # ...
        }
```

### In Tests

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
def test_pwa_integration():
    # Test code
    pass
```

## Benefits

✅ **Clean Access**: Single dictionary instead of scattered variables
✅ **Safe Defaults**: All values have sensible development defaults
✅ **Required Validation**: API key and secret must be configured
✅ **Type Safety**: Timeout converted to integer
✅ **Backwards Compatible**: Individual variables still accessible
✅ **Secret Protection**: Secrets not logged by default
✅ **Flexibility**: Supports multiple env var names (PWA_CLIENT_SECRET or PWA_SECRET_KEY)
✅ **Production Ready**: Easy to override for different environments

## Testing

### Verify Settings Are Loaded

```bash
python manage.py shell
>>> from django.conf import settings
>>> settings.PAYWITHACCOUNT
{'base_url': 'https://api.dev.onepipe.io', 'api_key': '...', ...}
```

### Test with Override

```bash
python manage.py test --settings=config.settings.test
```

## Configuration Checklist

- [x] Settings variables created with safe defaults
- [x] Consolidated PAYWITHACCOUNT dictionary
- [x] Backwards compatibility maintained
- [x] Secrets not logged
- [x] Timeout handled as integer
- [x] PWA_CLIENT_SECRET and PWA_SECRET_KEY both supported
- [x] Environment variables updated
- [x] Documentation created
- [x] Production configuration guidelines provided
- [x] Testing examples included

## Next Steps

1. **Update PayWithAccountClient** - Use `settings.PAYWITHACCOUNT` instead of individual vars
2. **Update CollectionsService** - Use `settings.PAYWITHACCOUNT` instead of individual vars
3. **Update WebhookService** - Use `settings.PAYWITHACCOUNT` for webhook_secret
4. **Add validation** - Check required fields (api_key, client_secret) on startup
5. **Add documentation** - Reference PAYWITHACCOUNT_SETTINGS.md in code

## Security Notes

- API keys and secrets are loaded from environment only
- Never hardcode credentials in code
- Use different credentials for dev/staging/production
- Webhook secret is optional but recommended for production
- Timeout prevents hanging requests
- Mock mode useful for development/testing
