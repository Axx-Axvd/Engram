-- Runs once on a fresh database volume (docker-entrypoint-initdb.d).
-- Enables pgvector so artifact embeddings can be stored and searched.
CREATE EXTENSION IF NOT EXISTS vector;
