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
    @echo "✅ Database ready! (migrations run automatically on app startup)"
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

# Production: Deploy (requires SSH access to your server)
deploy:
    #!/usr/bin/env bash
    set -e
    echo "🚀 Deploying to production server..."
    echo ""

    # Check we're on main branch
    BRANCH=$(git branch --show-current)
    if [ "$BRANCH" != "main" ]; then
        echo "❌ Error: Must be on main branch to deploy"
        echo "   Current branch: $BRANCH"
        exit 1
    fi

    # Check for uncommitted changes
    if [ -n "$(git status --porcelain)" ]; then
        echo "❌ Error: Uncommitted changes detected"
        echo "   Commit or stash changes before deploying"
        exit 1
    fi

    echo "✓ On main branch with clean working directory"
    echo ""
    echo "Deployment will be triggered by GitHub Actions"
    echo "Push to main to deploy, or manually run deployment script on your server"
    echo ""
    echo "Manual deployment:"
    echo "  ssh YOUR_USER@YOUR_SERVER_IP"
    echo "  cd /path/to/zapply"
    echo "  ./deploy.sh"

# Health check: Verify all services are running
health:
    @echo "🏥 Checking service health..."
    @curl -s http://localhost:8000/health | python3 -m json.tool || echo "❌ Backend is not responding"
    @curl -s http://localhost:3000 > /dev/null && echo "✅ Frontend is accessible" || echo "❌ Frontend is not accessible"
    @docker compose ps postgres | grep -q "Up" && echo "✅ Database is running" || echo "❌ Database is not running"

# Sync: Copy production data from server to local database (exact copy)
# NOTE: Configure SERVER variable and ensure passwordless sudo for docker on server.
server-local-sync:
    #!/usr/bin/env bash
    set -e
    # CUSTOMIZE: Set your server SSH connection string
    SERVER="${SERVER:-YOUR_USER@YOUR_SERVER_IP}"
    SERVER_DOCKER="sudo docker"
    SERVER_CONTAINER="zapply-postgres-prod"
    echo "📥 Syncing Server (production) → Local database..."
    echo ""

    DUMP_FILE="/tmp/zapply_server_dump_$(date +%s).sql"

    echo "1️⃣  Dumping server database..."
    ssh "$SERVER" "$SERVER_DOCKER exec $SERVER_CONTAINER pg_dump -U zapply -d zapply" > "$DUMP_FILE"

    echo "2️⃣  Terminating existing connections on local..."
    docker exec zapply-postgres psql -U zapply -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'zapply' AND pid <> pg_backend_pid();"

    echo "3️⃣  Dropping and recreating local database..."
    docker exec zapply-postgres psql -U zapply -d postgres -c "DROP DATABASE IF EXISTS zapply;"
    docker exec zapply-postgres psql -U zapply -d postgres -c "CREATE DATABASE zapply OWNER zapply;"

    echo "4️⃣  Restoring to local database..."
    docker exec -i zapply-postgres psql -U zapply -d zapply < "$DUMP_FILE"

    echo "5️⃣  Cleaning up..."
    rm -f "$DUMP_FILE"

    echo ""
    echo "✅ Local database is now an exact copy of server production!"

# Sync: Copy local data to server production database (exact copy)
# NOTE: Configure SERVER variable and ensure passwordless sudo for docker on server.
local-server-sync:
    #!/usr/bin/env bash
    set -e
    # CUSTOMIZE: Set your server SSH connection string
    SERVER="${SERVER:-YOUR_USER@YOUR_SERVER_IP}"
    SERVER_DOCKER="sudo docker"
    SERVER_CONTAINER="zapply-postgres-prod"
    echo "📤 Syncing Local → Server (production) database..."
    echo ""
    echo "⚠️  WARNING: This will completely replace production data on server!"
    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Aborted."
        exit 1
    fi
    echo ""

    DUMP_FILE="/tmp/zapply_local_dump_$(date +%s).sql"

    echo "1️⃣  Dumping local database..."
    docker exec zapply-postgres pg_dump -U zapply -d zapply > "$DUMP_FILE"

    echo "2️⃣  Terminating existing connections on server..."
    ssh "$SERVER" "$SERVER_DOCKER exec $SERVER_CONTAINER psql -U zapply -d postgres -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'zapply' AND pid <> pg_backend_pid();\""

    echo "3️⃣  Dropping and recreating server database..."
    ssh "$SERVER" "$SERVER_DOCKER exec $SERVER_CONTAINER psql -U zapply -d postgres -c 'DROP DATABASE IF EXISTS zapply;'"
    ssh "$SERVER" "$SERVER_DOCKER exec $SERVER_CONTAINER psql -U zapply -d postgres -c 'CREATE DATABASE zapply OWNER zapply;'"

    echo "4️⃣  Restoring to server database (streaming via SSH)..."
    cat "$DUMP_FILE" | ssh "$SERVER" "$SERVER_DOCKER exec -i $SERVER_CONTAINER psql -U zapply -d zapply"

    echo "5️⃣  Cleaning up..."
    rm -f "$DUMP_FILE"

    echo ""
    echo "✅ Server production database is now an exact copy of local!"

# Setup: Configure passwordless sudo for docker on server (run once, interactive)
server-setup-sudo:
    #!/usr/bin/env bash
    set -e
    # CUSTOMIZE: Set your server SSH connection string
    SERVER="${SERVER:-YOUR_USER@YOUR_SERVER_IP}"
    echo "🔧 Setting up passwordless sudo for docker on server..."
    echo ""
    echo "This will add a sudoers rule to allow running docker without password."
    echo "You will need to enter your server password when prompted."
    echo ""
    echo "Run these commands manually on server (SSH in first):"
    echo ""
    echo "  ssh $SERVER"
    echo "  sudo sh -c 'echo \"YOUR_USER ALL=(ALL) NOPASSWD: /usr/local/bin/docker\" >> /etc/sudoers'"
    echo ""
    echo "After that, run 'just server-local-sync' to test."

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
