# Production Deployment Guide

## Overview

This guide walks you through deploying Duty Bot to production with a real domain instead of ngrok.

## Pre-requisites

- Domain name with DNS configured
- SSL/TLS certificate (Let's Encrypt or equivalent)
- PostgreSQL database (production-grade)
- Server with Docker and Docker Compose installed
- Slack App configured with production credentials
- Telegram Bot configured with production settings

## Step 1: Prepare Production Environment

### 1.1 Create Production `.env` File

```bash
cp .env.production .env
```

Edit `.env` with your production values:

```env
# === DOMAIN CONFIGURATION ===
VITE_API_URL=https://yourdomain.com/api/admin
VITE_API_BACKEND=https://yourdomain.com
VITE_APP_HOST=yourdomain.com
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# === SLACK OAUTH ===
SLACK_REDIRECT_URI=https://yourdomain.com/api/admin/auth/slack/callback

# === DATABASE ===
DATABASE_URL=postgresql+asyncpg://user:password@postgres-host:5432/duty_bot

# === SECURITY ===
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
TELEGRAM_TOKEN=...
```

**Critical Variables:**
- `CORS_ORIGINS` - Must include your domain (required!)
- `VITE_API_URL` - Must use HTTPS
- `VITE_API_BACKEND` - Must use HTTPS
- `SLACK_REDIRECT_URI` - Must match Slack app settings
- `DATABASE_URL` - Use production database

## Step 2: Update Slack App Configuration

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Select your app
3. Go to **Settings → Basic Information**
4. Under **OAuth & Permissions**:
   - Update **Redirect URLs**: `https://yourdomain.com/api/admin/auth/slack/callback`
5. Go to **Event Subscriptions**:
   - Update **Request URL**: `https://yourdomain.com/slack/events`
   - Slack will verify the URL by sending a challenge request (must respond with 200 OK)

## Step 3: Update Telegram Bot Configuration

If using Telegram Mini App:

```bash
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebAppInfo \
  -d webapp_url=https://yourdomain.com
```

If using Telegram Webhook (for bot events):

```bash
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook \
  -d url=https://yourdomain.com/telegram/webhook \
  -d certificate=/path/to/cert.pem  # if using self-signed cert
```

## Step 4: Set up HTTPS with Reverse Proxy

### Option A: Using Nginx with Let's Encrypt

Create `/etc/nginx/sites-available/duty-bot`:

```nginx
upstream duty_bot_backend {
    server localhost:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL certificates from Let's Encrypt
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location / {
        proxy_pass http://duty_bot_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Host $server_name;

        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/duty-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Option B: Using Docker Compose with Traefik

Add Traefik service to `docker-compose.yml`:

```yaml
traefik:
  image: traefik:v2.10
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
    - ./traefik/acme.json:/acme.json
    - ./traefik/config.yml:/traefik.yml
  command:
    - "--api.insecure=false"
    - "--providers.docker=true"
    - "--entrypoints.web.address=:80"
    - "--entrypoints.websecure.address=:443"
    - "--certificatesresolvers.letsencrypt.acme.httpchallenge=true"
    - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
    - "--certificatesresolvers.letsencrypt.acme.email=your-email@example.com"
    - "--certificatesresolvers.letsencrypt.acme.storage=/acme.json"
```

Add labels to `app` service:

```yaml
app:
  labels:
    - "traefik.enable=true"
    - "traefik.http.routers.duty-bot.rule=Host(`yourdomain.com`,`www.yourdomain.com`)"
    - "traefik.http.routers.duty-bot.entrypoints=websecure"
    - "traefik.http.routers.duty-bot.tls.certresolver=letsencrypt"
    - "traefik.http.services.duty-bot.loadbalancer.server.port=8000"
```

## Step 5: Deploy with Docker Compose

```bash
# Pull latest changes
git pull origin main

# Build images
docker-compose build

# Start services
docker-compose up -d

# Run migrations (if needed)
docker-compose exec app alembic upgrade head

# Check logs
docker-compose logs -f app
```

## Step 6: Verify Production Setup

### Check Backend Health

```bash
curl https://yourdomain.com/health
```

Expected response: `{"status": "ok"}`

### Check Slack Integration

1. Try logging in with Slack OAuth on the web panel
2. Check that Slack events are being received:
   ```bash
   docker-compose logs -f app | grep "slack"
   ```

### Check Telegram Integration

1. Try accessing the Telegram Mini App
2. Verify webhook is working:
   ```bash
   curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo
   ```

### Monitor Security

Check that HSTS header is present:

```bash
curl -I https://yourdomain.com | grep Strict-Transport-Security
```

Expected: `Strict-Transport-Security: max-age=31536000; includeSubDomains`

## Step 7: Backup and Monitoring

### Database Backups

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/backups/duty_bot"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
docker-compose exec -T postgres pg_dump -U user duty_bot | \
  gzip > $BACKUP_DIR/duty_bot_$TIMESTAMP.sql.gz

# Keep only last 30 days of backups
find $BACKUP_DIR -type f -mtime +30 -delete
```

### Monitoring

Set up monitoring for:
- Application health checks
- Database connection pool usage
- Disk space (especially for PostgreSQL data)
- SSL certificate expiration
- Error rates and response times

## Troubleshooting

### CORS Errors

If you see CORS errors in browser console:

1. Verify `CORS_ORIGINS` env var includes your domain
2. Ensure protocol matches (http vs https)
3. Check for trailing slashes

```bash
# Debug: Check what CORS_ORIGINS is set to
docker-compose exec app printenv CORS_ORIGINS
```

### Slack OAuth Fails

If Slack OAuth redirect doesn't work:

1. Verify `SLACK_REDIRECT_URI` in Slack app settings
2. Check that it exactly matches: `https://yourdomain.com/api/admin/auth/slack/callback`
3. Ensure CORS_ORIGINS includes yourdomain.com

### SSL Certificate Issues

If you get SSL warnings:

1. Use Let's Encrypt (free, automatic renewal)
2. Use Certbot for certificate management:
   ```bash
   sudo certbot certonly --nginx -d yourdomain.com -d www.yourdomain.com
   sudo certbot renew --dry-run  # Test auto-renewal
   ```

## Performance Tips

1. **Enable Caching**: Add caching headers in Nginx
2. **Use CDN**: Serve static assets from CDN
3. **Database Optimization**: Index frequently queried fields
4. **Rate Limiting**: Already configured via slowapi
5. **Monitoring**: Use Prometheus + Grafana

## Security Checklist

- ✅ HTTPS enabled with valid certificate
- ✅ CORS_ORIGINS set to specific domains (not wildcards)
- ✅ Environment variables secured (not in git)
- ✅ Database password strong and stored securely
- ✅ Regular backups automated
- ✅ Security headers enabled (automatic)
- ✅ CSRF protection active (automatic)
- ✅ Rate limiting enabled (automatic)

## Migration from ngrok

If migrating from ngrok:

1. Deploy on production domain
2. Update Slack app settings with new domain
3. Update Telegram webhook with new domain
4. Update DNS/firewall rules if needed
5. Test with real Slack/Telegram webhooks
6. Monitor logs for any integration issues
7. Remove ngrok from development setup

You're now running in **production mode**! 🚀
