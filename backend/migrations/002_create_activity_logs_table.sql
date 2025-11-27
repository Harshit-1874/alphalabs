-- Create activity_logs table

CREATE TABLE activity_logs (
	user_id UUID NOT NULL, 
	agent_id UUID, 
	session_id UUID, 
	result_id UUID, 
	activity_type VARCHAR(30) NOT NULL, 
	description TEXT NOT NULL, 
	activity_metadata JSONB, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT check_activity_type_values CHECK (activity_type IN ('agent_created', 'agent_updated', 'agent_deleted', 'test_started', 'test_completed', 'result_generated', 'certificate_created', 'settings_updated', 'api_key_added')), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(agent_id) REFERENCES agents (id) ON DELETE SET NULL, 
	FOREIGN KEY(session_id) REFERENCES test_sessions (id) ON DELETE SET NULL, 
	FOREIGN KEY(result_id) REFERENCES test_results (id) ON DELETE SET NULL
)

;

-- Index: idx_activity_logs_type
CREATE INDEX idx_activity_logs_type ON activity_logs (user_id, activity_type);

-- Index: idx_activity_logs_user
CREATE INDEX idx_activity_logs_user ON activity_logs (user_id);

-- Index: idx_activity_logs_date
CREATE INDEX idx_activity_logs_date ON activity_logs USING btree (user_id, created_at DESC);
