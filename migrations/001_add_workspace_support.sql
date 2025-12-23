-- Migration: Add workspace support for multi-tenant data isolation
-- This migration adds Workspace and ChatChannel tables, and updates existing tables
-- to support workspace isolation.

-- Step 1: Create Workspace table
CREATE TABLE IF NOT EXISTS workspace (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    workspace_type VARCHAR NOT NULL,  -- 'telegram' or 'slack'
    external_id VARCHAR NOT NULL,  -- chat_id or workspace_id
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(workspace_type, external_id)
);

-- Step 2: Create ChatChannel table
CREATE TABLE IF NOT EXISTS chat_channel (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL,
    messenger VARCHAR NOT NULL,  -- 'telegram' or 'slack'
    external_id VARCHAR NOT NULL,  -- chat_id or channel_id
    display_name VARCHAR NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(workspace_id) REFERENCES workspace(id),
    UNIQUE(workspace_id, external_id)
);

-- Step 2.5: Ensure Workspace unique constraint exists (in case it was created without it)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'workspace_type_external_id_unique'
    ) THEN
        ALTER TABLE workspace ADD CONSTRAINT workspace_type_external_id_unique UNIQUE (workspace_type, external_id);
    END IF;
END $$;

-- Step 3: Create default workspace (for migrating existing data)
INSERT INTO workspace (name, workspace_type, external_id, created_at)
VALUES ('Default Workspace', 'telegram', '0', CURRENT_TIMESTAMP)
ON CONFLICT (workspace_type, external_id) DO NOTHING;

-- Step 4: Add workspace_id to user table if not exists
-- Check if column exists, if not add it
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user' AND column_name = 'workspace_id'
    ) THEN
        ALTER TABLE "user" ADD COLUMN workspace_id INTEGER DEFAULT 1;
        ALTER TABLE "user" ADD CONSTRAINT fk_user_workspace
            FOREIGN KEY (workspace_id) REFERENCES workspace(id);
    END IF;
END $$;

-- Step 5: Add workspace_id to team table if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'team' AND column_name = 'workspace_id'
    ) THEN
        ALTER TABLE team ADD COLUMN workspace_id INTEGER DEFAULT 1;
        ALTER TABLE team ADD CONSTRAINT fk_team_workspace
            FOREIGN KEY (workspace_id) REFERENCES workspace(id);
    END IF;
END $$;

-- Step 6: Create indices for performance
CREATE INDEX IF NOT EXISTS idx_workspace_external_id ON workspace(external_id);
CREATE INDEX IF NOT EXISTS idx_chat_channel_workspace_id ON chat_channel(workspace_id);
CREATE INDEX IF NOT EXISTS idx_user_workspace_id ON "user"(workspace_id);
CREATE INDEX IF NOT EXISTS idx_team_workspace_id ON team(workspace_id);
