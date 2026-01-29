# Production Deployment Stack Summary

## Architecture Overview

The production deployment uses a **4-service Docker Compose stack** with reverse proxy architecture:

```
Internet (Port 80)
        ↓
    [Nginx]  ← Reverse proxy, static files, security headers
        ↓
    [Django API]  ← Django REST Framework, Gunicorn WSGI
        ↓
    [PostgreSQL]  ← Database persistence
        ↓
    [Redis]  ← Cache and Celery task queue
```

## Services

### 1. Nginx (Reverse Proxy)
- **Image**: `nginx:1.27-alpine`
- **Port**: 80 (HTTP) & 443 (HTTPS-ready)
- **Role**: Public entry point, static file serving, security headers
- **Health Check**: `/api/v1/health/` endpoint
- **Config**: `docker/production/nginx/nginx.conf`
- **Dockerfile**: `docker/production/nginx/Dockerfile`

**Key Features:**
- Proxies to Django backend (django:8000)
- Serves static files from volume
- Serves media files from volume
- Adds security headers (X-Frame-Options, X-Content-Type-Options, etc.)
- Enables Gzip compression
- Caches static assets 30 days
- API-optimized timeouts (60s)

### 2. Django API (Application)
- **Image**: Multi-stage build from `docker/production/django/Dockerfile`
- **Base**: `python:3.12-slim`
- **Port**: 8000 (internal, exposed to Nginx only)
- **WSGI Server**: Gunicorn 21.2.0
- **Config**: `config/gunicorn.conf.py` (environment-based)
- **User**: `django:django` (non-root)

**Key Features:**
- Runs behind Nginx reverse proxy
- Auto-scales workers based on CPU: `(2 × CPU) + 1`, minimum 3
- Environment-configurable timeout (default 60s)
- Health check via `/api/v1/health/`
- Collects static files at build time
- Depends on PostgreSQL and Redis services

**Environment Variables:**
```
WEB_CONCURRENCY: 3              # Gunicorn workers
GUNICORN_TIMEOUT: 60            # Request timeout (seconds)
LOG_LEVEL: info                 # Logging level
```

### 3. PostgreSQL (Database)
- **Image**: `postgres:16-alpine`
- **Port**: 5432 (internal to Docker network)
- **Persistence**: `postgres_data` volume
- **Health Check**: `pg_isready` command

**Configuration:**
- User and password from `.env.production`
- Database name from environment
- Connection pooling optional (psycopg2-pool in requirements)

### 4. Redis (Cache)
- **Image**: `redis:7-alpine`
- **Port**: 6379 (internal to Docker network)
- **Persistence**: `redis_data` volume
- **Health Check**: Redis PING command

**Uses:**
- Django caching backend
- Celery task queue
- Session storage (optional)

## Volumes

| Volume | Source | Mount | Mode | Purpose |
|--------|--------|-------|------|---------|
| `staticfiles` | `./staticfiles` | `/static` (Nginx), `/app/staticfiles` (Django) | ro (Nginx), ro (Django) | Static assets |
| `media` | `./media` | `/media` (Nginx), `/app/media` (Django) | rw | User uploads |
| `postgres_data` | Docker managed | `/var/lib/postgresql/data` | rw | Database files |
| `redis_data` | Docker managed | `/data` | rw | Cache persistence |

## Networks

All services on `kore-prod-network` Docker network:
- Services communicate by container name (e.g., `django:8000`)
- Isolated from host network
- DNS resolution via Docker daemon

## Health Checks

| Service | Check | Interval | Timeout | Retries | Start Period |
|---------|-------|----------|---------|---------|--------------|
| Nginx | `wget http://localhost/api/v1/health/` | 30s | 5s | 3 | 10s |
| Django | `curl http://localhost:8000/api/v1/health/` | 30s | 10s | 3 | 40s |
| PostgreSQL | `pg_isready -U $POSTGRES_USER` | 10s | 5s | - | - |
| Redis | `redis-cli PING` | 10s | 5s | - | - |

Health checks enable:
- Automatic restart on failure
- Orchestration integration (Kubernetes, Swarm)
- Load balancer health monitoring

## Startup Sequence

1. **Docker Compose Creates:**
   - Docker network `kore-prod-network`
   - 4 volumes (postgresql_data, redis_data, plus bind mounts)
   - 4 containers in order

2. **Service Dependencies:**
   ```
   Nginx → depends_on: api
   API → depends_on: postgres (healthy), redis (healthy)
   Postgres → no dependencies
   Redis → no dependencies
   ```

3. **Startup Order (actual):**
   - PostgreSQL and Redis start first (no dependencies)
   - Django API waits for PostgreSQL and Redis health checks
   - Nginx waits for Django API

4. **Ready State:**
   - All 4 containers running with health checks passing
   - Accessible at `http://localhost/`

## Configuration Files

| File | Purpose |
|------|---------|
| `production.yml` | Docker Compose service definitions |
| `.envs/.env.production` | Environment variables (secrets) |
| `.envs/.env.production.example` | Example environment variables |
| `docker/production/django/Dockerfile` | Django application image |
| `docker/production/nginx/Dockerfile` | Nginx reverse proxy image |
| `docker/production/nginx/nginx.conf` | Nginx configuration |
| `config/gunicorn.conf.py` | Gunicorn WSGI server config |
| `config/settings/production.py` | Django production settings |

## Deployment Steps

### 1. Prepare Environment
```bash
# Copy example to actual production secrets
cp .envs/.env.production.example .envs/.env.production

# Edit with actual values
nano .envs/.env.production
```

### 2. Build Images
```bash
# Build both Docker images
docker compose -f production.yml build
```

### 3. Start Services
```bash
# Create containers and start services
docker compose -f production.yml up -d
```

### 4. Verify Deployment
```bash
# Check all services are running
docker compose -f production.yml ps

# View logs
docker compose -f production.yml logs

# Test endpoints
curl http://localhost/api/v1/health/
curl http://localhost/api/v1/transactions/
```

### 5. Create Superuser (if needed)
```bash
docker exec kore-api-prod python manage.py createsuperuser
```

## Monitoring

### Container Status
```bash
# Check running containers
docker ps --filter "label=com.docker.compose.project=kore"

# Check resource usage
docker stats kore-nginx-prod kore-api-prod kore-postgres-prod kore-redis-prod
```

### Logs
```bash
# View Nginx logs
docker logs kore-nginx-prod

# View Django logs
docker logs kore-api-prod

# Follow logs in real-time
docker compose -f production.yml logs -f
```

### Health
```bash
# Test each service
curl http://localhost/api/v1/health/                    # Via Nginx
curl http://localhost:8000/api/v1/health/              # Direct Django
docker exec kore-postgres-prod pg_isready
docker exec kore-redis-prod redis-cli PING
```

## Troubleshooting

### Services Won't Start
```bash
# Check logs
docker compose -f production.yml logs

# Check port availability
netstat -an | grep LISTEN

# Check resource limits
docker system df
```

### 502 Bad Gateway (Nginx → Django)
```bash
# Verify Django is running
docker ps | grep kore-api-prod

# Check Django logs
docker logs kore-api-prod

# Verify network
docker exec kore-nginx-prod nslookup django
```

### Database Connection Issues
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection
docker exec kore-api-prod python manage.py dbshell

# Check environment variables
docker exec kore-api-prod env | grep DATABASE
```

### Static Files Not Loading
```bash
# Verify files exist
docker exec kore-django-prod ls -la staticfiles/

# Rebuild cache
docker exec kore-api-prod python manage.py collectstatic --noinput

# Restart Nginx
docker restart kore-nginx-prod
```

## Performance Optimization

### Gunicorn Workers
```
WEB_CONCURRENCY = (2 × CPU_COUNT) + 1

Example:
- 1 CPU: 3 workers
- 2 CPU: 5 workers
- 4 CPU: 9 workers
```

Adjust in `production.yml`:
```yaml
environment:
  WEB_CONCURRENCY: "5"  # Override auto-calculation
```

### Request Timeouts
```
GUNICORN_TIMEOUT: 60s   # Time before request is killed

Adjust for:
- Image processing: increase to 120s
- API integrations: increase to 90s
```

### Database Connection Pooling
PostgreSQL connection pooling configured via psycopg2-pool in requirements:
```python
CONN_MAX_AGE = 60  # Minutes - Django ORM setting
```

### Nginx Caching
Adjust static file cache in `docker/production/nginx/nginx.conf`:
```nginx
location /static/ {
    expires 60d;  # Increase from 30d
}
```

## Scaling Considerations

### Horizontal Scaling
To run multiple API instances:
```yaml
api:
  deploy:
    replicas: 3  # 3 API instances
```

Nginx would round-robin across them using upstream balancing.

### Load Balancing
For production, use:
- **AWS**: Application Load Balancer (ALB)
- **GCP**: Cloud Load Balancer
- **Azure**: Application Gateway
- **Self-hosted**: Nginx upstream group or HAProxy

### Database Scaling
- **Read replicas**: PostgreSQL streaming replication
- **Vertical scaling**: Larger instance with more CPU/RAM
- **Connection pooling**: PgBouncer or pgpool-II

### Caching Strategy
- Django ORM queries cached in Redis
- Static files cached by browser (30 days)
- API responses cached where appropriate
- Session storage in Redis

## Security Considerations

### Network Security
- Services communicate via Docker network only
- Database port 5432 only exposed in compose (configurable)
- Django port 8000 only exposed to Nginx

### File Permissions
- Django user: `django:django` (non-root)
- Media files: `rw` permissions for uploads
- Static files: `ro` permissions for Nginx

### Environment Variables
- Secrets in `.env.production` (not in code)
- Example file `.env.production.example` in git
- `.env.production` in `.gitignore`

### Django Security Settings
In `config/settings/production.py`:
```python
DEBUG = False
ALLOWED_HOSTS = [os.getenv('ALLOWED_HOSTS', 'localhost')]
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

### Nginx Security Headers
```
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: no-referrer-when-downgrade
```

## Backup & Recovery

### Database Backup
```bash
# Backup PostgreSQL
docker exec kore-postgres-prod pg_dump -U postgres dbname > backup.sql

# Restore from backup
docker exec -i kore-postgres-prod psql -U postgres < backup.sql
```

### Volume Backup
```bash
# Backup volumes
docker run --rm -v postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres.tar.gz -C /data .
```

### Full Stack Backup
```bash
# Create comprehensive backup
docker compose -f production.yml down
tar czf kore-backup-$(date +%Y%m%d).tar.gz \
  .envs/ staticfiles/ media/ postgres_data redis_data
```

## Documentation Index

| Document | Purpose |
|----------|---------|
| [PRODUCTION_DEPLOYMENT_GUIDE.md](PRODUCTION_DEPLOYMENT_GUIDE.md) | Step-by-step deployment instructions |
| [PRODUCTION_DOCKERFILE_SUMMARY.md](PRODUCTION_DOCKERFILE_SUMMARY.md) | Django Dockerfile details |
| [docker/production/nginx/NGINX_CONFIGURATION.md](docker/production/nginx/NGINX_CONFIGURATION.md) | Nginx configuration guide |
| [docker/production/nginx/NGINX_QUICK_REFERENCE.md](docker/production/nginx/NGINX_QUICK_REFERENCE.md) | Nginx quick reference |
| [config/GUNICORN_CONFIGURATION.md](config/GUNICORN_CONFIGURATION.md) | Gunicorn setup details |
| [GUNICORN_SETUP_QUICK_REFERENCE.md](GUNICORN_SETUP_QUICK_REFERENCE.md) | Gunicorn quick reference |

## Quick Commands

```bash
# Start services
docker compose -f production.yml up -d

# Stop services
docker compose -f production.yml down

# View logs
docker compose -f production.yml logs -f

# Run Django command
docker exec kore-api-prod python manage.py [command]

# Access Django shell
docker exec -it kore-api-prod python manage.py shell

# Access PostgreSQL
docker exec -it kore-postgres-prod psql -U postgres

# Restart service
docker restart kore-api-prod
```

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | False | Django debug mode |
| `ALLOWED_HOSTS` | localhost | Comma-separated allowed hosts |
| `SECRET_KEY` | - | Django secret key (required) |
| `DATABASE_URL` | - | PostgreSQL connection string |
| `REDIS_URL` | redis://redis:6379 | Redis connection string |
| `WEB_CONCURRENCY` | Auto | Gunicorn worker count |
| `GUNICORN_TIMEOUT` | 60 | Request timeout in seconds |
| `LOG_LEVEL` | info | Logging level |
| `EMAIL_HOST` | - | SMTP host for emails |
| `EMAIL_PORT` | 587 | SMTP port |
| `EMAIL_USER` | - | SMTP username |
| `EMAIL_PASSWORD` | - | SMTP password |

All variables defined in `.envs/.env.production` (copy from `.env.production.example`).

## Next Steps

1. **Test Locally**: Run `docker compose -f production.yml up -d` and verify all services
2. **Configure HTTPS**: Add SSL certificates and update Nginx configuration
3. **Set Up Monitoring**: Configure logging aggregation and error tracking
4. **Performance Testing**: Load test the stack and optimize as needed
5. **CI/CD Integration**: Set up automated builds and deployments
6. **Backup Strategy**: Implement automated database and volume backups
7. **Documentation**: Update with your specific domain names and configurations
