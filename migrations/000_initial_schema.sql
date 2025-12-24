-- Migration: Create initial schema with all base tables
-- This migration creates the core tables needed by the application
-- and must be run before other migrations

-- Step 1: Create user table
CREATE TABLE IF NOT EXISTS "user" (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL,
    telegram_id BIGINT,
    telegram_username VARCHAR,
    username VARCHAR,
    slack_user_id VARCHAR,
    first_name VARCHAR,
    last_name VARCHAR,
    display_name VARCHAR,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Step 2: Create team table
CREATE TABLE IF NOT EXISTS team (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL,
    name VARCHAR NOT NULL,
    display_name VARCHAR NOT NULL,
    has_shifts BOOLEAN DEFAULT FALSE,
    team_lead_id INTEGER,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Step 3: Create team_members association table
CREATE TABLE IF NOT EXISTS team_members (
    user_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, team_id)
);

-- Step 4: Create rotation_config table
CREATE TABLE IF NOT EXISTS rotation_config (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL UNIQUE,
    enabled BOOLEAN DEFAULT FALSE,
    member_ids JSON NOT NULL,
    last_assigned_user_id INTEGER,
    last_assigned_date DATE,
    skip_unavailable BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Step 5: Create schedule table
CREATE TABLE IF NOT EXISTS schedule (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL,
    user_id INTEGER,
    date DATE NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Step 6: Create shift table
CREATE TABLE IF NOT EXISTS shift (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL,
    date DATE NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Step 7: Create shift_members association table
CREATE TABLE IF NOT EXISTS shift_members (
    user_id INTEGER NOT NULL,
    shift_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, shift_id)
);

-- Step 8: Create escalation table
CREATE TABLE IF NOT EXISTS escalation (
    id SERIAL PRIMARY KEY,
    team_id INTEGER,
    cto_id INTEGER,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Step 9: Create escalation_event table
CREATE TABLE IF NOT EXISTS escalation_event (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL,
    messenger VARCHAR NOT NULL,
    initiated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP WITHOUT TIME ZONE,
    escalated_to_level2_at TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Step 10: Create indices for performance
CREATE INDEX IF NOT EXISTS idx_user_workspace_id ON "user"(workspace_id);
CREATE INDEX IF NOT EXISTS idx_user_telegram_id ON "user"(telegram_id);
CREATE INDEX IF NOT EXISTS idx_user_telegram_username ON "user"(telegram_username);
CREATE INDEX IF NOT EXISTS idx_user_slack_user_id ON "user"(slack_user_id);
CREATE INDEX IF NOT EXISTS idx_user_username ON "user"(username);
CREATE INDEX IF NOT EXISTS idx_user_is_admin ON "user"(is_admin);

CREATE INDEX IF NOT EXISTS idx_team_workspace_id ON team(workspace_id);
CREATE INDEX IF NOT EXISTS idx_team_name ON team(name);
CREATE INDEX IF NOT EXISTS idx_schedule_team_id ON schedule(team_id);
CREATE INDEX IF NOT EXISTS idx_schedule_date ON schedule(date);
CREATE INDEX IF NOT EXISTS idx_shift_team_id ON shift(team_id);
CREATE INDEX IF NOT EXISTS idx_shift_date ON shift(date);
CREATE INDEX IF NOT EXISTS idx_escalation_team_id ON escalation(team_id);
CREATE INDEX IF NOT EXISTS idx_escalation_event_team_id ON escalation_event(team_id);

-- Step 11: Create unique constraints
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_workspace_telegram_username ON "user"(workspace_id, telegram_username) WHERE telegram_username IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_workspace_slack_user_id ON "user"(workspace_id, slack_user_id) WHERE slack_user_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_team_workspace_name ON team(workspace_id, name);
CREATE UNIQUE INDEX IF NOT EXISTS idx_schedule_team_date ON schedule(team_id, date);
CREATE UNIQUE INDEX IF NOT EXISTS idx_shift_team_date ON shift(team_id, date);
