-- Refactor User table to remove platform-specific fields and drop display_name column
-- These fields are now handled via UserAccount and dynamic property

-- 1. Create UserAccount records for existing Telegram users
INSERT INTO user_account (user_id, workspace_id, provider, provider_id, username, created_at)
SELECT id, workspace_id, 'telegram', telegram_id::text, telegram_username, created_at
FROM "user"
WHERE telegram_id IS NOT NULL
ON CONFLICT (provider_id, workspace_id) DO NOTHING;

-- 2. Create UserAccount records for existing Slack users
INSERT INTO user_account (user_id, workspace_id, provider, provider_id, username, created_at)
SELECT id, workspace_id, 'slack', slack_user_id, NULL, created_at
FROM "user"
WHERE slack_user_id IS NOT NULL
ON CONFLICT (provider_id, workspace_id) DO NOTHING;

-- 3. Remove unique constraints first
ALTER TABLE "user" DROP CONSTRAINT IF EXISTS user_workspace_telegram_username_unique;
ALTER TABLE "user" DROP CONSTRAINT IF EXISTS user_workspace_slack_user_id_unique;
-- These might have different names depending on how they were created
-- SQLAlchemy names them idx_user_workspace_telegram_username etc in 000_initial_schema.sql
DROP INDEX IF EXISTS idx_user_workspace_telegram_username;
DROP INDEX IF EXISTS idx_user_workspace_slack_user_id;

-- 4. Drop columns
ALTER TABLE "user" DROP COLUMN IF EXISTS telegram_id;
ALTER TABLE "user" DROP COLUMN IF EXISTS telegram_username;
ALTER TABLE "user" DROP COLUMN IF EXISTS slack_user_id;

-- display_name is kept in the current model

