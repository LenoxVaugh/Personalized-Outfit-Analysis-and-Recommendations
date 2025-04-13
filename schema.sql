-- Create search_cache table
CREATE TABLE IF NOT EXISTS search_cache (
    id SERIAL PRIMARY KEY,
    query VARCHAR(255) NOT NULL,
    results JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_search_cache_query 
ON search_cache(query);

-- Create index for date filtering
CREATE INDEX IF NOT EXISTS idx_search_cache_created_at 
ON search_cache(created_at);