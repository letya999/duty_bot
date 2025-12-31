# Development Guide

This guide covers everything you need to know for developing Duty Bot, including setup, running tests, and deployment.

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)
- [Running the Application](#running-the-application)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Database Management](#database-management)
- [Docker Development](#docker-development)
- [Common Development Tasks](#common-development-tasks)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Using Make (Recommended)

The fastest way to get started:

```bash
# Initial setup (one time)
make setup

# Start development servers
make dev

# Run tests
make test

# View available commands
make help
```

### Manual Setup

If you prefer to do things manually:

```bash
# Setup Python environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup Node.js dependencies
cd webapp && npm install && cd ..

# Generate security keys
python scripts/generate_security_keys.py --output .env.security
cat .env.security >> .env

# Start servers
python -m uvicorn app.main:app --reload  # Backend
cd webapp && npm run dev  # Frontend (in another terminal)
```

## Prerequisites

Before you begin, ensure you have:

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **PostgreSQL 13+** - [Download](https://www.postgresql.org/download/) (optional if using Docker)
- **Docker & Docker Compose** - [Download](https://www.docker.com/products/docker-desktop) (optional but recommended)
- **Git** - [Download](https://git-scm.com/)

### Verify Installation

```bash
python3 --version  # Should be 3.11+
node --version     # Should be 18+
npm --version      # Should be 8+
docker --version   # Should be 20.10+
git --version      # Should be 2.25+
```

## Local Development Setup

### Step 1: Clone and Navigate

```bash
git clone https://github.com/letya999/duty_bot.git
cd duty_bot
```

### Step 2: Run Setup Script

The easiest way to set up the entire development environment:

```bash
bash scripts/setup-dev.sh
```

This script will:
- Create a Python virtual environment
- Install Python dependencies
- Install Node.js dependencies
- Generate security keys
- Verify the installation

### Step 3: Configure Environment

Copy the example configuration and fill in your tokens:

```bash
cp .env.example .env
```

Edit `.env` and provide:

```env
# Telegram Bot (from @BotFather)
TELEGRAM_TOKEN=your_telegram_token_here

# Slack Bot (from Slack App settings)
SLACK_BOT_TOKEN=xoxb-your-slack-token
SLACK_SIGNING_SECRET=your-signing-secret

# Database (if not using Docker)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/duty_bot
```

### Step 4: Initialize Database

```bash
# Option 1: Using Make
make db-init

# Option 2: Using Alembic directly
alembic upgrade head
```

## Running the Application

### Development Mode (Both Backend and Frontend)

```bash
# Using Make (recommended)
make dev

# Or manually
# Terminal 1: Backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd webapp && npm run dev -- --host 0.0.0.0
```

**Access:**
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/api/docs
- Frontend (Vite): http://localhost:5173

### Backend Only

```bash
make backend
# or
python -m uvicorn app.main:app --reload
```

### Frontend Only

```bash
make frontend
# or
cd webapp && npm run dev
```

### Production Build

```bash
# Build frontend
cd webapp && npm run build && cd ..

# Run production server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Testing

### Run All Tests

```bash
make test
# or
pytest tests/
```

### Run Specific Test Categories

```bash
# Unit tests only
make test-unit

# Integration tests only
make test-integration

# Tests with coverage report
make test-cov

# Watch mode (auto-run on file changes)
make test-watch

# Skip slow tests
make test-fast
```

### Test Configuration

Test configuration is in `pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
env_files = .env.test
```

Environment variables for tests are in `.env.test`.

### Writing Tests

#### Unit Test Example

```python
# tests/unit/test_example.py
import pytest
from app.services.example_service import ExampleService

@pytest.mark.unit
def test_example_function():
    service = ExampleService()
    result = service.do_something()
    assert result == expected_value
```

#### Integration Test Example

```python
# tests/integration/test_example.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/test")
        assert response.status_code == 200
```

## Code Quality

### Linting

```bash
make lint
# or
flake8 app tests --max-line-length=120
mypy app --ignore-missing-imports
ruff check app tests
```

### Code Formatting

```bash
# Auto-format code
make format

# Check formatting without changes
make format-check
```

**Tools used:**
- **Black** - Code formatter
- **isort** - Import sorter
- **Flake8** - Linter
- **Mypy** - Type checker
- **Ruff** - Fast Python linter

### Pre-commit Hooks (Optional)

Setup automatic formatting before commits:

```bash
pip install pre-commit
pre-commit install
```

## Database Management

### Initialize Database

```bash
make db-init
# or
alembic upgrade head
```

### Create a New Migration

```bash
make db-migrate
# When prompted, enter description (e.g., "Add user_id to duty table")
```

Auto-migration will detect changes in `app/models.py` and create the migration.

### Manual Migration

If auto-migration doesn't work:

```bash
# Create empty migration
alembic revision -m "Add column to users"

# Edit the migration file in migrations/versions/
# Then apply:
alembic upgrade head
```

### Rollback Database

```bash
# Rollback one step
make db-downgrade
# or
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_hash>
```

### Reset Database (⚠️ Destructive)

```bash
make db-reset
# This will delete all data and recreate the schema
```

### Database Shell

```bash
# Using Make
make docker-shell-db

# Manual PostgreSQL connection
psql postgresql://user:password@localhost:5432/duty_bot
```

## Docker Development

### Using Docker Compose (Recommended)

```bash
# Start all services
make docker-up

# View logs
make docker-logs

# Stop services
make docker-down

# View app logs only
make docker-logs-app

# Open shell in container
make docker-shell
```

### Docker Compose Services

**Services defined in `docker-compose.yml`:**

1. **postgres** - PostgreSQL 15
2. **app** - FastAPI backend
3. **webapp** - Vite frontend dev server

### Building Images

```bash
# Build all images
make docker-build

# Build specific service
docker-compose build app
```

### Environment Variables in Docker

- Backend connects to `postgres:5432` (Docker hostname)
- Frontend proxies API to `http://app:8000`
- `.env` file is automatically loaded by docker-compose

### Developing with Docker

```bash
# Start containers
docker-compose up -d

# Access backend
curl http://localhost:8000/health

# Access frontend
open http://localhost:5173

# View live logs
docker-compose logs -f

# Make code changes - files are mounted as volumes
# Changes auto-reload (Python with --reload, React with HMR)

# Stop containers
docker-compose down
```

## Common Development Tasks

### Health Check

```bash
# Quick health check
make health

# Detailed health info
make health-detailed

# Manual API call
curl http://localhost:8000/health/detailed | python -m json.tool
```

### Check Configuration

```bash
make env-check
```

### Clean Up

```bash
# Remove cache, build artifacts, etc.
make clean

# More aggressive - also remove Docker volumes
make docker-clean
```

### Working with Telegram

1. Create a bot with @BotFather on Telegram
2. Copy the token to `.env` as `TELEGRAM_TOKEN`
3. Start the bot: `make dev`
4. Find your chat ID using @userinfobot
5. Set `TELEGRAM_CHAT_ID` in `.env`

### Working with Slack

1. Create a Slack app at https://api.slack.com/apps
2. Configure Slack App:
   - Enable Interactivity with webhook: `https://yourserver.com/slack/events`
   - Add Bot Token Scopes (see docs/SETUP_GUIDE.md)
   - Generate tokens
3. Copy tokens to `.env`:
   - `SLACK_BOT_TOKEN`
   - `SLACK_SIGNING_SECRET`
   - `SLACK_CLIENT_ID` and `SLACK_CLIENT_SECRET`

### Generating Security Keys

```bash
# Auto-generated during setup-dev.sh, but you can regenerate:
python scripts/generate_security_keys.py --output .env.security

# Or manually generate individual keys:
python -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'app'"

Make sure you're in the project root directory when running Python commands.

```bash
cd /path/to/duty_bot
python -m uvicorn app.main:app --reload
```

### "Port 8000 already in use"

```bash
# Find process using port 8000
lsof -i :8000

# Or use different port
python -m uvicorn app.main:app --port 8001
```

### "Database connection refused"

- **Local setup:** Ensure PostgreSQL is running
  ```bash
  # macOS
  brew services start postgresql

  # Linux
  sudo service postgresql start
  ```

- **Docker setup:** Check if postgres container is running
  ```bash
  docker-compose ps
  docker-compose logs postgres
  ```

### "npm ERR! 404 Not Found"

```bash
# Clear npm cache and reinstall
cd webapp
rm package-lock.json node_modules -rf
npm cache clean --force
npm install
```

### Tests Failing

```bash
# Run with verbose output
pytest tests/ -vv

# Run specific test
pytest tests/unit/test_file.py::test_function -v

# Show print statements
pytest tests/ -s

# Stop on first failure
pytest tests/ -x
```

### Docker Container Won't Start

```bash
# Check logs
docker-compose logs app

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

### Permission Denied on setup-dev.sh

```bash
chmod +x scripts/setup-dev.sh
bash scripts/setup-dev.sh
```

## Project Structure

```
duty_bot/
├── app/                      # FastAPI application
│   ├── main.py              # FastAPI app setup
│   ├── config.py            # Configuration and settings
│   ├── database.py          # Database connection
│   ├── models.py            # SQLAlchemy ORM models
│   ├── commands/            # Bot commands
│   ├── handlers/            # Telegram & Slack handlers
│   ├── routes/              # API routes
│   ├── services/            # Business logic
│   ├── repositories/        # Data access layer
│   ├── schemas/             # Pydantic models
│   ├── tasks/               # Scheduled background tasks
│   └── utils/               # Utility functions
├── tests/                    # Test suite
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── conftest.py          # Test fixtures
├── migrations/              # Alembic database migrations
├── scripts/                 # Utility scripts
├── webapp/                  # React frontend
│   ├── src/                 # React components
│   ├── public/              # Static files
│   └── package.json         # NPM dependencies
├── docs/                    # Documentation
├── docker-compose.yml       # Docker services configuration
├── Dockerfile              # Docker build file
├── requirements.txt        # Python dependencies
├── Makefile               # Make targets
└── README.md              # Project readme
```

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [React Documentation](https://react.dev/)
- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## Getting Help

- Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues
- Review [SETUP_GUIDE.md](./SETUP_GUIDE.md) for service configuration
- See [COMMANDS.md](./COMMANDS.md) for bot command reference
