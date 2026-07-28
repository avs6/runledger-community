-- Enable pgvector in Letta's database so its migrations (embedding VECTOR(...)) succeed.
-- Runs automatically on first init of runledger-memory-db.
CREATE EXTENSION IF NOT EXISTS vector;
