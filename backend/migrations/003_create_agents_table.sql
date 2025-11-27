-- Create agents table

CREATE TABLE agents (
	user_id UUID NOT NULL, 
	api_key_id UUID, 
	name VARCHAR(100) NOT NULL, 
	mode VARCHAR(10) NOT NULL, 
	model VARCHAR(100) NOT NULL, 
	indicators TEXT[] DEFAULT '{}' NOT NULL, 
	custom_indicators JSONB DEFAULT '[]' NOT NULL, 
	strategy_prompt TEXT NOT NULL, 
	tests_run INTEGER DEFAULT '0' NOT NULL, 
	best_pnl DECIMAL(10, 2), 
	total_profitable_tests INTEGER DEFAULT '0' NOT NULL, 
	avg_win_rate DECIMAL(5, 2), 
	avg_drawdown DECIMAL(5, 2), 
	is_archived BOOLEAN DEFAULT 'false' NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT check_mode_values CHECK (mode IN ('monk', 'omni')), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(api_key_id) REFERENCES api_keys (id) ON DELETE SET NULL
)

;

-- Index: idx_agents_active
CREATE INDEX idx_agents_active ON agents (user_id) WHERE is_archived = false;

-- Index: idx_agents_user
CREATE INDEX idx_agents_user ON agents (user_id);
