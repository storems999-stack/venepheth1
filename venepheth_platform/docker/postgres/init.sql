-- PostgreSQL initialization script
-- Runs once on first container startup

-- Create application user with limited privileges (principle of least privilege)
CREATE USER venepheth_app WITH PASSWORD 'change_me_in_env';

-- Create backup user (read-only)
CREATE USER venepheth_backup WITH PASSWORD 'change_me_backup_in_env';

-- Grant only necessary privileges to app user
GRANT CONNECT ON DATABASE venepheth_db TO venepheth_app;
GRANT USAGE, CREATE ON SCHEMA public TO venepheth_app;

-- Grant backup user read access
GRANT CONNECT ON DATABASE venepheth_db TO venepheth_backup;
GRANT USAGE ON SCHEMA public TO venepheth_backup;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO venepheth_backup;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO venepheth_backup;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- Trigram search
CREATE EXTENSION IF NOT EXISTS unaccent;     -- Accent-insensitive search
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- UUID generation
