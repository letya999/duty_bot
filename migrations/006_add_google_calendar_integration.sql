-- Add Google Calendar Integration table

CREATE TABLE IF NOT EXISTS google_calendar_integration (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL UNIQUE,
    service_account_key_encrypted TEXT NOT NULL,
    google_calendar_id VARCHAR(255) NOT NULL UNIQUE,
    public_calendar_url VARCHAR(500) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    last_sync_at TIMESTAMP NULL,
    service_account_email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workspace_id) REFERENCES workspace(id) ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX idx_google_calendar_integration_workspace_id ON google_calendar_integration(workspace_id);
CREATE INDEX idx_google_calendar_integration_google_calendar_id ON google_calendar_integration(google_calendar_id);
