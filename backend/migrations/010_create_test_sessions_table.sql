-- Create test_sessions table

CREATE TABLE test_sessions (
	user_id UUID NOT NULL, 
	agent_id UUID NOT NULL, 
	type VARCHAR(10) NOT NULL, 
	status VARCHAR(20) DEFAULT 'configuring' NOT NULL, 
	asset VARCHAR(20) NOT NULL, 
	timeframe VARCHAR(10) NOT NULL, 
	starting_capital DECIMAL(15, 2) NOT NULL, 
	safety_mode BOOLEAN DEFAULT 'true' NOT NULL, 
	allow_leverage BOOLEAN DEFAULT 'false' NOT NULL, 
	date_preset VARCHAR(20), 
	start_date DATE, 
	end_date DATE, 
	playback_speed VARCHAR(10), 
	total_candles INTEGER, 
	current_candle INTEGER DEFAULT '0' NOT NULL, 
	email_notifications BOOLEAN DEFAULT 'false' NOT NULL, 
	auto_stop_on_loss BOOLEAN DEFAULT 'false' NOT NULL, 
	auto_stop_loss_pct DECIMAL(5, 2), 
	current_equity DECIMAL(15, 2), 
	current_pnl_pct DECIMAL(10, 4), 
	max_drawdown_pct DECIMAL(10, 4), 
	elapsed_seconds INTEGER DEFAULT '0' NOT NULL, 
	open_position JSONB, 
	started_at TIMESTAMP WITH TIME ZONE, 
	paused_at TIMESTAMP WITH TIME ZONE, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT check_type_values CHECK (type IN ('backtest', 'forward')), 
	CONSTRAINT check_status_values CHECK (status IN ('configuring', 'initializing', 'running', 'paused', 'completed', 'failed', 'stopped')), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(agent_id) REFERENCES agents (id) ON DELETE CASCADE
)

;

-- Index: idx_sessions_type
CREATE INDEX idx_sessions_type ON test_sessions (type, status);

-- Index: idx_sessions_user
CREATE INDEX idx_sessions_user ON test_sessions (user_id);

-- Index: idx_sessions_active
CREATE INDEX idx_sessions_active ON test_sessions (user_id, status) WHERE status IN ('running', 'paused');

-- Index: idx_sessions_agent
CREATE INDEX idx_sessions_agent ON test_sessions (agent_id);
