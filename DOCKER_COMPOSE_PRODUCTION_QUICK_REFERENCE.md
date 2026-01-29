# Docker Compose Production Quick Reference

## File Location

**Main File**: `docker-compose.production.yml`

## Quick Start

```bash
# 1. Prepare environment files
mkdir -p .envs/.production
cp .envs/.production.example .envs/.production/.django
cp .envs/.production.example .envs/.production/.postgres
# Edit files with actual values
nano .envs/.production/.django

# 2. Build and start
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d

# 3. Initialize database
docker-compose -f docker-compose.production.yml exec django python manage.py migrate
docker-compose -f docker-compose.production.yml exec django python manage.py createsuperuser

# 4. Test
curl http://localhost/api/v1/health/
```

## Services Overview

| Service | Image | Port | Purpose | Optional |
|---------|-------|------|---------|----------|
| django | Custom (Dockerfile) | 8000 | App server (Gunicorn) | No |
| nginx | nginx:1.27-alpine | 80/443 | Reverse proxy | No |
| postgres | postgres:15-alpine | 5432 | Database | No |
| redis | redis:7-alpine | 6379 | Cache | No |
| rabbitmq | rabbitmq:3-management | 5672 | Message broker | Yes |
| celery_worker | Custom (Dockerfile) | - | Async tasks | Yes |
| celery_beat | Custom (Dockerfile) | - | Scheduled tasks | Yes |

## Environment Files Structure

```
.envs/.production/
├── .django                    # Django settings, email, security
├── .postgres                  # PostgreSQL credentials
└── .rabbitmq                  # RabbitMQ credentials (optional)
```

## Key Configuration

### Django Service
```yaml
command: gunicorn -c config/gunicorn.conf.py config.wsgi:application
env_file:
  - .envs/.production/.django
  - .envs/.production/.postgres
depends_on:
  postgres: {condition: service_healthy}
  redis: {condition: service_healthy}
volumes:
  - static_volume:/app/staticfiles
  - media_volume:/app/media
```

### Nginx Service
```yaml
image: nginx:1.27-alpine
ports:
  - "80:80"
  - "443:443"
volumes:
  - ./docker/production/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
  - static_volume:/static:ro
  - media_volume:/media:ro
```

### Database Service
```yaml
image: postgres:15-alpine
env_file:
  - .envs/.production/.postgres
volumes:
  - postgres_data:/var/lib/postgresql/data
```

### Redis Service
```yaml
image: redis:7-alpine
command: redis-server --appendonly yes
volumes:
  - redis_data:/data
```

## Essential Commands

### Startup/Shutdown

```bash
# Start all services
docker-compose -f docker-compose.production.yml up -d

# Stop all services (preserve data)
docker-compose -f docker-compose.production.yml stop

# Stop and remove containers (preserve volumes)
docker-compose -f docker-compose.production.yml down

# Start and rebuild images
docker-compose -f docker-compose.production.yml up -d --build

# View service status
docker-compose -f docker-compose.production.yml ps
```

### Logs

```bash
# View all logs (follow mode)
docker-compose -f docker-compose.production.yml logs -f

# View specific service logs
docker-compose -f docker-compose.production.yml logs -f django

# View last 100 lines
docker-compose -f docker-compose.production.yml logs --tail=100 django
```

### Database Operations

```bash
# Run migrations
docker-compose -f docker-compose.production.yml exec django python manage.py migrate

# Create superuser
docker-compose -f docker-compose.production.yml exec django python manage.py createsuperuser

# Access Django shell
docker-compose -f docker-compose.production.yml exec django python manage.py shell

# Collect static files
docker-compose -f docker-compose.production.yml exec django python manage.py collectstatic --noinput

# Database backup
docker-compose -f docker-compose.production.yml exec postgres pg_dump -U kore_prod_user kore_production > backup.sql

# Database restore
docker-compose -f docker-compose.production.yml exec -T postgres psql -U kore_prod_user kore_production < backup.sql
```

### Service Management

```bash
# Restart specific service
docker-compose -f docker-compose.production.yml restart django

# Rebuild and restart service
docker-compose -f docker-compose.production.yml up -d --build django

# Rebuild without cache
docker-compose -f docker-compose.production.yml build --no-cache django

# Restart without stopping dependents
docker-compose -f docker-compose.production.yml up -d --no-deps django
```

## Health Checks

Each service has health checks configured:

```bash
# View service health status
docker-compose -f docker-compose.production.yml ps

# Expected output (healthy):
# kore-nginx-prod    healthy
# kore-django-prod   healthy
# kore-postgres-prod healthy
# kore-redis-prod    healthy
```

## Volumes

| Volume | Source | Purpose |
|--------|--------|---------|
| `postgres_data` | Docker managed | PostgreSQL data |
| `redis_data` | Docker managed | Redis persistence |
| `static_volume` | Docker managed | Django static files |
| `media_volume` | Docker managed | User uploads |
| `rabbitmq_data` | Docker managed | RabbitMQ queues (optional) |

## Network

All services on `kore-prod-network` bridge network:
- Services communicate by name: `postgres:5432`, `redis:6379`
- Isolated from host network
- DNS resolution via Docker daemon

## Environment Variables

### Required in `.envs/.production/.django`
```bash
SECRET_KEY=your-secret-key-minimum-50-chars
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
```

### Database (auto-configured)
```bash
DATABASE_URL=postgres://user:password@postgres:5432/dbname
REDIS_URL=redis://redis:6379/0
```

### RabbitMQ Credentials (`.envs/.production/.rabbitmq`, if using Celery)
```bash
RABBITMQ_USER=kore_celery_user
RABBITMQ_PASSWORD=your-password
```

## Enabling Optional Services

### To Enable Celery with RabbitMQ

1. Uncomment `rabbitmq` service in `docker-compose.production.yml`
2. Create `.envs/.production/.rabbitmq`:
   ```bash
   RABBITMQ_USER=kore_celery_user
   RABBITMQ_PASSWORD=your-password
   RABBITMQ_VHOST=/kore
   ```
3. Uncomment `celery_worker` and `celery_beat` services
4. Update Django service to include `rabbitmq` in depends_on
5. Rebuild and restart: `docker-compose -f docker-compose.production.yml up -d --build`

## Common Issues

### 502 Bad Gateway
```bash
# Check if Django is running
docker-compose -f docker-compose.production.yml ps django

# View Django logs
docker-compose -f docker-compose.production.yml logs django

# Verify Nginx config
docker-compose -f docker-compose.production.yml exec nginx nginx -t
```

### Database Connection Error
```bash
# Check if PostgreSQL is running and healthy
docker-compose -f docker-compose.production.yml ps postgres

# View PostgreSQL logs
docker-compose -f docker-compose.production.yml logs postgres

# Verify credentials in .envs/.production/.postgres
cat .envs/.production/.postgres | grep POSTGRES
```

### Static Files Not Loading
```bash
# Verify files exist
docker-compose -f docker-compose.production.yml exec django ls -la staticfiles/

# Regenerate
docker-compose -f docker-compose.production.yml exec django python manage.py collectstatic --noinput

# Restart Nginx
docker-compose -f docker-compose.production.yml restart nginx
```

### Service Won't Start
```bash
# View full logs
docker-compose -f docker-compose.production.yml logs [service_name]

# Check dependencies are met
docker-compose -f docker-compose.production.yml ps

# Verify health checks passing
docker-compose -f docker-compose.production.yml ps | grep healthy
```

## Monitoring

```bash
# Resource usage
docker stats --no-stream

# Check container logs in real-time
docker-compose -f docker-compose.production.yml logs -f

# Specific service monitoring
docker-compose -f docker-compose.production.yml logs -f --tail=50 django

# Search logs for errors
docker-compose -f docker-compose.production.yml logs | grep -i error
```

## Performance Tuning

### Gunicorn Workers

Edit `.envs/.production/.django`:
```bash
WEB_CONCURRENCY=6        # Increase from 3 (more workers = more CPU usage)
GUNICORN_TIMEOUT=120     # Increase for slow requests
```

Then restart:
```bash
docker-compose -f docker-compose.production.yml restart django
```

### Database Connection Pool

Edit `.envs/.production/.postgres`:
```bash
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
```

### Celery Concurrency (if used)

Edit service command in `docker-compose.production.yml`:
```yaml
command: celery -A config worker -l info --concurrency=8
```

## Security

### Protect Credentials

```bash
# Never commit actual credentials
echo ".envs/.production/" >> .gitignore

# Only commit example file
git add .envs/.production.example

# Set file permissions
chmod 600 .envs/.production/*
```

### Network Isolation

- Services only exposed internally by default
- Only Nginx ports 80/443 exposed to internet
- Database/Redis not exposed unless explicitly configured
- RabbitMQ management port commented out

## Backup

```bash
# Backup database only
docker-compose -f docker-compose.production.yml exec postgres \
  pg_dump -U kore_prod_user kore_production | gzip > backup.sql.gz

# Backup all volumes
docker-compose -f docker-compose.production.yml down
tar czf kore-backup-$(date +%Y%m%d).tar.gz .envs/ postgres_data redis_data static_volume media_volume

# Restore
tar xzf kore-backup-20260129.tar.gz
docker-compose -f docker-compose.production.yml up -d
```

## Documentation

- **Full Guide**: [DOCKER_COMPOSE_PRODUCTION_GUIDE.md](DOCKER_COMPOSE_PRODUCTION_GUIDE.md)
- **Django Guide**: [PRODUCTION_DEPLOYMENT_GUIDE.md](PRODUCTION_DEPLOYMENT_GUIDE.md)
- **Gunicorn Guide**: [GUNICORN_SETUP_QUICK_REFERENCE.md](GUNICORN_SETUP_QUICK_REFERENCE.md)
- **Nginx Guide**: [docker/production/nginx/NGINX_QUICK_REFERENCE.md](docker/production/nginx/NGINX_QUICK_REFERENCE.md)

## File Locations

```
docker-compose.production.yml               # Main compose file
.envs/.production/
├── .django                                 # Django env vars
├── .postgres                               # Database env vars
└── .rabbitmq                               # RabbitMQ env vars (optional)
docker/production/
├── Dockerfile                              # Django image
└── nginx/
    ├── default.conf                        # Nginx configuration
    └── Dockerfile                          # Nginx image
config/
└── gunicorn.conf.py                        # Gunicorn config
```

## Next Steps

1. **Test Locally**: `docker-compose -f docker-compose.production.yml up -d`
2. **Run Migrations**: `docker-compose -f docker-compose.production.yml exec django python manage.py migrate`
3. **Configure HTTPS**: Update Nginx config with SSL certificates
4. **Setup Monitoring**: Add Prometheus/Grafana or ELK stack
5. **Automate Backups**: Schedule database backups
6. **CI/CD Integration**: Setup GitHub Actions or similar
