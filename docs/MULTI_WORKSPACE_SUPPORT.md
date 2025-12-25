# Multi-Workspace Support & Data Isolation

## Overview

The Duty Bot now supports **context-aware multi-workspace switching**, allowing a single user (identified by `telegram_id` or `slack_user_id`) to manage duties and schedules across multiple Telegram chats or Slack workspaces without re-authenticating.

## Architecture

### Key Concepts

1. **Workspace**: A boundary for data isolation. Each Telegram chat or Slack workspace gets its own `Workspace` record.
2. **User per Workspace**: Same `telegram_id` can have multiple `User` records - one per workspace.
3. **Session Context**: A session token represents a specific (user_id, workspace_id) context.
4. **Platform-based Identification**: Users matched across workspaces via platform ID (telegram_id or slack_user_id).

### Data Isolation Guarantee

Every query that returns schedule, shift, team, or user data **must** filter by `workspace_id`:

```python
# ✅ CORRECT: Filters by workspace
stmt = select(Schedule).join(Team).where(
    (Schedule.date == today) &
    (Team.workspace_id == workspace_id)  # REQUIRED
)

# ❌ WRONG: Missing workspace filter
stmt = select(Schedule).where(Schedule.date == today)
```

## User Flow

### Login (No Change)

1. User logs in with Telegram or Slack
2. If multiple workspaces exist → show workspace selection modal
3. If single workspace → enter automatically

### Workspace Switching

1. User clicks "Workspace Switcher" dropdown in sidebar (if >1 workspace)
2. User selects target workspace
3. Frontend calls `POST /web/auth/switch-workspace`
4. Backend validates access and creates new session token
5. Page reloads with new context (queries now filtered to new workspace)

### Permissions Model

```
Single User → Multiple Workspaces

User "john" (telegram_id=12345) can be:
├─ Admin in Workspace A (Telegram chat #alpha)
├─ Member in Workspace B (Telegram chat #beta)
└─ Admin in Workspace C (Slack workspace "engineering")

When in Workspace A:
- John sees only: teams, users, schedules, shifts from Workspace A
- John can edit: any data in Workspace A (because he's admin)

When in Workspace B:
- John sees only: teams, users, schedules, shifts from Workspace B
- John can view but NOT edit: data in Workspace B (because he's member)
```

## API Endpoints

### GET `/web/auth/workspaces`

**Purpose**: List all available workspaces for authenticated user

**Request**:
```bash
curl -X GET http://localhost:8000/web/auth/workspaces \
  -H "Cookie: session_token=<token>"
```

**Response**:
```json
{
  "workspaces": [
    {
      "id": 1,
      "name": "Engineering Team - Main",
      "type": "telegram",
      "is_current": true,
      "is_admin": true,
      "role": "admin"
    },
    {
      "id": 2,
      "name": "On-Call Rotation",
      "type": "slack",
      "is_current": false,
      "is_admin": false,
      "role": "member"
    }
  ]
}
```

### POST `/web/auth/switch-workspace`

**Purpose**: Switch to a different workspace and get new session token

**Request**:
```bash
curl -X POST http://localhost:8000/web/auth/switch-workspace \
  -H "Cookie: session_token=<token>" \
  -H "Content-Type: application/json" \
  -d '{"workspace_id": 2}'
```

**Response**:
```json
{
  "success": true,
  "session_token": "<new-token>",
  "workspace": {
    "id": 2,
    "name": "On-Call Rotation",
    "type": "slack"
  }
}
```

**Error Responses**:
- `400`: Missing workspace_id
- `403`: User not authorized for this workspace
- `404`: User or workspace not found
- `500`: Internal error

## Database Changes

No new tables required. Existing schema supports multi-workspace:

```
User:
  - workspace_id (FK to Workspace)
  - telegram_id (indexed, can have multiple User rows per telegram_id)
  - slack_user_id (indexed, can have multiple User rows per slack_user_id)

Team:
  - workspace_id (FK to Workspace, ensures team isolation)

Schedule:
  - team_id (FK to Team, cascades workspace via Team)

Shift:
  - team_id (FK to Team, cascades workspace via Team)
```

## Implementation Details

### Repository Layer Changes

**ScheduleRepository**:
- `list_by_user_and_date_range(user_id, start_date, end_date, workspace_id=None)`
  - Now joins with `Team` to filter by workspace
  - If `workspace_id` provided, only returns schedules from that workspace

- `list_by_date(duty_date, workspace_id=None)`
  - Now joins with `Team` to filter by workspace
  - Prevents cross-workspace data leakage

**ShiftRepository**:
- `list_by_user_and_date_range(user_id, start_date, end_date, workspace_id=None)`
  - Joins with `Team` to enforce workspace isolation

### Service Layer Changes

**ScheduleService**:
- `check_user_schedule_conflict(user_id, duty_date, workspace_id=None)`
  - Checks conflicts only within specified workspace

**ShiftService**:
- `check_user_shift_conflict(user, shift_date, workspace_id=None)`
  - Checks conflicts only within specified workspace

### Route Layer Changes

All routes in `/web/routes/` now include workspace filtering:

- `dashboard.py`: Schedule and Shift queries filter by `workspace_id`
- `schedules.py`: Monthly schedule query filters by `workspace_id`
- `auth.py`: New endpoints for workspace listing and switching

### Frontend Changes

**Navigation.tsx**:
- New state: `workspaces[]`, `currentWorkspace`, `isWorkspaceSwitcherOpen`
- New methods: `loadWorkspaces()`, `handleSwitchWorkspace()`
- UI: Dropdown switcher visible only if `workspaces.length > 1`
- On switch: Updates session token and reloads page

## Security Considerations

### ✅ What's Protected

1. **Data Isolation**: Each workspace is a separate data boundary
2. **User Verification**: Switch requires valid platform ID match
3. **Access Control**: User must exist in target workspace to switch
4. **Session Scoping**: Each token tied to specific (user_id, workspace_id)

### ⚠️ What to Watch

1. **Command Handlers**: Ensure bot commands validate workspace before processing
2. **Shared Resources**: Some settings (escalation CTO) might be global - document clearly
3. **Cross-Workspace Queries**: Any new query must include workspace filter
4. **Token Expiry**: Session timeout same across workspaces

## Testing Checklist

### Unit Tests
- [ ] `list_by_date()` filters by workspace
- [ ] `list_by_user_and_date_range()` filters by workspace
- [ ] `check_user_schedule_conflict()` respects workspace
- [ ] `check_user_shift_conflict()` respects workspace

### Integration Tests
- [ ] User with 2 workspaces can list them
- [ ] User can switch to different workspace
- [ ] User cannot access workspace they're not in
- [ ] After switch, dashboard shows correct workspace data
- [ ] Schedules page shows only current workspace

### Manual Tests
- [ ] Add bot to 2 Telegram chats
- [ ] Login with same Telegram user
- [ ] See workspace switcher dropdown
- [ ] Switch workspaces
- [ ] Dashboard data changes correctly
- [ ] Schedules page reflects new workspace
- [ ] Commands in bot work correctly in both chats

## Slack & Telegram Compatibility

Both platforms work identically:

### Telegram
- `Workspace.workspace_type = 'telegram'`
- `Workspace.external_id = <chat_id>`
- User identification via `telegram_id`

### Slack
- `Workspace.workspace_type = 'slack'`
- `Workspace.external_id = <workspace_id>`
- User identification via `slack_user_id`

The switcher UI shows platform icon (✈️ for Telegram, ⚡ for Slack).

## Future Enhancements

1. **Modal on Login**: Show workspace selection when user has >1 workspace
2. **Default Workspace**: Remember user's last workspace choice
3. **Workspace Nickname**: Allow users to rename workspaces in their view
4. **Quick Switch Keyboard**: Add keyboard shortcut for workspace switching
5. **Workspace Analytics**: Show per-workspace activity in reports

## Troubleshooting

### User sees no workspaces dropdown
- **Cause**: User only has 1 workspace
- **Solution**: Add bot to another chat to create second workspace

### Workspace switch fails with 403
- **Cause**: User doesn't exist in target workspace
- **Solution**: Ensure user is added to target workspace first

### Dashboard shows data from wrong workspace
- **Cause**: Session token not updated after switch
- **Solution**: Hard refresh browser (Ctrl+Shift+R)

### Schedule conflict check wrong
- **Cause**: Old code path not passing workspace_id
- **Solution**: Check all service calls pass workspace_id parameter
