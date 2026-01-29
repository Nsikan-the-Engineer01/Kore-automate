# DigitalOcean Staging Deployment Guide

## Overview

This guide walks you through deploying the Kore application to a DigitalOcean Ubuntu droplet using Docker Compose.

**Estimated Time**: 20-30 minutes

**Prerequisites**:
- DigitalOcean account
- SSH key pair generated locally
- Git repo cloned and ready to deploy

## Step 1: Create Ubuntu Droplet

### 1a. Create Droplet on DigitalOcean

1. Log in to [DigitalOcean Console](https://cloud.digitalocean.com)
2. Click **"Create"** → **"Droplets"**
3. **Choose Image**:
   - Select **"Ubuntu"** → **"24.04 LTS"** (Latest LTS)
4. **Choose Size**:
   - **Staging**: "Basic" - **$6/month** (1 GB RAM, 25 GB SSD)
   - **Recommended for testing**: "Basic" - **$12/month** (2 GB RAM, 50 GB SSD)
5. **Datacenter Region**: Choose closest to your location
6. **Authentication**: Select your SSH key (or create new)
7. **Hostname**: `kore-staging` (or your preference)
8. **Click "Create Droplet"**

**Wait for droplet to initialize** (1-2 minutes)

### 1b. Get Droplet IP

Once created, note the **IPv4 address** displayed on the droplet page.

```
Example: 192.0.2.1
```

## Step 2: Connect to Droplet & Install Docker

### 2a. SSH into Droplet

```bash
# Replace with your droplet IP
ssh root@<droplet-ip>

# Example:
# ssh root@192.0.2.1
```

### 2b. Update System

```bash
apt update && apt upgrade -y
```

### 2c. Install Docker

```bash
# Install Docker using official script
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Add root to docker group (so you can run docker without sudo)
usermod -aG docker root

# Activate new group membership
newgrp docker
```

### 2d. Install Docker Compose Plugin

```bash
# Docker Compose comes with Docker now, verify it's installed
docker compose version

# Expected output: Docker Compose version v2.x.x
```

### 2e. Verify Installation

```bash
docker --version
docker compose version
```

## Step 3: Clone Repository

### 3a. Clone Repo

```bash
cd /root
git clone <your-repo-url> kore
cd kore
```

### 3b. Verify Files

```bash
ls -la

# Should show:
# - docker-compose.production.yml
# - .envs/.production/.django.example
# - .envs/.production/.postgres.example
# - config/settings/production.py
```

## Step 4: Configure Environment Variables

### 4a. Create Production Environment Files

```bash
# Create actual files from templates
cp .envs/.production/.django.example .envs/.production/.django
cp .envs/.production/.postgres.example .envs/.production/.postgres
```

### 4b. Edit Django Configuration

```bash
nano .envs/.production/.django
```

**Update these critical variables**:

```bash
# Generate SECRET_KEY locally first:
# python -c "import secrets; print(secrets.token_urlsafe(50))"

DJANGO_SECRET_KEY=your-generated-50-char-secret-key
DJANGO_ALLOWED_HOSTS=<droplet-ip>,staging.yourdomain.com
DJANGO_CORS_ALLOWED_ORIGINS=https://staging-frontend.yourdomain.com,http://<droplet-ip>:3000
DJANGO_CSRF_TRUSTED_ORIGINS=https://<droplet-ip>,https://staging.yourdomain.com
DATABASE_URL=postgres://kore:change-me@postgres:5432/kore
REDIS_URL=redis://redis:6379/0
PWA_API_KEY=your-actual-pwa-key
PWA_CLIENT_SECRET=your-actual-pwa-secret
```

**Save**: Press `Ctrl+X` → `Y` → `Enter`

### 4c. Edit PostgreSQL Configuration

```bash
nano .envs/.production/.postgres
```

**Update password**:

```bash
POSTGRES_DB=kore
POSTGRES_USER=kore
POSTGRES_PASSWORD=change-me-to-strong-password
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
```

**Save**: Press `Ctrl+X` → `Y` → `Enter`

### 4d. Verify Files

```bash
# Check files were created
ls -la .envs/.production/

# Verify not in git history
git status .envs/.production/
```

**Expected**: Files show as untracked/ignored (not committed)

## Step 5: Build and Start Services

### 5a. Build Docker Images

```bash
docker compose -f docker-compose.production.yml build
```

**Wait for build to complete** (3-5 minutes)

### 5b. Start Services

```bash
docker compose -f docker-compose.production.yml up -d --build
```

**Monitor startup**:

```bash
# View logs
docker compose -f docker-compose.production.yml logs -f

# Press Ctrl+C to exit logs

# Check service status
docker compose -f docker-compose.production.yml ps
```

**Expected output**:
```
NAME                    STATUS
kore-nginx-prod         healthy
kore-api-prod           healthy
kore-postgres-prod      healthy
kore-redis-prod         healthy
```

## Step 6: Run Database Migrations

### 6a. Apply Migrations

```bash
docker compose -f docker-compose.production.yml exec django python manage.py migrate
```

**Expected output**:
```
Running migrations:
  Applying app1.0001_initial... OK
  Applying app2.0002_feature... OK
  ...
```

### 6b. Verify Database Connected

If successful, database is running and migrations applied.

## Step 7: Create Superuser

### 7a. Create Admin Account

```bash
docker compose -f docker-compose.production.yml exec django python manage.py createsuperuser
```

**Follow prompts**:
```
Username: admin
Email: admin@example.com
Password: your-secure-password
Password (again): your-secure-password
```

## Step 8: Verify Deployment

### 8a. Test Health Endpoint

```bash
curl http://<droplet-ip>/api/v1/health/

# Expected response:
# {"status":"ok"}
```

### 8b. Test API Endpoint

```bash
# Try to list transactions (should fail without auth, but endpoint exists)
curl http://<droplet-ip>/api/v1/transactions/

# Expected: 401 Unauthorized (authentication required)
```

### 8c. Access Admin Panel

```
Open browser: http://<droplet-ip>/admin
Username: admin
Password: your-superuser-password
```

### 8d. Check Service Logs

```bash
# View all logs
docker compose -f docker-compose.production.yml logs

# View specific service
docker compose -f docker-compose.production.yml logs django
docker compose -f docker-compose.production.yml logs nginx
docker compose -f docker-compose.production.yml logs postgres
```

## Step 9: (Optional) Configure Domain + HTTPS

### 9a. Point DNS to Droplet

In your domain registrar:

1. Go to DNS settings
2. Create **A record**:
   - **Name**: `api-staging` (or your subdomain)
   - **Type**: A
   - **Value**: `<droplet-ip>`
   - **TTL**: 3600 (1 hour)

**Wait for DNS propagation** (10 minutes to 24 hours)

### 9b. Test Domain Access

```bash
curl http://staging.yourdomain.com/api/v1/health/
```

### 9c. Configure SSL/HTTPS (Optional, For Later)

**After domain is working**, configure HTTPS:

1. Update Nginx config with certificates
2. Set environment variables:
   ```bash
   SECURE_SSL_REDIRECT=true
   SESSION_COOKIE_SECURE=true
   CSRF_COOKIE_SECURE=true
   ```
3. Restart services:
   ```bash
   docker compose -f docker-compose.production.yml restart
   ```

See [Docker Compose Production Guide](DOCKER_COMPOSE_PRODUCTION_GUIDE.md) for SSL setup details.

## Troubleshooting

### Problem: Services Won't Start

```bash
# Check logs
docker compose -f docker-compose.production.yml logs

# Common causes:
# 1. Environment variables not set correctly
# 2. Port already in use
# 3. Disk space full
```

**Solution**:
```bash
# Check disk space
df -h

# Check port 80 is free
netstat -tlnp | grep :80

# Restart services
docker compose -f docker-compose.production.yml restart
```

### Problem: Database Connection Error

```
Error: could not connect to server
```

**Check**:
```bash
# 1. PostgreSQL is running
docker compose -f docker-compose.production.yml ps postgres

# 2. Credentials match
cat .envs/.production/.postgres
cat .envs/.production/.django | grep DATABASE_URL

# 3. Check PostgreSQL logs
docker compose -f docker-compose.production.yml logs postgres

# 4. Try to connect directly
docker compose -f docker-compose.production.yml exec postgres psql -U kore -d kore
```

**Solution**:
```bash
# If password is wrong, update both files
nano .envs/.production/.django
nano .envs/.production/.postgres

# Restart
docker compose -f docker-compose.production.yml restart
```

### Problem: 502 Bad Gateway (Nginx)

```bash
# Check Django is running
docker compose -f docker-compose.production.yml ps django

# Check Django logs
docker compose -f docker-compose.production.yml logs django

# Check Nginx configuration
docker compose -f docker-compose.production.yml exec nginx nginx -t
```

**Solution**:
```bash
# Restart both
docker compose -f docker-compose.production.yml restart django nginx
```

### Problem: ALLOWED_HOSTS Rejected

```
DisallowedHost: "..." is not in ALLOWED_HOSTS
```

**Solution**:
```bash
# Update environment variable
nano .envs/.production/.django

# Add your domain/IP to DJANGO_ALLOWED_HOSTS
DJANGO_ALLOWED_HOSTS=<droplet-ip>,staging.yourdomain.com

# Restart
docker compose -f docker-compose.production.yml restart django
```

### Problem: CORS Blocked Requests

```
Access-Control-Allow-Origin header is missing
```

**Solution**:
```bash
# Update CORS origins
nano .envs/.production/.django

# Update DJANGO_CORS_ALLOWED_ORIGINS
DJANGO_CORS_ALLOWED_ORIGINS=https://staging-frontend.yourdomain.com,http://localhost:3000

# Restart
docker compose -f docker-compose.production.yml restart django
```

### Problem: Static Files Not Loading

```bash
# Collect static files
docker compose -f docker-compose.production.yml exec django python manage.py collectstatic --noinput

# Check files exist
docker compose -f docker-compose.production.yml exec django ls -la staticfiles/

# Restart Nginx
docker compose -f docker-compose.production.yml restart nginx
```

### Problem: View Container Shell for Debugging

```bash
# Access Django container
docker compose -f docker-compose.production.yml exec django /bin/bash

# Inside container, try:
python manage.py shell
python manage.py check
python manage.py migrate --plan
```

## Common Operations

### View Live Logs

```bash
# Follow Django logs
docker compose -f docker-compose.production.yml logs -f django

# Follow all logs
docker compose -f docker-compose.production.yml logs -f
```

### Stop Services

```bash
# Stop but preserve data
docker compose -f docker-compose.production.yml stop

# Stop and remove containers (volumes preserved)
docker compose -f docker-compose.production.yml down

# Remove everything including volumes (careful!)
docker compose -f docker-compose.production.yml down -v
```

### Restart Services

```bash
# Restart one service
docker compose -f docker-compose.production.yml restart django

# Restart all
docker compose -f docker-compose.production.yml restart
```

### Backup Database

```bash
# Backup to file
docker compose -f docker-compose.production.yml exec postgres pg_dump -U kore kore > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from file
docker compose -f docker-compose.production.yml exec -T postgres psql -U kore kore < backup.sql
```

### Update Application Code

```bash
# Pull latest code
git pull

# Rebuild and restart
docker compose -f docker-compose.production.yml up -d --build

# Run migrations if needed
docker compose -f docker-compose.production.yml exec django python manage.py migrate
```

## Quick Reference

| Task | Command |
|------|---------|
| **Start services** | `docker compose -f docker-compose.production.yml up -d` |
| **View logs** | `docker compose -f docker-compose.production.yml logs -f` |
| **Stop services** | `docker compose -f docker-compose.production.yml stop` |
| **Run migrations** | `docker compose -f docker-compose.production.yml exec django python manage.py migrate` |
| **Create superuser** | `docker compose -f docker-compose.production.yml exec django python manage.py createsuperuser` |
| **Database shell** | `docker compose -f docker-compose.production.yml exec postgres psql -U kore kore` |
| **Django shell** | `docker compose -f docker-compose.production.yml exec django python manage.py shell` |
| **Container shell** | `docker compose -f docker-compose.production.yml exec django /bin/bash` |
| **Restart service** | `docker compose -f docker-compose.production.yml restart django` |
| **Backup database** | `docker compose -f docker-compose.production.yml exec postgres pg_dump -U kore kore > backup.sql` |

## After Deployment

### Monitoring

1. **Check logs regularly**:
   ```bash
   docker compose -f docker-compose.production.yml logs --tail=50
   ```

2. **Monitor service health**:
   ```bash
   watch docker compose -f docker-compose.production.yml ps
   ```

### Maintenance

1. **Keep system updated**:
   ```bash
   apt update && apt upgrade -y
   ```

2. **Pull latest application code**:
   ```bash
   git pull
   docker compose -f docker-compose.production.yml up -d --build
   ```

3. **Backup database regularly**:
   ```bash
   # Create backup script for cron
   docker compose -f docker-compose.production.yml exec postgres pg_dump -U kore kore > /backups/kore_$(date +%Y%m%d_%H%M%S).sql
   ```

### Security

1. **Change default PostgreSQL password** (done in env file)
2. **Set strong SECRET_KEY** (done in env file)
3. **Configure HTTPS** when domain is ready
4. **Use firewall to restrict access** (DigitalOcean Firewall)

## Security Checklist

- [ ] Changed all "change-me" values in environment files
- [ ] Generated unique SECRET_KEY
- [ ] Set strong database password
- [ ] Updated ALLOWED_HOSTS to your domain/IP
- [ ] Configured CORS_ALLOWED_ORIGINS
- [ ] Configured CSRF_TRUSTED_ORIGINS
- [ ] SSH key authentication only (no password auth)
- [ ] Environment files are git ignored
- [ ] Example files are in git
- [ ] Backups scheduled
- [ ] HTTPS configured (if using domain)

## Next Steps

1. ✅ Test all endpoints work with your frontend
2. ✅ Set up error tracking (Sentry)
3. ✅ Configure email sending
4. ✅ Set up database backups
5. ✅ Configure monitoring/alerts
6. ✅ Document any custom environment variables
7. ✅ Test disaster recovery (restore from backup)

## Support

**For detailed information**:
- [Docker Compose Production Guide](DOCKER_COMPOSE_PRODUCTION_GUIDE.md)
- [Environment Variables Setup](ENVIRONMENT_VARIABLES_SETUP.md)
- [Production Security Settings](config/settings/production.py)
- [Nginx Configuration](docker/production/nginx/default.conf)

## Quick Troubleshooting Summary

| Error | Cause | Fix |
|-------|-------|-----|
| `DisallowedHost` | Domain not in ALLOWED_HOSTS | Update `.envs/.production/.django` |
| `CORS blocked` | Origin not in CORS_ALLOWED_ORIGINS | Update `.envs/.production/.django` |
| `502 Bad Gateway` | Django not running | Check `docker logs`, restart django |
| `Connection refused` | PostgreSQL not running | Check database status, restart postgres |
| `Static files 404` | Not collected | Run `collectstatic --noinput` |
| `Permission denied` | SSH key issue | Check SSH configuration |
| `Port already in use` | Nginx/port conflict | Check `netstat -tlnp` |

**Get help**: Check logs and environment files, then restart services.
