# Environment Files Setup - Summary

## What Was Created ✅

### Example Configuration Files (Committed to Git)

Three template files showing all required environment variables with placeholders:

1. **`.envs/.production/.django.example`** (2.6 KB)
   - Django application settings
   - PayWithAccount (PWA) configuration
   - Email and security settings
   - Gunicorn settings

2. **`.envs/.production/.postgres.example`** (1.0 KB)
   - PostgreSQL credentials
   - Connection pool settings
   - Database initialization arguments

3. **`.envs/.production/.rabbitmq.example`** (1.3 KB)
   - RabbitMQ credentials
   - Virtual host configuration
   - Memory and performance settings

### Actual Configuration Files (Git Ignored)

When you copy the example files, actual working files are created:
- `.envs/.production/.django` (git ignored)
- `.envs/.production/.postgres` (git ignored)
- `.envs/.production/.rabbitmq` (git ignored)

### Documentation

**`ENVIRONMENT_VARIABLES_SETUP.md`** (9.2 KB)
- Complete setup instructions
- Variable reference table
- Security best practices
- Common mistakes and fixes
- Example configurations
- Troubleshooting guide

### Updated Git Configuration

**`.gitignore`** (Updated)
```gitignore
.envs/*                           # Ignore all env files
!.envs/.env.example               # Except legacy example
!.envs/.production/               # Allow production directory
.envs/.production/*               # Ignore all production files
!.envs/.production/*.example      # Except example templates
```

**Result**: 
- ✅ Example files are committed
- ✅ Actual secrets are NOT committed
- ✅ Safe collaboration without exposing passwords

## File Structure

```
.envs/
├── .production/
│   ├── .django                     (actual - git ignored)
│   ├── .django.example             ✅ (template - committed)
│   ├── .postgres                   (actual - git ignored)
│   ├── .postgres.example           ✅ (template - committed)
│   ├── .rabbitmq                   (actual - git ignored, optional)
│   └── .rabbitmq.example           ✅ (template - committed, optional)
└── .env.example                    (legacy)

ENVIRONMENT_VARIABLES_SETUP.md      ✅ (comprehensive guide)
```

## Key Variables

### Django (`.django`)

**Required**:
- `DJANGO_SECRET_KEY` - 50+ character unique secret
- `DJANGO_ALLOWED_HOSTS` - Your domain names
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection URL
- `PWA_API_KEY` / `PWA_CLIENT_SECRET` - PayWithAccount credentials

**Example**:
```bash
DJANGO_SECRET_KEY=your-50-char-unique-secret-key-here
DJANGO_ALLOWED_HOSTS=api.yourdomain.com,yourdomain.com
DATABASE_URL=postgres://user:password@postgres:5432/kore_production
REDIS_URL=redis://redis:6379/0
PWA_API_KEY=your-actual-key
PWA_CLIENT_SECRET=your-actual-secret
```

### PostgreSQL (`.postgres`)

**Required**:
- `POSTGRES_USER` - Database username
- `POSTGRES_PASSWORD` - Database password (strong!)
- `POSTGRES_DB` - Database name

**Example**:
```bash
POSTGRES_USER=kore_prod_user
POSTGRES_PASSWORD=your-strong-password-with-special-chars
POSTGRES_DB=kore_production
```

### RabbitMQ (`.rabbitmq`) - Optional

**Required** (only if using Celery):
- `RABBITMQ_USER` - RabbitMQ username
- `RABBITMQ_PASSWORD` - RabbitMQ password (strong!)
- `RABBITMQ_VHOST` - Virtual host name

**Example**:
```bash
RABBITMQ_USER=kore_celery_user
RABBITMQ_PASSWORD=your-strong-rabbitmq-password
RABBITMQ_VHOST=/kore
```

## Setup Procedure

### Step 1: Copy Example Files
```bash
# Create actual files from templates
cp .envs/.production/.django.example .envs/.production/.django
cp .envs/.production/.postgres.example .envs/.production/.postgres
cp .envs/.production/.rabbitmq.example .envs/.production/.rabbitmq
```

### Step 2: Edit Configuration
```bash
# Edit Django settings
nano .envs/.production/.django

# Edit PostgreSQL settings
nano .envs/.production/.postgres

# Edit RabbitMQ settings (if using Celery)
nano .envs/.production/.rabbitmq
```

### Step 3: Update Critical Values

In `.envs/.production/.django`:
```bash
# Generate new secret key
python -c "import secrets; print(secrets.token_urlsafe(50))"

# Update these variables
DJANGO_SECRET_KEY=your-generated-key
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgres://kore_prod_user:YOUR_PASSWORD@postgres:5432/kore_production
DJANGO_CORS_ALLOWED_ORIGINS=https://yourdomain.com
PWA_API_KEY=your-actual-key
PWA_CLIENT_SECRET=your-actual-secret
```

In `.envs/.production/.postgres`:
```bash
# Generate strong password
openssl rand -base64 32

# Update password
POSTGRES_PASSWORD=your-generated-strong-password
```

### Step 4: Verify and Deploy
```bash
# Verify files exist
ls -la .envs/.production/

# Verify not in git
git status .envs/.production/

# Build and start
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d
```

## Security Checklist

✅ **Before Deployment**:
- [ ] Changed `DJANGO_SECRET_KEY` from "change-me"
- [ ] Set strong `POSTGRES_PASSWORD` (20+ chars with special chars)
- [ ] Updated `DJANGO_ALLOWED_HOSTS` to your domain
- [ ] Configured `DATABASE_URL` with postgres password
- [ ] Set `PWA_API_KEY` and `PWA_CLIENT_SECRET` to actual values
- [ ] Configured email settings (if sending emails)
- [ ] Verified `.env*.example` files are committed
- [ ] Verified actual `.env*` files are NOT committed
- [ ] Ensured `.gitignore` is updated correctly

## Common Mistakes to Avoid

❌ **Don't**:
- Don't use "change-me" as actual values
- Don't hardcode secrets in code
- Don't commit actual environment files to git
- Don't share passwords via email or chat
- Don't use same password across environments
- Don't leave default values in production

✅ **Do**:
- Do generate unique secrets for each environment
- Do use strong passwords (20+ chars with special chars)
- do commit example files to show required variables
- Do use environment variables for ALL secrets
- Do rotate passwords periodically
- Do set restrictive file permissions: `chmod 600 .envs/.production/*`

## Integration with Docker Compose

The `docker-compose.production.yml` file uses these environment files:

```yaml
services:
  django:
    env_file:
      - .envs/.production/.django
      - .envs/.production/.postgres
    environment:
      DATABASE_URL: postgres://...  # Constructed from postgres env vars
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: amqp://...  # From rabbitmq env vars

  postgres:
    env_file:
      - .envs/.production/.postgres

  rabbitmq:
    env_file:
      - .envs/.production/.rabbitmq
```

**Result**: All services automatically pick up configuration from environment files.

## Validation

### Check Files Are Properly Set Up

```bash
# 1. Verify actual files exist
[ -f .envs/.production/.django ] && echo "✅ .django exists" || echo "❌ .django missing"
[ -f .envs/.production/.postgres ] && echo "✅ .postgres exists" || echo "❌ .postgres missing"

# 2. Verify example files exist (for git)
[ -f .envs/.production/.django.example ] && echo "✅ .django.example exists" || echo "❌ .django.example missing"

# 3. Verify not committed
git status .envs/.production/.django | grep -q "new file" && echo "❌ .django is tracked!" || echo "✅ .django is git ignored"

# 4. Verify variables are set
grep -q "change-me" .envs/.production/.django && echo "⚠️  'change-me' still in .django" || echo "✅ No 'change-me' placeholders"
```

## Documentation Reference

**For detailed setup guide**: → `ENVIRONMENT_VARIABLES_SETUP.md`

Topics covered:
- Overview and file structure
- Git configuration explanation
- Step-by-step setup instructions
- Complete variable reference table
- Security best practices
- Common mistakes with examples
- Example configurations (dev/staging/prod)
- Troubleshooting guide
- Environment variable validation

## Next Steps

1. ✅ Copy example files: `cp .envs/.production/.*.example .envs/.production/`
2. ✅ Edit configuration: `nano .envs/.production/.django` etc.
3. ✅ Verify setup with guide: `ENVIRONMENT_VARIABLES_SETUP.md`
4. ✅ Deploy: `docker-compose -f docker-compose.production.yml up -d`

## Summary

**Created**:
- 3 example configuration files (templates)
- 1 comprehensive setup guide (9.2 KB)
- Updated .gitignore for proper security

**Status**: 🟢 Ready to configure and deploy

**Next**: Copy example files, edit with your values, and deploy!

See `ENVIRONMENT_VARIABLES_SETUP.md` for complete instructions.
