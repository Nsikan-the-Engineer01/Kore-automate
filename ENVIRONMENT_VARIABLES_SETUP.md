# Environment Variables Setup Guide

## Overview

This guide explains how to set up environment variables for the Kore application in production. The application uses environment files to manage configuration without hardcoding sensitive values.

## File Structure

```
.envs/
├── .env.example                    # Legacy format (root level)
└── .production/
    ├── .django.example             # ← COPY & EDIT THIS
    ├── .postgres.example           # ← COPY & EDIT THIS
    ├── .rabbitmq.example           # ← COPY & EDIT THIS (optional)
    ├── .django                     # (git ignored - actual values)
    ├── .postgres                   # (git ignored - actual values)
    └── .rabbitmq                   # (git ignored - actual values)
```

## Git Configuration

The `.gitignore` file is configured to:
```gitignore
.envs/*                    # Ignore all environment files
!.envs/.env.example        # EXCEPT example files
!.envs/.production/        # Allow production directory
.envs/.production/*        # Ignore all production env files
!.envs/.production/*.example  # EXCEPT example files
```

**This means:**
- ✅ Example files (`.*.example`) are committed to git
- ✅ Actual env files (`.django`, `.postgres`, `.rabbitmq`) are NOT committed
- ✅ Safe to commit without exposing secrets

## Setup Instructions

### Step 1: Copy Example Files to Actual Files

```bash
# Copy Django example to actual file
cp .envs/.production/.django.example .envs/.production/.django

# Copy PostgreSQL example to actual file
cp .envs/.production/.postgres.example .envs/.production/.postgres

# Copy RabbitMQ example (only if using Celery)
cp .envs/.production/.rabbitmq.example .envs/.production/.rabbitmq
```

### Step 2: Edit Configuration Files

```bash
# Edit Django configuration
nano .envs/.production/.django

# Edit PostgreSQL configuration
nano .envs/.production/.postgres

# Edit RabbitMQ configuration (if using Celery)
nano .envs/.production/.rabbitmq
```

### Step 3: Update Critical Values

**In `.envs/.production/.django`:**

```bash
# Required - Django secret key (minimum 50 characters, unique)
DJANGO_SECRET_KEY=your-very-long-and-unique-secret-key-with-50-chars-minimum

# Required - Your domain names
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,api.yourdomain.com

# Required - Database URL (update with postgres password)
DATABASE_URL=postgres://kore_prod_user:YOUR_PASSWORD@postgres:5432/kore_production

# Required - Frontend URLs for CORS
DJANGO_CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Required if using email - SMTP credentials
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Update PayWithAccount credentials if using PWA
PWA_API_KEY=your-actual-pwa-api-key
PWA_CLIENT_SECRET=your-actual-pwa-secret
```

**In `.envs/.production/.postgres`:**

```bash
# Required - Set a strong database password
POSTGRES_PASSWORD=your-very-strong-database-password-with-special-chars
```

**In `.envs/.production/.rabbitmq`** (if using Celery):

```bash
# Required - Set a strong RabbitMQ password
RABBITMQ_PASSWORD=your-very-strong-rabbitmq-password
```

### Step 4: Verify Setup

```bash
# Check files exist
ls -la .envs/.production/

# Expected output:
# .django          (actual file - git ignored)
# .django.example  (template file - committed to git)
# .postgres        (actual file - git ignored)
# .postgres.example (template file - committed to git)
# .rabbitmq        (actual file - git ignored, optional)
# .rabbitmq.example (template file - committed to git, optional)
```

## Environment Variables Reference

### Django Configuration (`django.example`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DJANGO_SETTINGS_MODULE` | Yes | `config.settings.production` | Django settings module to use |
| `DJANGO_SECRET_KEY` | **Yes** | `change-me` | Django secret key (50+ chars, unique) |
| `DJANGO_ALLOWED_HOSTS` | **Yes** | `your-domain.com` | Comma-separated allowed hostnames |
| `DJANGO_DEBUG` | No | `False` | Debug mode (never True in production) |
| `DJANGO_CORS_ALLOWED_ORIGINS` | **Yes** | `https://...` | Comma-separated CORS origins |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | **Yes** | `https://...` | Comma-separated CSRF trusted origins |
| `DATABASE_URL` | **Yes** | `postgres://...` | PostgreSQL connection string |
| `REDIS_URL` | **Yes** | `redis://...` | Redis connection URL |
| `CELERY_BROKER_URL` | No | `amqp://...` | RabbitMQ broker URL (if using Celery) |
| `CELERY_RESULT_BACKEND` | No | `redis://...` | Celery result backend (if using Celery) |
| `PWA_API_KEY` | **Yes** | `change-me` | PayWithAccount API key |
| `PWA_CLIENT_SECRET` | **Yes** | `change-me` | PayWithAccount client secret |
| `KORE_FEE_PERCENT` | Yes | `0.015` | Transaction fee percentage |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `WEB_CONCURRENCY` | No | `3` | Gunicorn worker count |
| `GUNICORN_TIMEOUT` | No | `60` | Request timeout in seconds |

### PostgreSQL Configuration (`postgres.example`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POSTGRES_USER` | Yes | `kore_prod_user` | Database username |
| `POSTGRES_PASSWORD` | **Yes** | `change-me` | Database password (strong, unique) |
| `POSTGRES_DB` | Yes | `kore_production` | Database name |
| `POSTGRES_HOST` | Yes | `postgres` | Database hostname (in Docker network) |
| `POSTGRES_PORT` | Yes | `5432` | Database port |
| `DATABASE_POOL_SIZE` | No | `10` | Connection pool size |
| `DATABASE_MAX_OVERFLOW` | No | `20` | Additional connections allowed |
| `DATABASE_POOL_RECYCLE` | No | `3600` | Connection recycle time (seconds) |

### RabbitMQ Configuration (`rabbitmq.example`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RABBITMQ_USER` | Yes | `kore_celery_user` | RabbitMQ username |
| `RABBITMQ_PASSWORD` | **Yes** | `change-me` | RabbitMQ password (strong, unique) |
| `RABBITMQ_VHOST` | Yes | `/kore` | RabbitMQ virtual host |
| `RABBITMQ_HOST` | Yes | `rabbitmq` | RabbitMQ hostname (in Docker network) |
| `RABBITMQ_PORT` | Yes | `5672` | RabbitMQ AMQP port |
| `RABBITMQ_ERLANG_COOKIE` | Yes | `change-me` | Erlang cookie for clustering |

## Security Best Practices

### ✅ DO

- ✅ Use strong, unique passwords (20+ characters with special chars)
- ✅ Regenerate `DJANGO_SECRET_KEY` for each environment
- ✅ Keep actual env files in `.gitignore`
- ✅ Commit only `.example` template files
- ✅ Use environment variables for ALL secrets
- ✅ Set file permissions restrictively: `chmod 600 .envs/.production/*`
- ✅ Rotate passwords periodically
- ✅ Use different credentials for each environment (dev, staging, prod)

### ❌ DON'T

- ❌ Hardcode secrets in source code
- ❌ Commit actual environment files to git
- ❌ Use same passwords across environments
- ❌ Share passwords via email or chat
- ❌ Use simple/predictable passwords
- ❌ Store passwords in comments
- ❌ Leave example files with real values
- ❌ Enable DEBUG=True in production

## Common Mistakes

### ❌ Mistake: Wrong DATABASE_URL Format

**Incorrect**:
```bash
DATABASE_URL=postgres://localhost/kore  # Missing user/password
```

**Correct**:
```bash
DATABASE_URL=postgres://kore_prod_user:PASSWORD@postgres:5432/kore_production
```

### ❌ Mistake: Forgot to Change Secret Key

**Incorrect**:
```bash
DJANGO_SECRET_KEY=change-me  # Default value!
```

**Correct**:
```bash
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(50))"
DJANGO_SECRET_KEY=your-generated-50-character-unique-secret-key
```

### ❌ Mistake: Domain Mismatch

**Incorrect**:
```bash
DJANGO_ALLOWED_HOSTS=localhost  # Doesn't match request domain
```

**Correct**:
```bash
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,api.yourdomain.com
```

### ❌ Mistake: Missing CORS Configuration

**Incorrect**:
```bash
DJANGO_CORS_ALLOWED_ORIGINS=*  # Too permissive
```

**Correct**:
```bash
DJANGO_CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

## Example Configurations

### Development (Local)

```bash
# .envs/.production/.django
DJANGO_SECRET_KEY=dev-secret-key-not-secure
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
DJANGO_DEBUG=False
DATABASE_URL=postgres://kore_dev_user:dev_password@localhost:5432/kore_dev
PWA_MOCK_MODE=inspect
```

### Staging

```bash
# .envs/.production/.django
DJANGO_SECRET_KEY=staging-secret-key-50-chars-unique-staging-env
DJANGO_ALLOWED_HOSTS=api-staging.yourdomain.com,staging-api.yourdomain.com
DJANGO_CORS_ALLOWED_ORIGINS=https://staging.yourdomain.com,https://staging-app.yourdomain.com
DATABASE_URL=postgres://kore_staging_user:staging_pwd@postgres:5432/kore_staging
PWA_MOCK_MODE=inspect
```

### Production

```bash
# .envs/.production/.django
DJANGO_SECRET_KEY=production-secret-key-50-chars-unique-production-env
DJANGO_ALLOWED_HOSTS=api.yourdomain.com,yourdomain.com,www.yourdomain.com
DJANGO_CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
DATABASE_URL=postgres://kore_prod_user:strong_prod_password@postgres:5432/kore_production
PWA_MOCK_MODE=production
LOG_LEVEL=WARNING
```

## Troubleshooting

### Database Connection Error

```
Error: could not connect to server: Connection refused
```

**Check**:
1. PostgreSQL service is running: `docker ps | grep postgres`
2. DATABASE_URL is correct: `echo $DATABASE_URL`
3. Password is correct in both `.django` and `.postgres` files
4. Host matches Docker network: should be `postgres`, not `localhost`

### Invalid DJANGO_SECRET_KEY

```
Error: DJANGO_SECRET_KEY must be at least 50 characters
```

**Fix**:
```bash
# Generate new key
python -c "import secrets; print(secrets.token_urlsafe(50))"

# Update in .envs/.production/.django
DJANGO_SECRET_KEY=<generated-key>
```

### CORS Origin Not Allowed

```
Error: CORS policy: Cross-origin request blocked
```

**Fix**:
```bash
# Add frontend origin to DJANGO_CORS_ALLOWED_ORIGINS
DJANGO_CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### PayWithAccount API Error

```
Error: PWA API key is invalid or expired
```

**Fix**:
1. Verify PWA credentials in `.envs/.production/.django`
2. Check PWA base URL matches: `PWA_BASE_URL=https://api.dev.onepipe.io`
3. Verify PWA_MOCK_MODE is set correctly (`inspect` for dev, `production` for prod)

## Environment Variable Validation

Before deploying, validate all required variables:

```bash
#!/bin/bash
# Check required variables are set

required_vars=(
    "DJANGO_SECRET_KEY"
    "DJANGO_ALLOWED_HOSTS"
    "DATABASE_URL"
    "REDIS_URL"
    "PWA_API_KEY"
    "PWA_CLIENT_SECRET"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Missing required variable: $var"
        exit 1
    fi
done

echo "✅ All required variables are set"
```

## Next Steps

1. **Copy example files**:
   ```bash
   cp .envs/.production/.*.example .envs/.production/
   ```

2. **Edit configuration**:
   ```bash
   nano .envs/.production/.django
   nano .envs/.production/.postgres
   ```

3. **Verify setup**:
   ```bash
   docker-compose -f docker-compose.production.yml config | grep -i "DJANGO_SECRET_KEY"
   ```

4. **Build and start**:
   ```bash
   docker-compose -f docker-compose.production.yml build
   docker-compose -f docker-compose.production.yml up -d
   ```

## References

- [Django Environment Variables](https://docs.djangoproject.com/en/stable/howto/deployment/#environment-variables)
- [Twelve-Factor App Configuration](https://12factor.net/config)
- [Docker Compose Environment File](https://docs.docker.com/compose/environment-variables/)
- [Python Secrets Module](https://docs.python.org/3/library/secrets.html)
