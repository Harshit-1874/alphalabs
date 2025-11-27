-- Create api_keys table

CREATE TABLE api_keys (
	user_id UUID NOT NULL, 
	provider VARCHAR(50) DEFAULT 'openrouter' NOT NULL, 
	label VARCHAR(100), 
	encrypted_key TEXT NOT NULL, 
	key_prefix VARCHAR(20), 
	is_default BOOLEAN DEFAULT 'false' NOT NULL, 
	status VARCHAR(20) DEFAULT 'untested' NOT NULL, 
	last_used_at TIMESTAMP WITHOUT TIME ZONE, 
	last_validated_at TIMESTAMP WITHOUT TIME ZONE, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT check_status_values CHECK (status IN ('valid', 'invalid', 'untested')), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;

-- Index: idx_api_keys_user
CREATE INDEX idx_api_keys_user ON api_keys (user_id);

-- Index: idx_api_keys_default
CREATE INDEX idx_api_keys_default ON api_keys (user_id, is_default) WHERE is_default = true;
