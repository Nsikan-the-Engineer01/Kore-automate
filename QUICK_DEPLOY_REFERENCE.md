# Quick Deployment Reference

This is a condensed reference for deploying to DigitalOcean. For detailed explanations, see [DIGITALOCEAN_DEPLOYMENT_GUIDE.md](DIGITALOCEAN_DEPLOYMENT_GUIDE.md).

## 🚀 One-Command Deployment (Automated)

```bash
# On your local machine, upload the deploy script to droplet:
scp docker/production/deploy.sh root@YOUR_DROPLET_IP:/root/

# SSH into droplet and run:
ssh root@YOUR_DROPLET_IP
cd ~
chmod +x deploy.sh
./deploy.sh https://github.com/your-username/kore.git YOUR_DROPLET_IP
```

The script will:
1. Clone the repository
2. Create environment files from templates
3. Prompt you to edit secrets
4. Build and start Docker services
5. Run migrations
6. Create superuser
7. Verify deployment

## ⚙️ Manual Step-by-Step Deployment

If you prefer manual control or the script fails:

```bash
# 1. SSH into droplet
ssh root@YOUR_DROPLET_IP

# 2. Update system and install Docker
apt-get update && apt-get upgrade -y
apt-get install -y docker.io docker-compose-plugin git

# 3. Clone repository
git clone https://github.com/your-username/kore.git
cd kore

# 4. Create environment files from templates
mkdir -p .envs/.production
cp .envs/.production/.django.example .envs/.production/.django
cp .envs/.production/.postgres.example .envs/.production/.postgres

# Edit both files with your secrets:
# - Set DJANGO_ALLOWED_HOSTS=YOUR_DROPLET_IP
# - Set PostgreSQL password
# - Set other secrets
nano .envs/.production/.django
nano .envs/.production/.postgres

# 5. Build and start services
docker compose -f docker-compose.production.yml up -d --build

# 6. Run migrations
docker compose -f docker-compose.production.yml exec django python manage.py migrate

# 7. Create superuser
docker compose -f docker-compose.production.yml exec django python manage.py createsuperuser

# 8. Verify deployment
curl http://YOUR_DROPLET_IP/api/v1/health/
```

## 🔍 Verify Deployment

After running the deployment script or manual steps:

```bash
# Check services are running
docker compose -f docker-compose.production.yml ps

# Test health endpoint (should return 200)
curl http://YOUR_DROPLET_IP/api/v1/health/

# Access admin panel (login with superuser credentials)
http://YOUR_DROPLET_IP/admin/

# View API documentation
http://YOUR_DROPLET_IP/api/schema/
```

## 📋 Essential Commands

| Command | Purpose |
|---------|---------|
| `docker compose -f docker-compose.production.yml ps` | View service status |
| `docker compose -f docker-compose.production.yml logs -f` | Stream all logs |
| `docker compose -f docker-compose.production.yml logs django` | View Django logs only |
| `docker compose -f docker-compose.production.yml restart` | Restart all services |
| `docker compose -f docker-compose.production.yml down` | Stop all services |
| `docker compose -f docker-compose.production.yml exec django python manage.py shell` | Open Django shell |

## 🐛 Troubleshooting

**Services won't start:**
```bash
docker compose -f docker-compose.production.yml logs
```

**Database connection error:**
- Check `POSTGRES_PASSWORD` is the same in `.django` and `.postgres` files
- Verify PostgreSQL is running: `docker compose -f docker-compose.production.yml ps postgres`

**502 Bad Gateway:**
```bash
docker compose -f docker-compose.production.yml logs django
docker compose -f docker-compose.production.yml logs nginx
```

**ALLOWED_HOSTS error:**
- Set `DJANGO_ALLOWED_HOSTS=YOUR_DROPLET_IP` in `.envs/.production/.django`
- Restart Django: `docker compose -f docker-compose.production.yml restart django`

For more troubleshooting, see [DIGITALOCEAN_DEPLOYMENT_GUIDE.md](DIGITALOCEAN_DEPLOYMENT_GUIDE.md#troubleshooting).

## 🔐 After Deployment

1. **Update system crontab for backups** (optional)
2. **Configure domain and HTTPS** (optional, see DIGITALOCEAN_DEPLOYMENT_GUIDE.md)
3. **Setup monitoring** (optional, see DIGITALOCEAN_DEPLOYMENT_GUIDE.md)
4. **Keep Docker images updated:**
   ```bash
   docker pull postgres:15-alpine
   docker pull redis:7-alpine
   docker pull nginx:1.27-alpine
   ```
