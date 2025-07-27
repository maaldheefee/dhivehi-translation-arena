# Dhivehi Translation Arena

A blind testing platform for comparing Arabic to Dhivehi translations across a selection of different LLM models. Dhivehi support is rare in most LLMs, so this platform is a way to compare the quality of translations.

## Features

- Blind testing of translations from Arabic to Dhivehi
- Voting system to select the best translation
- Pre-selected test queries and custom query input
- Cost tracking for API calls
- Storage of translations and votes for later analysis

## Quick Start (Recommended)

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- [just](https://github.com/casey/just) command runner (optional but recommended)

### 1. Clone and Setup
```bash
git clone <repository-url>
cd dhivehi-translation-arena

# Copy environment template and fill in your API keys
cp example.env .env
# Edit .env with your actual API keys
```

### 2. Deploy with Docker
```bash
# Using just (recommended)
just up

# Or using docker-compose directly
docker-compose up -d
```

The application will be available at http://localhost:8101

## Common Commands

This project uses a `justfile` for common operations. Install [just](https://github.com/casey/just) and run:

```bash
# See all available commands
just

# Development
just dev          # Run in development mode
just setup        # Set up development environment

# Docker deployment
just up           # Start the application
just down         # Stop the application
just logs         # View logs
just restart      # Restart the application

# Database management
just init-db      # Initialize/reset database (⚠️ destructive)
just backup       # Create database backup

# Maintenance
just status       # Check application status
just docker-clean # Clean up Docker resources (⚠️ destructive)
```

## Development Setup

For local development without Docker:

1. **Install dependencies:**
   ```bash
   just setup
   # Or manually:
   uv venv
   uv pip install -e .[dev]
   ```

2. **Set up environment:**
   ```bash
   cp example.env .env
   # Edit .env with your API keys
   ```

3. **Initialize database:**
   ```bash
   just init-db
   # Or manually:
   uv run flask init-db
   ```

4. **Run development server:**
   ```bash
   just dev
   # Or manually:
   uv run flask run
   ```

## Environment Variables

Create a `.env` file from `example.env` with:

```env
# Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# OpenRouter API Key (for Sonnet 3.7 access)
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Flask secret key (used for session management)
SECRET_KEY=your_secret_key_here
```

## Deployment Notes

- **Target Users:** 1-3 users with rare usage
- **Architecture:** Single container deployment suitable for low-traffic scenarios
- **Data Persistence:** SQLite database stored in `./data` directory (mounted as Docker volume)
- **Port:** Application runs on port 8101 (mapped from container port 8080)
- **Future:** Ready for Cloudflare Zero Trust Tunnel integration (see `DEPLOYMENT.md`)

## Data Storage

All translations and votes are stored in a SQLite database located in the `data` directory. The database is automatically created when you run `just init-db` or start the Docker container for the first time.

## Troubleshooting

- **Check status:** `just status`
- **View logs:** `just logs`
- **Database issues:** `just init-db` (⚠️ this will reset all data)
- **Docker issues:** `just docker-clean` (⚠️ this will remove unused Docker resources)

For detailed deployment instructions and Cloudflare tunnel setup, see `DEPLOYMENT.md`.
