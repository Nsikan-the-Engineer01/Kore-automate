# Production Docker Compose Setup Guide

## Overview

The `docker-compose.production.yml` file defines a complete production-ready containerized application stack with the following services:

- **Django**: Application server (with Gunicorn WSGI)
- **Nginx**: Reverse proxy and static file server
- **PostgreSQL**: Database (version 15)
- **Redis**: In-memory cache and session store
- **RabbitMQ**: Message broker (optional, for Celery)
- **Celery Worker**: Async task processor (optional)
- **Celery Beat**: Scheduled task scheduler (optional)

## File Structure

```
.envs/
├── .production/
│   ├── .django              # Django environment variables
│   ├── .postgres            # PostgreSQL credentials
│   └── .rabbitmq            # RabbitMQ credentials (optional)
└── .env.production.example  # Legacy format

docker-compose.production.yml     # Main production compose file
docker/production/
├── Dockerfile               # Django application image
├── django/
│   └── Dockerfile           # Alternative Django image location
└── nginx/
    ├── default.conf         # Nginx configuration
    └── Dockerfile           # Nginx image
```

## Services Configuration

### 1. Django Service

**Purpose**: Django application server running Gunicorn WSGI server

**Configuration**:
```yaml
django:
  build: docker/production/Dockerfile
  image: kore-django:latest
  container_name: kore-django-prod
  restart: always
  command: gunicorn -c config/gunicorn.conf.py config.wsgi:application
  expose: "8000"
```

**Environment Files**:
- `.envs/.production/.django` - Django settings, email, security
- `.envs/.production/.postgres` - Database credentials

**Dependencies**:
- `postgres:healthy` - Waits for database to be ready
- `redis:healthy` - Waits for cache to be ready
- `rabbitmq:healthy` (optional) - Waits for message broker

**Volumes**:
- `static_volume:/app/staticfiles` - Collectstatic output for Nginx
- `media_volume:/app/media` - User uploads

**Health Check**:
```bash
curl -f http://localhost:8000/api/v1/health/
```

### 2. Nginx Service

**Purpose**: Reverse proxy, TLS termination, static file serving

**Configuration**:
```yaml
nginx:
  image: nginx:1.27-alpine
  container_name: kore-nginx-prod
  restart: always
  ports: "80:80", "443:443"
```

**Configuration File**:
- `./docker/production/nginx/default.conf` - Read-only mount

**Volumes**:
- `static_volume:/static:ro` - Read-only static files
- `media_volume:/media:ro` - Read-only media files

**Dependencies**:
- `django` - Waits for Django to start

**Health Check**:
```bash
wget http://localhost/api/v1/health/
```

### 3. PostgreSQL Service

**Purpose**: Primary relational database

**Configuration**:
```yaml
postgres:
  image: postgres:15-alpine
  container_name: kore-postgres-prod
  restart: always
```

**Environment File**:
- `.envs/.production/.postgres` - User, password, database name

**Volumes**:
- `postgres_data:/var/lib/postgresql/data` - Database persistence

**Health Check**:
```bash
pg_isready -U ${POSTGRES_USER}
```

**Optional Port Exposure**:
```yaml
ports:
  - "5432:5432"  # For backup/restore operations
```

### 4. Redis Service

**Purpose**: In-memory cache, session store, Celery result backend

**Configuration**:
```yaml
redis:
  image: redis:7-alpine
  container_name: kore-redis-prod
  restart: always
  command: redis-server --appendonly yes
```

**Volumes**:
- `redis_data:/data` - Persistence with AOF

**Health Check**:
```bash
redis-cli PING
```

### 5. RabbitMQ Service (Optional)

**When to Use**: If implementing async tasks via Celery

**Configuration**:
```yaml
rabbitmq:
  image: rabbitmq:3-management-alpine
  container_name: kore-rabbitmq-prod
  restart: always
```

**Environment File**:
- `.envs/.production/.rabbitmq` - Credentials and configuration

**Volumes**:
- `rabbitmq_data:/var/lib/rabbitmq` - Queue persistence

**Ports**:
- `5672` - AMQP protocol (internal only by default)
- `15672` - Management UI (optional, expose for staging only)

### 6. Celery Worker (Optional)

**When to Use**: If async task processing is needed

**Configuration**:
```yaml
celery_worker:
  image: kore-django:latest
  command: celery -A config worker -l info --concurrency=4
```

**Dependencies**:
- `postgres`
- `redis`
- `rabbitmq`

**Command Options**:
- `--concurrency=4` - Number of worker processes
- `-l info` - Log level
- `--autoscale=10,3` - Auto-scale between 3-10 workers

### 7. Celery Beat (Optional)

**When to Use**: For periodic/scheduled tasks

**Configuration**:
```yaml
celery_beat:
  image: kore-django:latest
  command: celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

**Requires**:
- `django_celery_beat` package installed
- RabbitMQ and Redis running
- PostgreSQL for schedule storage

## Named Volumes

| Volume | Purpose | Mount Point | Persistence |
|--------|---------|------------|-------------|
| `postgres_data` | Database files | `/var/lib/postgresql/data` | Persistent |
| `redis_data` | Cache with AOF | `/data` | Persistent (AOF) |
| `static_volume` | Django static files | `/app/staticfiles` → Nginx `/static` | Persistent |
| `media_volume` | User uploads | `/app/media` | Persistent |
| `rabbitmq_data` | RabbitMQ queues | `/var/lib/rabbitmq` | Persistent (optional) |

## Networks

**Single Bridge Network**: `kore-prod-network`
- All services communicate via service name (e.g., `postgres:5432`)
- Isolated from host network (except exposed ports)
- DNS resolution via Docker daemon

## Environment Variables

### Django Configuration (`.envs/.production/.django`)

Required:
```bash
SECRET_KEY=your-secret-key-minimum-50-chars
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

Database (auto-configured):
```bash
DATABASE_URL=postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
REDIS_URL=redis://redis:6379/0
```

Optional:
```bash
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
WEB_CONCURRENCY=3
GUNICORN_TIMEOUT=60
```

### PostgreSQL Credentials (`.envs/.production/.postgres`)

```bash
POSTGRES_USER=kore_prod_user
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=kore_production
```

### RabbitMQ Credentials (`.envs/.production/.rabbitmq`)

```bash
RABBITMQ_USER=kore_celery_user
RABBITMQ_PASSWORD=your-secure-password
RABBITMQ_VHOST=/kore
```

## Getting Started

### 1. Prepare Environment Files

```bash
# Create production env directory
mkdir -p .envs/.production

# Copy and edit files
cp .envs/.production.example .envs/.production/.django
cp .envs/.production.example .envs/.production/.postgres
cp .envs/.production.example .envs/.production/.rabbitmq  # if using Celery

# Edit with actual values
nano .envs/.production/.django
nano .envs/.production/.postgres
```

### 2. Build Images

```bash
# Build Django and Nginx images
docker-compose -f docker-compose.production.yml build

# Optionally pre-pull images
docker-compose -f docker-compose.production.yml pull
```

### 3. Start Services

```bash
# Create and start all services
docker-compose -f docker-compose.production.yml up -d

# View startup logs
docker-compose -f docker-compose.production.yml logs -f

# Wait for all services to be healthy
docker-compose -f docker-compose.production.yml ps
```

### 4. Initialize Database

```bash
# Run migrations
docker-compose -f docker-compose.production.yml exec django python manage.py migrate

# Create superuser
docker-compose -f docker-compose.production.yml exec django python manage.py createsuperuser

# Collect static files
docker-compose -f docker-compose.production.yml exec django python manage.py collectstatic --noinput
```

### 5. Verify Deployment

```bash
# Test health endpoints
curl http://localhost/api/v1/health/
curl http://localhost/api/v1/

# View service logs
docker-compose -f docker-compose.production.yml logs django
docker-compose -f docker-compose.production.yml logs nginx
docker-compose -f docker-compose.production.yml logs postgres
```

## Common Operations

### View Logs

```bash
# All services
docker-compose -f docker-compose.production.yml logs -f

# Specific service
docker-compose -f docker-compose.production.yml logs -f django

# Last 100 lines
docker-compose -f docker-compose.production.yml logs --tail=100 django

# Search for errors
docker-compose -f docker-compose.production.yml logs | grep ERROR
```

### Execute Management Commands

```bash
# Run migrations
docker-compose -f docker-compose.production.yml exec django python manage.py migrate

# Create superuser
docker-compose -f docker-compose.production.yml exec django python manage.py createsuperuser

# Django shell
docker-compose -f docker-compose.production.yml exec django python manage.py shell

# Collect static files
docker-compose -f docker-compose.production.yml exec django python manage.py collectstatic --noinput

# Database backup
docker-compose -f docker-compose.production.yml exec postgres pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} > backup.sql
```

### Restart Services

```bash
# Restart specific service
docker-compose -f docker-compose.production.yml restart django

# Restart all services
docker-compose -f docker-compose.production.yml restart

# Restart without stopping dependents
docker-compose -f docker-compose.production.yml up -d --no-deps django
```

### Update Services

```bash
# Rebuild a service
docker-compose -f docker-compose.production.yml build --no-cache django

# Rebuild and restart
docker-compose -f docker-compose.production.yml up -d --build django

# Update all services
docker-compose -f docker-compose.production.yml pull
docker-compose -f docker-compose.production.yml up -d
```

### Stop Services

```bash
# Stop all services (preserve data)
docker-compose -f docker-compose.production.yml stop

# Stop specific service
docker-compose -f docker-compose.production.yml stop django

# Stop and remove containers (preserve volumes)
docker-compose -f docker-compose.production.yml down

# Remove everything including volumes
docker-compose -f docker-compose.production.yml down -v
```

## Health Checks

All services have health checks configured. To monitor:

```bash
# View health status
docker-compose -f docker-compose.production.yml ps

# Expected output:
# NAME               STATUS
# kore-nginx-prod    healthy
# kore-django-prod   healthy
# kore-postgres-prod healthy
# kore-redis-prod    healthy

# View health check details
docker inspect kore-django-prod --format='{{json .State.Health}}'
```

## Troubleshooting

### Django Won't Start

```bash
# Check logs
docker-compose -f docker-compose.production.yml logs django

# Common issues:
# - Database not ready: Ensure postgres is healthy
# - Migrations pending: Run `python manage.py migrate`
# - Missing environment variables: Check .envs/.production/ files
```

### Database Connection Error

```bash
# Verify PostgreSQL is running and healthy
docker-compose -f docker-compose.production.yml ps postgres

# Check credentials
docker-compose -f docker-compose.production.yml logs postgres

# Test connection from Django
docker-compose -f docker-compose.production.yml exec django python -c "import django; django.setup(); from django.db import connection; print(connection.ensure_connection())"
```

### Nginx Returns 502 Bad Gateway

```bash
# Verify Django is running
docker-compose -f docker-compose.production.yml ps django

# Check Nginx logs
docker-compose -f docker-compose.production.yml logs nginx

# Verify Nginx config
docker-compose -f docker-compose.production.yml exec nginx nginx -t
```

### Static Files Not Loading

```bash
# Verify files exist in volume
docker-compose -f docker-compose.production.yml exec django ls -la staticfiles/

# Regenerate static files
docker-compose -f docker-compose.production.yml exec django python manage.py collectstatic --noinput

# Restart Nginx
docker-compose -f docker-compose.production.yml restart nginx
```

### Celery Not Processing Tasks

```bash
# Verify Celery worker is running
docker-compose -f docker-compose.production.yml ps celery_worker

# Check worker logs
docker-compose -f docker-compose.production.yml logs celery_worker

# Inspect Celery active tasks
docker-compose -f docker-compose.production.yml exec celery_worker celery -A config inspect active

# Verify RabbitMQ connection
docker-compose -f docker-compose.production.yml exec celery_worker celery -A config inspect brokers
```

## Scaling and Performance

### Scale Celery Workers

```bash
# Scale to 5 worker containers
docker-compose -f docker-compose.production.yml up -d --scale celery_worker=5

# Note: Each instance needs a unique container name (use service name without explicit container_name)
```

### Adjust Gunicorn Workers

Edit `.envs/.production/.django`:
```bash
WEB_CONCURRENCY=6  # Increase from default 3
```

Then restart:
```bash
docker-compose -f docker-compose.production.yml restart django
```

### Monitor Resource Usage

```bash
# Check container resource consumption
docker stats

# Specific services
docker stats kore-django-prod kore-postgres-prod
```

## Security Considerations

### Environment Files

```bash
# Ensure .envs/.production/ is NOT in git
echo ".envs/.production/" >> .gitignore

# Set proper permissions
chmod 600 .envs/.production/*

# Never commit actual credentials
git add .envs/.production.example  # Example only
```

### Network Security

- Services communicate via internal Docker network
- Only expose ports 80 and 443 (Nginx)
- Database and Redis not exposed by default
- RabbitMQ management port (15672) commented out

### Database Security

- Non-root PostgreSQL user configured
- Strong password required in `.envs/.production/.postgres`
- Database port not exposed in default config
- Connection pooling with connection limits

### Django Security

- `DEBUG=False` enforced in production
- `SECURE_SSL_REDIRECT=True` enforced
- `SESSION_COOKIE_SECURE=True` enforced
- `CSRF_COOKIE_SECURE=True` enforced
- HSTS headers configured
- Allowed hosts restricted

## Backup and Recovery

### Database Backup

```bash
# Full database backup
docker-compose -f docker-compose.production.yml exec postgres \
  pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup with compression
docker-compose -f docker-compose.production.yml exec postgres \
  pg_dump -U ${POSTGRES_USER} -Fc ${POSTGRES_DB} > backup.custom

# Restore from backup
docker-compose -f docker-compose.production.yml exec -T postgres \
  psql -U ${POSTGRES_USER} ${POSTGRES_DB} < backup.sql
```

### Volume Backup

```bash
# Backup all volumes
docker-compose -f docker-compose.production.yml down
tar czf kore-backup-$(date +%Y%m%d).tar.gz \
  .envs/ \
  $(docker volume ls -q | grep kore)

# Restore volumes
docker-compose -f docker-compose.production.yml up -d
```

## Next Steps

1. **Setup HTTPS**: Configure SSL certificates in Nginx
2. **Configure Email**: Update SMTP credentials in `.envs/.production/.django`
3. **Setup Monitoring**: Add monitoring with Prometheus/Grafana
4. **Configure Backups**: Automate database backups
5. **Setup CI/CD**: Automate deployments with GitHub Actions or similar
6. **Performance Tuning**: Monitor and optimize resource allocation
7. **Error Tracking**: Configure Sentry for error monitoring
8. **Logging**: Centralize logs with ELK or similar

## References

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Django Production Deployment](https://docs.djangoproject.com/en/stable/howto/deployment/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)
- [Celery Documentation](https://docs.celeryproject.org/)
- [RabbitMQ Docker Image](https://hub.docker.com/_/rabbitmq)
