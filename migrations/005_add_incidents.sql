-- Migration: Add incident tracking table
-- This migration adds the Incident table for tracking incident start/end times and metrics

-- Step 1: Create incident_status_enum type
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'incident_status_enum') THEN
        CREATE TYPE incident_status_enum AS ENUM ('active', 'resolved');
    END IF;
END
$$;

-- Step 2: Create incident table
CREATE TABLE IF NOT EXISTS incident (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL,
    name VARCHAR NOT NULL,
    status incident_status_enum DEFAULT 'active' NOT NULL,
    start_time TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    end_time TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(workspace_id) REFERENCES workspace(id)
);

-- Step 3: Create indices for performance
CREATE INDEX IF NOT EXISTS idx_incident_workspace_id ON incident(workspace_id);
CREATE INDEX IF NOT EXISTS idx_incident_start_time ON incident(start_time);
CREATE INDEX IF NOT EXISTS idx_incident_workspace_start_time ON incident(workspace_id, start_time);
CREATE INDEX IF NOT EXISTS idx_incident_workspace_status ON incident(workspace_id, status);
