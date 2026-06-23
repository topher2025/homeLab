-- ============================
-- Router Logs Table
-- ============================
CREATE TABLE router_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    threadname VARCHAR(15) NOT NULL,
    level VARCHAR(10),
    logger VARCHAR(15),
    message TEXT
);

-- Indexes for performance
CREATE INDEX idx_router_logs_timestamp ON router_logs (timestamp);
CREATE INDEX idx_router_logs_level ON router_logs (level);


-- ============================
-- Migrations Table
-- ============================
CREATE TABLE migrations (
    version VARCHAR(50) PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);