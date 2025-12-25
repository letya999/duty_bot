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

-- Step 4: Add foreign key constraints to user and team tables
-- These reference the workspace table created above
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_user_workspace_id') THEN
        ALTER TABLE "user" ADD CONSTRAINT fk_user_workspace_id FOREIGN KEY (workspace_id) REFERENCES workspace(id);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_team_workspace_id') THEN
        ALTER TABLE team ADD CONSTRAINT fk_team_workspace_id FOREIGN KEY (workspace_id) REFERENCES workspace(id);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_team_lead_id') THEN
        ALTER TABLE team ADD CONSTRAINT fk_team_lead_id FOREIGN KEY (team_lead_id) REFERENCES "user"(id);
    END IF;
END $$;

-- Step 5: Add foreign key constraints to other tables
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_team_members_user_id') THEN
        ALTER TABLE team_members ADD CONSTRAINT fk_team_members_user_id FOREIGN KEY (user_id) REFERENCES "user"(id);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_team_members_team_id') THEN
        ALTER TABLE team_members ADD CONSTRAINT fk_team_members_team_id FOREIGN KEY (team_id) REFERENCES team(id);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_rotation_config_team_id') THEN
        ALTER TABLE rotation_config ADD CONSTRAINT fk_rotation_config_team_id FOREIGN KEY (team_id) REFERENCES team(id);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_rotation_config_last_assigned_user_id') THEN
        ALTER TABLE rotation_config ADD CONSTRAINT fk_rotation_config_last_assigned_user_id FOREIGN KEY (last_assigned_user_id) REFERENCES "user"(id);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_schedule_team_id') THEN
        ALTER TABLE schedule ADD CONSTRAINT fk_schedule_team_id FOREIGN KEY (team_id) REFERENCES team(id);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_schedule_user_id') THEN
        ALTER TABLE schedule ADD CONSTRAINT fk_schedule_user_id FOREIGN KEY (user_id) REFERENCES "user"(id);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_shift_team_id') THEN
        ALTER TABLE shift ADD CONSTRAINT fk_shift_team_id FOREIGN KEY (team_id) REFERENCES team(id);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_shift_members_user_id') THEN
        ALTER TABLE shift_members ADD CONSTRAINT fk_shift_members_user_id FOREIGN KEY (user_id) REFERENCES "user"(id);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_shift_members_shift_id') THEN
        ALTER TABLE shift_members ADD CONSTRAINT fk_shift_members_shift_id FOREIGN KEY (shift_id) REFERENCES shift(id);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_escalation_team_id') THEN
        ALTER TABLE escalation ADD CONSTRAINT fk_escalation_team_id FOREIGN KEY (team_id) REFERENCES team(id);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_escalation_cto_id') THEN
        ALTER TABLE escalation ADD CONSTRAINT fk_escalation_cto_id FOREIGN KEY (cto_id) REFERENCES "user"(id);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_escalation_event_team_id') THEN
        ALTER TABLE escalation_event ADD CONSTRAINT fk_escalation_event_team_id FOREIGN KEY (team_id) REFERENCES team(id);
    END IF;
END $$;

-- Step 6: Create indices for performance
CREATE INDEX IF NOT EXISTS idx_workspace_external_id ON workspace(external_id);
CREATE INDEX IF NOT EXISTS idx_chat_channel_workspace_id ON chat_channel(workspace_id);
