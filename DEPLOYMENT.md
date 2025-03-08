# Deployment Guide for Dhivehi Translation Arena

This guide explains how to deploy the Dhivehi Translation Arena application using Flask's built-in development server.

## Prerequisites

- Python 3.13 or higher

## Files Overview

- `dhivehi-translation-arena.service`: Systemd service file for the application

## Deployment Steps

### Set Up Systemd Service for the Application

The `dhivehi-translation-arena.service` file defines a systemd service that will run the application on boot.

To install and enable the service:

```bash
sudo cp dhivehi-translation-arena.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable dhivehi-translation-arena.service
sudo systemctl start dhivehi-translation-arena.service
```

## Troubleshooting

### Checking Service Status

```bash
sudo systemctl status dhivehi-translation-arena.service
```

### Viewing Logs

```bash
# Application logs
sudo journalctl -u dhivehi-translation-arena.service

# Cloudflare tunnel logs
sudo journalctl -u cloudflared-tunnel.service
```

### Common Issues

1.  **Port already in use**: If port 8080 is already in use, change the port in `app.py` and update the `cloudflared-config.yml` file accordingly.
2.  **Permission issues**: Ensure that the user specified in the service files has the necessary permissions to run the application and access the required files.
3.  **Cloudflare tunnel not connecting**: Check the Cloudflare tunnel logs for any error messages. Make sure your credentials file is valid and that the tunnel is properly configured in the Cloudflare dashboard.
4.  **Certificate issues**: Ensure the `certificate.pem` file is correctly downloaded and the path in `cloudflared-config.yml` is accurate.