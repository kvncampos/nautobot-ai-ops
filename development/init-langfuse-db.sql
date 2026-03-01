-- Initialize langfuse database for Langfuse observability stack
CREATE DATABASE langfuse;

-- Create a langfuse-specific user (optional, for better security)
-- For dev, using shared nautobot user is fine
-- CREATE USER langfuse WITH PASSWORD 'changeme';
-- GRANT ALL PRIVILEGES ON DATABASE langfuse TO langfuse;
