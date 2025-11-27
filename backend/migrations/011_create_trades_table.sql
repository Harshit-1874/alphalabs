-- Create trades table

CREATE TABLE trades (
	session_id UUID NOT NULL, 
	trade_number INTEGER NOT NULL, 
	type VARCHAR(10) NOT NULL, 
	entry_price DECIMAL(20, 8) NOT NULL, 
	entry_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	entry_candle INTEGER, 
	entry_reasoning TEXT, 
	exit_price DECIMAL(20, 8), 
	exit_time TIMESTAMP WITH TIME ZONE, 
	exit_candle INTEGER, 
	exit_type VARCHAR(20), 
	exit_reasoning TEXT, 
	size DECIMAL(20, 8) NOT NULL, 
	leverage INTEGER DEFAULT '1' NOT NULL, 
	pnl_amount DECIMAL(15, 2), 
	pnl_pct DECIMAL(10, 4), 
	stop_loss DECIMAL(20, 8), 
	take_profit DECIMAL(20, 8), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT 'NOW()' NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT check_trade_type_values CHECK (type IN ('long', 'short')), 
	CONSTRAINT check_exit_type_values CHECK (exit_type IN ('take_profit', 'stop_loss', 'manual', 'signal')), 
	FOREIGN KEY(session_id) REFERENCES test_sessions (id) ON DELETE CASCADE
)

;

-- Index: idx_trades_session
CREATE INDEX idx_trades_session ON trades (session_id);

-- Index: idx_trades_session_time
CREATE INDEX idx_trades_session_time ON trades (session_id, entry_time);
