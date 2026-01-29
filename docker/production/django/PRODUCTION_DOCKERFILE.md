# Production Dockerfile Documentation

## Overview

The production Dockerfile (`docker/production/django/Dockerfile`) is optimized for production deployments with:
- **Multi-stage build** for minimal image size
- **Non-root user** execution for security
- **Health checks** for container orchestration
- **Production-grade WSGI server** (Gunicorn)
- **Proper static file handling** at runtime

## Build Specifications

### Base Image
- `python:3.12-slim` - Lightweight Python image with essential dependencies

### Environment Variables
- `PYTHONDONTWRITEBYTECODE=1` - Prevents Python from writing .pyc files
- `PYTHONUNBUFFERED=1` - Ensures Python output is logged immediately
- `PIP_NO_CACHE_DIR=1` - Reduces image size by not caching pip packages
- `PIP_DISABLE_PIP_VERSION_CHECK=1` - Skips pip version check for faster builds

### Dependencies

**Build Stage:**
- `build-essential` - GCC compiler for native extensions
- `libpq-dev` - PostgreSQL development libraries

**Runtime Stage:**
- `libpq5` - PostgreSQL runtime library
- `curl` - For health checks

### Requirements Structure

```
requirements/
├── base.txt          # Core Django + app dependencies
├── local.txt         # Development dependencies
└── production.txt    # Production-only packages
```

**Production Requirements:**
- `gunicorn==21.2.0` - WSGI HTTP server
- `psycopg2-pool==1.1.0` - Connection pooling for PostgreSQL
- `sentry-sdk==1.40.0` - Error tracking and monitoring
- `python-decouple==3.8` - Configuration management
- `python-json-logger==2.0.7` - JSON logging for better log aggregation

### Security Features

1. **Non-root User**
   ```dockerfile
   RUN groupadd -r django && \
       useradd -r -g django django
   ```
   - Prevents container escape vulnerabilities
   - Limits damage if the application is compromised

2. **File Permissions**
   - Static files: `/app/staticfiles` - chowned to django:django
   - Media files: `/app/media` - chowned to django:django

3. **Minimized Final Image**
   - Multi-stage build removes build tools from final image
   - Only runtime dependencies are included
   - Reduces attack surface

### Health Check

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/ || exit 1
```

**Parameters:**
- `interval=30s` - Check health every 30 seconds
- `timeout=10s` - Health check must complete within 10 seconds
- `start-period=40s` - Give container 40s to start before health checks
- `retries=3` - Mark unhealthy after 3 consecutive failures

**Endpoint:** `/api/v1/health/`
- This endpoint should return a 200 status with a simple JSON response
- Implement in your Django app for monitoring

## Gunicorn Configuration

```bash
gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 3 \
  --timeout 60 \
  --access-logfile - \
  --error-logfile -
```

**Parameters:**
- `--workers 3` - Number of worker processes
  - Rule: `(2 × CPU_CORES) + 1`
  - For CPU-intensive: same as CPU cores
  - Adjust based on your server specifications
- `--timeout 60` - Request timeout in seconds
- `--access-logfile -` - Log to stdout (for container logging)
- `--error-logfile -` - Log errors to stdout

## Building the Image

### Basic Build

```bash
docker build -f docker/production/django/Dockerfile -t kore-api:latest .
```

### With Tag Versioning

```bash
docker build -f docker/production/django/Dockerfile \
  -t kore-api:v1.0.0 \
  -t kore-api:latest \
  .
```

### Build Args (if needed)

```bash
docker build -f docker/production/django/Dockerfile \
  --build-arg PYTHON_VERSION=3.12 \
  -t kore-api:latest \
  .
```

## Running the Container

### Docker Run

```bash
docker run -d \
  --name kore-api \
  -p 8000:8000 \
  --env-file .envs/.env.production \
  --health-cmd="curl -f http://localhost:8000/api/v1/health/" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  --restart unless-stopped \
  kore-api:latest
```

### Docker Compose

```bash
docker compose -f production.yml up -d
```

See `production.yml` for complete Docker Compose configuration with:
- PostgreSQL 16
- Redis 7
- Proper networking
- Volume management
- Health checks

## Static Files Management

### At Build Time (Current Approach)

```dockerfile
RUN python manage.py collectstatic --noinput --clear || true
```

**Advantages:**
- Faster container startup
- No runtime overhead
- Static files are part of the image

**Disadvantages:**
- Larger image size
- Requires rebuild for static changes

### At Runtime (Alternative)

If static files are environment-dependent, initialize on container start:

```bash
# In entrypoint script before gunicorn
python manage.py collectstatic --noinput --clear
gunicorn ...
```

### With CDN (Recommended for Production)

1. Configure Django settings:
   ```python
   STATIC_URL = 'https://cdn.yourdomain.com/static/'
   STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
   ```

2. Deploy static files to CDN separately:
   ```bash
   python manage.py collectstatic
   # Upload to S3/CloudFront/similar
   ```

3. Remove or minimize static files from container

## Production Checklist

- [ ] Set `DEBUG=False` in `.env.production`
- [ ] Generate secure `SECRET_KEY` (use `django-environ` or similar)
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set up PostgreSQL with secure credentials
- [ ] Configure Redis for Celery/caching
- [ ] Enable HTTPS/SSL
- [ ] Set up email service (SendGrid, AWS SES, etc.)
- [ ] Configure Sentry for error tracking
- [ ] Set up log aggregation (ELK, Splunk, etc.)
- [ ] Configure health check endpoint
- [ ] Test health checks
- [ ] Set up monitoring and alerting
- [ ] Configure database backups
- [ ] Set up CI/CD pipeline
- [ ] Test production deployment locally with Docker Compose
- [ ] Review security settings (HTTPS, CSRF, CORS)
- [ ] Set up rate limiting
- [ ] Configure request/response logging

## Performance Tuning

### Gunicorn Workers

```python
# Calculate optimal worker count:
# (2 × CPU_CORES) + 1

# Example:
# 2 CPU cores: (2 × 2) + 1 = 5 workers
# 4 CPU cores: (2 × 4) + 1 = 9 workers
# 8 CPU cores: (2 × 8) + 1 = 17 workers
```

### Database Optimization

```python
# psycopg2-pool for connection pooling
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'CONN_MAX_AGE': 600,  # Connection reuse timeout
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}
```

### Caching Strategy

```python
# Use Redis for caching
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

## Troubleshooting

### Image Size Too Large

Check Docker image layers:
```bash
docker history kore-api:latest
```

Optimize by:
- Removing build dependencies in final stage (already done)
- Reducing number of layers
- Cleaning package manager caches

### Health Check Failing

```bash
# Test endpoint directly
docker exec kore-api curl http://localhost:8000/api/v1/health/

# Check container logs
docker logs kore-api

# Verify endpoint exists in Django
# Create endpoint in core_apps/common/views.py if missing
```

### Permission Denied Errors

```bash
# Check file ownership
docker exec kore-api ls -la /app/staticfiles

# Should show: django:django ownership
```

## Deployment Platforms

### AWS ECS

```json
{
  "image": "kore-api:latest",
  "essential": true,
  "portMappings": [{
    "containerPort": 8000,
    "hostPort": 8000
  }],
  "healthCheck": {
    "command": ["CMD-SHELL", "curl -f http://localhost:8000/api/v1/health/ || exit 1"],
    "interval": 30,
    "timeout": 10,
    "retries": 3,
    "startPeriod": 40
  }
}
```

### Kubernetes

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: kore-api
spec:
  containers:
  - name: api
    image: kore-api:latest
    ports:
    - containerPort: 8000
    livenessProbe:
      httpGet:
        path: /api/v1/health/
        port: 8000
      initialDelaySeconds: 40
      periodSeconds: 30
    readinessProbe:
      httpGet:
        path: /api/v1/health/
        port: 8000
      initialDelaySeconds: 10
      periodSeconds: 5
```

## References

- [Gunicorn Configuration](https://docs.gunicorn.org/en/stable/configure.html)
- [Django Deployment](https://docs.djangoproject.com/en/5.2/howto/deployment/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [OWASP Container Security](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
