-- Migration: Add workspace support for multi-tenant data isolation
-- This migration adds Workspace and ChatChannel tables, and updates existing tables
-- to support workspace isolation.

-- Step 1: Create Workspace table
CREATE TABLE IF NOT EXISTS workspace (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR NOT NULL,
    workspace_type VARCHAR NOT NULL,  -- 'telegram' or 'slack'
    external_id VARCHAR NOT NULL UNIQUE,  -- chat_id or workspace_id
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Step 2: Create ChatChannel table
CREATE TABLE IF NOT EXISTS chat_channel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER NOT NULL,
    messenger VARCHAR NOT NULL,  -- 'telegram' or 'slack'
    external_id VARCHAR NOT NULL,  -- chat_id or channel_id
    display_name VARCHAR NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(workspace_id) REFERENCES workspace(id),
    UNIQUE(workspace_id, external_id)
);

-- Step 3: Create default workspace (for migrating existing data)
INSERT OR IGNORE INTO workspace (id, name, workspace_type, external_id, created_at)
VALUES (1, 'Default Workspace', 'telegram', '0', datetime('now'));

-- Step 4: Add workspace_id to user table
-- Note: For SQLite, we need to use ALTER TABLE
-- First, rename old table
ALTER TABLE user RENAME TO user_old;

-- Create new user table with workspace_id
CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER NOT NULL,
    telegram_username VARCHAR,
    slack_user_id VARCHAR,
    display_name VARCHAR NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(workspace_id) REFERENCES workspace(id),
    UNIQUE(workspace_id, telegram_username),
    UNIQUE(workspace_id, slack_user_id)
);

-- Migrate existing data to default workspace
INSERT INTO user (id, workspace_id, telegram_username, slack_user_id, display_name, created_at)
SELECT id, 1, telegram_username, slack_user_id, display_name, created_at FROM user_old;

-- Drop old table
DROP TABLE user_old;

-- Step 5: Add workspace_id to team table
ALTER TABLE team RENAME TO team_old;

CREATE TABLE team (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER NOT NULL,
    name VARCHAR NOT NULL,
    display_name VARCHAR NOT NULL,
    has_shifts BOOLEAN DEFAULT 0,
    team_lead_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(workspace_id) REFERENCES workspace(id),
    FOREIGN KEY(team_lead_id) REFERENCES user(id),
    UNIQUE(workspace_id, name)
);

-- Migrate existing data to default workspace
INSERT INTO team (id, workspace_id, name, display_name, has_shifts, team_lead_id, created_at)
SELECT id, 1, name, display_name, has_shifts, team_lead_id, created_at FROM team_old;

-- Drop old table
DROP TABLE team_old;

-- Step 6: Create indices for performance
CREATE INDEX IF NOT EXISTS idx_workspace_external_id ON workspace(external_id);
CREATE INDEX IF NOT EXISTS idx_chat_channel_workspace_id ON chat_channel(workspace_id);
CREATE INDEX IF NOT EXISTS idx_user_workspace_id ON user(workspace_id);
CREATE INDEX IF NOT EXISTS idx_team_workspace_id ON team(workspace_id);
