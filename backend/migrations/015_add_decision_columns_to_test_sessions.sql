-- Add decision_mode and decision_interval_candles columns to test_sessions table

-- Add decision_mode column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'test_sessions' AND column_name = 'decision_mode'
    ) THEN
        ALTER TABLE test_sessions
        ADD COLUMN decision_mode VARCHAR(20) DEFAULT 'every_candle' NOT NULL;
    END IF;
END $$;

-- Add decision_interval_candles column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'test_sessions' AND column_name = 'decision_interval_candles'
    ) THEN
        ALTER TABLE test_sessions
        ADD COLUMN decision_interval_candles INTEGER DEFAULT 1 NOT NULL;
    END IF;
END $$;

