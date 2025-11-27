-- Create market_data_cache table

CREATE TABLE market_data_cache (
	asset VARCHAR(20) NOT NULL, 
	timeframe VARCHAR(10) NOT NULL, 
	timestamp TIMESTAMP WITH TIME ZONE NOT NULL, 
	open DECIMAL(20, 8) NOT NULL, 
	high DECIMAL(20, 8) NOT NULL, 
	low DECIMAL(20, 8) NOT NULL, 
	close DECIMAL(20, 8) NOT NULL, 
	volume DECIMAL(20, 8) NOT NULL, 
	indicators JSONB, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_market_data_asset_timeframe_timestamp UNIQUE (asset, timeframe, timestamp)
)

;

-- Index: idx_market_data_asset
CREATE INDEX idx_market_data_asset ON market_data_cache (asset);

-- Index: idx_market_data_timestamp
CREATE INDEX idx_market_data_timestamp ON market_data_cache USING btree (asset, timeframe, timestamp DESC);

-- Index: idx_market_data_timeframe
CREATE INDEX idx_market_data_timeframe ON market_data_cache (asset, timeframe);
