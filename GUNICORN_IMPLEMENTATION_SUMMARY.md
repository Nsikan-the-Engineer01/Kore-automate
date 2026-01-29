# Gunicorn Configuration Implementation Summary

## ✅ Completed

### 1. Gunicorn Configuration File
**File:** `config/gunicorn.conf.py`

**Features:**
- ✅ Safe environment variable reading with type conversion
- ✅ `bind = "0.0.0.0:8000"` - Fixed binding
- ✅ `workers` - Reads from `WEB_CONCURRENCY` env var
  - Default: `(2 × CPU_CORES) + 1` with minimum of 3
- ✅ `timeout` - Reads from `GUNICORN_TIMEOUT` env var
  - Default: 60 seconds
- ✅ `loglevel` - Reads from `LOG_LEVEL` env var
  - Default: "info"
- ✅ `accesslog = "-"` - Log to stdout
- ✅ `errorlog = "-"` - Log to stderr
- ✅ Server lifecycle hooks (on_starting, when_ready, on_exit)
- ✅ SSL configuration support (optional via env vars)
- ✅ Comprehensive documentation and examples

### 2. Updated Production Dockerfile
**File:** `docker/production/django/Dockerfile`

**Changes:**
- ✅ Updated entrypoint to use gunicorn config file:
  ```dockerfile
  CMD ["gunicorn", "-c", "config/gunicorn.conf.py", "config.wsgi:application"]
  ```
- ✅ Cleaner command (configuration moved to file)
- ✅ All settings now configurable via environment variables

### 3. Updated Docker Compose
**File:** `production.yml`

**Changes:**
- ✅ Added `environment` section with Gunicorn variables:
  ```yaml
  environment:
    WEB_CONCURRENCY: "3"
    GUNICORN_TIMEOUT: "60"
    LOG_LEVEL: "info"
  ```
- ✅ Easy to override for different deployments

### 4. Updated Environment Template
**File:** `.envs/.env.production.example`

**Added:**
- ✅ `WEB_CONCURRENCY=3` - Number of workers
- ✅ `GUNICORN_TIMEOUT=60` - Request timeout
- ✅ `LOG_LEVEL=info` - Logging verbosity

### 5. Configuration Documentation
**File:** `config/GUNICORN_CONFIGURATION.md`

**Includes:**
- Overview and configuration file details
- Environment variable reference table
- Usage examples (Docker Compose, Docker Run, Direct)
- Worker count calculation guide
- Production configuration recommendations
- Logging explanation and viewing commands
- Performance tuning strategies
- Common issues and troubleshooting
- Advanced configuration options
- References

## Configuration Hierarchy

```
Environment Variables (Highest Priority)
    ↓
config/gunicorn.conf.py (get_env with defaults)
    ↓
Hardcoded Defaults (Lowest Priority)
```

## Key Specifications

| Setting | Value | Source |
|---------|-------|--------|
| Bind | `0.0.0.0:8000` | Hardcoded |
| Workers | `(2 × CPU_CORES) + 1` min 3 | `WEB_CONCURRENCY` env var |
| Timeout | 60s | `GUNICORN_TIMEOUT` env var |
| Access Log | stdout (`-`) | Hardcoded |
| Error Log | stderr (`-`) | Hardcoded |
| Log Level | info | `LOG_LEVEL` env var |

## Usage Examples

### Docker Compose (Recommended)

```yaml
services:
  api:
    environment:
      WEB_CONCURRENCY: "5"
      GUNICORN_TIMEOUT: "120"
      LOG_LEVEL: "debug"
```

### Docker Run

```bash
docker run -e WEB_CONCURRENCY=5 \
           -e GUNICORN_TIMEOUT=120 \
           -e LOG_LEVEL=debug \
           kore-api:latest
```

### Local Development

```bash
# Using defaults
gunicorn -c config/gunicorn.conf.py config.wsgi:application

# With custom values
WEB_CONCURRENCY=2 \
GUNICORN_TIMEOUT=30 \
LOG_LEVEL=debug \
gunicorn -c config/gunicorn.conf.py config.wsgi:application
```

## Worker Count Recommendations

### Small Servers (1-2 CPUs)
```yaml
WEB_CONCURRENCY: "3"
```

### Medium Servers (4-8 CPUs)
```yaml
WEB_CONCURRENCY: "9"
```

### Large Servers (16+ CPUs)
```yaml
WEB_CONCURRENCY: "33"
```

### Memory-Constrained
```yaml
WEB_CONCURRENCY: "2"
```

## Files Modified/Created

```
✅ config/gunicorn.conf.py                 (NEW)
✅ config/GUNICORN_CONFIGURATION.md        (NEW)
✅ docker/production/django/Dockerfile      (MODIFIED)
✅ production.yml                           (MODIFIED)
✅ .envs/.env.production.example            (MODIFIED)
```

## Integration Points

### Production Dockerfile
The Dockerfile now uses:
```dockerfile
CMD ["gunicorn", "-c", "config/gunicorn.conf.py", "config.wsgi:application"]
```

This allows all gunicorn settings to be configured via environment variables without rebuilding the image.

### Docker Compose
The production.yml includes default values:
```yaml
environment:
  WEB_CONCURRENCY: "3"
  GUNICORN_TIMEOUT: "60"
  LOG_LEVEL: "info"
```

Override these in your deployment without modifying compose files.

### Environment Variables
All configuration is environment-based:
- `.envs/.env.production` - File-based for persistent secrets
- Docker `environment:` section - For service-specific settings
- `docker run -e` flags - For command-line overrides

## Type-Safe Configuration

The `get_env()` function in gunicorn.conf.py provides:
- Safe type conversion (str, int, bool)
- Fallback to defaults on parse errors
- Type validation before use

```python
# Example conversions
workers = get_env('WEB_CONCURRENCY', default_workers, int)
# If env var is not set or invalid, uses default_workers

loglevel = get_env('LOG_LEVEL', 'info').lower()
# Reads as string and converts to lowercase
```

## Logging

### Log Output
Both access and error logs go to stdout/stderr:
- **Access logs**: stdout (visible with `docker logs`)
- **Error logs**: stderr (visible with `docker logs`)

### Viewing Logs
```bash
# Real-time logs
docker logs -f kore-api-prod

# Last 100 lines
docker logs --tail 100 kore-api-prod

# With timestamps
docker logs -t kore-api-prod
```

## Monitoring

### Check Worker Status
```bash
docker exec kore-api-prod ps aux | grep gunicorn
```

### Monitor Resource Usage
```bash
docker stats kore-api-prod
```

### View Configuration Applied
```bash
docker logs kore-api-prod | grep -E "(Workers|Timeout|Log level|Bind)"
```

## Production Checklist

- [ ] Set appropriate `WEB_CONCURRENCY` for your server
- [ ] Configure `GUNICORN_TIMEOUT` based on expected request times
- [ ] Set `LOG_LEVEL` to "info" or "warning" in production
- [ ] Test locally with `docker compose -f production.yml up`
- [ ] Verify gunicorn starts with correct settings
- [ ] Monitor logs after deployment
- [ ] Set up log aggregation (ELK, Splunk, CloudWatch)
- [ ] Configure resource limits for container
- [ ] Set up health check monitoring
- [ ] Plan for scaling (CPU-based horizontal scaling)

## Scaling Recommendations

### Horizontal Scaling (Multiple Containers)
- Each container can run the default calculated workers
- Use load balancer (Nginx, HAProxy, AWS ALB) in front
- Scale based on CPU/Memory metrics

### Vertical Scaling (Larger Server)
- Increase `WEB_CONCURRENCY` with more CPUs
- Monitor memory usage
- Use connection pooling for database

### Auto-Scaling (Kubernetes/ECS)
- Set requests/limits based on testing
- Use metric-based scaling (CPU, Memory)
- Configure HPA with appropriate thresholds

## References

- **Configuration File:** [config/gunicorn.conf.py](config/gunicorn.conf.py)
- **Configuration Guide:** [config/GUNICORN_CONFIGURATION.md](config/GUNICORN_CONFIGURATION.md)
- **Production Dockerfile:** [docker/production/django/Dockerfile](docker/production/django/Dockerfile)
- **Docker Compose:** [production.yml](production.yml)
- **Gunicorn Documentation:** https://docs.gunicorn.org/en/stable/configure.html

---

**Status:** ✅ Complete and Production-Ready
**Last Updated:** January 29, 2026
