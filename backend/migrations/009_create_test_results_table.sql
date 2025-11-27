-- Create test_results table

CREATE TABLE test_results (
	session_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	agent_id UUID NOT NULL, 
	type VARCHAR(10) NOT NULL, 
	asset VARCHAR(20) NOT NULL, 
	mode VARCHAR(10) NOT NULL, 
	timeframe VARCHAR(10) NOT NULL, 
	start_date TIMESTAMP WITH TIME ZONE NOT NULL, 
	end_date TIMESTAMP WITH TIME ZONE NOT NULL, 
	duration_seconds INTEGER NOT NULL, 
	duration_display VARCHAR(50), 
	starting_capital DECIMAL(15, 2) NOT NULL, 
	ending_capital DECIMAL(15, 2) NOT NULL, 
	total_pnl_amount DECIMAL(15, 2) NOT NULL, 
	total_pnl_pct DECIMAL(10, 4) NOT NULL, 
	total_trades INTEGER NOT NULL, 
	winning_trades INTEGER NOT NULL, 
	losing_trades INTEGER NOT NULL, 
	win_rate DECIMAL(5, 2) NOT NULL, 
	max_drawdown_pct DECIMAL(10, 4), 
	sharpe_ratio DECIMAL(6, 3), 
	profit_factor DECIMAL(6, 3), 
	avg_trade_pnl DECIMAL(10, 4), 
	best_trade_pnl DECIMAL(10, 4), 
	worst_trade_pnl DECIMAL(10, 4), 
	avg_holding_time_seconds INTEGER, 
	avg_holding_time_display VARCHAR(50), 
	equity_curve JSONB, 
	ai_summary TEXT, 
	is_profitable BOOLEAN GENERATED ALWAYS AS ((total_pnl_pct >= 0)) STORED NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT 'NOW()' NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT check_result_type_values CHECK (type IN ('backtest', 'forward')), 
	CONSTRAINT check_result_mode_values CHECK (mode IN ('monk', 'omni')), 
	UNIQUE (session_id), 
	FOREIGN KEY(session_id) REFERENCES test_sessions (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(agent_id) REFERENCES agents (id) ON DELETE CASCADE
)

;

-- Index: idx_results_profitable
CREATE INDEX idx_results_profitable ON test_results (user_id, is_profitable);

-- Index: idx_results_user
CREATE INDEX idx_results_user ON test_results (user_id);

-- Index: idx_results_date
CREATE INDEX idx_results_date ON test_results USING btree (user_id, created_at DESC);

-- Index: idx_results_type
CREATE INDEX idx_results_type ON test_results (user_id, type);

-- Index: idx_results_agent
CREATE INDEX idx_results_agent ON test_results (agent_id);
