-- Migration: Add missing columns to user table
-- This migration ensures the user table has all columns required by the application

-- Add first_name if missing
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS first_name VARCHAR;

-- Add last_name if missing
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS last_name VARCHAR;

-- Add username if missing
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS username VARCHAR;

-- Add telegram_id if missing. Use BIGINT for Telegram IDs as they can exceed 32-bit integer range
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS telegram_id BIGINT;

-- Add indices for new columns
CREATE INDEX IF NOT EXISTS idx_user_username ON "user"(username);
CREATE INDEX IF NOT EXISTS idx_user_telegram_id ON "user"(telegram_id);
