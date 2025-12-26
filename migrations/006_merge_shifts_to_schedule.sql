-- Add is_shift column to schedule
ALTER TABLE schedule ADD COLUMN is_shift BOOLEAN DEFAULT FALSE;

-- Update unique constraint on schedule
ALTER TABLE schedule DROP CONSTRAINT IF EXISTS schedule_team_date_unique;
ALTER TABLE schedule ADD CONSTRAINT schedule_team_user_date_unique UNIQUE (team_id, user_id, date);

-- Migrate data from shifts to schedules if tables exist
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'shift_members') THEN
        INSERT INTO schedule (team_id, user_id, "date", is_shift, created_at)
        SELECT s.team_id, sm.user_id, s.date, TRUE, s.created_at
        FROM shift s
        JOIN shift_members sm ON s.id = sm.shift_id
        ON CONFLICT (team_id, user_id, date) DO NOTHING;
    END IF;
END $$;

-- Drop old shift tables
DROP TABLE IF EXISTS shift_members cascade;
DROP TABLE IF EXISTS shift cascade;
