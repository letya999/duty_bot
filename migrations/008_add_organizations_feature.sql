-- Migration: Add Organizations feature for grouping workspaces
-- This migration creates Organization and UserAccount tables and updates related tables
-- to support multi-workspace organizations

-- Step 1: Create organization table
CREATE TABLE IF NOT EXISTS organization (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    created_by_user_id INTEGER,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Step 2: Create user_account table (for multiple login methods per user)
CREATE TABLE IF NOT EXISTS user_account (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    workspace_id INTEGER,
    provider VARCHAR NOT NULL,  -- 'slack', 'telegram'
    provider_id VARCHAR NOT NULL,  -- slack_user_id or telegram_id
    username VARCHAR,  -- slack username or telegram username
    account_email VARCHAR,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES "user"(id),
    FOREIGN KEY(workspace_id) REFERENCES workspace(id),
    UNIQUE(provider_id, workspace_id)
);

-- Step 3: Add organization_id to user table
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS organization_id INTEGER;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_user_organization_id') THEN
        ALTER TABLE "user" ADD CONSTRAINT fk_user_organization_id FOREIGN KEY (organization_id) REFERENCES organization(id);
    END IF;
END $$;

-- Step 4: Add is_superadmin to user table
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_superadmin BOOLEAN DEFAULT FALSE;

-- Step 5: Add organization_id to workspace table
ALTER TABLE workspace ADD COLUMN IF NOT EXISTS organization_id INTEGER;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_workspace_organization_id') THEN
        ALTER TABLE workspace ADD CONSTRAINT fk_workspace_organization_id FOREIGN KEY (organization_id) REFERENCES organization(id);
    END IF;
END $$;

-- Step 6: Add organization_id to team table
ALTER TABLE team ADD COLUMN IF NOT EXISTS organization_id INTEGER;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_team_organization_id') THEN
        ALTER TABLE team ADD CONSTRAINT fk_team_organization_id FOREIGN KEY (organization_id) REFERENCES organization(id);
    END IF;
END $$;

-- Step 7: Add organization_id to incident table
ALTER TABLE incident ADD COLUMN IF NOT EXISTS organization_id INTEGER;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_incident_organization_id') THEN
        ALTER TABLE incident ADD CONSTRAINT fk_incident_organization_id FOREIGN KEY (organization_id) REFERENCES organization(id);
    END IF;
END $$;

-- Step 8: Add organization_id to escalation table
ALTER TABLE escalation ADD COLUMN IF NOT EXISTS organization_id INTEGER;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_escalation_organization_id') THEN
        ALTER TABLE escalation ADD CONSTRAINT fk_escalation_organization_id FOREIGN KEY (organization_id) REFERENCES organization(id);
    END IF;
END $$;

-- Step 9: Create indices for performance
CREATE INDEX IF NOT EXISTS idx_organization_created_by_user_id ON organization(created_by_user_id);
CREATE INDEX IF NOT EXISTS idx_user_account_user_id ON user_account(user_id);
CREATE INDEX IF NOT EXISTS idx_user_account_workspace_id ON user_account(workspace_id);
CREATE INDEX IF NOT EXISTS idx_user_account_provider ON user_account(provider);
CREATE INDEX IF NOT EXISTS idx_user_organization_id ON "user"(organization_id);
CREATE INDEX IF NOT EXISTS idx_workspace_organization_id ON workspace(organization_id);
CREATE INDEX IF NOT EXISTS idx_team_organization_id ON team(organization_id);
CREATE INDEX IF NOT EXISTS idx_incident_organization_id ON incident(organization_id);
CREATE INDEX IF NOT EXISTS idx_escalation_organization_id ON escalation(organization_id);
