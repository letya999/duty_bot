# Duty Bot - IT Team Duty Management

A bot for managing duty schedules and shifts in IT teams. Works simultaneously in Telegram and Slack with identical commands.

## Features

- **Duty Management**: Set and view duty schedules
- **Shift Management**: Manage team shifts
- **Team Management**: Create and manage teams with members
- **Escalation**: Multi-level escalation with automatic escalation
- **Automation**: Daily digest, duty reminders, auto-escalation

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

3. Configure environment variables in `.env`:
```env
TELEGRAM_TOKEN=your_telegram_bot_token
SLACK_BOT_TOKEN=xoxb-your-slack-token
SLACK_SIGNING_SECRET=your_slack_signing_secret
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/duty_bot
TIMEZONE=UTC
MORNING_DIGEST_TIME=09:00
REMINDER_BEFORE_MINUTES=30
ESCALATION_TIMEOUT_MINUTES=15
```

### Running with Docker

```bash
docker-compose up -d
```

The bot will:
- Create database tables automatically
- Start Telegram bot
- Start Slack bot
- Setup scheduled tasks

### Manual Setup (without Docker)

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Setup PostgreSQL:
```bash
createdb duty_bot
```

3. Update `DATABASE_URL` in `.env`

4. Run the application:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

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

## Development

### Project Structure

```
duty_bot/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── database.py          # Database setup
│   ├── models.py            # SQLAlchemy models
│   ├── handlers/            # Telegram and Slack handlers
│   │   ├── telegram_handler.py
│   │   └── slack_handler.py
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
├── docker-compose.yml       # Docker Compose setup
├── Dockerfile               # Docker image
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

## Troubleshooting

### Database connection error
- Check PostgreSQL is running
- Verify DATABASE_URL in .env
- Ensure database exists

### Telegram/Slack token errors
- Verify tokens in .env
- Check token permissions
- Ensure webhooks are configured for Slack

### Commands not working
- Check bot has proper permissions
- Verify team names and user mentions
- Check logs: `docker logs duty_bot_app`

## License

MIT
