# Nginx Quick Reference

## What Nginx Does
- Listens on **port 80** (HTTP)
- Proxies requests to **django:8000** (Django app)
- Serves **static files** and **media**
- Adds **security headers**
- **Compresses** responses

## Key Locations

| Path | Handler | Notes |
|------|---------|-------|
| `/api/v1/health/` | Proxy to Django | Health check endpoint |
| `/static/` | Volume mounted | Cache 30 days |
| `/media/` | Volume mounted | Cache 7 days |
| `/` (everything else) | Proxy to Django | All API requests |

## Proxy Headers Sent

```
Host: $host                                    # Original host
X-Real-IP: $remote_addr                        # Client IP
X-Forwarded-For: $proxy_add_x_forwarded_for    # IP chain
X-Forwarded-Proto: $scheme                     # http or https
```

## Config File Locations

- **Nginx Config:** `docker/production/nginx/nginx.conf`
- **Dockerfile:** `docker/production/nginx/Dockerfile`
- **Compose:** `production.yml`

## Common Settings

| Setting | Value | Purpose |
|---------|-------|---------|
| `listen` | 80 | HTTP port |
| `upstream` | django:8000 | Backend server |
| `client_max_body_size` | 10m | Upload limit |
| `proxy_connect_timeout` | 60s | Connection timeout |
| `proxy_read_timeout` | 60s | Response timeout |
| `gzip` | on | Enable compression |
| `gzip_types` | text/*, application/json | Compress these |

## Startup

```bash
# Build and start all services
docker compose -f production.yml up -d

# Verify Nginx is running
docker ps | grep nginx

# View Nginx logs
docker logs kore-nginx-prod

# Test endpoint
curl http://localhost/api/v1/health/
```

## Security Headers Added

| Header | Purpose |
|--------|---------|
| `X-Frame-Options: SAMEORIGIN` | Prevent clickjacking |
| `X-Content-Type-Options: nosniff` | Prevent MIME sniffing |
| `X-XSS-Protection` | Browser XSS protection |
| `Referrer-Policy` | Control referrer info |
| `Permissions-Policy` | Restrict browser access |

## Health Check

Nginx health check:
```bash
# Inside container
wget http://localhost/api/v1/health/

# From host
curl http://localhost/api/v1/health/
```

Status: Container fails if 3+ checks fail within 30s intervals.

## Static Files

Django static files at:
```
/static/                          # Mount point in container
staticfiles/ (in project root)     # Volume source on host
```

Cached by browser for 30 days with immutable flag.

## Troubleshooting

### Can't reach http://localhost/
- Check Nginx is running: `docker ps`
- Check port 80 is not in use: `netstat -an | grep :80`

### 502 Bad Gateway
```bash
# Check Django is running
docker ps | grep api

# Check logs
docker logs kore-api-prod
docker logs kore-nginx-prod
```

### Static files not loading
```bash
# Verify Django collected files
docker exec kore-api-prod python manage.py collectstatic --noinput

# Check Nginx can see them
docker exec kore-nginx-prod ls -la /static/
```

### Slow requests
- Increase timeouts in `nginx.conf`
- Check Django logs for slow operations
- Check network between Nginx and Django

## HTTPS Setup (Future)

```nginx
listen 443 ssl;
ssl_certificate /etc/nginx/ssl/cert.pem;
ssl_certificate_key /etc/nginx/ssl/key.pem;

# Redirect HTTP to HTTPS
server {
    listen 80;
    return 301 https://$host$request_uri;
}
```

Mount certificates in `production.yml`:
```yaml
volumes:
  - ./ssl:/etc/nginx/ssl:ro
```

## Performance

- **Compression**: Gzip enabled for JSON/text
- **Caching**: Browser caches static assets 30 days
- **Connection pooling**: Reuses connections to Django
- **Buffering**: Optimized for API responses

## Files to Know

1. **`docker/production/nginx/nginx.conf`** - Main configuration
2. **`docker/production/nginx/Dockerfile`** - Container image
3. **`production.yml`** - Docker Compose file (service definition)
4. **`docker/production/nginx/NGINX_CONFIGURATION.md`** - Detailed guide

## Testing

```bash
# Full stack test
docker compose -f production.yml up -d

# Health check
curl http://localhost/api/v1/health/

# List transactions
curl http://localhost/api/v1/transactions/

# Check static files
curl http://localhost/static/

# View logs
docker compose -f production.yml logs -f
```

## Key Concepts

**Reverse Proxy**: Nginx sits between client and Django, forwarding requests and managing responses.

**Upstream**: Backend server definition (`django:8000`).

**Proxy Headers**: Headers telling Django about original request (IP, protocol, host).

**Static Files**: Images, CSS, JS served directly by Nginx without hitting Django.

**Gzip**: Compression reduces bandwidth by 60-80%.

## Common Edits

### Increase upload size
```nginx
client_max_body_size 100m;  # Change from 10m
```

### Increase timeouts
```nginx
proxy_connect_timeout 120s;
proxy_send_timeout 120s;
proxy_read_timeout 120s;
```

### Add custom header
```nginx
add_header X-Custom-Header "value" always;
```

### Change backend server
```nginx
upstream django {
    server new-host:8000;  # Change from django:8000
}
```

After edits:
```bash
# Reload Nginx without downtime
docker exec kore-nginx-prod nginx -s reload
```

## Monitoring

Check container status:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

View resource usage:
```bash
docker stats kore-nginx-prod
```

Follow logs in real-time:
```bash
docker logs -f kore-nginx-prod
```

Search logs for errors:
```bash
docker logs kore-nginx-prod | grep ERROR
```

## Docker Compose Service

In `production.yml`:
```yaml
nginx:
  build:
    context: .
    dockerfile: docker/production/nginx/Dockerfile
  container_name: kore-nginx-prod
  ports:
    - "80:80"
  volumes:
    - staticfiles:/static:ro
    - media:/media:rw
  depends_on:
    - api
  healthcheck:
    test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost/api/v1/health/"]
    interval: 30s
    timeout: 5s
    retries: 3
```

This defines the Nginx service with:
- **Build context**: Root directory with Dockerfile path
- **Container name**: `kore-nginx-prod`
- **Port mapping**: 80 (external) → 80 (internal)
- **Volumes**: Static files (read-only), media (read-write)
- **Dependencies**: Starts after API service
- **Health check**: Verifies Nginx is responding
