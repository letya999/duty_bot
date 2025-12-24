-- Migration: Add duty statistics table for Phase 5 reports
-- This migration adds the DutyStats table for tracking monthly duty and shift counts per user and team

-- Step 1: Create duty_stats table
CREATE TABLE IF NOT EXISTS duty_stats (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    duty_days INTEGER DEFAULT 0,
    shift_days INTEGER DEFAULT 0,
    hours_worked INTEGER,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(workspace_id) REFERENCES workspace(id),
    FOREIGN KEY(team_id) REFERENCES team(id),
    FOREIGN KEY(user_id) REFERENCES "user"(id),
    UNIQUE(workspace_id, team_id, user_id, year, month)
);

-- Step 2: Create indices for performance
CREATE INDEX IF NOT EXISTS idx_duty_stats_workspace_id ON duty_stats(workspace_id);
CREATE INDEX IF NOT EXISTS idx_duty_stats_team_id ON duty_stats(team_id);
CREATE INDEX IF NOT EXISTS idx_duty_stats_user_id ON duty_stats(user_id);
CREATE INDEX IF NOT EXISTS idx_duty_stats_year_month ON duty_stats(year, month);
CREATE INDEX IF NOT EXISTS idx_duty_stats_updated_at ON duty_stats(updated_at);
