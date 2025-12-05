-- Migration: Add Council Mode support to test_sessions and ai_thoughts tables
-- Date: 2025-12-05
-- Description: Adds fields to support multi-LLM council deliberation for trading decisions

-- Add council mode configuration fields to test_sessions
ALTER TABLE test_sessions 
ADD COLUMN council_mode BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN council_models JSONB DEFAULT NULL,
ADD COLUMN council_chairman_model VARCHAR(100) DEFAULT NULL;

-- Add comments for new fields
COMMENT ON COLUMN test_sessions.council_mode IS 'Whether council mode (multi-LLM deliberation) is enabled';
COMMENT ON COLUMN test_sessions.council_models IS 'Array of model IDs participating in council deliberation';
COMMENT ON COLUMN test_sessions.council_chairman_model IS 'Model ID for chairman that synthesizes final decision';

-- Add council deliberation fields to ai_thoughts
ALTER TABLE ai_thoughts 
ADD COLUMN council_stage1 JSONB DEFAULT NULL,
ADD COLUMN council_stage2 JSONB DEFAULT NULL,
ADD COLUMN council_metadata JSONB DEFAULT NULL;

-- Add comments for council fields
COMMENT ON COLUMN ai_thoughts.council_stage1 IS 'Stage 1: Individual responses from all council models';
COMMENT ON COLUMN ai_thoughts.council_stage2 IS 'Stage 2: Peer rankings of decisions';
COMMENT ON COLUMN ai_thoughts.council_metadata IS 'Council metadata (aggregate rankings, label mappings, etc.)';

-- Create index for querying council mode sessions
CREATE INDEX idx_sessions_council_mode ON test_sessions(council_mode) WHERE council_mode = TRUE;

