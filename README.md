# Duty Bot - IT Team Duty Management

A bot for managing duty schedules and shifts in IT teams. Works simultaneously in Telegram and Slack with identical commands.

## Features

- **Duty Management**: Set and view duty schedules
- **Shift Management**: Manage team shifts
- **Team Management**: Create and manage teams with members
- **Escalation**: Multi-level escalation with automatic escalation
- **Automation**: Daily digest, duty reminders, auto-escalation
- **Telegram Mini App**: Interactive calendar-based schedule viewer for Telegram with responsive UI

## Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Telegram Bot Token (from @BotFather)
- Slack Bot Token and Signing Secret (from Slack App configuration)

### Installation

1. Clone the repository:
```bash
git clone <repo_url>
cd duty_bot
```

2. Create `.env` file (from `.env.example`):
```bash
cp .env.example .env
```

3. Create `.env` file with configuration (see detailed setup section below)

## Detailed Configuration Guide

This section guides you through setting up all required services. Follow the steps in order.

### Step 1: Database Setup

The bot requires PostgreSQL. You can use Docker or install PostgreSQL locally.

#### Option A: Docker PostgreSQL (Recommended)

Docker Compose will handle this automatically. Just ensure Docker is running.

#### Option B: Local PostgreSQL

1. Install PostgreSQL 12+
2. Create database:
```bash
createdb duty_bot
```

3. Get your connection string:
```
postgresql+asyncpg://postgres:yourpassword@localhost:5432/duty_bot
```

Update `DATABASE_URL` in `.env` with your connection string.

---

### Step 2: Telegram Bot Setup

1. **Create Telegram Bot:**
   - Open Telegram and find [@BotFather](https://t.me/botfather)
   - Send `/start` and then `/newbot`
   - Follow the instructions to create a bot
   - BotFather will give you a token: `123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij`

2. **Get Telegram Chat ID (for sending messages to a group):**
   - Add the bot to your chat/group
   - Send any message in that chat
   - Find your chat ID using [@userinfobot](https://t.me/userinfobot) or send to [@getidsbot](https://t.me/getidsbot)
   - Your chat ID will look like: `-1001234567890` (negative for groups)

3. **Set Mini App Button (Optional):**
   - Go back to [@BotFather](https://t.me/botfather)
   - Select your bot with `/mybots`
   - Choose "Menu Button"
   - Set Web App URL (e.g., `https://yourdomain.com/webapp` or `http://localhost:8000/webapp`)

4. **Configure in `.env`:**
```env
# Your bot token from BotFather
TELEGRAM_TOKEN=123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij

# Chat ID where bot sends messages (optional if using only groups/users)
TELEGRAM_CHAT_ID=-1001234567890

# Bot username for Telegram Login Widget (without @)
VITE_TELEGRAM_BOT_USERNAME=your_bot_username
```

5. **Set Admin IDs (Optional):**
   - Get your Telegram ID using [@userinfobot](https://t.me/userinfobot)
   - Add to `.env`:
```env
# Comma-separated Telegram user IDs with admin permissions
ADMIN_TELEGRAM_IDS=123456789,987654321
```

---

### Step 3: Slack Bot Setup (Optional)

If you don't need Slack, you can skip this section.

#### 3.1: Create Slack App

1. Go to [Slack API](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Name your app (e.g., "Duty Bot")
4. Select your Slack Workspace
5. Click "Create App"

#### 3.2: Configure Bot Token Scopes

1. In your Slack App, go to "OAuth & Permissions" (left sidebar)
2. Under "Scopes" → "Bot Token Scopes", add:
   - `chat:write` - Send messages
   - `users:read` - Read user info
   - `commands` - Use slash commands
   - `app_mentions:read` - Read app mentions

3. Under "Scopes" → "User Token Scopes", add:
   - `identify` - For authentication

#### 3.3: Install App to Workspace

1. Go to "Basic Information" tab
2. Click "Install to Workspace"
3. Authorize the app

#### 3.4: Get Credentials

1. Go to "OAuth & Permissions"
2. Copy:
   - **Bot User OAuth Token** (starts with `xoxb-`): `SLACK_BOT_TOKEN`
   - **Signing Secret** (Basic Information tab): `SLACK_SIGNING_SECRET`

3. Find your **Channel ID**:
   - Open your Slack workspace
   - Right-click a channel → "View channel details"
   - Copy Channel ID (starts with `C`)

4. For admin permissions, get Slack User IDs:
   - Right-click a user → "View profile"
   - Copy User ID (starts with `U`)

#### 3.5: Configure Event Subscriptions

1. Go to "Event Subscriptions" (left sidebar)
2. Enable Events
3. Set Request URL to: `https://yourdomain.com/slack/events` (replace with your domain)
   - For local development, use ngrok: `https://abcd1234.ngrok.io/slack/events`
4. Under "Subscribe to bot events", add:
   - `message.channels`
   - `message.im`
   - `app_mention`

5. Click "Save Changes"

#### 3.6: Configure in `.env`

```env
# Slack Bot Credentials
SLACK_BOT_TOKEN=xoxb-your-bot-token-here

# Signing Secret for verifying Slack webhooks
SLACK_SIGNING_SECRET=your-signing-secret-here

# Channel ID where bot sends messages
SLACK_CHANNEL_ID=C123456789

# OAuth credentials for admin panel login (optional)
SLACK_CLIENT_ID=your-client-id-here
SLACK_CLIENT_SECRET=your-client-secret-here

# OAuth redirect URI
# For local dev: http://localhost:8000/web/auth/slack-callback
# For production: https://yourdomain.com/web/auth/slack-callback
SLACK_REDIRECT_URI=http://localhost:8000/web/auth/slack-callback

# Admin Slack user IDs with permissions
ADMIN_SLACK_IDS=U123456789,U987654321
```

---

### Step 4: Google Calendar Integration (Optional)

If you don't need Google Calendar sync, you can skip this section.

#### 4.1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project:
   - Click project dropdown at top
   - Click "New Project"
   - Name it (e.g., "Duty Bot Calendar")
   - Click "Create"

#### 4.2: Enable Google Calendar API

1. In the project, go to "APIs & Services" → "Library"
2. Search for "Google Calendar API"
3. Click on it and press "Enable"

#### 4.3: Create Service Account

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "Service Account"
3. Fill in the form:
   - Service account name: "duty-bot"
   - Click "Create and Continue"
4. Grant roles:
   - Select role: "Editor"
   - Click "Continue"
5. Click "Create Key":
   - Format: JSON
   - Click "Create"
   - A JSON file will download

6. Save this JSON file securely - you'll need its contents for `.env`

#### 4.4: Configure Service Account

1. Open the downloaded JSON file
2. Copy the entire JSON content
3. Add to `.env`:

```env
# Google Calendar Integration
# Paste the entire service account JSON here as a single line
# Or for readability, you can format it with escaped newlines
GOOGLE_SERVICE_ACCOUNT_KEY='{"type":"service_account","project_id":"your-project-id","private_key_id":"key-id","private_key":"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n","client_email":"duty-bot@project.iam.gserviceaccount.com","client_id":"123456789","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs"}'
```

#### 4.5: Enable Google Calendar Integration in the App

Once the bot is running:
1. Go to Admin Panel (http://localhost:8000 or your domain)
2. Navigate to Settings → Google Calendar
3. Upload your service account JSON key
4. The integration will automatically:
   - Create a new Google Calendar
   - Make it publicly accessible
   - Share the calendar URL
   - Start syncing duty schedules

**Note:** Google Calendar sync happens automatically every 4 hours. You can also manually sync from the Admin Panel.

---

### Step 5: Application Settings

Configure these environment variables for your deployment:

```env
# === DATABASE ===
# PostgreSQL connection string
# Docker: postgresql+asyncpg://user:password@postgres:5432/duty_bot
# Local: postgresql+asyncpg://user:password@localhost:5432/duty_bot
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/duty_bot

# === TIMEZONE & SCHEDULING ===
# Timezone for all scheduled tasks (use IANA timezone names)
# Examples: UTC, Europe/Moscow, US/Eastern, Europe/London
TIMEZONE=UTC

# Time to send morning duty digest (24-hour format HH:MM)
MORNING_DIGEST_TIME=09:00

# Minutes before scheduled event to send reminder
REMINDER_BEFORE_MINUTES=30

# Minutes before auto-escalation to level 2
ESCALATION_TIMEOUT_MINUTES=15

# === SERVER ===
# Server host (0.0.0.0 to listen on all interfaces)
HOST=0.0.0.0

# Server port
PORT=8000

# === LOGGING ===
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# === ENCRYPTION ===
# Secret key for encrypting Google service account keys
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
ENCRYPTION_KEY=your-random-secret-key-here-min-32-chars

# === FRONTEND ===
# API base URL for frontend
# Local: http://localhost:8000/api/admin
# Production: https://yourdomain.com/api/admin
VITE_API_URL=http://localhost:8000/api/admin

# Backend API URL (used by Docker services)
VITE_API_BACKEND=http://app:8000
```

---

### Step 6: Create `.env` File

Create a `.env` file in the project root with all the configurations from steps 1-5:

```bash
# Complete .env file example
cp .env.example .env
# Then edit .env with your values:
nano .env  # or use your preferred editor
```

The `.env` file should contain:
- Database URL
- Telegram token and chat ID
- Slack credentials (if using Slack)
- Google service account key (if using Google Calendar)
- Timezone and scheduling settings
- Server configuration
- Encryption key

---

### Running with Docker

```bash
docker-compose up -d
```

The bot will automatically:
- Create database tables
- Start Telegram bot (if token provided)
- Start Slack bot (if tokens provided)
- Setup scheduled tasks:
  - Daily digest at configured time
  - Escalation checks every minute
  - Google Calendar sync every 4 hours
  - Monthly statistics recalculation
- Start admin web panel
- Start Telegram mini app

#### Verify the Bot is Running

```bash
# Check all services are healthy
docker-compose ps

# View logs
docker-compose logs -f app

# Check scheduler status
curl http://localhost:8000/test/scheduler-status
```

#### First Steps After Startup

1. **Access Admin Panel:**
   - Go to http://localhost:8000
   - Set up teams and members
   - Configure workspace settings

2. **Test Telegram Bot:**
   - Add bot to your Telegram chat
   - Send `/duty` to see current duties
   - Send `/help` to see all available commands

3. **Test Slack Bot (if configured):**
   - Add bot to your Slack workspace
   - Mention the bot in a channel
   - Send commands like `/duty` or `/team list`

4. **Setup Google Calendar (Optional):**
   - Go to Admin Panel → Settings → Google Calendar
   - Upload your service account JSON key
   - The integration will create a calendar and start syncing
   - Manual sync: Admin Panel → Settings → Google Calendar → Sync button
   - Automatic sync: Every 4 hours

5. **Verify Scheduled Tasks:**
   - Morning digest will send at configured time
   - Check logs for any errors:
   ```bash
   docker-compose logs app | grep -i "digest\|sync\|escalation"
   ```

### Manual Setup (without Docker)

If you prefer to run without Docker, follow these steps:

#### 1. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# If using the webapp, install Node dependencies
cd webapp
npm install
cd ..
```

#### 2. Setup PostgreSQL

```bash
# Create database
createdb duty_bot

# Or with user/password
createdb -U postgres duty_bot
```

#### 3. Run Database Migrations

```bash
# Copy the database URL from your .env
# Migrations will run automatically on app startup
# Or manually with Alembic (if configured):
# alembic upgrade head
```

#### 4. Start the Application

```bash
# In the project root directory
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The application will:
- Connect to PostgreSQL using `DATABASE_URL` from `.env`
- Create database tables automatically
- Initialize all scheduled tasks
- Start listening on port 8000

#### 5. Start the Webapp (Optional)

In a separate terminal:

```bash
cd webapp
npm run dev
```

The webapp will be available at `http://localhost:5173` in development mode.

For production build:

```bash
cd webapp
npm run build
# The build output will be in webapp/dist
# Copy to app/webapp directory to be served by FastAPI
```

---

## Environment Variables Reference

Here's a complete list of all environment variables:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `TELEGRAM_TOKEN` | Yes (if using Telegram) | Bot token from BotFather | `123456:ABC...` |
| `TELEGRAM_CHAT_ID` | No | Chat ID for sending messages | `-1001234567890` |
| `SLACK_BOT_TOKEN` | Yes (if using Slack) | Slack bot token | `xoxb-...` |
| `SLACK_SIGNING_SECRET` | Yes (if using Slack) | Slack signing secret | `abc123...` |
| `SLACK_CHANNEL_ID` | Yes (if using Slack) | Channel ID for messages | `C123456789` |
| `SLACK_CLIENT_ID` | No | For Slack OAuth login | `123456789.123...` |
| `SLACK_CLIENT_SECRET` | No | For Slack OAuth login | `xoxp-...` |
| `SLACK_REDIRECT_URI` | No | OAuth callback URL | `http://localhost:8000/web/auth/slack-callback` |
| `DATABASE_URL` | Yes | PostgreSQL connection | `postgresql+asyncpg://user:pass@localhost/duty_bot` |
| `TIMEZONE` | No | Timezone for tasks | `UTC`, `Europe/Moscow` |
| `MORNING_DIGEST_TIME` | No | Digest time (24h) | `09:00` |
| `REMINDER_BEFORE_MINUTES` | No | Reminder minutes before | `30` |
| `ESCALATION_TIMEOUT_MINUTES` | No | Auto-escalation timeout | `15` |
| `HOST` | No | Server host | `0.0.0.0` |
| `PORT` | No | Server port | `8000` |
| `LOG_LEVEL` | No | Logging level | `INFO`, `DEBUG` |
| `ENCRYPTION_KEY` | Yes | For encrypting secrets | 32+ character random string |
| `ADMIN_TELEGRAM_IDS` | No | Admin Telegram IDs | `123,456,789` |
| `ADMIN_SLACK_IDS` | No | Admin Slack IDs | `U123,U456` |
| `VITE_API_URL` | No | Frontend API URL | `http://localhost:8000/api/admin` |
| `VITE_API_BACKEND` | No | Docker backend URL | `http://app:8000` |
| `VITE_TELEGRAM_BOT_USERNAME` | No | Bot username for mini app | `your_bot_name` |

---

## Networking & Deployment

### Local Development

For local development with all services:

```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Or manually in separate terminals:
# Terminal 1: PostgreSQL
docker run --name postgres -e POSTGRES_PASSWORD=password -p 5432:5432 postgres:15

# Terminal 2: Application
python -m uvicorn app.main:app --reload

# Terminal 3: Frontend
cd webapp && npm run dev
```

### Production Deployment

For production deployment:

1. **Use environment-specific `.env` file:**
   ```bash
   cp .env.example .env.production
   # Edit .env.production with production values
   ```

2. **Use a proper reverse proxy (nginx, Caddy):**
   ```bash
   # Example nginx config (simplified)
   server {
       listen 80;
       server_name yourdomain.com;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

3. **For Slack webhook:**
   - Set `SLACK_REDIRECT_URI` to your production domain
   - Update Event Subscriptions Request URL to production URL
   - Example: `https://yourdomain.com/slack/events`

4. **For Google Calendar:**
   - Service account works globally, no special setup needed
   - Make sure `ENCRYPTION_KEY` is set securely

5. **For Telegram Mini App:**
   - Set Menu Button URL in BotFather to your production domain
   - Example: `https://yourdomain.com/webapp`

---

## Commands

### Duty
- `/duty` - Show all on-duty today
- `/duty <team>` - Mention team's duty person/shift

### Team Management
- `/team list` - List all teams
- `/team <name>` - Show team info
- `/team add <name> "<display_name>"` - Create team
- `/team add <name> "<display_name>" --shifts` - Create with shifts
- `/team edit <name> --name <new_name>` - Rename team
- `/team edit <name> --display "<new_name>"` - Change display name
- `/team edit <name> --shifts` - Enable shifts
- `/team edit <name> --no-shifts` - Disable shifts
- `/team lead <team> @user` - Set team lead
- `/team add-member <team> @user` - Add member
- `/team remove-member <team> @user` - Remove member
- `/team move @user <from_team> <to_team>` - Move member
- `/team delete <team>` - Delete team

### Scheduling (without shifts)
- `/schedule <team>` - Show current week
- `/schedule <team> next` - Show next week
- `/schedule <team> <month>` - Show month
- `/schedule <team> set <date> @user` - Set duty
- `/schedule <team> set <date>-<date> @user` - Set range
- `/schedule <team> clear <date>` - Clear duty
- `/schedule <team> clear <date>-<date>` - Clear range

### Shifts (with shifts)
- `/shift <team>` - Show current week
- `/shift <team> next` - Show next week
- `/shift <team> <month>` - Show month
- `/shift <team> set <date> @user1 @user2 ...` - Set shift
- `/shift <team> set <date>-<date> @user1 @user2 ...` - Set range
- `/shift <team> add <date> @user` - Add to shift
- `/shift <team> remove <date> @user` - Remove from shift
- `/shift <team> clear <date>` - Clear shift
- `/shift <team> clear <date>-<date>` - Clear range

### Escalation
- `/escalation` - Show escalation settings
- `/escalation cto @user` - Set CTO
- `/escalate <team>` - Escalate to team lead
- `/escalate level2` - Escalate to CTO
- `/escalate ack` - Acknowledge escalation

## Date Format

- `DD.MM` - Current or next year if date passed
- `DD.MM.YYYY` - Specific year
- Month name (Russian or English) - First day of month
- `DD.MM-DD.MM` - Date range

## Configuration

All configuration is done via environment variables:

- `TELEGRAM_TOKEN` - Telegram bot token
- `SLACK_BOT_TOKEN` - Slack bot token
- `SLACK_SIGNING_SECRET` - Slack signing secret
- `DATABASE_URL` - PostgreSQL connection string
- `TIMEZONE` - Timezone for scheduling (default: UTC)
- `MORNING_DIGEST_TIME` - Time for daily digest (HH:MM format, default: 09:00)
- `REMINDER_BEFORE_MINUTES` - Minutes before digest to send reminders (default: 30)
- `ESCALATION_TIMEOUT_MINUTES` - Minutes before auto-escalation (default: 15)
- `LOG_LEVEL` - Logging level (default: INFO)
- `HOST` - Server host (default: 0.0.0.0)
- `PORT` - Server port (default: 8000)

## Telegram Mini App

The Duty Bot includes a modern Telegram Mini App for convenient schedule management with an interactive calendar interface.

### Features

- 📅 **Interactive Calendar** - Visual month view showing all duty assignments
- 👥 **Team Management** - Browse teams and assign duties
- 📱 **Mobile Optimized** - Fully responsive design for all devices
- 🎨 **Theme Support** - Automatically matches your Telegram theme
- ⚡ **Fast** - Built with React and Vite for optimal performance

### Setup Mini App

1. The mini app is located in the `webapp/` directory
2. Environment variables are in `webapp/.env` (copy from `webapp/.env.example`)
3. Development: `cd webapp && npm install && npm run dev`
4. Production: Use Docker Compose to run all services together

### Using the Mini App

The mini app is available when the bot sends a keyboard button with the mini app action. Users can:
- View the entire month's schedule in a calendar
- Click any day to see who's on duty
- Assign duties to team members for specific dates
- View team member profiles

### API Endpoints

The mini app uses these API endpoints (all require valid Telegram authentication):

- `GET /api/miniapp/user/info` - Get current user information
- `GET /api/miniapp/schedule/month?year=2024&month=12` - Get monthly schedule
- `GET /api/miniapp/schedule/day/{date}` - Get daily schedule
- `POST /api/miniapp/schedule/assign` - Assign duty to user
- `DELETE /api/miniapp/schedule/{schedule_id}` - Remove duty assignment
- `GET /api/miniapp/teams` - List all teams
- `GET /api/miniapp/teams/{team_id}/members` - Get team members

For more details, see [webapp/README.md](webapp/README.md)

## Development

### Project Structure

```
duty_bot/
├── app/                     # Backend application
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── database.py          # Database setup
│   ├── models.py            # SQLAlchemy models
│   ├── handlers/            # Telegram and Slack handlers
│   │   ├── telegram_handler.py
│   │   └── slack_handler.py
│   ├── routes/              # API routes
│   │   └── miniapp.py       # Mini app API endpoints
│   ├── services/            # Business logic
│   │   ├── user_service.py
│   │   ├── team_service.py
│   │   ├── schedule_service.py
│   │   ├── shift_service.py
│   │   └── escalation_service.py
│   ├── commands/            # Command parsing and handling
│   │   ├── parser.py
│   │   └── handlers.py
│   └── tasks/               # Scheduled tasks
│       └── scheduled_tasks.py
├── webapp/                  # Telegram Mini App (React + TypeScript)
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── hooks/           # Custom React hooks
│   │   ├── services/        # API client
│   │   ├── types/           # TypeScript types
│   │   ├── styles/          # Global styles
│   │   ├── App.tsx          # Main app component
│   │   └── main.tsx         # Entry point
│   ├── package.json         # Node.js dependencies
│   ├── vite.config.ts       # Vite configuration
│   ├── Dockerfile           # Docker image for mini app
│   └── README.md            # Mini app documentation
├── migrations/              # Database migrations
├── docker-compose.yml       # Docker Compose setup
├── Dockerfile               # Docker image for backend
├── requirements.txt         # Python dependencies
└── .env.example             # Example environment file
```

### Database Schema

- `user` - Telegram/Slack users
- `team` - Teams configuration
- `team_members` - Many-to-many team members
- `schedule` - Duty schedules
- `shift` - Shift schedules
- `shift_members` - Many-to-many shift members
- `escalation` - Escalation configuration
- `escalation_event` - Escalation events history

## Scheduled Jobs

The application runs several automated jobs:

### 1. Morning Digest (Daily)
- **Schedule:** Daily at `MORNING_DIGEST_TIME` (default: 09:00)
- **What it does:** Sends current day's duty assignments to all configured workspaces
- **Configure:** Set `MORNING_DIGEST_TIME=HH:MM` in `.env`
- **Test:** `POST /test/morning-digest`

### 2. Escalation Checks (Every Minute)
- **Schedule:** Every 1 minute
- **What it does:** Automatically escalates unresolved incidents to level 2 after timeout
- **Configure:** Set `ESCALATION_TIMEOUT_MINUTES` in `.env`
- **Test:** `POST /test/check-escalations`

### 3. Google Calendar Sync (Every 4 Hours)
- **Schedule:** Every 4 hours
- **What it does:** Automatically syncs all duty schedules to Google Calendar
- **Configure:** Set up Google Calendar in Admin Panel
- **Note:** Syncs 1 day back to 90 days forward
- **Test:** `POST /test/sync-google-calendars`
- **Manual trigger:** Admin Panel → Settings → Google Calendar → Sync button

### 4. Monthly Statistics (Monthly)
- **Schedule:** 1st of each month at 01:00
- **What it does:** Recalculates duty and shift statistics for the previous month
- **Configure:** Automatic, no configuration needed

### View All Scheduled Jobs

```bash
# Get status of all jobs
curl http://localhost:8000/test/scheduler-status

# Response example:
# {
#   "status": "ok",
#   "scheduler_running": true,
#   "jobs_count": 4,
#   "jobs": [
#     {
#       "id": "morning_digest",
#       "name": "Morning duty digest",
#       "next_run_time": "2024-01-15 09:00:00+00:00",
#       "trigger": "cron[hour='9', minute='0']"
#     },
#     ...
#   ]
# }
```

---

## Troubleshooting

### Database Connection Error

```
Error: could not connect to server
```

**Solutions:**
- Verify PostgreSQL is running: `docker ps` or `psql --version`
- Check `DATABASE_URL` in `.env` is correct
- Ensure database exists: `createdb duty_bot`
- For Docker: ensure PostgreSQL service is in `docker-compose.ps`

```bash
# Test connection
psql postgresql://user:password@localhost:5432/duty_bot
```

### Telegram Bot Not Responding

**Solutions:**
- Verify `TELEGRAM_TOKEN` is correct in `.env`
- Check bot was created with BotFather
- Ensure bot is added to your chat
- Check logs: `docker logs duty_bot_app | grep -i telegram`
- Try test endpoint: `POST /test/morning-digest`

### Slack Bot Not Working

**Solutions:**
- Verify `SLACK_BOT_TOKEN` and `SLACK_SIGNING_SECRET` in `.env`
- Check Event Subscriptions URL is publicly accessible
- For local dev, use ngrok: `ngrok http 8000`
- Update Event URL to: `https://YOUR_NGROK_URL.ngrok.io/slack/events`
- Check logs: `docker logs duty_bot_app | grep -i slack`
- Verify bot is installed in workspace and has correct scopes

### Google Calendar Not Syncing

**Solutions:**
- Check `ENCRYPTION_KEY` is set in `.env`
- Verify service account JSON is valid
- Ensure Google Calendar API is enabled in Google Cloud
- Check logs: `docker logs duty_bot_app | grep -i calendar`
- Manual sync: Admin Panel → Settings → Google Calendar → Sync button
- Test sync: `POST /test/sync-google-calendars`

### Scheduled Tasks Not Running

```bash
# Check scheduler status
curl http://localhost:8000/test/scheduler-status

# View logs
docker logs duty_bot_app | grep -i "scheduled\|digest\|sync"

# Restart app
docker-compose restart app
```

### Commands Not Working

**Solutions:**
- Verify team names are correct
- Check user mentions are in proper format: `@username`
- Ensure bot has permissions in the chat
- Review logs: `docker logs duty_bot_app`
- Test with `/help` command first

### Port Already in Use

```bash
# Port 8000 is already in use
# Change port in .env:
PORT=8001

# Then restart
docker-compose restart app
```

### Memory or Resource Issues

```bash
# Check container resource usage
docker stats duty_bot_app

# Increase Docker memory limit
# Edit docker-compose.yml:
services:
  app:
    deploy:
      resources:
        limits:
          memory: 1G
```

### Viewing Detailed Logs

```bash
# Real-time logs
docker-compose logs -f app

# Last 50 lines
docker logs --tail 50 duty_bot_app

# Search for errors
docker logs duty_bot_app | grep ERROR

# With timestamp
docker logs --timestamps duty_bot_app
```

---

## Support & Contributing

For issues and feature requests, please open a GitHub issue with:
1. Description of the problem
2. Relevant logs (sanitized)
3. Steps to reproduce
4. Your configuration (without sensitive tokens)

## License

MIT
