-- Create user_settings table

CREATE TABLE user_settings (
	user_id UUID NOT NULL, 
	theme VARCHAR(10) DEFAULT 'dark' NOT NULL, 
	accent_color VARCHAR(20) DEFAULT 'cyan' NOT NULL, 
	sidebar_collapsed BOOLEAN DEFAULT 'false' NOT NULL, 
	chart_grid_lines BOOLEAN DEFAULT 'true' NOT NULL, 
	chart_crosshair BOOLEAN DEFAULT 'true' NOT NULL, 
	chart_candle_colors VARCHAR(20) DEFAULT 'green_red' NOT NULL, 
	email_notifications JSONB DEFAULT '{
            "test_completed": true,
            "trade_executed": true,
            "daily_summary": false,
            "stop_loss_hit": true,
            "marketing": false
        }' NOT NULL, 
	inapp_notifications JSONB DEFAULT '{
            "show_toasts": true,
            "sound_effects": true,
            "desktop_notifications": false
        }' NOT NULL, 
	default_asset VARCHAR(20) DEFAULT 'BTC/USDT' NOT NULL, 
	default_timeframe VARCHAR(10) DEFAULT '1h' NOT NULL, 
	default_capital DECIMAL(15, 2) DEFAULT '10000.00' NOT NULL, 
	default_playback_speed VARCHAR(10) DEFAULT 'normal' NOT NULL, 
	safety_mode_default BOOLEAN DEFAULT 'true' NOT NULL, 
	allow_leverage_default BOOLEAN DEFAULT 'false' NOT NULL, 
	max_position_size_pct INTEGER DEFAULT '50' NOT NULL, 
	max_leverage INTEGER DEFAULT '5' NOT NULL, 
	max_loss_per_trade_pct DECIMAL(5, 2) DEFAULT '5.00' NOT NULL, 
	max_daily_loss_pct DECIMAL(5, 2) DEFAULT '10.00' NOT NULL, 
	max_total_drawdown_pct DECIMAL(5, 2) DEFAULT '20.00' NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT check_theme_values CHECK (theme IN ('dark', 'light', 'system')), 
	CONSTRAINT check_accent_color_values CHECK (accent_color IN ('cyan', 'purple', 'green', 'amber')), 
	CONSTRAINT check_max_position_size_pct_range CHECK (max_position_size_pct BETWEEN 1 AND 100), 
	CONSTRAINT check_max_leverage_range CHECK (max_leverage BETWEEN 1 AND 10), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;

-- Index: idx_user_settings_user
CREATE INDEX idx_user_settings_user ON user_settings (user_id);
