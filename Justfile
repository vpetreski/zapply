# Justfile for Zapply
# Run `just` to see all available commands

# Default recipe - show help
default:
    @just --list

# Setup: Install all dependencies and configure environment
setup:
    @echo "📦 Installing Python dependencies with uv..."
    uv sync
    @echo "🎭 Installing Playwright browsers..."
    uv run playwright install chromium
    @echo "📦 Installing frontend dependencies..."
    cd frontend && npm install
    @echo "📝 Setting up environment file..."
    @if [ ! -f .env ]; then cp .env.example .env && echo "Created .env from template. Please edit with your API keys."; else echo ".env already exists"; fi
    @echo "✅ Setup complete!"

# Install Python dependencies
install-py:
    uv sync

# Install frontend dependencies
install-fe:
    cd frontend && npm install

# Database: Start PostgreSQL in Docker
db-start:
    docker compose up -d postgres
    @echo "⏳ Waiting for database to be ready..."
    @sleep 3
    @echo "✅ Database is running"

# Database: Stop PostgreSQL
db-stop:
    docker compose stop postgres

# Database: Create migration
db-migrate name:
    uv run alembic revision --autogenerate -m "{{name}}"

# Database: Check migration status
db-status:
    @echo "📊 Database Migration Status"
    @echo "============================"
    @echo ""
    @echo "Current version:"
    @uv run alembic current
    @echo ""
    @echo "Migration history:"
    @uv run alembic history | head -10
    @echo ""
    @echo "To apply pending migrations: just db-upgrade"

# Database: Apply migrations
db-upgrade:
    @echo "⬆️  Applying database migrations..."
    uv run alembic upgrade head
    @echo "✅ Database is up to date!"

# Database: Rollback one migration
db-downgrade:
    @echo "⚠️  Rolling back one migration..."
    uv run alembic downgrade -1
    @echo "✅ Migration rolled back"

# Database: Reset database (WARNING: destroys all data)
db-reset:
    @echo "⚠️  WARNING: This will destroy all data!"
    @read -p "Are you sure? (yes/no): " confirm && [ "$$confirm" = "yes" ] || exit 1
    docker compose down -v
    just db-start
    just db-upgrade

# Development: Run backend server
dev-backend:
    #!/usr/bin/env bash
    unset ANTHROPIC_API_KEY
    export PYTHONUNBUFFERED=1
    uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Development: Run frontend dev server
dev-frontend:
    cd frontend && npm run dev

# Development: Run both backend and frontend (requires separate terminals)
dev:
    @echo "Run these in separate terminals:"
    @echo "  Terminal 1: just dev-backend"
    @echo "  Terminal 2: just dev-frontend"
    @echo ""
    @echo "Or use a terminal multiplexer like tmux/screen"

# Development: Full local setup and run
dev-setup:
    just db-start
    just db-upgrade
    @echo "✅ Database ready!"
    @echo ""
    @echo "Now run in separate terminals:"
    @echo "  Terminal 1: just dev-backend"
    @echo "  Terminal 2: just dev-frontend"

# Docker: Build all containers
docker-build:
    docker compose build

# Docker: Start all services
docker-up:
    docker compose up -d

# Docker: Stop all services
docker-down:
    docker compose down

# Docker: View logs
docker-logs:
    docker compose logs -f

# Docker: Rebuild and restart all services
docker-restart:
    docker compose down
    docker compose build
    docker compose up -d

# Code Quality: Format Python code
format:
    uv run black app/
    uv run ruff check --fix app/

# Code Quality: Lint Python code
lint:
    uv run ruff check app/
    uv run mypy app/

# Code Quality: Format frontend code
format-fe:
    cd frontend && npm run lint

# Testing: Run Python tests
test:
    uv run pytest

# Testing: Run tests with coverage
test-cov:
    uv run pytest --cov=app --cov-report=html
    @echo "Coverage report: htmlcov/index.html"

# Clean: Remove generated files
clean:
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
    find . -type f -name "*.pyo" -delete
    find . -type d -name "*.egg-info" -exec rm -rf {} +
    find . -type d -name ".pytest_cache" -exec rm -rf {} +
    rm -rf htmlcov/
    rm -rf .coverage
    rm -rf dist/
    rm -rf build/

# Git: Quick commit with message
commit message:
    git add -A
    git commit -m "{{message}}"

# Git: Quick commit and push
push message:
    git add -A
    git commit -m "{{message}}"
    git push

# Production: Deploy to Synology NAS (requires SSH access)
deploy:
    @echo "🚀 Deploying to Synology NAS..."
    @echo "TODO: Add deployment commands"

# Health check: Verify all services are running
health:
    @echo "🏥 Checking service health..."
    @curl -s http://localhost:8000/health | python3 -m json.tool || echo "❌ Backend is not responding"
    @curl -s http://localhost:3000 > /dev/null && echo "✅ Frontend is accessible" || echo "❌ Frontend is not accessible"
    @docker compose ps postgres | grep -q "Up" && echo "✅ Database is running" || echo "❌ Database is not running"

# Show current status
status:
    @echo "📊 Zapply Status"
    @echo "================"
    @echo ""
    @echo "Docker Services:"
    @docker compose ps
    @echo ""
    @echo "Git Status:"
    @git status -s
    @echo ""
    @echo "Current Branch:"
    @git branch --show-current
