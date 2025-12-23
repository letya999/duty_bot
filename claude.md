# Duty Bot - IT Team Duty Management

## Project Overview

A duty management bot for IT teams working in Telegram and Slack simultaneously. One instance = one Telegram chat + one Slack channel with identical commands and functionality.

## Key Features

- **Duty viewing**: Check who's on duty today
- **Team management**: Create teams, manage members, assign team leads
- **Scheduling**: Set duty schedules for teams or shifts for teams with shift mode
- **Escalation**: Multi-level escalation with automatic escalation after timeout
- **Automation**: Daily morning digest, duty reminders, auto-escalation

## Tech Stack

- Python 3.11+
- FastAPI (webhooks)
- python-telegram-bot
- slack-bolt
- SQLAlchemy + asyncpg (PostgreSQL)
- APScheduler
- Docker Compose (PostgreSQL + app)

## Database Entities

- **User**: Telegram username, Slack user ID, display name
- **Team**: Name (identifier), display name, shift flag, team lead
- **TeamMember**: User-Team relationship
- **Schedule**: Duty for specific date (teams without shifts)
- **Shift**: Multiple people for specific date (teams with shifts)
- **Escalation**: Settings for escalation levels
- **EscalationEvent**: Tracks escalation events and auto-escalation

## Commands

### Duty
- `/duty` - Show all on-duty today without mentions
- `/duty <team>` - Mention team's duty person/shift

### Team Management
- `/team list` - List all teams
- `/team <name>` - Show team composition
- `/team add <name> "<display_name>"` - Create team
- `/team add <name> "<display_name>" --shifts` - Create with shift mode
- `/team edit <name>` - Modify team
- `/team lead <team> @user` - Assign team lead
- `/team delete <team>` - Delete team
- `/team add-member <team> @user` - Add member
- `/team remove-member <team> @user` - Remove member
- `/team move @user <from> <to>` - Move member between teams

### Scheduling (no shifts)
- `/schedule <team>` - Show current week
- `/schedule <team> next` - Show next week
- `/schedule <team> <month>` - Show month
- `/schedule <team> set <date> @user` - Assign duty
- `/schedule <team> set <date>-<date> @user` - Assign range
- `/schedule <team> clear <date>` - Remove duty

### Shifts (with shifts)
- `/shift <team>` - Show current week
- `/shift <team> set <date> @user1 @user2 ...` - Set shift
- `/shift <team> add <date> @user` - Add to shift
- `/shift <team> remove <date> @user` - Remove from shift
- `/shift <team> clear <date>` - Clear shift

### Escalation
- `/escalation` - Show escalation settings
- `/escalation cto @user` - Set CTO (level 2)
- `/escalate <team>` - Escalate to team lead
- `/escalate level2` - Escalate to CTO
- `/escalate ack` - Acknowledge escalation

## Configuration

Environment variables:
- `TELEGRAM_TOKEN`
- `SLACK_BOT_TOKEN`
- `SLACK_SIGNING_SECRET`
- `DATABASE_URL`
- `TIMEZONE`
- `MORNING_DIGEST_TIME` (HH:MM format)
- `REMINDER_BEFORE_MINUTES`
- `ESCALATION_TIMEOUT_MINUTES`

## Project Structure

```
duty_bot/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── models.py
│   ├── database.py
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── telegram_handler.py
│   │   └── slack_handler.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   ├── team_service.py
│   │   ├── schedule_service.py
│   │   ├── shift_service.py
│   │   └── escalation_service.py
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── parser.py
│   │   └── handlers.py
│   └── tasks/
│       ├── __init__.py
│       └── scheduled_tasks.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Implementation Status

- [ ] Database models and migrations
- [ ] Service layer
- [ ] Command parsing and handlers
- [ ] Telegram integration
- [ ] Slack integration
- [ ] Scheduled tasks
- [ ] Docker setup
- [ ] Testing
