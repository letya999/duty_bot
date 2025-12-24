# Duty Bot - Setup Guide

This guide will help you set up and run Duty Bot locally or in production.

## Prerequisites

- **Python 3.9+** - For backend
- **Node.js 16+** - For frontend (webapp)
- **PostgreSQL 12+** - For database
- **Docker** (optional) - For containerized setup

## Backend Setup

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and update with your values:

```bash
cp .env.example .env
```

**Required variables:**
```env
TELEGRAM_TOKEN=your_bot_token
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your_secret
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/duty_bot
```

**OAuth for web admin panel:**
```env
SLACK_CLIENT_ID=your_client_id
SLACK_CLIENT_SECRET=your_client_secret
SLACK_REDIRECT_URI=http://localhost:8000/web/auth/slack-callback
```

### 3. Initialize Database

```bash
# Create database
createdb duty_bot

# Run migrations (if using alembic)
# alembic upgrade head
```

### 4. Run Backend

```bash
python -m app.main
```

Server will start on `http://localhost:8000`

## Frontend Setup

### 1. Install Dependencies

```bash
cd webapp
npm install
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Update with your values:
```env
VITE_API_URL=http://localhost:8000/api/miniapp
VITE_TELEGRAM_BOT_USERNAME=your_bot_username
```

### 3. Run Development Server

```bash
npm run dev
```

App will start on `http://localhost:5173`

### 4. Build for Production

```bash
npm run build
```

This creates a `dist/` directory with static files.

## Authentication Setup

### Telegram Login Widget

1. **Create a Telegram Bot** (if you don't have one):
   - Open Telegram and chat with `@BotFather`
   - Use `/start` and follow instructions to create a bot
   - Copy your bot token

2. **Set Bot Username**:
   - In `@BotFather`, use `/setusername` to set bot username
   - Update `VITE_TELEGRAM_BOT_USERNAME` in webapp `.env`

3. **Add to Backend Config**:
   ```env
   TELEGRAM_TOKEN=your_bot_token
   ```

### Slack OAuth

1. **Create Slack App**:
   - Go to https://api.slack.com/apps
   - Click "Create New App" → "From scratch"
   - Name: "Duty Bot Admin"
   - Select your workspace

2. **Configure OAuth**:
   - Go to "OAuth & Permissions"
   - Add Redirect URL: `http://localhost:8000/web/auth/slack-callback`
   - Add Scopes:
     - `chat:write`
     - `users:read`
     - `users:read.email`
     - `team:read`

3. **Get Credentials**:
   - Copy Client ID and Client Secret from "Basic Information"
   - Install app to workspace
   - Copy Bot User OAuth Token

4. **Update `.env`**:
   ```env
   SLACK_CLIENT_ID=your_id
   SLACK_CLIENT_SECRET=your_secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_SIGNING_SECRET=your_secret
   SLACK_REDIRECT_URI=http://localhost:8000/web/auth/slack-callback
   ```

## Docker Setup

### Using Docker Compose

```bash
docker-compose up
```

This will:
- Start PostgreSQL database
- Start backend on port 8000
- Start frontend on port 5173

### Manual Docker

```bash
# Build backend image
docker build -t duty-bot-backend .

# Build frontend image
docker build -t duty-bot-webapp ./webapp

# Run containers
docker run -p 8000:8000 duty-bot-backend
docker run -p 5173:5173 duty-bot-webapp
```

## Project Structure

```
duty_bot/
├── app/                    # Backend (FastAPI)
│   ├── main.py            # Main app
│   ├── models.py          # Database models
│   ├── config.py          # Configuration
│   ├── routes/            # API routes
│   ├── services/          # Business logic
│   ├── handlers/          # Telegram/Slack handlers
│   └── web/               # Web admin panel
├── webapp/                 # Frontend (React + Tailwind)
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/        # Pages
│   │   ├── services/     # API client
│   │   └── types/        # TypeScript types
│   └── public/           # Static files
├── requirements.txt       # Python dependencies
└── .env.example          # Environment variables template
```

## Admin Panel URLs

### Local Development
- **Web Admin Panel**: http://localhost:5173
- **Swagger API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Production
- Replace `localhost:8000` with your domain
- Update OAuth redirect URIs in Slack app settings
- Update `SLACK_REDIRECT_URI` in `.env`

## Creating Admin Users

### Via Telegram

1. Start using the bot
2. Get your Telegram user ID from `@userinfobot`
3. Add to `.env`:
   ```env
   ADMIN_TELEGRAM_IDS=your_id
   ```

### Via Slack

1. Start using the bot
2. Get your Slack user ID (format: U123456789)
3. Add to `.env`:
   ```env
   ADMIN_SLACK_IDS=U123456789
   ```

### Via Web Admin Panel

1. Login to web admin panel
2. Go to Settings (admin only)
3. Promote users to admin from the list

## Troubleshooting

### Database Connection Error

```
Error: can't connect to database
```

**Solution:**
- Check PostgreSQL is running
- Verify DATABASE_URL is correct
- Create database: `createdb duty_bot`

### Telegram Login Not Working

- Check `TELEGRAM_TOKEN` is correct (from @BotFather)
- Verify `VITE_TELEGRAM_BOT_USERNAME` matches your bot username
- Check bot username is set in @BotFather (`/setusername`)

### Slack OAuth Error "Invalid redirect_uri"

- Verify `SLACK_REDIRECT_URI` in `.env`
- Check it matches exactly in Slack App Settings
- For localhost, use: `http://localhost:8000/web/auth/slack-callback`

### Port Already in Use

```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Kill process on port 5173
lsof -ti:5173 | xargs kill -9
```

## Testing

### Backend Tests

```bash
pytest
```

### Frontend Tests

```bash
cd webapp
npm test
```

## Development

### Code Style

**Python:**
```bash
# Format code
black app/

# Lint
flake8 app/
```

**TypeScript/React:**
```bash
cd webapp
npm run lint
```

## Production Deployment

### Environment Variables

Update `.env` with production values:
- Set `LOG_LEVEL=WARNING`
- Use production database URL
- Update API URLs to use your domain
- Set secure Slack redirect URI

### Build Frontend

```bash
cd webapp
npm run build
```

Static files will be in `webapp/dist/`

### Run Backend

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app.main:app
```

### Serve Frontend

Use Nginx or Apache to serve files from `webapp/dist/`

## More Information

- [Implementation Plan](./IMPLEMENTATION_PLAN.md)
- [OAuth Setup Guide](./OAUTH_SETUP.md)
- [Architecture](./ARCHITECTURE.md)

## Support

For issues and questions:
1. Check the logs: `docker logs <container-name>`
2. Review configuration in `.env`
3. Check GitHub issues
