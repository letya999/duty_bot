# Duty Bot - IT Team Duty Management

A bot for managing duty schedules and shifts in IT teams, working simultaneously in Telegram and Slack with identical commands.

## Features

- **Multi-platform**: Telegram and Slack support.
- **Duty & Shifts**: Manage simple daily duties or complex shift-based schedules.
- **Escalation**: Multi-level escalation (Team Lead -> CTO) with automatic timeouts.
- **Automation**: Daily digests, reminders, and Google Calendar synchronization.
- **Interactive UI**: Telegram Mini App with a calendar view and an Admin Panel.

## Quick Start

1. **Clone & Prepare**:
   ```bash
   git clone <repo_url> && cd duty_bot
   cp .env.example .env
   ```

2. **Generate Security Keys**:
   ```bash
   # Required for encrypting sensitive data and session security
   python scripts/generate_security_keys.py --output .env.security
   cat .env.security >> .env
   rm .env.security
   ```

3. **Configure**: Fill in your `TELEGRAM_TOKEN` and `SLACK_BOT_TOKEN` in `.env`.

4. **Launch**:
   ```bash
   docker-compose up -d
   ```
   *Access the Admin Panel at http://localhost:8000*

## Core Commands

| Category | Command | Description |
|----------|---------|-------------|
| **Duty** | `/duty [team]` | Show who is on duty today |
| **Team** | `/team list` | List all teams |
|          | `/team add-member <team> @user` | Add member to team |
| **Schedule** | `/schedule <team> set <date> @user` | Set duty for a specific date/range |
| **Shift** | `/shift <team> add <date> @user` | Add user to a specific shift |
| **Escalation**| `/escalate <team>` | Manually escalate to team lead |
|          | `/escalate ack` | Acknowledge/resolve current incident |

*For full command list and date formats, see the [Commands Documentation](docs/COMMANDS.md).*

## Configuration Reference

Key environment variables in `.env`:

| Variable | Description |
|----------|-------------|
| `TELEGRAM_TOKEN` | Bot token from @BotFather |
| `SLACK_BOT_TOKEN`| Bot token starting with `xoxb-` |
| `DATABASE_URL` | PostgreSQL connection string |
| `TIMEZONE` | Timezone for tasks (default: `UTC`) |
| `MORNING_DIGEST_TIME`| Time for daily digest (default: `09:00`) |
| `ENCRYPTION_KEY` | **Required.** Encrypts sensitive data in DB |

## Advanced Setup

- **Telegram Mini App**: Configure `VITE_TELEGRAM_BOT_USERNAME` and set the Menu Button in @BotFather.
- **Google Calendar**: Setup a Service Account in Google Cloud and upload the JSON key in the Admin Panel.
- **Service Configuration**: See the [Service Setup Guide](docs/SETUP_GUIDE.md) for step-by-step external integration details.
- **Manual Setup**: See the project structure and setup instructions for non-docker installation.

## Automated Jobs

The system automatically handles:
- **Morning Digest**: Daily duty overview.
- **Auto-escalation**: Level 2 escalation after `ESCALATION_TIMEOUT_MINUTES`.
- **Google Sync**: Synchronizes schedules every 4 hours.
- **Monthly Stats**: Recalculates performance metrics on the 1st of each month.

---
[Commands Reference](docs/COMMANDS.md) | [Troubleshooting](docs/TROUBLESHOOTING.md) | [License: MIT](LICENSE)
