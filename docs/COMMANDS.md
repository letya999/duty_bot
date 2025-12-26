# Duty Bot Commands Reference

All commands work identically in Telegram and Slack.

## Duty Status
- `/duty` - Show all on-duty today across all teams.
- `/duty [team]` - Show current duty person for a specific team.

## Team Management
- `/team list` - List all teams in the workspace.
- `/team [name]` - Show detailed info about a team.
- `/team add <name> "<display_name>"` - Create a new team.
- `/team add <name> "<display_name>" --shifts` - Create a team with shift support.
- `/team edit <name> --name <new_name>` - Rename team.
- `/team add-member <team> @user` - Add a member to a team.
- `/team remove-member <team> @user` - Remove a member from a team.
- `/team lead <team> @user` - Set team lead.
- `/team delete <team>` - Permanent team deletion.

## Scheduling (Daily Duties)
*Used for teams without shifts.*
- `/schedule <team>` - Show current week schedule.
- `/schedule <team> next` - Show next week schedule.
- `/schedule <team> [month]` - Show schedule for a specific month (e.g., `January`).
- `/schedule <team> set <date> @user` - Set duty for a specific date.
- `/schedule <team> set <date>-<date> @user` - Set duty for a date range.
- `/schedule <team> clear <date>` - Clear duty for a date.

## Shift Management
*Used for teams with `--shifts` enabled.*
- `/shift <team>` - Show current week shifts.
- `/shift <team> add <date> @user` - Add a user to a specific shift.
- `/shift <team> remove <date> @user` - Remove a user from a shift.
- `/shift <team> clear <date>` - Clear all members from a shift.

## Escalation
- `/escalation` - Show current escalation level settings and status.
- `/escalate <team>` - Manually escalate current issue to the team lead.
- `/escalate level2` - Manually escalate to level 2 (CTO).
- `/escalate ack` - Acknowledge and resolve the current escalation.

## Date Formats
- `DD.MM` - e.g., `25.12` (assumes current or next year).
- `DD.MM.YYYY` - e.g., `25.12.2024`.
- `Month Name` - e.g., `January` or `Январь`.
- `DD.MM-DD.MM` - e.g., `20.12-25.12`.
