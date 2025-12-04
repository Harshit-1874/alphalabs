-- Update notification type constraint to include 'test_started'
ALTER TABLE notifications DROP CONSTRAINT IF EXISTS check_notification_type_values;
ALTER TABLE notifications ADD CONSTRAINT check_notification_type_values CHECK (
    type IN ('test_started', 'test_completed', 'trade_executed', 'stop_loss_hit', 'system_alert', 'daily_summary')
);

