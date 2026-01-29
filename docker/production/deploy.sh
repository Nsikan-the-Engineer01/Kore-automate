#!/bin/bash

# Kore Production Deployment Script
# This script automates the DigitalOcean droplet deployment process
# Usage: chmod +x deploy.sh && ./deploy.sh <repo-url> <droplet-ip>

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║ $1${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
}

print_step() {
    echo -e "${YELLOW}→ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Validate arguments
if [ $# -lt 1 ]; then
    print_error "Usage: ./deploy.sh <repo-url> [optional: droplet-ip]"
    echo ""
    echo "Examples:"
    echo "  ./deploy.sh https://github.com/user/kore.git"
    echo "  ./deploy.sh https://github.com/user/kore.git 192.168.1.100"
    exit 1
fi

REPO_URL=$1
DROPLET_IP=${2:-"localhost"}

print_header "Kore Production Deployment Script"

# Step 1: Clone repository
print_step "Step 1: Cloning repository from $REPO_URL"
if [ -d "kore" ]; then
    print_error "Directory 'kore' already exists. Skipping clone."
else
    git clone "$REPO_URL" kore || {
        print_error "Failed to clone repository"
        exit 1
    }
    print_success "Repository cloned"
fi

cd kore || {
    print_error "Failed to change to kore directory"
    exit 1
}

# Step 2: Create environment files from templates
print_step "Step 2: Creating environment files from templates"

mkdir -p .envs/.production

if [ ! -f ".envs/.production/.django" ]; then
    cp .envs/.production/.django.example .envs/.production/.django
    print_success "Created .envs/.production/.django (edit with your secrets)"
else
    print_error ".envs/.production/.django already exists"
fi

if [ ! -f ".envs/.production/.postgres" ]; then
    cp .envs/.production/.postgres.example .envs/.production/.postgres
    print_success "Created .envs/.production/.postgres (edit with your secrets)"
else
    print_error ".envs/.production/.postgres already exists"
fi

# Step 3: Prompt to edit environment files
print_step "Step 3: Edit environment files with your secrets"
echo ""
echo "Please edit the following files with your actual secrets:"
echo "  1. .envs/.production/.django"
echo "  2. .envs/.production/.postgres"
echo ""
echo "Required Django variables:"
echo "  - DEBUG=False"
echo "  - SECRET_KEY=<generate-with-django-secret>"
echo "  - ALLOWED_HOSTS=<your-domain-or-ip>"
echo "  - DJANGO_SETTINGS_MODULE=config.settings.production"
echo ""
echo "Required PostgreSQL variables:"
echo "  - POSTGRES_DB=kore"
echo "  - POSTGRES_USER=kore"
echo "  - POSTGRES_PASSWORD=<strong-password>"
echo ""
read -p "Press Enter when you've edited both files (or Ctrl+C to cancel)..."

# Step 4: Build and start services
print_step "Step 4: Building and starting Docker services"
echo ""
echo "This may take 2-5 minutes on first build..."
docker compose -f docker-compose.production.yml up -d --build || {
    print_error "Failed to start services"
    echo "Check logs with: docker compose -f docker-compose.production.yml logs"
    exit 1
}

print_success "Services started"
echo ""
echo "Service status:"
docker compose -f docker-compose.production.yml ps

# Step 5: Run migrations
print_step "Step 5: Running database migrations"
sleep 10  # Wait for database to be ready
docker compose -f docker-compose.production.yml exec django python manage.py migrate || {
    print_error "Failed to run migrations"
    echo "Check logs with: docker compose -f docker-compose.production.yml logs django"
    exit 1
}
print_success "Migrations completed"

# Step 6: Create superuser
print_step "Step 6: Creating superuser account"
echo ""
echo "You'll be prompted to enter superuser credentials:"
docker compose -f docker-compose.production.yml exec django python manage.py createsuperuser

# Step 7: Verify deployment
print_step "Step 7: Verifying deployment"
echo ""
echo "Testing health endpoint..."

if [ "$DROPLET_IP" = "localhost" ]; then
    HEALTH_URL="http://localhost/api/v1/health/"
else
    HEALTH_URL="http://$DROPLET_IP/api/v1/health/"
fi

sleep 5

if curl -f -s "$HEALTH_URL" > /dev/null; then
    print_success "Health check passed!"
    echo ""
    print_header "Deployment Successful!"
    echo ""
    echo "Your Kore API is now running!"
    echo ""
    echo "Access points:"
    echo "  API Health:  $HEALTH_URL"
    echo "  Admin Panel: http://$DROPLET_IP/admin/"
    echo "  Docs:        http://$DROPLET_IP/api/schema/"
    echo ""
    echo "Useful commands:"
    echo "  View logs:           docker compose -f docker-compose.production.yml logs -f"
    echo "  Stop services:       docker compose -f docker-compose.production.yml down"
    echo "  Restart services:    docker compose -f docker-compose.production.yml restart"
    echo "  Access shell:        docker compose -f docker-compose.production.yml exec django python manage.py shell"
    echo ""
else
    print_error "Health check failed!"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check service logs: docker compose -f docker-compose.production.yml logs django"
    echo "  2. Verify services are running: docker compose -f docker-compose.production.yml ps"
    echo "  3. Check ALLOWED_HOSTS matches your droplet IP: $DROPLET_IP"
    echo "  4. Review DIGITALOCEAN_DEPLOYMENT_GUIDE.md troubleshooting section"
    exit 1
fi
