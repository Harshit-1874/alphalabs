-- Create exports table

CREATE TABLE exports (
	user_id UUID NOT NULL, 
	format VARCHAR(10) DEFAULT 'zip' NOT NULL, 
	status VARCHAR(20) DEFAULT 'processing' NOT NULL, 
	progress_pct INTEGER DEFAULT '0' NOT NULL, 
	error_message TEXT, 
	download_url TEXT, 
	size_mb DECIMAL(10, 2), 
	expires_at TIMESTAMP WITH TIME ZONE, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT check_export_status_values CHECK (status IN ('processing', 'ready', 'failed', 'expired')), 
	CONSTRAINT check_export_format_values CHECK (format IN ('json', 'zip')), 
	CONSTRAINT check_progress_pct_range CHECK (progress_pct BETWEEN 0 AND 100), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;

-- Index: idx_exports_user
CREATE INDEX idx_exports_user ON exports (user_id);

-- Index: idx_exports_status
CREATE INDEX idx_exports_status ON exports (user_id, status);

-- Index: idx_exports_created
CREATE INDEX idx_exports_created ON exports USING btree (user_id, created_at DESC);
