-- Migration: Initial Schema (Consolidated 001-009)
-- This migration creates the complete schema for the Production ready application
-- Includes: Core User/Team, Workspaces, Organizations, Incidents, Duty Stats, and Google Calendar Integration

-- ==========================================
-- 1. Enums & Types
-- ==========================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'incident_status_enum') THEN
        CREATE TYPE incident_status_enum AS ENUM ('active', 'resolved');
    END IF;
END
$$;

-- ==========================================
-- 2. Organizations & Workspaces
-- ==========================================

-- Create Organization table (Level 0 - Top level grouping)
CREATE TABLE IF NOT EXISTS organization (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    created_by_user_id INTEGER, -- FK added later to avoid circular dependency
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create Workspace table (Level 1 - Tenant)
CREATE TABLE IF NOT EXISTS workspace (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER REFERENCES organization(id),
    name VARCHAR NOT NULL,
    workspace_type VARCHAR NOT NULL,
    external_id VARCHAR NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(workspace_type, external_id)
);

-- Index for workspaces
CREATE INDEX IF NOT EXISTS idx_workspace_external_id ON workspace(external_id);
CREATE INDEX IF NOT EXISTS idx_workspace_organization_id ON workspace(organization_id);

-- ==========================================
-- 3. Users & Accounts
-- ==========================================

-- Create User table (The central identity)
CREATE TABLE IF NOT EXISTS "user" (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspace(id), -- Main workspace link
    organization_id INTEGER REFERENCES organization(id),
    
    -- Identity fields
    telegram_id BIGINT,
    telegram_username VARCHAR,
    username VARCHAR,
    slack_user_id VARCHAR,
    first_name VARCHAR,
    last_name VARCHAR,
    display_name VARCHAR,
    
    -- Roles
    is_admin BOOLEAN DEFAULT FALSE,
    is_superadmin BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create UserAccount table (For linking multiple auth providers: Slack, Telegram, etc.)
CREATE TABLE IF NOT EXISTS user_account (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    workspace_id INTEGER REFERENCES workspace(id),
    provider VARCHAR NOT NULL,  -- 'slack', 'telegram'
    provider_id VARCHAR NOT NULL,  -- slack_user_id or telegram_id
    username VARCHAR,
    account_email VARCHAR,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider_id, workspace_id)
);

-- Indices for Users
CREATE INDEX IF NOT EXISTS idx_user_workspace_id ON "user"(workspace_id);
CREATE INDEX IF NOT EXISTS idx_user_organization_id ON "user"(organization_id);
CREATE INDEX IF NOT EXISTS idx_user_telegram_id ON "user"(telegram_id);
CREATE INDEX IF NOT EXISTS idx_user_telegram_username ON "user"(telegram_username);
CREATE INDEX IF NOT EXISTS idx_user_slack_user_id ON "user"(slack_user_id);
CREATE INDEX IF NOT EXISTS idx_user_username ON "user"(username);
CREATE INDEX IF NOT EXISTS idx_user_is_admin ON "user"(is_admin);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_workspace_telegram_username ON "user"(workspace_id, telegram_username) WHERE telegram_username IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_workspace_slack_user_id ON "user"(workspace_id, slack_user_id) WHERE slack_user_id IS NOT NULL;

-- Indices for UserAccounts
CREATE INDEX IF NOT EXISTS idx_user_account_user_id ON user_account(user_id);
CREATE INDEX IF NOT EXISTS idx_user_account_workspace_id ON user_account(workspace_id);
CREATE INDEX IF NOT EXISTS idx_user_account_provider ON user_account(provider);

-- Update Organization creator FK
ALTER TABLE organization ADD CONSTRAINT fk_organization_creator FOREIGN KEY (created_by_user_id) REFERENCES "user"(id);


-- ==========================================
-- 4. Teams & Structure
-- ==========================================

-- Create Team table
CREATE TABLE IF NOT EXISTS team (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspace(id),
    organization_id INTEGER REFERENCES organization(id),
    name VARCHAR NOT NULL,
    display_name VARCHAR NOT NULL,
    has_shifts BOOLEAN DEFAULT FALSE,
    team_lead_id INTEGER REFERENCES "user"(id),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_team_workspace_name ON team(workspace_id, name);
CREATE INDEX IF NOT EXISTS idx_team_workspace_id ON team(workspace_id);
CREATE INDEX IF NOT EXISTS idx_team_organization_id ON team(organization_id);
CREATE INDEX IF NOT EXISTS idx_team_name ON team(name);

-- Create Team Members association
CREATE TABLE IF NOT EXISTS team_members (
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    team_id INTEGER NOT NULL REFERENCES team(id),
    PRIMARY KEY (user_id, team_id)
);

-- Create ChatChannels (Linked to Workspace)
CREATE TABLE IF NOT EXISTS chat_channel (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspace(id),
    messenger VARCHAR NOT NULL,
    external_id VARCHAR NOT NULL,
    display_name VARCHAR NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(workspace_id, external_id)
);
CREATE INDEX IF NOT EXISTS idx_chat_channel_workspace_id ON chat_channel(workspace_id);


-- ==========================================
-- 5. Scheduling & Rotation
-- ==========================================

-- Rotation Config
CREATE TABLE IF NOT EXISTS rotation_config (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL UNIQUE REFERENCES team(id),
    enabled BOOLEAN DEFAULT FALSE,
    member_ids JSON NOT NULL,
    last_assigned_user_id INTEGER REFERENCES "user"(id),
    last_assigned_date DATE,
    skip_unavailable BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Schedule (Unified with Shifts)
CREATE TABLE IF NOT EXISTS schedule (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES team(id),
    user_id INTEGER REFERENCES "user"(id),
    date DATE NOT NULL,
    is_shift BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (team_id, user_id, date)
);

CREATE INDEX IF NOT EXISTS idx_schedule_team_id ON schedule(team_id);
CREATE INDEX IF NOT EXISTS idx_schedule_date ON schedule(date);


-- ==========================================
-- 6. Logic: Incidents, Escalations, Stats
-- ==========================================

-- Escalation Config
CREATE TABLE IF NOT EXISTS escalation (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES team(id),
    organization_id INTEGER REFERENCES organization(id),
    cto_id INTEGER REFERENCES "user"(id),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_escalation_team_id ON escalation(team_id);
CREATE INDEX IF NOT EXISTS idx_escalation_organization_id ON escalation(organization_id);

-- Escalation Events (History)
CREATE TABLE IF NOT EXISTS escalation_event (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES team(id),
    messenger VARCHAR NOT NULL,
    initiated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP WITHOUT TIME ZONE,
    escalated_to_level2_at TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_escalation_event_team_id ON escalation_event(team_id);

-- Incidents
CREATE TABLE IF NOT EXISTS incident (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspace(id),
    organization_id INTEGER REFERENCES organization(id),
    name VARCHAR NOT NULL,
    status incident_status_enum DEFAULT 'active' NOT NULL,
    start_time TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    end_time TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_incident_workspace_id ON incident(workspace_id);
CREATE INDEX IF NOT EXISTS idx_incident_organization_id ON incident(organization_id);
CREATE INDEX IF NOT EXISTS idx_incident_start_time ON incident(start_time);
CREATE INDEX IF NOT EXISTS idx_incident_workspace_start_time ON incident(workspace_id, start_time);
CREATE INDEX IF NOT EXISTS idx_incident_workspace_status ON incident(workspace_id, status);

-- Duty Stats
CREATE TABLE IF NOT EXISTS duty_stats (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspace(id),
    team_id INTEGER NOT NULL REFERENCES team(id),
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    duty_days INTEGER DEFAULT 0,
    shift_days INTEGER DEFAULT 0,
    hours_worked INTEGER,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(workspace_id, team_id, user_id, year, month)
);
CREATE INDEX IF NOT EXISTS idx_duty_stats_workspace_id ON duty_stats(workspace_id);
CREATE INDEX IF NOT EXISTS idx_duty_stats_team_id ON duty_stats(team_id);
CREATE INDEX IF NOT EXISTS idx_duty_stats_user_id ON duty_stats(user_id);
CREATE INDEX IF NOT EXISTS idx_duty_stats_year_month ON duty_stats(year, month);


-- ==========================================
-- 7. Integrations: Google Calendar
-- ==========================================

-- Google Calendar Integration
CREATE TABLE IF NOT EXISTS google_calendar_integration (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspace(id) ON DELETE CASCADE,
    service_account_key_encrypted TEXT NOT NULL,
    google_calendar_id VARCHAR(255) NOT NULL UNIQUE,
    public_calendar_url VARCHAR(500) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    last_sync_at TIMESTAMP NULL,
    service_account_email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_google_calendar_integration_workspace_id ON google_calendar_integration(workspace_id);
CREATE INDEX idx_google_calendar_integration_google_calendar_id ON google_calendar_integration(google_calendar_id);

-- Google Calendar Team Association
CREATE TABLE IF NOT EXISTS google_calendar_teams (
    integration_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    PRIMARY KEY (integration_id, team_id),
    FOREIGN KEY (integration_id) REFERENCES google_calendar_integration(id) ON DELETE CASCADE,
    FOREIGN KEY (team_id) REFERENCES team(id) ON DELETE CASCADE
);

-- ==========================================
-- 8. Admin Logs
-- ==========================================

CREATE TABLE IF NOT EXISTS admin_log (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspace(id),
    admin_user_id INTEGER NOT NULL REFERENCES "user"(id),
    action VARCHAR NOT NULL,
    target_user_id INTEGER REFERENCES "user"(id),
    timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    details TEXT
);
CREATE INDEX IF NOT EXISTS idx_admin_log_workspace_id ON admin_log(workspace_id);
CREATE INDEX IF NOT EXISTS idx_admin_log_admin_user_id ON admin_log(admin_user_id);
CREATE INDEX IF NOT EXISTS idx_admin_log_target_user_id ON admin_log(target_user_id);
CREATE INDEX IF NOT EXISTS idx_admin_log_timestamp ON admin_log(timestamp);

-- ==========================================
-- 9. Initial Seed Data
-- ==========================================

-- Create default workspace
INSERT INTO workspace (name, workspace_type, external_id, created_at)
VALUES ('Default Workspace', 'telegram', '0', CURRENT_TIMESTAMP)
ON CONFLICT (workspace_type, external_id) DO NOTHING;

