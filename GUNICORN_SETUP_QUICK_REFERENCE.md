# Gunicorn Configuration - Quick Setup

## What Changed?

Gunicorn configuration is now managed through a Python configuration file (`config/gunicorn.conf.py`) that reads environment variables.

**Before:**
```dockerfile
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "60"]
```

**After:**
```dockerfile
CMD ["gunicorn", "-c", "config/gunicorn.conf.py", "config.wsgi:application"]
```

## Quick Start

### 1. No Changes Needed for Default Setup

If you don't need to customize Gunicorn settings, everything works with defaults:
- Workers: Auto-calculated as `(2 × CPU_CORES) + 1` (minimum 3)
- Timeout: 60 seconds
- Log level: info

### 2. Customize via Environment Variables

Set these environment variables to customize Gunicorn:

```bash
# Number of worker processes
WEB_CONCURRENCY=5

# Request timeout in seconds
GUNICORN_TIMEOUT=120

# Logging level (debug, info, warning, error, critical)
LOG_LEVEL=info
```

### 3. Docker Compose Example

```yaml
services:
  api:
    image: kore-api:latest
    environment:
      WEB_CONCURRENCY: "5"
      GUNICORN_TIMEOUT: "120"
      LOG_LEVEL: "info"
```

### 4. Docker Run Example

```bash
docker run -e WEB_CONCURRENCY=5 \
           -e GUNICORN_TIMEOUT=120 \
           -e LOG_LEVEL=info \
           kore-api:latest
```

## Configuration File

**Location:** `config/gunicorn.conf.py`

This file:
- Reads environment variables
- Provides type-safe conversion
- Sets sensible defaults
- Configures logging to stdout/stderr

**No modifications needed** - it's production-ready as-is.

## Environment Variables Reference

| Variable | Default | Example | Purpose |
|----------|---------|---------|---------|
| `WEB_CONCURRENCY` | Auto (2×CPU+1, min 3) | `5`, `9`, `17` | Number of worker processes |
| `GUNICORN_TIMEOUT` | `60` | `120`, `30` | Request timeout in seconds |
| `LOG_LEVEL` | `info` | `debug`, `warning` | Logging verbosity |

## CPU-Based Worker Calculation

Default worker count: `(2 × CPU_CORES) + 1`

**Examples:**
- 1 CPU: 3 workers
- 2 CPUs: 5 workers
- 4 CPUs: 9 workers
- 8 CPUs: 17 workers

**Override:**
```bash
WEB_CONCURRENCY=20
```

## Common Configurations

### Development
```bash
WEB_CONCURRENCY=2
GUNICORN_TIMEOUT=30
LOG_LEVEL=debug
```

### Small Production (1-2 CPUs)
```bash
WEB_CONCURRENCY=3
GUNICORN_TIMEOUT=60
LOG_LEVEL=info
```

### Medium Production (4-8 CPUs)
```bash
WEB_CONCURRENCY=9
GUNICORN_TIMEOUT=120
LOG_LEVEL=info
```

### Large Production (16+ CPUs)
```bash
WEB_CONCURRENCY=33
GUNICORN_TIMEOUT=120
LOG_LEVEL=info
```

## Troubleshooting

### Workers not starting
Check `WEB_CONCURRENCY` is a valid integer:
```bash
docker logs kore-api-prod
```

### Requests timing out
Increase `GUNICORN_TIMEOUT`:
```bash
GUNICORN_TIMEOUT=180
```

### Memory usage growing
Reduce `WEB_CONCURRENCY`:
```bash
WEB_CONCURRENCY=2
```

### See application startup logs
Set `LOG_LEVEL=debug`:
```bash
LOG_LEVEL=debug
```

## Files Changed

```
✅ config/gunicorn.conf.py                  - New configuration file
✅ config/GUNICORN_CONFIGURATION.md         - Detailed documentation
✅ docker/production/django/Dockerfile      - Updated entrypoint
✅ production.yml                           - Added environment variables
✅ .envs/.env.production.example            - Added gunicorn variables
```

## Next Steps

1. **Test locally:**
   ```bash
   docker compose -f production.yml up -d
   curl http://localhost:8000/api/v1/health/
   ```

2. **Customize for your server:**
   - Edit `.envs/.env.production`
   - Set `WEB_CONCURRENCY` based on CPU cores
   - Set `GUNICORN_TIMEOUT` based on expected request times

3. **Monitor in production:**
   ```bash
   docker logs -f kore-api-prod
   docker stats kore-api-prod
   ```

## Documentation

For detailed information, see:
- `config/GUNICORN_CONFIGURATION.md` - Complete configuration guide
- `GUNICORN_IMPLEMENTATION_SUMMARY.md` - Implementation details
- `PRODUCTION_DEPLOYMENT_GUIDE.md` - Deployment instructions

---

**Status:** ✅ Ready to Use
