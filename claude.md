# Duty Bot - IT Team Duty Management System

## Project Overview

A comprehensive multi-platform duty management system for IT teams. Provides identical functionality across **Telegram** and **Slack** with role-based scheduling, escalation workflows, automated reminders, Google Calendar integration, and a web-based admin dashboard.

**Architecture**: Async-first FastAPI backend with PostgreSQL, supporting multiple isolated workspaces (per Telegram chat or Slack workspace) that can be grouped into organizations for shared resource management.

## Key Features

- **Multi-Platform**: Telegram and Slack with identical commands and seamless synchronization
- **Flexible Scheduling**:
  - Simple duty assignments for teams without shifts
  - Complex shift management with multiple people per date
- **Escalation System**: Multi-level escalation (Team Lead → CTO) with automatic escalation after configurable timeout
- **Automation**: Daily morning digest, duty reminders, auto-escalation checks, Google Calendar sync (every 4 hours)
- **Admin Panel**: Web-based dashboard with authentication, team management, schedule editing, and reporting
- **Telegram Mini App**: Calendar interface for convenient duty viewing in Telegram
- **Multi-Organization Support**: Group multiple workspaces with shared user and team management
- **Performance Metrics**: Automatic monthly stats calculation and duty history tracking

## Tech Stack

**Backend**:
- Python 3.11+ with async/await throughout
- FastAPI (async web framework with automatic OpenAPI docs)
- SQLAlchemy 2.0 with asyncpg for PostgreSQL

**Messaging & Integrations**:
- python-telegram-bot (webhook-based)
- slack-bolt (async SDK)
- Google Calendar API (via service accounts)

**Infrastructure**:
- PostgreSQL (with async connection pooling)
- APScheduler (timezone-aware scheduled tasks)
- Docker Compose (3-service orchestration: PostgreSQL, FastAPI app, React webapp)

**Frontend**:
- React + Vite (separate npm project in `webapp/`)

**Security & Middleware**:
- Pydantic for data validation
- Custom security headers (CSP, HSTS, X-Frame-Options)
- CSRF token protection on state-changing requests
- Rate limiting (slowapi)
- Session-based authentication with persistent storage

## Database Models (13 ORM Entities)

**Core Entities**:
- **User**: Multi-provider support (Telegram username, Slack ID)
- **UserAccount**: Provider-specific credentials (Telegram/Slack)
- **Team**: Team metadata with shift mode flag
- **TeamMember**: Many-to-many user-team association
- **TeamLead**: Team leadership assignment

**Workspace & Organization**:
- **Workspace**: Isolated instance (Telegram chat or Slack workspace)
- **ChatChannel**: Specific channel within workspace
- **Organization**: Groups multiple workspaces for shared resources

**Scheduling**:
- **Schedule**: Duty assignments (single user per date for non-shift teams)
- **RotationConfig**: Duty rotation settings for teams
- **ShiftHistory**: Tracks shift completions and performance metrics

**Escalation & Automation**:
- **Escalation**: Escalation level configuration per workspace
- **EscalationEvent**: Tracks active escalations and automatic level transitions

## Architecture & Patterns

### Layered Architecture
```
Handlers (Telegram/Slack)
  → Command Handler (unified command dispatch)
  → Service Layer (business logic, validation)
  → Repository Layer (data access with generic CRUD base)
  → SQLAlchemy Models (PostgreSQL ORM)
```

### Key Design Patterns

1. **Repository Pattern**: Generic `BaseRepository[ModelT]` with standard CRUD, specialized repos extend with domain-specific queries
2. **Service Pattern**: Business logic with injected repositories, maintains data integrity and constraints
3. **Dependency Injection**: FastAPI's `Depends()` for database sessions, repositories, and authenticated users
4. **Handler Abstraction**: Platform-specific handlers (TelegramHandler, SlackHandler) call platform-agnostic CommandHandler
5. **Multi-Workspace Isolation**: Each Telegram chat/Slack workspace is completely isolated; queries always filter by `workspace_id`
6. **Organization Constraint**: 1 user per team within an organization (enforced in service layer)
7. **Async-First Design**: All database operations, services, and handlers are async
8. **Lifespan Management**: Proper startup/shutdown of external services (bot handlers, scheduler) via FastAPI lifespan context manager

## Project Structure

```
duty_bot/
├── app/                              # Main FastAPI application
│   ├── main.py                       # FastAPI app entry point, lifespan, route setup
│   ├── database.py                   # SQLAlchemy async setup, migrations loader
│   ├── models.py                     # All 13 SQLAlchemy ORM models
│   ├── exceptions.py                 # Custom exception hierarchy with error codes
│   ├── dependencies.py               # Dependency injection setup (get_db, get_current_user, etc.)
│   ├── config/
│   │   ├── settings.py               # Pydantic settings from .env with validators
│   │   └── openapi.py                # OpenAPI schema customization
│   ├── handlers/                     # Platform handlers
│   │   ├── telegram_handler.py       # python-telegram-bot integration
│   │   └── slack_handler.py          # slack-bolt integration
│   ├── services/                     # Business logic layer (14+ service files)
│   │   ├── user_service.py           # User CRUD with multi-provider support
│   │   ├── team_service.py           # Team management, member assignment
│   │   ├── schedule_service.py       # Duty assignment logic
│   │   ├── escalation_service.py     # Escalation workflows
│   │   ├── google_calendar_service.py
│   │   ├── stats_service.py          # Performance metrics calculation
│   │   └── [more services]
│   ├── repositories/                 # Data access layer (15+ repository files)
│   │   ├── base_repository.py        # Generic CRUD operations
│   │   ├── user_repository.py        # User queries with provider lookups
│   │   ├── schedule_repository.py    # Date-range and team schedule queries
│   │   ├── team_repository.py        # Team queries with eager loading
│   │   └── [more repositories]
│   ├── commands/                     # Command parsing and dispatch
│   │   ├── handlers.py               # CommandHandler with all bot commands
│   │   └── parser.py                 # DateParser, CommandParser utilities
│   ├── routes/admin/                 # Web admin panel and API routes
│   │   ├── auth.py, auth_api.py      # Authentication and OAuth flows
│   │   ├── dashboard.py              # Main admin dashboard
│   │   ├── schedules.py              # Schedule management endpoints
│   │   ├── reports.py                # Reporting and stats endpoints
│   │   ├── settings.py               # Workspace settings management
│   │   ├── incidents.py              # Incident/escalation management
│   │   └── api.py                    # Public API endpoints
│   ├── auth/                         # Authentication layer
│   │   ├── session_persistent.py     # Persistent session storage
│   │   ├── oauth.py                  # OAuth flows (Telegram, Slack)
│   │   └── session.py                # Session management utilities
│   ├── middleware/                   # HTTP middleware
│   │   ├── security_headers.py       # CSP, HSTS, X-Frame-Options headers
│   │   ├── csrf_protection.py        # CSRF token validation
│   │   └── rate_limiter.py           # Request rate limiting (slowapi)
│   ├── tasks/
│   │   └── scheduled_tasks.py        # APScheduler job definitions (cron & interval)
│   ├── utils/                        # Utility functions
│   │   ├── retry.py                  # Retry decorators with exponential backoff
│   │   ├── encryption.py             # Encryption utilities for sensitive data
│   │   ├── validators.py             # Custom validators
│   │   └── auth.py                   # Auth utilities
│   └── schemas/                      # Pydantic request/response models
├── tests/                            # Comprehensive test suite
│   ├── conftest.py                   # Pytest fixtures, in-memory SQLite setup
│   ├── commands/, handlers/, services/, repositories/, models/, utils/
│   └── fixtures/                     # Test data factories
├── migrations/                       # SQL migration files (auto-loaded on startup)
├── webapp/                           # React + Vite frontend (separate npm project)
├── scripts/                          # Helper scripts (generate_security_keys.py, etc.)
├── docs/                             # Documentation
│   ├── COMMANDS.md                   # Complete command reference
│   ├── SETUP_GUIDE.md                # Integration setup (Google Calendar, OAuth)
│   └── TROUBLESHOOTING.md            # Common issues and solutions
├── docker-compose.yml                # 3-service orchestration
├── Dockerfile                        # App container definition
├── requirements.txt                  # Python dependencies
├── pytest.ini                        # Pytest configuration
└── .env.example                      # Environment variable template
```

## Development Rules & Conventions

### Naming Conventions

**Files & Modules**:
- Repositories: `{model_name}_repository.py`
- Services: `{domain}_service.py`
- Handlers: `{platform}_handler.py`

**Classes**:
- Repositories: `{Model}Repository` (e.g., `UserRepository`)
- Services: `{Domain}Service` (e.g., `TeamService`)
- Models: PascalCase
- Enums: `{Entity}Enum`

**Database**:
- Tables: snake_case (e.g., `team_members`, `chat_channel`)
- Columns: snake_case (e.g., `user_id`, `created_at`)
- Unique constraints: `{table}_{column}_unique`

**Functions**: snake_case, private methods prefixed with `_`

### Code Organization

**Services**:
- Dependency injection via constructor: `def __init__(self, repo: Repository)`
- Business logic and validation
- Multiple services can collaborate (e.g., TeamService uses UserService)

**Repositories**:
- Extend `BaseRepository[ModelT]` for standard CRUD (`get_by_id`, `list_all`, `create`, `update`, `delete`)
- Custom methods for complex queries using SQLAlchemy's `select()`, `joinedload()`, `selectinload()`
- All async: `async def query_method(...) -> Model`

**Handlers**:
- Platform-specific setup and webhook handling
- Delegate business logic to CommandHandler (platform-agnostic)
- Workspace auto-creation on first message

### Error Handling

**Custom Exception Hierarchy** (`app/exceptions.py`):
```
ApplicationException (base, 500)
  ├── ValidationError (400)
  ├── AuthenticationError (401)
  ├── AuthorizationError (403)
  ├── NotFoundError (404)
  ├── ConflictError (409)
  └── CommandError (400)
```

All exceptions include:
- `message`: Human-readable error message
- `status_code`: HTTP status code
- `error_code`: Machine-readable identifier (e.g., "VALIDATION_ERROR")
- `details`: Optional dict with additional context

### Type Hints

- Strict typing throughout: `str | None`, `List[User]`
- Generic types: `BaseRepository[ModelT]`
- Async methods: `async def method(...) -> ReturnType`

### Async/Await

- All database operations: explicit `await`
- All service calls: `async def` and `await`
- Database session management: `async with get_db() as db:`
- Retry logic for connection errors: `retry_on_connection_error()` decorator with exponential backoff

### Logging

- Structured logging with Python `logging` module
- Each module: `logger = logging.getLogger(__name__)`
- Request logging middleware logs all HTTP requests/responses
- Migration and startup/shutdown events logged to INFO level

## Critical Project Rules

### 1. Workspace Isolation

- **Every query must filter by `workspace_id`** - This is non-negotiable for data privacy
- Each Telegram chat and Slack workspace is completely isolated
- Data should never leak between workspaces
- Workspace auto-creation on first message (platform-specific handler responsibility)

### 2. User-Team Constraints

- **One user per team within an organization** - Enforced in `TeamService.add_member()`
- Users can belong to multiple workspaces
- Users can have multiple provider accounts (Telegram + Slack) as `UserAccount` entities

### 3. Schedule vs. Shift Modes

- Non-shift teams: **1 user per date** (update existing or create new)
- Shift teams: **Multiple users per date** (insert new records, keep all)
- Enforce via `Team.has_shifts` flag
- Both stored in same `Schedule` table with `is_shift` boolean flag

### 4. Database Constraints

- **Unique constraints** strictly enforced:
  - Team name: `(workspace_id, name)`
  - Schedule: `(team_id, user_id, date)` for shifts; non-shift teams have 1 per date
  - User provider: `(provider_id, workspace_id)`
  - Team member: No duplicate members
- **Cascading deletes** on foreign keys (team deletion cascades to schedules, escalations)

### 5. Authentication & Master Admins

- Master admins (in `ADMIN_TELEGRAM_IDS`, `ADMIN_SLACK_IDS`) are **always** admin in any workspace
- Checked in `get_current_user()` dependency - auto-promotes master admins
- Session-based auth with persistent token storage
- Bearer token from Authorization header OR `session_token` cookie

### 6. Command Date Parsing

Supported formats (platform-agnostic in `commands/parser.py`):
- `DD.MM` - inferred year (current or next if in past)
- `DD.MM.YYYY` - explicit year
- Month names: English & Russian, full & abbreviated
- Ranges: `DD.MM-DD.MM`
- Keywords: "next", month names

### 7. Security Middleware

- **CSRF Protection**: Validate tokens on state-changing requests (POST, PUT, DELETE, PATCH)
- **Security Headers**: CSP, HSTS, X-Frame-Options, X-Content-Type-Options
- **Rate Limiting**: slowapi integration on endpoints
- No plain-text sensitive data in database (use encryption utilities)

### 8. Startup & Shutdown Sequence

Must follow this order (in `main.py` lifespan):

**Startup**:
1. Apply database migrations
2. Create ORM tables
3. Start Telegram handler
4. Initialize Slack handler
5. Start scheduled tasks (morning digest, auto-escalation, stats, calendar sync)

**Shutdown** (reverse order):
1. Stop scheduled tasks gracefully
2. Stop Telegram handler
3. Close database connections
4. Log completion

### 9. Testing

- **asyncio_mode = auto** for pytest
- In-memory SQLite for unit/integration tests (faster, no cleanup)
- Test fixtures in `conftest.py` (db_session, workspace_factory, user_factory)
- Mirror app structure: `tests/commands/`, `tests/services/`, etc.
- File naming: `test_*.py`, class naming: `Test*`, method naming: `test_*`
- Async tests: `@pytest.mark.asyncio`

### 10. Configuration Management

- Single `Pydantic BaseSettings` in `app/config/settings.py` with `@lru_cache()` singleton
- `.env` file support with automatic loading
- Field validators for whitespace stripping and empty string conversion
- Environment variable precedence: `.env` > defaults

**Key Variables**:
- `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`
- `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`
- `DATABASE_URL` (PostgreSQL connection string)
- `TIMEZONE` (default: UTC)
- `ENCRYPTION_KEY` (required for sensitive data encryption)
- `ADMIN_TELEGRAM_IDS`, `ADMIN_SLACK_IDS` (comma-separated)

### 11. Connection Pooling & Resilience

- PostgreSQL: `QueuePool` with `pool_pre_ping=True` (health check before use)
- Pool config: `pool_size=10, max_overflow=10, pool_recycle=3600`
- SQLite (tests): `NullPool` (no pooling)
- Implement retry logic with exponential backoff for transient failures
- Decorator: `@retry_on_connection_error(max_retries=4, base_wait=2)`

### 12. Code Quality Standards

- **No over-engineering**: Only implement what's required, trust framework guarantees
- **Avoid premature abstraction**: 3 similar lines of code is OK, don't create utilities for one-time operations
- **Minimal error handling**: Validate at system boundaries (user input, external APIs), not for internal invariants
- **Clean imports**: Remove unused imports, organize by standard library → third-party → local
- **Avoid backwards compatibility hacks**: If something is unused, delete it completely
- **Comments**: Only add where logic is not self-evident; self-documenting code is preferred

---

## Automated Jobs

The system automatically handles these APScheduler tasks:

- **Morning Digest** (Cron): Daily at `MORNING_DIGEST_TIME`, sends duty overview
- **Auto-escalation** (Interval): Every minute, escalates unacknowledged incidents
- **Monthly Stats** (Cron): 1st of month at 01:00 UTC, recalculates performance metrics
- **Google Calendar Sync** (Interval): Every 4 hours, synchronizes schedules to Google Calendar

All jobs are timezone-aware (via `TIMEZONE` env var).

---

## Implementation Status

- [x] Database models and migrations
- [x] Async repository and service layers
- [x] Command parsing and unified handlers
- [x] Telegram handler with webhook integration
- [x] Slack handler with bolt integration
- [x] Scheduled tasks (APScheduler)
- [x] Docker setup with postgres + app + webapp
- [x] Admin web panel with authentication
- [x] Google Calendar integration
- [x] Comprehensive test suite
- [x] Security middleware (CSP, CSRF, rate limiting)
- [x] Telegram Mini App calendar interface
- [x] Multi-organization and workspace support
- [x] Performance metrics and duty history tracking
