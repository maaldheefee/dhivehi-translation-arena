# Dhivehi Translation Arena - Common Commands
# Use `just` to run these commands

# Show available commands
default:
    @just --list

# Development commands
# ===================

# Install dependencies and set up development environment
setup:
    uv venv
    uv pip install -e .[dev]

# Run the application in development mode
dev:
    uv run --no-cache flask run --host 0.0.0.0 --port 8101 --debug

# Initialize the database (⚠️  WARNING: This will create/reset the database)
init-db:
    @echo "⚠️  WARNING: This will initialize/reset the database!"
    @echo "Press Ctrl+C to cancel, or Enter to continue..."
    @read
    uv run flask init-db

# Docker commands
# ===============

# Check if Docker is running
docker-status:
    @echo "Checking Docker status..."
    @docker --version || (echo "❌ Docker not found. Please install Docker Desktop." && exit 1)
    @docker ps > /dev/null || (echo "❌ Docker not running. Please start Docker Desktop." && exit 1)
    @echo "✅ Docker is running"

# Build the Docker image
build:
    docker build -t dhivehi-translation-arena .

# Run with Docker Compose (production deployment) - builds if needed
up:
    @just docker-status
    docker-compose up -d --build

# Run in development mode with live reload
up-dev:
    @just docker-status
    docker-compose -f compose.dev.yml up -d --build

# Run explicit production configuration
up-prod:
    @just docker-status
    docker-compose -f compose.yml up -d --build

# Stop Docker containers (auto-detects which compose file)
down:
    @echo "Stopping all containers..."
    -docker-compose down 2>/dev/null || true
    -docker-compose -f compose.dev.yml down 2>/dev/null || true
    -docker-compose -f compose.yml down 2>/dev/null || true

# View logs from Docker containers
logs:
    docker-compose logs -f

# Restart the application
restart:
    docker-compose restart

# Database and data management
# ============================

# Backup the database (⚠️  Creates a timestamped backup)
backup:
    @echo "Creating database backup..."
    cp data/translations.db "data/translations_backup_$(date +%Y%m%d_%H%M%S).db"
    @echo "Backup created successfully"

# Clean up old backup files (⚠️  WARNING: This will delete old backup files)
clean-backups:
    @echo "⚠️  WARNING: This will delete backup files older than 30 days!"
    @echo "Press Ctrl+C to cancel, or Enter to continue..."
    @read
    find data/ -name "translations_backup_*.db" -mtime +30 -delete
    @echo "Old backups cleaned up"

# Maintenance commands
# ===================

# Clean up Docker resources (⚠️  WARNING: This removes unused Docker resources)
docker-clean:
    @echo "⚠️  WARNING: This will remove unused Docker images, containers, and volumes!"
    @echo "Press Ctrl+C to cancel, or Enter to continue..."
    @read
    docker system prune -f
    docker volume prune -f

# View application status
status:
    @echo "=== Docker Containers ==="
    docker-compose ps
    @echo ""
    @echo "=== Database Status ==="
    @if [ -f "data/translations.db" ]; then echo "Database exists"; else echo "Database not found - run 'just init-db'"; fi
    @echo ""
    @echo "=== Environment ==="
    @if [ -f ".env" ]; then echo ".env file exists"; else echo ".env file missing - copy from example.env"; fi

# Development utilities
# ====================

# Format code with ruff
format:
    ruff format

# Lint code with ruff
lint:
    ruff check --fix --unsafe-fixes
    ruff check --select I --fix
    ruff format
