# 🚀 Implementation Plan: Advanced Bot Features

## 📊 Overview
Detailed roadmap for implementing 5 major features:
1. **User Roles & Admin System** (PHASE 1)
2. **Web Admin Panel + OAuth** (PHASE 2)
3. **Conflict Detection** (PHASE 3)
4. **Auto-rotation Schedules** (PHASE 4)
5. **Duty Statistics & Reports** (PHASE 5)

---

## 🎯 PHASE 1: User Roles & Admin System

### Objective
Implement a permission system where admin users can control who can modify schedules and team configurations. By default (if ADMIN_IDS not configured), all users can perform actions.

### Database Changes
**File:** `app/models.py`

```python
# Add to User model:
- is_admin: Boolean, default=False  # Marks user as workspace admin

# New table needed:
class AdminLog(Base):
    __tablename__ = 'admin_log'
    - id: Integer, primary_key
    - workspace_id: Integer, FK
    - admin_user_id: Integer, FK
    - action: String (e.g., "added_admin", "removed_admin", "changed_schedule")
    - target_user_id: Integer, FK (who was affected)
    - timestamp: DateTime
    - details: String (JSON with change details)
```

### Configuration Changes
**File:** `.env`

```env
# Admin user IDs (comma-separated)
# If not set, all users can perform admin actions
ADMIN_TELEGRAM_IDS=123456789,987654321
ADMIN_SLACK_IDS=U12345678,U87654321
```

**File:** `app/config.py`

```python
# Add to Settings class:
admin_telegram_ids: str = ""  # Comma-separated IDs
admin_slack_ids: str = ""     # Comma-separated IDs

# Helper method:
def get_admin_ids(self, platform: str) -> list[str]:
    """Parse admin IDs from config"""
    if platform == 'telegram':
        return [id.strip() for id in self.admin_telegram_ids.split(',') if id.strip()]
    elif platform == 'slack':
        return [id.strip() for id in self.admin_slack_ids.split(',') if id.strip()]
    return []
```

### Service Layer Changes
**File:** `app/services/user_service.py`

```python
# Add new methods:
async def set_admin(self, user_id: int, is_admin: bool) -> User:
    """Set or unset admin status for a user"""

async def get_all_admins(self, workspace_id: int) -> list[User]:
    """Get all admin users in workspace"""

async def is_admin(self, user_id: int, workspace_id: int) -> bool:
    """Check if user is admin in workspace"""
```

**File:** `app/services/admin_service.py` (NEW FILE)

```python
class AdminService:
    """Manage admin operations and audit logs"""

    async def check_permission(self, user_id: int, workspace_id: int, action: str) -> bool:
        """Check if user has permission for action"""
        # If no admins configured, allow all
        # If admins configured, only they can perform actions

    async def log_action(self, workspace_id: int, admin_id: int, action: str,
                        target_user_id: int = None, details: str = None) -> None:
        """Log admin action for audit trail"""

    async def get_action_history(self, workspace_id: int, limit: int = 100) -> list[AdminLog]:
        """Get recent admin actions"""
```

### Telegram Handler Changes
**File:** `app/handlers/telegram_handler.py`

Add permission checks before executing commands:

```python
# For commands that require admin: team add/edit/delete, schedule set/clear, shift set/add/remove/clear, escalation cto

async def check_admin_permission(self, user_id: int, workspace_id: int, action: str) -> bool:
    """Check if user has permission to perform action"""
    admin_service = AdminService(db)
    return await admin_service.check_permission(user_id, workspace_id, action)

# New command handler:
async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin commands"""
    # /admin list - show all admins
    # /admin add @user - add admin (only for existing admins)
    # /admin remove @user - remove admin
```

### New Commands

**Command:** `/admin`
```
/admin list                 → Show all admins in workspace
/admin add @user           → Add user as admin (only admins can run)
/admin remove @user        → Remove user from admins (only admins can run)
```

### Permission Matrix

| Command | Read Only | Requires Admin |
|---------|-----------|----------------|
| `/duty` | ✅ | ❌ |
| `/team list` | ✅ | ❌ |
| `/team <name>` | ✅ | ❌ |
| `/team add/edit/delete/lead` | ❌ | ✅ |
| `/schedule show` | ✅ | ❌ |
| `/schedule set/clear` | ❌ | ✅ |
| `/shift show` | ✅ | ❌ |
| `/shift set/add/remove/clear` | ❌ | ✅ |
| `/escalation` | ✅ | ❌ |
| `/escalation cto` | ❌ | ✅ |
| `/escalate` | ✅ | ❌ |
| `/help` | ✅ | ❌ |
| `/admin list` | ✅ | ❌ |
| `/admin add/remove` | ❌ | ✅ |

### Files to Modify
- `app/models.py` - Add User.is_admin, AdminLog table
- `app/config.py` - Add admin config parsing
- `app/services/user_service.py` - Add admin methods
- `app/services/admin_service.py` - NEW FILE
- `app/handlers/telegram_handler.py` - Add admin checks and /admin command
- `.env.example` - Add ADMIN_IDS configs
- `app/main.py` - Initialize admin service

### Migration Required
```sql
ALTER TABLE user ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;
CREATE TABLE admin_log (
    id INTEGER PRIMARY KEY,
    workspace_id INTEGER NOT NULL,
    admin_user_id INTEGER NOT NULL,
    action STRING NOT NULL,
    target_user_id INTEGER,
    timestamp DATETIME DEFAULT NOW(),
    details TEXT
);
```

---

## 📱 PHASE 2: Web Admin Panel + OAuth

### Objective
Create a web application for:
- OAuth login (Telegram, Slack)
- Admin dashboard with statistics
- Manage schedules visually
- View audit logs
- Configure settings

### Structure
```
app/web/
├── __init__.py
├── auth.py                 # OAuth logic
├── routes/
│   ├── __init__.py
│   ├── auth.py            # /auth/login, /auth/callback
│   ├── dashboard.py       # /dashboard (statistics)
│   ├── schedules.py       # /schedules (management)
│   ├── settings.py        # /settings (configure admins)
│   └── reports.py         # /reports (HTML exports)
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── schedules.html
│   ├── settings.html
│   └── reports.html
└── static/
    ├── css/
    └── js/
```

### Key Features
- **OAuth Providers:**
  - Telegram: Using telegram-login-widget or manual verification
  - Slack: Standard OAuth 2.0 flow

- **Dashboard Page:**
  - Current duties by team
  - Upcoming shifts
  - Quick statistics
  - Admin actions log

- **Schedules Page:**
  - Calendar view
  - Drag-drop to reschedule
  - Conflict indicators
  - Batch operations

- **Settings Page:**
  - Manage admins (only for existing admins)
  - Configure auto-rotation
  - Set work hours
  - Holiday management

- **Reports Page:**
  - Monthly statistics (HTML, PDF, CSV)
  - Team workload distribution
  - Individual duty history
  - Export buttons

### Files to Create
- `app/web/__init__.py`
- `app/web/auth.py`
- `app/web/routes/auth.py`
- `app/web/routes/dashboard.py`
- `app/web/routes/schedules.py`
- `app/web/routes/settings.py`
- `app/web/routes/reports.py`
- `app/web/templates/*.html`
- `app/web/static/css/style.css`
- `app/web/static/js/app.js`

### Files to Modify
- `app/main.py` - Add web app mount
- `requirements.txt` - Add Jinja2, aiofiles, etc.

---

## ⚠️ PHASE 3: Conflict Detection

### Objective
Prevent double-booking of staff. Warn admins when trying to schedule the same person twice on the same day.

### Logic
**File:** `app/services/schedule_service.py`, `app/services/shift_service.py`

```python
async def check_schedule_conflict(self, team_id: int, date: Date, user_id: int) -> bool:
    """Check if user already scheduled for this date"""

async def check_shift_conflict(self, team_id: int, date: Date, user_id: int) -> bool:
    """Check if user already in shift for this date"""
```

**File:** `app/commands/handlers.py`

```python
# In schedule_set method:
conflicts = await self.schedule_service.check_schedule_conflict(team.id, date, user.id)
if conflicts:
    return f"⚠️ {user.display_name} is already scheduled for {date}. Use --force to override."

# In shift_set method:
conflicts = await self.shift_service.check_shift_conflict(team.id, date, user.id)
if conflicts:
    return f"⚠️ {user.display_name} is already in shift for {date}. Use --force to override."
```

### UI Feedback
- Show warning when conflict detected
- Option to override with `--force` flag
- Log conflict attempts in admin_log

### Files to Modify
- `app/services/schedule_service.py` - Add conflict check method
- `app/services/shift_service.py` - Add conflict check method
- `app/commands/handlers.py` - Add conflict detection before set operations
- `app/handlers/telegram_handler.py` - Handle --force flag

---

## 🔄 PHASE 4: Auto-rotation Schedules

### Objective
Automatically rotate duty assignments among team members. Admin can enable rotation per team, and system automatically assigns next available person.

### Database Changes
**File:** `app/models.py`

```python
class RotationConfig(Base):
    __tablename__ = 'rotation_config'
    - id: Integer, primary_key
    - team_id: Integer, FK (unique)
    - enabled: Boolean, default=False
    - member_order: JSON (list of user_ids in rotation order)
    - last_assigned_user_id: Integer, FK
    - last_assigned_date: Date
    - skip_unavailable: Boolean (skip people on vacation)
    - created_at: DateTime
    - updated_at: DateTime
```

### Service Layer
**File:** `app/services/rotation_service.py` (NEW FILE)

```python
class RotationService:
    """Manage rotation schedules"""

    async def enable_rotation(self, team_id: int, member_ids: list[int]) -> RotationConfig:
        """Enable auto-rotation for team with member order"""

    async def disable_rotation(self, team_id: int) -> None:
        """Disable rotation"""

    async def get_next_person(self, team_id: int, date: Date) -> User:
        """Get next person in rotation"""

    async def assign_rotation(self, team_id: int, date: Date) -> User:
        """Auto-assign next person and return"""

    async def skip_user(self, team_id: int, date: Date) -> None:
        """Skip user and assign next"""
```

### Commands
**Command:** `/schedule <team> rotate [enable|disable|set-order|assign]`

```
/schedule backend rotate enable @user1 @user2 @user3
  → Enable rotation with order: user1 → user2 → user3 → user1 → ...

/schedule backend rotate assign 01.12
  → Assign next person in rotation to Dec 1

/schedule backend rotate disable
  → Disable auto-rotation for this team
```

### Files to Create
- `app/services/rotation_service.py`

### Files to Modify
- `app/models.py` - Add RotationConfig table
- `app/commands/handlers.py` - Add rotation methods
- `app/handlers/telegram_handler.py` - Add rotation command parsing

---

## 📊 PHASE 5: Duty Statistics & Reports

### Objective
Track duty assignments and generate reports showing who worked how much.

### Database Changes
**File:** `app/models.py`

```python
class DutyStats(Base):
    __tablename__ = 'duty_stats'
    - id: Integer, primary_key
    - workspace_id: Integer, FK
    - user_id: Integer, FK
    - team_id: Integer, FK
    - year: Integer
    - month: Integer
    - duty_days: Integer (count of duty days)
    - shift_days: Integer (count of shift days)
    - total_hours: Float (optional, if tracking hours)
    - created_at: DateTime
    - updated_at: DateTime
```

### Service Layer
**File:** `app/services/stats_service.py` (NEW FILE)

```python
class StatsService:
    """Generate statistics and reports"""

    async def update_stats(self, workspace_id: int, month: int = None, year: int = None) -> None:
        """Recalculate stats for period"""

    async def get_user_stats(self, user_id: int, year: int, month: int = None) -> dict:
        """Get stats for user"""

    async def get_team_stats(self, team_id: int, year: int, month: int = None) -> dict:
        """Get stats for team"""

    async def get_workspace_stats(self, workspace_id: int, year: int) -> dict:
        """Get workspace-wide stats"""

    async def generate_monthly_report(self, workspace_id: int, year: int, month: int) -> str:
        """Generate HTML report for month"""

    async def generate_user_report(self, user_id: int, year: int) -> str:
        """Generate user's yearly report"""
```

### Report Generation
**File:** `app/web/routes/reports.py`

```python
# Reports should include:
- Monthly team workload distribution (bar charts)
- Individual duty history (table with dates)
- Comparison with others (who worked more/less)
- Export to PDF/CSV/Excel
- Printable view
```

### Scheduled Task
**File:** `app/tasks/scheduled_tasks.py`

```python
# Add job:
- Every 1st of month at 00:00
- Recalculate stats for previous month
- Send summary report to teams
```

### Files to Create
- `app/services/stats_service.py`

### Files to Modify
- `app/models.py` - Add DutyStats table
- `app/tasks/scheduled_tasks.py` - Add monthly stats job
- `app/web/routes/reports.py` - Add report generation

---

## 📝 Summary Table

| Phase | Feature | Complexity | Files | Est. Lines |
|-------|---------|-----------|-------|-----------|
| 1 | User Roles & Admin System | Medium | 4 create, 5 modify | 800+ |
| 2 | Web Admin Panel + OAuth | High | 8+ create, 2 modify | 2000+ |
| 3 | Conflict Detection | Low | 0 create, 3 modify | 300+ |
| 4 | Auto-rotation | Medium | 1 create, 3 modify | 600+ |
| 5 | Statistics & Reports | High | 2 create, 3 modify | 1200+ |

---

## 🔗 Dependencies Between Phases

```
PHASE 1 (User Roles)
    ↓
PHASE 3 (Conflict Detection) ← can run in parallel with PHASE 1
    ↓
PHASE 4 (Auto-rotation)
    ↓
PHASE 5 (Statistics)
    ↓
PHASE 2 (Web Admin) ← needs all previous features
```

---

## ✅ Checklist

### Phase 1 Checklist
- [ ] Add User.is_admin column to models
- [ ] Create AdminLog table
- [ ] Add admin config parsing to settings
- [ ] Create AdminService with permission checks
- [ ] Add admin methods to UserService
- [ ] Add /admin command to Telegram handler
- [ ] Add permission middleware to all admin commands
- [ ] Create migration script
- [ ] Test admin functionality
- [ ] Commit and push

### Phase 2 Checklist
- [ ] Create web app structure
- [ ] Implement Telegram OAuth
- [ ] Implement Slack OAuth
- [ ] Create login page
- [ ] Create dashboard page
- [ ] Create schedules management page
- [ ] Create settings page
- [ ] Create reports page
- [ ] Add CSS/JS styling
- [ ] Integrate with database
- [ ] Test all flows
- [ ] Commit and push

### Phase 3 Checklist
- [ ] Add conflict check methods to services
- [ ] Add conflict detection to handlers
- [ ] Add --force flag support
- [ ] Test conflict scenarios
- [ ] Commit and push

### Phase 4 Checklist
- [ ] Create RotationConfig model
- [ ] Create RotationService
- [ ] Implement rotation logic
- [ ] Add /schedule rotate commands
- [ ] Test rotation assignments
- [ ] Commit and push

### Phase 5 Checklist
- [ ] Create DutyStats model
- [ ] Create StatsService
- [ ] Implement stats calculations
- [ ] Create report generation
- [ ] Add monthly stats job
- [ ] Create web reports pages
- [ ] Test report generation
- [ ] Commit and push

---

## 🚀 Start Here

Begin with **PHASE 1: User Roles & Admin System**
- Most foundational
- Required for other phases
- Moderate complexity
- Est. 4-6 hours of work
