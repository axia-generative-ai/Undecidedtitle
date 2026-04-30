-- 001_init_vectorstore.sql
--
-- Schema for the manual chunk vector store.
-- The embedding column dimension is provider-dependent:
--   bge-m3                   -> 1024
--   text-embedding-3-small   -> 1536
-- This file uses a placeholder `__EMBEDDING_DIM__` that
-- `scripts/init_db.py` substitutes at runtime based on the configured
-- embedding model. **Switching providers requires recreating this table**
-- because pgvector cannot ALTER an existing vector column to a new dim.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- for gen_random_uuid()

CREATE TABLE IF NOT EXISTS manual_chunks (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manual_id    TEXT NOT NULL,
    equipment_id TEXT NOT NULL,
    page         INT  NOT NULL,
    chunk_index  INT  NOT NULL,
    chunk_text   TEXT NOT NULL,
    embedding    VECTOR(__EMBEDDING_DIM__) NOT NULL,
    metadata     JSONB,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS manual_chunks_embedding_hnsw
    ON manual_chunks
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS manual_chunks_equipment_id
    ON manual_chunks (equipment_id);

CREATE INDEX IF NOT EXISTS manual_chunks_manual_id
    ON manual_chunks (manual_id);
