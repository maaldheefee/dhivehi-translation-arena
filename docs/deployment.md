# Deployment Guide for Dhivehi Translation Arena

This guide explains how to deploy the Dhivehi Translation Arena application using Docker for local deployment, with optional Cloudflare Zero Trust Tunnel setup for remote access.

## Overview

- **Target Users:** 1-3 users with rare usage
- **Architecture:** Single Docker container with SQLite database
- **Deployment:** Local Docker with optional Cloudflare tunnel for remote access
- **Port:** Application runs on port 8101

## Prerequisites

### Required
- [Docker Desktop](https://docs.docker.com/get-docker/) installed and running
- [just](https://github.com/casey/just) command runner (recommended)

### Optional (for remote access)
- Cloudflare account
- Domain registered with Cloudflare

## Quick Deployment

### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd dhivehi-translation-arena

# Copy and configure environment variables
cp example.env .env
# Edit .env with your API keys (see Environment Variables section below)
```

### 2. Deploy with Docker

```bash
# Check Docker status and deploy
just up

# Or manually:
just docker-status  # Check if Docker is running
docker-compose up -d --build
```

The application will be available at http://localhost:8101

## Environment Variables

Edit your `.env` file with the following required variables:

```env
# Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# OpenRouter API Key (for non-Gemini models)
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Flask secret key (used for session management)
SECRET_KEY=your_secret_key_here
```

## Common Operations

### Using justfile (Recommended)

```bash
# See all available commands
just

# Application management
just up           # Start the application
just down         # Stop the application
just restart      # Restart the application
just logs         # View application logs
just status       # Check application status

# Database operations
just init-db      # Initialize/reset database (⚠️ destructive)
just backup       # Create database backup

# Maintenance
just docker-clean # Clean up Docker resources (⚠️ destructive)
```

### Manual Docker Commands

```bash
# Start the application
docker-compose up -d

# Stop the application
docker-compose down

# View logs
docker-compose logs -f

# Rebuild and restart
docker-compose up -d --build

# Check container status
docker-compose ps
```

## Troubleshooting

### Docker Issues

1. **Docker not running:**
   ```bash
   just docker-status  # Check Docker status
   ```
   - Ensure Docker Desktop is installed and running
   - Look for Docker whale icon in system tray

2. **Build failures:**
   ```bash
   docker-compose down
   docker system prune -f  # Clean up
   just up  # Rebuild and start
   ```

3. **Port conflicts:**
   - Check if port 8101 is already in use
   - Modify port in `docker-compose.yml` if needed

### Application Issues

1. **Database problems:**
   ```bash
   just init-db  # Reset database (⚠️ loses all data)
   ```

2. **API key issues:**
   - Verify `.env` file exists and contains valid API keys
   - Check logs: `just logs`

3. **Permission issues:**
   - Ensure `data` directory is writable
   - Check Docker volume mounts

## Cloudflare Zero Trust Tunnel Setup

For remote access to your local deployment:

### 1. Install cloudflared

**Windows:**
```powershell
# Download from: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
# Or using winget:
winget install --id Cloudflare.cloudflared
```

**Other platforms:**
See [Cloudflare installation guide](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/)

### 2. Authenticate with Cloudflare

```bash
cloudflared tunnel login
```

This opens a browser window to authenticate with your Cloudflare account.

### 3. Create a Tunnel

```bash
# Create tunnel
cloudflared tunnel create dhivehi-arena

# Note the tunnel ID from the output
```

### 4. Configure the Tunnel

Create `~/.cloudflared/config.yml` (or `%USERPROFILE%\.cloudflared\config.yml` on Windows):

```yaml
tunnel: dhivehi-arena
credentials-file: /path/to/your/tunnel/credentials.json

ingress:
  - hostname: your-domain.com
    service: http://localhost:8101
  - service: http_status:404
```

### 5. Create DNS Record

```bash
cloudflared tunnel route dns dhivehi-arena your-domain.com
```

### 6. Run the Tunnel

```bash
# Test the tunnel
cloudflared tunnel run dhivehi-arena

# Or run as a service (see Cloudflare docs for your OS)
```

### Alternative: Quick Tunnel (No Domain Required)

For temporary access without a domain:

```bash
# Start your application first
just up

# Then create a quick tunnel
cloudflared tunnel --url http://localhost:8101
```

This provides a temporary `*.trycloudflare.com` URL.

## Security Considerations

- **API Keys:** Never commit `.env` file to version control
- **Database:** SQLite database contains all translation data
- **Access:** Consider implementing authentication for production use
- **Tunnel:** Use Cloudflare Access policies to restrict tunnel access

## Backup and Recovery

### Database Backup

```bash
# Create backup
just backup

# Manual backup
cp data/dhivehi_translation_arena.db "data/dhivehi_translation_arena_backup_$(date +%Y%m%d_%H%M%S).db"
```

### Restore from Backup

```bash
# Stop application
just down

# Restore database
cp data/YOUR_BACKUP_FILE.db data/dhivehi_translation_arena.db

# Start application
just up
```

## Performance Notes

- **Low Traffic:** Optimized for 1-3 users with rare usage
- **SQLite:** Suitable for low-concurrency scenarios
- **Single Container:** Simple deployment, easy to manage
- **Resource Usage:** Minimal resource requirements

## Support

For issues:
1. Check logs: `just logs`
2. Verify status: `just status`
3. Review troubleshooting section above
4. Check Docker Desktop status and logs