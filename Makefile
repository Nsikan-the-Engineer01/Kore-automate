.PHONY: help up-local down-local logs-local migrate-local up-prod down-prod logs-prod migrate-prod shell-prod

# Default target
help:
	@echo "╔═══════════════════════════════════════════════════════════════╗"
	@echo "║           Kore Project - Docker Compose Commands              ║"
	@echo "╚═══════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "📦 LOCAL DEVELOPMENT COMMANDS:"
	@echo "  make up-local          - Start local development environment"
	@echo "  make down-local        - Stop local development environment"
	@echo "  make logs-local        - View local logs (all services)"
	@echo "  make migrate-local     - Run database migrations (local)"
	@echo ""
	@echo "🚀 PRODUCTION COMMANDS:"
	@echo "  make up-prod           - Start production environment"
	@echo "  make down-prod         - Stop production environment"
	@echo "  make logs-prod         - View production logs (all services)"
	@echo "  make migrate-prod      - Run database migrations (production)"
	@echo "  make shell-prod        - Open Django shell in production"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""

# ============================================================================
# LOCAL DEVELOPMENT COMMANDS
# ============================================================================

up-local:
	@echo "🚀 Starting local development environment..."
	docker compose -f local.yml up -d
	@echo "✅ Local environment is running!"
	@echo "   📱 Django API: http://localhost:8000"
	@echo "   📧 Mailpit:   http://localhost:8025"
	@echo ""

down-local:
	@echo "🛑 Stopping local development environment..."
	docker compose -f local.yml down
	@echo "✅ Local environment stopped!"

logs-local:
	@echo "📋 Streaming local logs (press Ctrl+C to exit)..."
	docker compose -f local.yml logs -f

migrate-local:
	@echo "🔄 Running database migrations (local)..."
	docker compose -f local.yml exec api python manage.py migrate
	@echo "✅ Migrations complete!"

# ============================================================================
# PRODUCTION COMMANDS
# ============================================================================

up-prod:
	@echo "🚀 Starting production environment..."
	docker compose -f docker-compose.production.yml up -d --build
	@echo "✅ Production environment is running!"
	@echo "   🌐 Application: http://localhost:80"
	@echo ""
	@echo "⚠️  Run migrations and verify deployment:"
	@echo "   make migrate-prod"
	@echo "   docker compose -f docker-compose.production.yml ps"
	@echo ""

down-prod:
	@echo "🛑 Stopping production environment..."
	docker compose -f docker-compose.production.yml down
	@echo "✅ Production environment stopped!"

logs-prod:
	@echo "📋 Streaming production logs (press Ctrl+C to exit)..."
	docker compose -f docker-compose.production.yml logs -f

migrate-prod:
	@echo "🔄 Running database migrations (production)..."
	docker compose -f docker-compose.production.yml exec django python manage.py migrate
	@echo "✅ Migrations complete!"

shell-prod:
	@echo "🐚 Opening Django shell in production..."
	docker compose -f docker-compose.production.yml exec django python manage.py shell
