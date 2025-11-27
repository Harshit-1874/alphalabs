-- Create notifications table

CREATE TABLE notifications (
	user_id UUID NOT NULL, 
	session_id UUID, 
	result_id UUID, 
	type VARCHAR(30) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	message TEXT NOT NULL, 
	is_read BOOLEAN DEFAULT 'false' NOT NULL, 
	read_at TIMESTAMP WITH TIME ZONE, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT check_notification_type_values CHECK (type IN ('test_completed', 'trade_executed', 'stop_loss_hit', 'system_alert', 'daily_summary')), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(session_id) REFERENCES test_sessions (id) ON DELETE CASCADE, 
	FOREIGN KEY(result_id) REFERENCES test_results (id) ON DELETE CASCADE
)

;

-- Index: idx_notifications_read
CREATE INDEX idx_notifications_read ON notifications (user_id, is_read);

-- Index: idx_notifications_user
CREATE INDEX idx_notifications_user ON notifications (user_id);

-- Index: idx_notifications_date
CREATE INDEX idx_notifications_date ON notifications USING btree (user_id, created_at DESC);
