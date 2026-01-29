# Nginx Reverse Proxy Configuration

## Overview

Nginx acts as a reverse proxy in front of the Django application, handling:
- HTTP requests on port 80
- Proxying to Django backend (port 8000)
- Static file serving
- Security headers
- Compression
- Caching

## Configuration File

**Location:** `docker/production/nginx/nginx.conf`

**Key Features:**
- Upstream definition pointing to `django:8000`
- Proxy headers setup (Host, X-Real-IP, X-Forwarded-For, X-Forwarded-Proto)
- Client upload limit: 10MB
- Gzip compression enabled
- API-suitable timeouts
- Security headers
- Static and media file serving with caching
- Health check endpoint passthrough

## Upstream Configuration

```nginx
upstream django {
    server django:8000;
}
```

This defines the backend Django application accessible at `django:8000` via the Docker network.

## Server Configuration

### Listen Port
```nginx
listen 80;
server_name _;
```

- Listens on port 80 (HTTP)
- Accepts all server names (using `_`)

### Client Upload Size
```nginx
client_max_body_size 10m;
```

- Allows uploads up to 10MB
- Adjust based on your file upload requirements

### Compression
```nginx
gzip on;
gzip_types text/plain text/css text/xml text/javascript 
           application/x-javascript application/xml+rss 
           application/json application/javascript;
```

- Reduces bandwidth for JSON API responses
- Improves response times

### Timeouts (API-Suitable)
```nginx
proxy_connect_timeout 60s;
proxy_send_timeout 60s;
proxy_read_timeout 60s;
```

- Suitable for API operations
- Allows up to 60 seconds for operations
- Adjust based on your longest running endpoint

### Buffer Settings
```nginx
proxy_buffer_size 4k;
proxy_buffers 8 4k;
proxy_busy_buffers_size 8k;
```

- Optimized for API responses
- Balances memory usage with performance

## Locations

### Health Check
```nginx
location /api/v1/health/ {
    proxy_pass http://django;
    # ...
    access_log off;
}
```

- Proxies to Django health endpoint
- Disables access logging (reduces I/O)
- Caches for 10 seconds upstream

### Static Files
```nginx
location /static/ {
    alias /static/;
    expires 30d;
    add_header Cache-Control "public, immutable";
    access_log off;
}
```

- Serves from `/static/` volume
- Cache expires in 30 days
- Immutable caching headers
- Disables access logging

### Media Files
```nginx
location /media/ {
    alias /media/;
    expires 7d;
    add_header Cache-Control "public";
    access_log off;
}
```

- Serves from `/media/` volume
- Cache expires in 7 days
- Disables access logging

### API Root
```nginx
location / {
    proxy_pass http://django;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

- Proxies all other requests to Django
- Sets required proxy headers
- Maintains connection pool
- Doesn't rewrite redirects

## Proxy Headers

### Host
```nginx
proxy_set_header Host $host;
```
- Original host from client request

### X-Real-IP
```nginx
proxy_set_header X-Real-IP $remote_addr;
```
- Client's real IP address
- Used for logging and IP-based features

### X-Forwarded-For
```nginx
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```
- Chain of IP addresses
- Last IP is the current proxy

### X-Forwarded-Proto
```nginx
proxy_set_header X-Forwarded-Proto $scheme;
```
- Original protocol (http or https)
- Used to detect HTTPS in Django

## Security Headers

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "no-referrer-when-downgrade" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
```

- Prevents clickjacking
- Prevents MIME sniffing
- Prevents XSS attacks
- Controls referrer information
- Restricts browser permissions

## Hidden Files Protection

```nginx
location ~ /\.(?!well-known) {
    deny all;
    access_log off;
    log_not_found off;
}
```

- Blocks access to dotfiles (.env, .git, etc.)
- Allows .well-known directory (for Let's Encrypt)
- Disables logging for missing files

## Dockerfile

**Location:** `docker/production/nginx/Dockerfile`

```dockerfile
FROM nginx:1.27-alpine
```

- Base image: Alpine Linux (minimal)
- Nginx version: 1.27

**Key steps:**
- Remove default configuration
- Copy custom configuration
- Create static and media directories
- Add health check
- Expose port 80
- Run in foreground mode

### Health Check
```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/api/v1/health/
```

- Checks health every 30 seconds
- 5-second timeout
- 10-second start period
- 3 retry attempts before marking unhealthy

## Build and Run

### Build Image
```bash
docker build -f docker/production/nginx/Dockerfile -t kore-nginx:latest .
```

### Run Container
```bash
docker run -d \
  --name kore-nginx \
  -p 80:80 \
  -v ./staticfiles:/static:ro \
  -v ./media:/media:rw \
  --link kore-api:django \
  kore-nginx:latest
```

### Docker Compose
```bash
docker compose -f production.yml up -d
```

## Configuration for HTTPS

To add HTTPS support:

1. **Add SSL certificate volumes:**
```nginx
server {
    listen 80;
    listen 443 ssl;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
}
```

2. **Update Docker Compose:**
```yaml
volumes:
  - ./ssl:/etc/nginx/ssl:ro
```

3. **Add redirect HTTP to HTTPS:**
```nginx
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}
```

## Caching Strategy

### Static Assets
- 30-day expiry
- Immutable flag (cache forever if content hasn't changed)
- Disabled access logging

### Media Files
- 7-day expiry
- Public caching
- Disabled access logging

### API Responses
- No caching (Django should handle if needed)
- Standard access logging

### Health Check
- Not logged (reduces I/O)

## Performance Optimization

### Gzip Compression
- Enabled for text content
- Reduces bandwidth by 60-80%
- Minimal CPU overhead

### Connection Pooling
- `proxy_http_version 1.1`
- Reuses upstream connections
- Reduces latency

### Buffering
- Balances memory and performance
- Prevents buffering issues with large responses

### Caching
- Static files cached in browser
- Health checks not logged
- Reduces server load

## Troubleshooting

### 502 Bad Gateway

Check if Django is running:
```bash
docker logs kore-api-prod
docker ps | grep django
```

Check Nginx logs:
```bash
docker logs kore-nginx-prod
```

Verify upstream address:
```bash
docker exec kore-nginx-prod cat /etc/nginx/conf.d/kore.conf
```

### Slow Requests

Check Nginx performance:
```bash
docker logs kore-nginx-prod
```

Increase timeouts if needed:
```nginx
proxy_connect_timeout 120s;
proxy_send_timeout 120s;
proxy_read_timeout 120s;
```

### Large File Upload Issues

Increase `client_max_body_size`:
```nginx
client_max_body_size 100m;
```

### Static Files Not Serving

Check volume mounting:
```bash
docker exec kore-nginx-prod ls -la /static/
```

Verify Django collected static files:
```bash
docker exec kore-api-prod ls -la staticfiles/
```

## Files

- **Configuration:** `docker/production/nginx/nginx.conf`
- **Dockerfile:** `docker/production/nginx/Dockerfile`
- **Docker Compose:** `production.yml`

## Next Steps

1. Test locally: `docker compose -f production.yml up -d`
2. Verify health: `curl http://localhost/api/v1/health/`
3. Check static files: `curl http://localhost/static/`
4. For HTTPS, add certificates and update configuration
5. Monitor logs: `docker logs -f kore-nginx-prod`

## References

- **Nginx Documentation:** https://nginx.org/en/docs/
- **Reverse Proxy Guide:** https://nginx.org/en/docs/http/ngx_http_proxy_module.html
- **SSL Configuration:** https://nginx.org/en/docs/http/ngx_http_ssl_module.html
