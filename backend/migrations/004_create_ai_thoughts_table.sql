-- Create ai_thoughts table

CREATE TABLE ai_thoughts (
	session_id UUID NOT NULL, 
	trade_id UUID, 
	candle_number INTEGER NOT NULL, 
	timestamp TIMESTAMP WITH TIME ZONE NOT NULL, 
	candle_data JSONB NOT NULL, 
	indicator_values JSONB NOT NULL, 
	thought_type VARCHAR(20) NOT NULL, 
	reasoning TEXT NOT NULL, 
	decision VARCHAR(10), 
	confidence DECIMAL(5, 2), 
	order_data JSONB, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT 'NOW()' NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT check_thought_type_values CHECK (thought_type IN ('analysis', 'decision', 'execution')), 
	CONSTRAINT check_decision_values CHECK (decision IN ('long', 'short', 'hold', 'close')), 
	FOREIGN KEY(session_id) REFERENCES test_sessions (id) ON DELETE CASCADE, 
	FOREIGN KEY(trade_id) REFERENCES trades (id) ON DELETE SET NULL
)

;

-- Index: idx_thoughts_trade
CREATE INDEX idx_thoughts_trade ON ai_thoughts (trade_id) WHERE trade_id IS NOT NULL;

-- Index: idx_thoughts_session
CREATE INDEX idx_thoughts_session ON ai_thoughts (session_id);

-- Index: idx_thoughts_session_candle
CREATE INDEX idx_thoughts_session_candle ON ai_thoughts (session_id, candle_number);
