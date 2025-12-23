# Multi-Workspace Architecture

## Overview

Current system has no data isolation between different Telegram chats and Slack channels. This design introduces **Workspace** concept for proper multi-tenancy.

## Architecture

### Workspace Types

1. **Telegram Chat Workspace**
   - One workspace per Telegram chat
   - Different chats = different workspaces
   - Independent Teams, Users, Schedules
   - Isolated data completely

2. **Slack Workspace**
   - One workspace per Slack organization/workspace
   - Multiple channels in same workspace share Teams/Users/Schedules
   - Data shared across channels in same Slack workspace

### Database Model Relationships

```
Workspace (root container)
├── name: str (Telegram: "TG Chat 12345", Slack: "MyOrg")
├── workspace_type: enum ('telegram' | 'slack')
├── external_id: str (Telegram chat_id or Slack workspace_id)
│
├── ChatChannel (specific chat/channel) [1:N]
│   ├── messenger: 'telegram' | 'slack'
│   └── external_id: str (chat_id or channel_id)
│
├── User (people in this workspace) [1:N]
│   ├── telegram_username (unique per workspace)
│   ├── slack_user_id (unique per workspace)
│   ├── display_name
│   └── TeamMember [M:N] → Team
│
└── Team (duty/shift teams) [1:N]
    ├── name (unique per workspace)
    ├── display_name
    ├── has_shifts
    ├── team_lead_user → User
    ├── members [M:N] → User
    ├── Schedule [1:N]
    ├── Shift [1:N]
    └── Escalation [1:N]
```

### Key Changes

| Entity | Before | After |
|--------|--------|-------|
| **User** | Global | Per Workspace |
| **Team** | Global | Per Workspace |
| **telegram_username** | Unique globally | Unique per workspace |
| **slack_user_id** | Unique globally | Unique per workspace |
| **Chat/Channel tracking** | None | ChatChannel model |

## Backward Compatibility

This is a **breaking change**. All existing data will be migrated to a default workspace:

- **Telegram**: `workspace_id=1` for existing chat
- **Slack**: `workspace_id=1` for existing workspace

## Implementation Steps

1. Update `models.py` with new Workspace and ChatChannel
2. Create migration script
3. Update services to accept `workspace_id` parameter
4. Update handlers to extract `workspace_id` from context
5. Update command handlers to pass `workspace_id`
6. Update scheduled tasks to be workspace-aware
7. Test multi-workspace isolation

## Future Enhancements

- Multi-channel support in Telegram (Private groups, channels)
- Workspace settings (timezone per workspace)
- Cross-workspace team references
