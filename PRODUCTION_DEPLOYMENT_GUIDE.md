# Production Deployment Quick Reference

## File Structure

```
docker/production/
└── django/
    ├── Dockerfile                    # Production-grade Django Dockerfile
    └── PRODUCTION_DOCKERFILE.md      # Full documentation
```

## Key Features

✅ **Multi-stage build** - Minimal final image size
✅ **Non-root user execution** - Enhanced security
✅ **Health checks** - Container orchestration ready
✅ **Gunicorn WSGI server** - Production-grade Python application server
✅ **Static file handling** - Runtime collection
✅ **Proper logging** - JSON logging to stdout/stderr

## Quick Start

### 1. Build Image

```bash
docker build -f docker/production/django/Dockerfile \
  -t kore-api:latest .
```

### 2. Test Locally

```bash
docker compose -f production.yml up -d
```

### 3. Verify Health

```bash
docker logs kore-api-prod
curl http://localhost:8000/api/v1/health/
```

## Environment Configuration

### Create Production Environment File

```bash
cp .envs/.env.production.example .envs/.env.production
# Edit .envs/.env.production with real values
```

### Key Variables

```env
DEBUG=False
SECRET_KEY=your-secure-key-here
POSTGRES_HOST=postgres
POSTGRES_USER=kore_prod_user
POSTGRES_PASSWORD=secure-password
DOMAIN=yourdomain.com
```

## Container Specifications

| Component | Specification |
|-----------|---------------|
| Base Image | `python:3.12-slim` |
| User | `django:django` (non-root) |
| Port | `8000` |
| Workers | `3` (Gunicorn) |
| Timeout | `60s` |
| Health Check | `/api/v1/health/` every 30s |

## Static Files

Static files are collected at **build time**:

```dockerfile
RUN python manage.py collectstatic --noinput --clear || true
```

If you need runtime collection, modify the entrypoint or use CDN.

## Common Commands

### Build with Version Tag

```bash
docker build -f docker/production/django/Dockerfile \
  -t kore-api:v1.0.0 \
  -t kore-api:latest \
  .
```

### Run Single Container

```bash
docker run -d \
  --name kore-api \
  -p 8000:8000 \
  --env-file .envs/.env.production \
  --restart unless-stopped \
  kore-api:latest
```

### View Health Status

```bash
docker ps --filter "name=kore-api" --format "{{.Status}}"
```

### View Logs

```bash
docker logs -f kore-api-prod
```

### Connect to Container

```bash
docker exec -it kore-api-prod /bin/bash
```

## Production Checklist

- [ ] Configure `.env.production` with production values
- [ ] Build and test image locally
- [ ] Test with `docker compose -f production.yml up`
- [ ] Verify `/api/v1/health/` endpoint returns 200
- [ ] Verify static files are served correctly
- [ ] Check security headers in responses
- [ ] Test database connectivity
- [ ] Verify Celery/Redis connectivity (if used)
- [ ] Set up monitoring and alerting
- [ ] Configure log aggregation
- [ ] Push image to container registry
- [ ] Deploy to production platform
- [ ] Monitor health checks
- [ ] Test failure recovery

## Docker Compose (production.yml)

Includes:
- **API container** (Gunicorn)
- **PostgreSQL 16** (Database)
- **Redis 7** (Cache/Celery broker)
- **Health checks** for all services
- **Named volumes** for persistence
- **Bridge network** for service communication

## Troubleshooting

### Health Check Fails

```bash
docker logs kore-api-prod
docker exec kore-api-prod curl http://localhost:8000/api/v1/health/
```

Ensure endpoint exists in Django:
```python
# core_apps/common/views.py
from rest_framework.response import Response
from rest_framework import status

def health(request):
    return Response({'status': 'healthy'}, status=status.HTTP_200_OK)
```

### Static Files Missing

```bash
docker exec kore-api-prod python manage.py collectstatic --noinput
```

### Database Connection Issues

```bash
docker exec kore-api-prod python manage.py shell
>>> from django.db import connection
>>> connection.ensure_connection()  # Test connection
```

### Permission Errors

```bash
docker exec kore-api-prod ls -la /app/staticfiles/
# Should show: drwxr-xr-x django django
```

## Deployment Platforms

### AWS ECS
- Use ECS task definitions
- Reference: [AWS ECS Task Definition Example]

### Kubernetes
- Use Helm charts or manifests
- Health checks map to liveness/readiness probes

### DigitalOcean App Platform
- Push image to registry
- Configure in app.yaml

### Heroku
- Build from Dockerfile
- Set environment variables in Heroku Config Vars

## Monitoring & Alerts

Configure monitoring for:
- Container health status
- CPU and memory usage
- Disk space
- Database connection pool
- Request response times
- Error rates

Example metrics to track:
- Request latency (p50, p95, p99)
- Error rate (5xx responses)
- Database query time
- Cache hit/miss ratio
- Worker count and utilization

## References

- **Dockerfile**: `docker/production/django/Dockerfile`
- **Documentation**: `docker/production/django/PRODUCTION_DOCKERFILE.md`
- **Compose File**: `production.yml`
- **Env Example**: `.envs/.env.production.example`
- **Requirements**: `requirements/production.txt`
