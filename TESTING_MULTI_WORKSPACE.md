# Multi-Workspace Testing Guide

This guide provides instructions for testing the duty bot's multi-workspace (multi-tenancy) architecture.

## Overview

The duty bot now supports complete data isolation across multiple workspaces:

- **Telegram**: Each Telegram chat is a separate workspace with its own Teams, Users, and Schedules
- **Slack**: Each Slack workspace is a separate workspace with its own Teams, Users, and Schedules

## Testing Setup

### Prerequisites

1. Bot running locally or deployed with proper configuration
2. Multiple Telegram chats for testing (you can create test groups)
3. Slack workspace(s) with bot installed and proper permissions
4. Database access (for verification)

### Configuration

Ensure your `.env` file has:

```env
# Telegram configuration
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=123456789  # Optional: for broadcasts (morning digest, escalations)

# Slack configuration
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
SLACK_CHANNEL_ID=C...  # Optional: for broadcasts

# Other
MORNING_DIGEST_TIME=08:00
ESCALATION_TIMEOUT_MINUTES=5
```

## Test Scenarios

### Scenario 1: Telegram Multi-Chat Isolation

Test that each Telegram chat maintains separate Teams and Users.

#### Steps:

1. **Chat A Setup** (Chat ID: 111222333)
   ```
   /team add backend "Backend Team"
   /team add-member backend @developer1
   /schedule backend set 2025-12-24 @developer1
   ```

2. **Chat B Setup** (Chat ID: 444555666)
   ```
   /team add frontend "Frontend Team"
   /team add-member frontend @designer1
   /schedule frontend set 2025-12-24 @designer1
   ```

3. **Verify Isolation**:
   - In Chat A: `/team list` should show only `backend`
   - In Chat B: `/team list` should show only `frontend`
   - They should NOT see each other's teams

#### Expected Results:

- Chat A and Chat B have completely independent team structures
- Users with same @username can exist in both chats (separate workspace users)
- Schedules in Chat A don't affect Chat B

### Scenario 2: Slack Workspace Isolation

Test that each Slack workspace maintains separate data.

#### Steps:

1. **Workspace A Setup**:
   ```
   /team add ops "Operations Team"
   /team add-member ops @alice
   /schedule ops set 2025-12-24 @alice
   ```

2. **Workspace B Setup** (if you have multiple Slack workspaces):
   ```
   /team add support "Support Team"
   /team add-member support @bob
   /schedule support set 2025-12-24 @bob
   ```

3. **Verify Isolation**:
   - Each workspace should have independent teams
   - Users from Workspace A shouldn't appear in Workspace B

#### Expected Results:

- Complete data isolation between Slack workspaces
- Each workspace can have its own team structure and members

### Scenario 3: Cross-Messenger Compatibility

Test that both Telegram and Slack workspaces can coexist in the same database.

#### Steps:

1. Setup Telegram chat with `/team add backend "Backend"`
2. Setup Slack workspace with `/team add frontend "Frontend"`
3. Query database to verify both workspaces exist

#### Expected Results:

```sql
SELECT id, workspace_type, external_id, name FROM workspace;
```

Should show:
- workspace_id=1, workspace_type='telegram', external_id=111222333, name='Telegram Chat 111222333'
- workspace_id=2, workspace_type='slack', external_id=xyzabc123, name='Slack Workspace xyzabc123'

### Scenario 4: Scheduled Tasks (Multi-Workspace Execution)

Test that scheduled tasks execute across all workspaces.

#### Setup:

1. Create duties in multiple Telegram chats
2. Create duties in multiple Slack workspaces

#### Using Test Endpoints:

```bash
# Trigger morning digest manually
curl -X POST http://localhost:8000/test/morning-digest

# Check what's scheduled
curl -X GET http://localhost:8000/test/scheduler-status

# Trigger escalation check
curl -X POST http://localhost:8000/test/check-escalations
```

#### Expected Results:

- Morning digest is sent to ALL Telegram chats with configured duties
- Telegram messages go to respective chat IDs (from workspace.external_id)
- Slack messages go to the configured SLACK_CHANNEL_ID
- Logs show execution for each workspace:
  ```
  Morning digest sent to Telegram workspace 1
  Morning digest sent to Slack workspace 2
  Morning digest sent to all workspaces
  ```

### Scenario 5: User and Team Lookups

Test that user/team lookups are workspace-scoped.

#### Setup:

1. Create user @developer in Chat A (Telegram workspace 1)
2. Create user @developer in Chat B (Telegram workspace 2)
3. In Chat A: `/team lead backend @developer`

#### Expected Results:

- Chat A's @developer is added as lead to backend team
- Chat B's @developer is NOT affected
- In Chat B, if you try to add the same user, it's a different User record

#### Verification:

```sql
SELECT id, telegram_username, workspace_id FROM "user" WHERE telegram_username='developer';
```

Should show multiple rows with same username but different workspace_ids.

### Scenario 6: Escalations (Workspace-Scoped CTO)

Test that escalations and CTO assignments are workspace-specific.

#### Setup - Chat A:

```
/escalation cto @level2_support_a
```

#### Setup - Chat B:

```
/escalation cto @level2_support_b
```

#### Verify:

- `/escalation` in Chat A should show `level2_support_a` as CTO
- `/escalation` in Chat B should show `level2_support_b` as CTO
- They don't conflict

#### Test Auto-Escalation:

1. Setup escalation in Chat A
2. Trigger auto-escalation via `/escalate team_name`
3. Verify only Chat A receives escalation message

### Scenario 7: Date Parsing (Bug Fix Verification)

Test that 2-digit years are correctly parsed.

#### In any chat/workspace:

```
/schedule backend set 23.12.25 @developer
/schedule backend week
```

#### Expected Results:

- Date should be parsed as 2025-12-23 (not year 0025)
- Shows up correctly in schedule view

## Database Verification

To verify workspace isolation at the database level:

```sql
-- List all workspaces
SELECT id, workspace_type, external_id, name FROM workspace;

-- Verify users are workspace-scoped
SELECT id, telegram_username, slack_user_id, workspace_id FROM "user" ORDER BY workspace_id;

-- Verify teams are workspace-scoped
SELECT id, name, workspace_id FROM team ORDER BY workspace_id;

-- Verify schedules (through team relationship)
SELECT s.id, s.date, u.display_name, t.name, t.workspace_id
FROM schedule s
LEFT JOIN "user" u ON s.user_id = u.id
LEFT JOIN team t ON s.team_id = t.id
ORDER BY t.workspace_id;
```

## Common Issues and Troubleshooting

### Issue 1: "User not found" errors

**Cause**: User lookup is workspace-scoped. Users must be added to the same workspace where they're being used.

**Solution**: Ensure you're adding the user in the same chat/workspace where you're using them.

### Issue 2: Teams appearing across workspaces

**Cause**: Stale cache or database issue

**Solution**:
1. Verify teams have workspace_id set in database
2. Check that get_team_by_name includes workspace filter
3. Restart the application

### Issue 3: Morning digest not sending

**Possible causes**:
1. TELEGRAM_CHAT_ID or SLACK_CHANNEL_ID not configured
2. No duties set up in any workspace
3. Scheduled tasks not running

**Solution**:
1. Configure chat/channel IDs in .env
2. Use test endpoints to trigger manually
3. Check application logs for errors

### Issue 4: Escalations not triggering

**Cause**: CTO not set or no active escalation event

**Solution**:
1. Use `/escalation cto @user` to set CTO in workspace
2. Use `/escalate team_name` to create escalation event
3. Check timeout setting (ESCALATION_TIMEOUT_MINUTES)

## Performance Testing

For multi-workspace systems with many workspaces:

```bash
# Time the morning digest across multiple workspaces
time curl -X POST http://localhost:8000/test/morning-digest

# Check scheduler efficiency
curl -X GET http://localhost:8000/test/scheduler-status
```

Expected behavior: Linear time complexity with number of workspaces (should complete quickly for 10+ workspaces).

## Backward Compatibility

The system maintains backward compatibility:

- **Default Workspace**: All existing data migrated to workspace_id=1
- **Single Workspace Deployments**: Continue to work as before
- **Config Optional**: TELEGRAM_CHAT_ID and SLACK_CHANNEL_ID are optional for test mode

### Migration Verification:

```sql
-- Should have default workspace (id=1)
SELECT * FROM workspace WHERE id=1;

-- All existing users should have workspace_id=1
SELECT COUNT(*) FROM "user" WHERE workspace_id IS NOT NULL;

-- All existing teams should have workspace_id=1
SELECT COUNT(*) FROM team WHERE workspace_id IS NOT NULL;
```

## Testing Checklist

- [ ] Telegram Chat A: Create team, add users, set schedules
- [ ] Telegram Chat B: Create team, add users, set schedules (different from A)
- [ ] Verify Chat A and B have independent data
- [ ] Slack Workspace 1: Create team and schedule
- [ ] Slack Workspace 2: Create team and schedule (if available)
- [ ] Verify Slack workspaces have independent data
- [ ] Test user @mentions are workspace-scoped
- [ ] Test team lookups only find teams in same workspace
- [ ] Test escalation CTO assignment is workspace-specific
- [ ] Run morning digest test endpoint
- [ ] Verify digest sent to all workspaces
- [ ] Test 2-digit year parsing (23.12.25 → 2025-12-23)
- [ ] Database audit: verify workspace_id on all records

## Next Steps

Once testing is complete:

1. Update deployment documentation
2. Plan migration strategy for production deployments
3. Consider additional multi-workspace features:
   - Workspace management UI
   - Per-workspace configuration
   - Cross-workspace reporting
