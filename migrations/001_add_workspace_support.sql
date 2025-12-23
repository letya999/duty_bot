-- Migration: Add workspace support for multi-tenant data isolation
-- This migration adds Workspace and ChatChannel tables, and updates existing tables
-- to support workspace isolation.

-- Step 1: Create Workspace table
CREATE TABLE IF NOT EXISTS workspace (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    workspace_type VARCHAR NOT NULL,
    external_id VARCHAR NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(workspace_type, external_id)
);

-- Step 2: Create ChatChannel table
CREATE TABLE IF NOT EXISTS chat_channel (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL,
    messenger VARCHAR NOT NULL,
    external_id VARCHAR NOT NULL,
    display_name VARCHAR NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(workspace_id) REFERENCES workspace(id),
    UNIQUE(workspace_id, external_id)
);

-- Step 3: Create default workspace (for migrating existing data)
INSERT INTO workspace (name, workspace_type, external_id, created_at)
VALUES ('Default Workspace', 'telegram', '0', CURRENT_TIMESTAMP)
ON CONFLICT (workspace_type, external_id) DO NOTHING;

-- Step 4: Create indices for performance
CREATE INDEX IF NOT EXISTS idx_workspace_external_id ON workspace(external_id);
CREATE INDEX IF NOT EXISTS idx_chat_channel_workspace_id ON chat_channel(workspace_id);
