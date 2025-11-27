-- Create certificates table

CREATE TABLE certificates (
	result_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	verification_code VARCHAR(30) NOT NULL, 
	agent_name VARCHAR(100) NOT NULL, 
	model VARCHAR(100) NOT NULL, 
	mode VARCHAR(10) NOT NULL, 
	test_type VARCHAR(10) NOT NULL, 
	asset VARCHAR(20) NOT NULL, 
	pnl_pct DECIMAL(10, 4) NOT NULL, 
	win_rate DECIMAL(5, 2) NOT NULL, 
	total_trades INTEGER NOT NULL, 
	max_drawdown_pct DECIMAL(10, 4), 
	sharpe_ratio DECIMAL(6, 3), 
	duration_display VARCHAR(50) NOT NULL, 
	test_period VARCHAR(100) NOT NULL, 
	pdf_url TEXT, 
	image_url TEXT, 
	qr_code_url TEXT, 
	share_url TEXT NOT NULL, 
	view_count INTEGER DEFAULT '0' NOT NULL, 
	issued_at TIMESTAMP WITH TIME ZONE DEFAULT 'NOW()' NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT 'NOW()' NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT check_cert_test_type_values CHECK (test_type IN ('backtest', 'forward')), 
	CONSTRAINT check_cert_mode_values CHECK (mode IN ('monk', 'omni')), 
	UNIQUE (result_id), 
	FOREIGN KEY(result_id) REFERENCES test_results (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	UNIQUE (verification_code)
)

;

-- Index: idx_certificates_user
CREATE INDEX idx_certificates_user ON certificates (user_id);

-- Index: idx_certificates_result
CREATE INDEX idx_certificates_result ON certificates (result_id);

-- Index: idx_certificates_code
CREATE INDEX idx_certificates_code ON certificates (verification_code);
