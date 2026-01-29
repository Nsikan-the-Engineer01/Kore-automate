# Gunicorn Configuration Guide

## Overview

The Gunicorn configuration is managed through `config/gunicorn.conf.py` which reads environment variables for flexible runtime configuration.

## Configuration File

**Location:** `config/gunicorn.conf.py`

**Features:**
- Safe environment variable reading with type conversion
- Intelligent worker calculation based on CPU cores
- Sensible defaults for all settings
- Server hooks for logging lifecycle events
- SSL support (optional, via environment variables)

## Environment Variables

### Core Configuration

| Variable | Default | Type | Description |
|----------|---------|------|-------------|
| `WEB_CONCURRENCY` | `(2 × CPU_CORES) + 1` | int | Number of Gunicorn worker processes |
| `GUNICORN_TIMEOUT` | `60` | int | Worker timeout in seconds |
| `LOG_LEVEL` | `info` | str | Logging level (debug, info, warning, error, critical) |

### Bind Configuration

| Variable | Default | Type | Description |
|----------|---------|------|-------------|
| (hardcoded) | `0.0.0.0:8000` | str | Server bind address and port |

### SSL Configuration (Optional)

| Variable | Default | Type | Description |
|----------|---------|------|-------------|
| `GUNICORN_KEYFILE` | None | str | Path to SSL key file |
| `GUNICORN_CERTFILE` | None | str | Path to SSL certificate file |
| `GUNICORN_SSL_VERSION` | `TLS` | str | SSL version to use |
| `GUNICORN_CERT_REQS` | `0` | int | Certificate requirements |
| `GUNICORN_CA_CERTS` | None | str | Path to CA certificate file |
| `GUNICORN_CIPHERS` | None | str | SSL ciphers to use |

## Usage Examples

### Docker Compose (Recommended)

```yaml
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

### Direct Command Line

```bash
# With default configuration
gunicorn -c config/gunicorn.conf.py config.wsgi:application

# With environment variables
WEB_CONCURRENCY=8 \
GUNICORN_TIMEOUT=90 \
LOG_LEVEL=debug \
gunicorn -c config/gunicorn.conf.py config.wsgi:application
```

## Worker Count Calculation

The default worker count is calculated as: `(2 × CPU_CORES) + 1`

**Examples:**
- 1 CPU: (2 × 1) + 1 = 3 workers
- 2 CPUs: (2 × 2) + 1 = 5 workers
- 4 CPUs: (2 × 4) + 1 = 9 workers
- 8 CPUs: (2 × 8) + 1 = 17 workers

**Override with `WEB_CONCURRENCY`:**
```bash
WEB_CONCURRENCY=20 gunicorn -c config/gunicorn.conf.py config.wsgi:application
```

## Configuration in Production

### Production Docker Compose

The `production.yml` file includes default Gunicorn settings:

```yaml
environment:
  WEB_CONCURRENCY: "3"
  GUNICORN_TIMEOUT: "60"
  LOG_LEVEL: "info"
```

Adjust these based on your server specifications:

**For small servers (1-2 CPUs):**
```yaml
environment:
  WEB_CONCURRENCY: "3"
  GUNICORN_TIMEOUT: "60"
  LOG_LEVEL: "info"
```

**For medium servers (4-8 CPUs):**
```yaml
environment:
  WEB_CONCURRENCY: "9"
  GUNICORN_TIMEOUT: "120"
  LOG_LEVEL: "info"
```

**For large servers (16+ CPUs):**
```yaml
environment:
  WEB_CONCURRENCY: "33"
  GUNICORN_TIMEOUT: "120"
  LOG_LEVEL: "info"
```

## Logging

### Log Levels

- **debug**: Verbose logging for debugging
- **info**: General informational messages (default)
- **warning**: Warning messages for potentially problematic situations
- **error**: Error messages for failures
- **critical**: Critical failures

### Log Output

Both access and error logs go to stdout/stderr (prefixed with `-`):
- Access logs: `/dev/stdout` (stdout)
- Error logs: `/dev/stderr` (stderr)

This allows Docker to capture logs via standard container logging drivers.

### Viewing Logs

```bash
# Follow logs in real-time
docker logs -f kore-api-prod

# See last 100 lines
docker logs --tail 100 kore-api-prod

# View logs with timestamps
docker logs -t kore-api-prod
```

## Performance Tuning

### CPU-Bound Applications

For applications with CPU-intensive operations:
```bash
WEB_CONCURRENCY=<num_cpus> gunicorn -c config/gunicorn.conf.py config.wsgi:application
```

### I/O-Bound Applications

For applications with many I/O operations (database calls, API requests):
```bash
WEB_CONCURRENCY=$((2 * $(nproc) + 1)) gunicorn -c config/gunicorn.conf.py config.wsgi:application
```

### Memory Constraints

For servers with limited memory:
```bash
WEB_CONCURRENCY=2 gunicorn -c config/gunicorn.conf.py config.wsgi:application
```

## Monitoring and Metrics

### Worker Status

Check active workers:
```bash
docker exec kore-api-prod ps aux | grep gunicorn
```

### Resource Usage

Monitor resource consumption:
```bash
docker stats kore-api-prod
```

### Connection Pool

Monitor PostgreSQL connections:
```bash
docker exec kore-api-postgres psql -U <user> -d <db> -c "SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;"
```

## Common Issues

### Workers Keep Crashing

**Symptoms:** Workers restart frequently in logs

**Solutions:**
1. Increase timeout: `GUNICORN_TIMEOUT=120`
2. Reduce worker count: `WEB_CONCURRENCY=2`
3. Check application logs for errors: `docker logs kore-api-prod`
4. Monitor memory: `docker stats kore-api-prod`

### Slow Requests

**Symptoms:** Requests take longer than expected

**Solutions:**
1. Increase workers: `WEB_CONCURRENCY=<higher_value>`
2. Increase timeout: `GUNICORN_TIMEOUT=120`
3. Check database performance
4. Profile application with tools like Django Debug Toolbar

### Memory Leaks

**Symptoms:** Container memory usage grows over time

**Solutions:**
1. Reduce worker count
2. Lower `max_requests` in gunicorn.conf.py
3. Profile with memory profiling tools
4. Check for circular references in application

## Configuration in production.yml

```yaml
services:
  api:
    environment:
      # Gunicorn configuration via environment variables
      WEB_CONCURRENCY: "3"        # Adjust based on CPU cores
      GUNICORN_TIMEOUT: "60"      # Request timeout in seconds
      LOG_LEVEL: "info"            # Logging verbosity
```

## Advanced Configuration

### Custom Worker Class

To use a different worker class (e.g., `uvicorn` for async), modify `gunicorn.conf.py`:

```python
worker_class = "uvicorn.workers.UvicornWorker"
```

### Request Hooks

Add custom logic in `gunicorn.conf.py`:

```python
def on_start(server):
    """Called when Gunicorn starts."""
    pass

def on_exit(server):
    """Called when a worker exits."""
    pass

def post_worker_init(worker):
    """Called just after a worker is initialized."""
    pass

def pre_request(worker, req):
    """Called just before a request is processed."""
    pass

def post_request(worker, req, environ, resp):
    """Called after a request is processed."""
    pass
```

## References

- **Config File:** [config/gunicorn.conf.py](config/gunicorn.conf.py)
- **Production Dockerfile:** [docker/production/django/Dockerfile](docker/production/django/Dockerfile)
- **Docker Compose:** [production.yml](production.yml)
- **Gunicorn Docs:** https://docs.gunicorn.org/
- **Django Deployment:** https://docs.djangoproject.com/en/5.2/howto/deployment/
