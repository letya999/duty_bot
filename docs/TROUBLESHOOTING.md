# Troubleshooting Guide

## Network & HTTPS Issues

### Request URL Not Responding (Slack/Telegram)
**Problem**: Slack or Telegram says "This URL didn't respond with the expected challenge parameter" or "Request URL unreachable"

**Solutions**:
1. **Verify HTTPS**: All URLs must be HTTPS. If developing locally, use `ngrok` to create a public tunnel:
   ```bash
   ngrok http 8000
   ```
   Copy the `https://...ngrok-free.dev` URL provided.

2. **Test the URL manually**:
   ```bash
   curl -X POST https://your-ngrok-url.ngrok-free.dev/slack/events
   ```
   You should get a response (may be an error, but not a timeout).

3. **Check firewall**: Ensure your machine/server allows inbound traffic on port 8000 (or your `PORT`).

4. **Restart application**: Changes to port or URL require restart:
   ```bash
   docker-compose restart app
   ```

### ngrok Connection Lost
**Problem**: ngrok disconnects or URL changes frequently

**Solution**:
- ngrok free tier has limited uptime. For development:
  - Restart ngrok and update the URL in Slack/Telegram settings
  - Use `ngrok http 8000 --region us` for more stable connections (may vary by region)
  - For production, use a stable domain with HTTPS certificate (not ngrok)

---

## Slack-Specific Issues

### Event Subscription Verification Failed
**Problem**: "Invalid request URL" error when setting Event Subscriptions Request URL

**Causes & Solutions**:
1. **URL not HTTPS**: Ensure URL uses `https://`, not `http://`
2. **Server not running**: Start the application before adding URL to Slack
3. **Wrong endpoint**: Should be `/slack/events`, not something else
4. **Signing Secret issue**: Make sure `SLACK_SIGNING_SECRET` is correctly set in `.env`

### Slash Commands Not Triggering
**Problem**: Typing `/duty` in Slack does nothing

**Solutions**:
1. **Request URL not set**: Go to **Slash Commands** → Select your command → Check "Request URL" is filled in correctly
2. **URL is different**: Each slash command needs its Request URL set to `https://your-url/slack/events`
3. **Bot not installed**: Go to **Install App** → Click **Reinstall to Workspace**
4. **Insufficient permissions**: The bot needs `commands` scope. Check **OAuth & Permissions** → **Bot Token Scopes**

### Events Not Reaching Your App
**Problem**: Command works in Slack but app doesn't process it

**Solutions**:
1. **Check server logs**:
   ```bash
   docker-compose logs -f app | grep -i slack
   ```
2. **Verify signing secret**: Run test to check if signature validation works:
   ```bash
   # Check if SLACK_SIGNING_SECRET matches the one in Slack app settings
   echo $SLACK_SIGNING_SECRET
   ```
3. **Check network latency**: Slack may timeout if your server responds slowly (>3 seconds)
4. **Event not subscribed**: Go to **Event Subscriptions** → **Subscribe to bot events** → Ensure events like `app_mention` or `message.channels` are added

### Bot Can't Write Messages
**Problem**: "/duty" command is received but bot doesn't send responses

**Solutions**:
1. **Missing `chat:write` scope**: Go to **OAuth & Permissions** → **Bot Token Scopes** → Add `chat:write`
2. **Bot not added to channel**: The bot needs to be added to the channel first. Type `@botname` in the channel.
3. **Invalid channel ID**: Ensure `SLACK_CHANNEL_ID` is correct (should look like `C123ABC456`)
4. **Token expired**: Try clicking **Reinstall to Workspace** to generate a new token

### OAuth/Authentication Issues
**Problem**: Users can't log in via Slack, or OAuth flow fails

**Solutions**:
1. **Redirect URL mismatch**: Go to **OAuth & Permissions** → **Redirect URLs** → Ensure it matches your callback endpoint:
   - Should be: `https://your-url/api/admin/auth/slack/callback`
   - NOT: `https://your-url/slack/events`
2. **Client ID/Secret wrong**: Copy fresh credentials from **Basic Information** → **App Credentials**
3. **Scope missing**: Add `users:read` and `users:read.email` if your app needs user info
4. **User not authorized**: Check app permissions in Slack workspace settings

---

## Google Calendar Issues

### Service Account Authentication Failed
**Problem**: "Permission denied" or "Invalid credentials" when syncing calendar

**Solutions**:
1. **Check JSON key validity**:
   ```bash
   # Verify the JSON is valid
   cat $GOOGLE_SERVICE_ACCOUNT_KEY_PATH | jq .
   ```
2. **Service account not shared calendar**:
   - Go to Google Calendar
   - **Settings & sharing** → **Share with specific people**
   - Add the email from the JSON (looks like: `name@project-id.iam.gserviceaccount.com`)
   - Grant `Editor` permission
3. **API not enabled**: Verify Google Calendar API is enabled in Google Cloud Console

### Events Not Syncing to Google Calendar
**Problem**: Events are created in your app but don't appear in Google Calendar

**Solutions**:
1. **Service account doesn't have access**: Follow steps in "Service Account Authentication Failed" above
2. **Wrong calendar ID**: Ensure the calendar ID is correct (should start with an email or UUID)
3. **Check sync logs**:
   ```bash
   docker-compose logs -f app | grep -i calendar
   ```
4. **Restart sync**: Go to Admin Panel → **Settings** → **Google Calendar** → Re-upload JSON or toggle sync off/on

### Encryption Error After Key Change
**Problem**: "Failed to decrypt calendar credentials" after changing `ENCRYPTION_KEY`

**Solution**:
- This happens because existing encrypted credentials can't be decrypted with the new key
- **Fix**: Go to Admin Panel → **Settings** → **Google Calendar** → Delete existing config and re-upload the JSON file

### Calendar API Rate Limited
**Problem**: "Quota exceeded" or "Too many requests" errors

**Solutions**:
1. **Check quotas** in Google Cloud Console → **APIs & Services** → **Quotas**
2. **Reduce sync frequency**: Adjust app settings to sync less often
3. **Use shared calendar wisely**: Avoid syncing millions of events at once

---

## Telegram Issues

### Bot Not Responding
**Problem**: Telegram bot doesn't respond to messages

**Solutions**:
1. **Invalid token**: Verify `TELEGRAM_TOKEN` is correct (get from BotFather)
   ```bash
   # Check if token is set
   echo $TELEGRAM_TOKEN
   ```
2. **Webhook not set**: If using webhooks instead of polling, verify webhook URL in Telegram:
   ```bash
   curl https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo
   ```
3. **Check logs**:
   ```bash
   docker-compose logs -f app | grep -i telegram
   ```

### Mini App Not Loading
**Problem**: "Mini App" button in Telegram doesn't open or shows error

**Solutions**:
1. **URL not HTTPS**: Telegram requires HTTPS for Mini Apps
2. **Wrong URL**: Check BotFather → Your bot → **Bot Settings** → **Menu Button** → Verify URL
3. **CORS issues**: If Mini App can't access API, check CORS settings in your app

---

## Database Issues

### Connection Refused
**Problem**: "Cannot connect to database" error on startup

**Solutions**:
1. **PostgreSQL not running**: Start database service
   ```bash
   docker-compose up -d db
   ```
2. **Wrong connection string**: Verify `DATABASE_URL` in `.env`
   - Should look like: `postgresql://user:password@localhost:5432/dbname`
3. **Port conflicts**: If port 5432 is taken, change in `docker-compose.yml`
4. **Check logs**:
   ```bash
   docker-compose logs db
   ```

### Migration Errors
**Problem**: "Alembic migration failed" or "Schema mismatch" errors

**Solutions**:
1. **Automatic migration**: Most apps run migrations on startup. Check logs:
   ```bash
   docker-compose logs app | grep -i migration
   ```
2. **Manual migration** (if auto-migration disabled):
   ```bash
   docker-compose exec app alembic upgrade head
   ```
3. **Reset database** (CAUTION - deletes all data):
   ```bash
   docker-compose down -v  # Remove volumes
   docker-compose up -d    # Recreate database
   ```

---

## Environment Variable Issues

### Variable Not Found or Wrong Value
**Problem**: Error saying environment variable is not set or has wrong value

**Solutions**:
1. **Check `.env` file**: Ensure variable is there and no extra spaces:
   ```bash
   grep SLACK_BOT_TOKEN .env
   ```
2. **Reload environment**: Variables only load when container starts
   ```bash
   docker-compose down
   docker-compose up -d
   ```
3. **Check for typos**: Variable names are case-sensitive (`SLACK_TOKEN` ≠ `slack_token`)

### Secrets in Public Code
**Problem**: Accidentally committed tokens or secrets to git

**Solutions**:
1. **Regenerate tokens immediately**: Go to the service (Slack, Google, Telegram) and generate new tokens
2. **Remove from git history**: Use `git filter-branch` or `BFG Repo-Cleaner` to remove sensitive files
3. **Add to `.gitignore`**:
   ```
   .env
   *.key
   service-account-*.json
   ```

---

## Performance Issues

### Slow Response Times
**Problem**: Commands take 10+ seconds to respond

**Solutions**:
1. **Check database performance**: Run slow query logs
2. **Check external API latency**: Google Calendar API, Slack API calls may be slow
3. **Monitor resource usage**:
   ```bash
   docker-compose stats
   ```
4. **Optimize queries**: Check application logs for database query times

### High CPU/Memory Usage
**Problem**: Application uses excessive resources

**Solutions**:
1. **Check for memory leaks**:
   ```bash
   docker-compose top app
   ```
2. **Reduce event subscription**: Too many subscribed events may cause overhead
3. **Restart application**:
   ```bash
   docker-compose restart app
   ```

---

## General Debugging Commands

### View Application Logs
```bash
# All logs
docker-compose logs -f app

# Specific service logs
docker-compose logs -f db
docker-compose logs -f app

# Filter by keyword
docker-compose logs app | grep -i error
```

### Restart Services
```bash
# Restart app
docker-compose restart app

# Restart all
docker-compose restart

# Full rebuild
docker-compose down
docker-compose up -d --build
```

### Check Service Health
```bash
# List running containers
docker-compose ps

# Check specific container
docker-compose exec app ps aux

# Health check
curl http://localhost:8000/health
```

### Test Endpoints
```bash
# Test Slack events endpoint
curl -X POST http://localhost:8000/slack/events \
  -H "Content-Type: application/json" \
  -d '{"type":"url_verification","challenge":"test123"}'

# Test health
curl http://localhost:8000/health
```

---

## Getting Help

If you're still stuck:
1. Check the logs for error messages: `docker-compose logs app`
2. Verify all environment variables are set: `grep -E "SLACK|TELEGRAM|GOOGLE" .env`
3. Try restarting everything: `docker-compose down && docker-compose up -d --build`
4. Check the [SETUP_GUIDE.md](SETUP_GUIDE.md) for service configuration details
5. Open an issue on GitHub with logs and environment variables (excluding secrets)
