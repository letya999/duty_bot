# Duty Bot Commands Reference

All commands work identically in Telegram and Slack.

## Quick Reference

| Command | Description | Admin Only |
|---------|-------------|-----------|
| `/duty` | Show on-duty people today | No |
| `/team` | List teams & manage members | Partial |
| `/schedule` | Manage duty schedule | Partial |
| `/shift` | Manage team shifts | Partial |
| `/escalation` | Escalation settings | No |
| `/escalate` | Escalate an issue | No |
| `/incident` | Manage incidents | Partial |
| `/admin` | Manage admins | Yes |
| `/help` | Show command list | No |

---

## Duty Status

### `/duty`
Show all on-duty people for today across all teams.

**Usage:**
- `/duty` - Show all teams' duty status
- `/duty <team>` - Show specific team's duty person/shift

**Example:**
```
/duty
/duty backend
```

---

## Team Management

### `/team`
List, create, and manage teams.

**Sub-commands:**

**View Teams:**
- `/team` or `/team list` - List all teams
- `/team <name>` - Show team details and members

**Create Teams:** (Admin only)
- `/team add <name> "<display_name>"` - Create team without shifts
- `/team add <name> "<display_name>" --shifts` - Create team with shift support

**Edit Teams:** (Admin only)
- `/team edit <name> --name <new_name>` - Rename team
- `/team edit <name> --display "<new_name>"` - Change display name
- `/team edit <name> --shifts` - Enable shifts
- `/team edit <name> --no-shifts` - Disable shifts

**Manage Members:** (Admin only)
- `/team lead <team> @user` - Set team lead
- `/team add-member <team> @user` - Add member to team
- `/team remove-member <team> @user` - Remove member from team
- `/team move @user <from_team> <to_team>` - Move member between teams

**Delete Teams:** (Admin only)
- `/team delete <team>` - Delete team permanently

**Examples:**
```
/team list
/team backend
/team add backend "Backend Team"
/team add frontend "Frontend Team" --shifts
/team edit backend --name backend-services
/team lead backend @alice
/team add-member backend @bob
```

---

## Scheduling (Daily Duties)

*Used for teams without shifts enabled.*

### `/schedule`
View and manage duty schedules.

**Sub-commands:**

**View Schedules:**
- `/schedule <team>` - Show current week schedule
- `/schedule <team> next` - Show next week schedule
- `/schedule <team> <month>` - Show specific month (e.g., `december`, `декабрь`)

**Set Duty:** (Admin only)
- `/schedule <team> set <date> @user` - Set duty for single date
- `/schedule <team> set <date>-<date> @user` - Set duty for date range
- `/schedule <team> set <date> @user --force` - Override existing duty

**Clear Duty:** (Admin only)
- `/schedule <team> clear <date>` - Clear duty for single date
- `/schedule <team> clear <date>-<date>` - Clear duty for date range

**Rotation Management:** (Admin only)
- `/schedule <team> rotate` - Show rotation status
- `/schedule <team> rotate enable @user1 @user2 @user3` - Enable rotation with user order
- `/schedule <team> rotate assign <date>` - Auto-assign next person in rotation
- `/schedule <team> rotate disable` - Disable rotation

**Examples:**
```
/schedule backend
/schedule backend next
/schedule backend december
/schedule backend set 25.12 @alice
/schedule backend set 20.12-25.12 @bob
/schedule backend set 25.12 @alice --force
/schedule backend clear 25.12
/schedule backend clear 20.12-25.12
/schedule backend rotate enable @alice @bob @charlie
/schedule backend rotate assign 26.12
```

---

## Shift Management

*Used for teams with shifts enabled.*

### `/shift`
View and manage team shifts (multiple people on same day).

**Sub-commands:**

**View Shifts:**
- `/shift <team>` - Show current week shifts
- `/shift <team> next` - Show next week shifts
- `/shift <team> <month>` - Show specific month

**Set Shifts:** (Admin only)
- `/shift <team> set <date> @user1 @user2 ...` - Set shift with multiple users
- `/shift <team> set <date>-<date> @user1 @user2 ...` - Set shifts for date range
- `/shift <team> set <date> @user1 @user2 ... --force` - Override existing shift

**Add/Remove Users:** (Admin only)
- `/shift <team> add <date> @user` - Add user to shift
- `/shift <team> add <date> @user --force` - Add user, override conflicts
- `/shift <team> remove <date> @user` - Remove user from shift

**Clear Shifts:** (Admin only)
- `/shift <team> clear <date>` - Clear entire shift
- `/shift <team> clear <date>-<date>` - Clear shifts for date range

**Examples:**
```
/shift frontend
/shift frontend next
/shift frontend december
/shift frontend set 25.12 @alice @bob
/shift frontend set 20.12-25.12 @alice @bob @charlie
/shift frontend add 25.12 @dave
/shift frontend remove 25.12 @alice
/shift frontend clear 25.12
```

---

## Escalation

### `/escalation`
Show escalation settings and current status.

**Sub-commands:**
- `/escalation` - Show team leads and CTO
- `/escalation cto @user` - Set CTO (Admin only)

**Examples:**
```
/escalation
/escalation cto @alice
```

---

## Escalate

### `/escalate`
Escalate an issue to the appropriate person.

**Sub-commands:**
- `/escalate <team>` - Escalate to team lead
- `/escalate level2` - Escalate to CTO
- `/escalate ack` - Acknowledge/resolve escalation

**Examples:**
```
/escalate backend
/escalate level2
/escalate ack
```

---

## Incident Management

### `/incident`
Create and manage incidents.

**Sub-commands:**

**View Incidents:**
- `/incident` or `/incident list` - List active incidents
- `/incident metrics [week|month|quarter|year]` - Show incident metrics

**Manage Incidents:**
- `/incident start <name>` - Start new incident
- `/incident stop` - Resolve current incident
- `/incident stop <name>` - Resolve specific incident

**Examples:**
```
/incident
/incident list
/incident start "Database connection pool exhausted"
/incident stop
/incident stop "Database connection pool exhausted"
/incident metrics month
/incident metrics quarter
```

---

## Admin Management

### `/admin`
Manage administrator permissions.

**Sub-commands:**
- `/admin` or `/admin list` - List all admins
- `/admin add @user` - Add admin (Admin only)
- `/admin remove @user` - Remove admin (Admin only)

**Examples:**
```
/admin
/admin list
/admin add @alice
/admin remove @bob
```

---

## Help

### `/help`
Display full command reference and usage.

**Usage:**
- `/help` - Show all available commands
- `/start` - (Telegram only) Show help on startup

---

## Date Formats

The bot supports flexible date formats:

| Format | Example | Notes |
|--------|---------|-------|
| `DD.MM` | `25.12` | Assumes current or next year |
| `DD.MM.YYYY` | `25.12.2024` | Full date |
| `DD.MM-DD.MM` | `20.12-25.12` | Date range (same year) |
| Month name (EN) | `december` | Case-insensitive |
| Month name (RU) | `декабрь` | Case-insensitive |

**Examples:**
```
/schedule backend set 25.12 @alice
/schedule backend set 25.12.2024 @alice
/schedule backend set 20.12-25.12 @alice
/schedule backend december
```

---

## Permission Levels

### No Permissions Required
- `/duty` - View current duty
- `/escalation` - View escalation settings
- `/escalate` - Escalate issues
- `/incident` - View incidents
- `/help` - View help

### Admin Permissions Required
- Team creation/editing/deletion
- Schedule/shift management
- Member management
- Rotation management
- Admin management (`/admin add`, `/admin remove`)
- Setting escalation (CTO)
- Incident creation/resolution

### To Check Your Permissions
Currently, you can only see if you're admin when attempting an admin-only command. A permission check will show an error if you lack required permissions.
