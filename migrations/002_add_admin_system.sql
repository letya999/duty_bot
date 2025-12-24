-- Migration: Add admin system with user roles and audit logs
-- This migration adds admin support and admin audit logging

-- Step 1: Add is_admin column to user table
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;

-- Step 2: Create admin_log table for audit trail
CREATE TABLE IF NOT EXISTS admin_log (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL,
    admin_user_id INTEGER NOT NULL,
    action VARCHAR NOT NULL,
    target_user_id INTEGER,
    timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    details TEXT,
    FOREIGN KEY(workspace_id) REFERENCES workspace(id),
    FOREIGN KEY(admin_user_id) REFERENCES "user"(id),
    FOREIGN KEY(target_user_id) REFERENCES "user"(id)
);

-- Step 3: Create indices for performance
CREATE INDEX IF NOT EXISTS idx_admin_log_workspace_id ON admin_log(workspace_id);
CREATE INDEX IF NOT EXISTS idx_admin_log_admin_user_id ON admin_log(admin_user_id);
CREATE INDEX IF NOT EXISTS idx_admin_log_target_user_id ON admin_log(target_user_id);
CREATE INDEX IF NOT EXISTS idx_admin_log_timestamp ON admin_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_user_is_admin ON "user"(is_admin);
