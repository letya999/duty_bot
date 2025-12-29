-- Refactor User table to remove platform-specific fields and drop display_name column
-- These fields are now handled via UserAccount and dynamic property

-- Remove unique constraints first
ALTER TABLE "user" DROP CONSTRAINT IF EXISTS user_workspace_telegram_username_unique;
ALTER TABLE "user" DROP CONSTRAINT IF EXISTS user_workspace_slack_user_id_unique;

-- Drop columns
ALTER TABLE "user" DROP COLUMN IF EXISTS telegram_id;
ALTER TABLE "user" DROP COLUMN IF EXISTS telegram_username;
ALTER TABLE "user" DROP COLUMN IF EXISTS slack_user_id;
-- display_name is kept

