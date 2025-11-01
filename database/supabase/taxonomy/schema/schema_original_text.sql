-- ============================================================================
-- Original Policy Text Table Schema
-- ============================================================================
-- Stores chunked policy text with embeddings for semantic search
-- Uses pgvector extension for efficient similarity search
--
-- Usage:
--   1. Run this script in Supabase SQL Editor
--   2. Verify pgvector extension is enabled
--   3. Run original_text_loader.py to populate data
-- ============================================================================

-- Enable pgvector extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- Drop existing table if exists (for development/testing)
-- DROP TABLE IF EXISTS original_text CASCADE;

-- Create original_text table
CREATE TABLE IF NOT EXISTS original_text (
    -- Primary Key
    text_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Product Information
    product_name TEXT NOT NULL,

    -- Text Content
    text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    char_count INTEGER NOT NULL CHECK (char_count >= 0),

    -- Embeddings (2000 dimensions for text-embedding-3-large)
    original_embedding VECTOR(2000),

    -- Metadata (JSONB for flexible schema)
    metadata JSONB DEFAULT '{}'::JSONB,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- Indexes
-- ============================================================================

-- Index on product_name for filtering by product
CREATE INDEX IF NOT EXISTS idx_original_text_product_name
ON original_text(product_name);

-- Index on chunk_index for ordering
CREATE INDEX IF NOT EXISTS idx_original_text_chunk_index
ON original_text(product_name, chunk_index);

-- Vector similarity search index (HNSW - Hierarchical Navigable Small World)
-- This enables fast approximate nearest neighbor search
-- m=16: number of connections per layer (higher = more accurate but slower)
-- ef_construction=64: size of dynamic candidate list (higher = better quality but slower build)
CREATE INDEX IF NOT EXISTS idx_original_text_embedding_hnsw
ON original_text
USING hnsw (original_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- GIN index on metadata JSONB for fast JSON queries
CREATE INDEX IF NOT EXISTS idx_original_text_metadata
ON original_text USING GIN(metadata);

-- Index on created_at for temporal queries
CREATE INDEX IF NOT EXISTS idx_original_text_created_at
ON original_text(created_at DESC);

-- ============================================================================
-- Triggers
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_original_text_updated_at
    BEFORE UPDATE ON original_text
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Function: Search similar text chunks using cosine similarity
CREATE OR REPLACE FUNCTION search_similar_original_text(
    query_embedding VECTOR(2000),
    match_count INTEGER DEFAULT 10,
    filter_product TEXT DEFAULT NULL
)
RETURNS TABLE (
    text_id UUID,
    product_name TEXT,
    text TEXT,
    chunk_index INTEGER,
    similarity FLOAT,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ot.text_id,
        ot.product_name,
        ot.text,
        ot.chunk_index,
        1 - (ot.original_embedding <=> query_embedding) AS similarity,
        ot.metadata
    FROM original_text ot
    WHERE
        (filter_product IS NULL OR ot.product_name = filter_product)
        AND ot.original_embedding IS NOT NULL
    ORDER BY ot.original_embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Function: Get full document by product name (all chunks in order)
CREATE OR REPLACE FUNCTION get_full_document_by_product(
    p_product_name TEXT
)
RETURNS TABLE (
    text_id UUID,
    chunk_index INTEGER,
    text TEXT,
    char_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ot.text_id,
        ot.chunk_index,
        ot.text,
        ot.char_count
    FROM original_text ot
    WHERE ot.product_name = p_product_name
    ORDER BY ot.chunk_index ASC;
END;
$$ LANGUAGE plpgsql;

-- Function: Get statistics for original_text table
CREATE OR REPLACE FUNCTION get_original_text_stats()
RETURNS TABLE (
    total_chunks BIGINT,
    total_products BIGINT,
    total_characters BIGINT,
    chunks_with_embeddings BIGINT,
    avg_chunk_size NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT AS total_chunks,
        COUNT(DISTINCT product_name)::BIGINT AS total_products,
        SUM(char_count)::BIGINT AS total_characters,
        COUNT(original_embedding)::BIGINT AS chunks_with_embeddings,
        ROUND(AVG(char_count), 2) AS avg_chunk_size
    FROM original_text;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Row Level Security (RLS)
-- ============================================================================

-- Enable RLS
ALTER TABLE original_text ENABLE ROW LEVEL SECURITY;

-- Policy: Allow service role full access
CREATE POLICY "Service role has full access to original_text"
ON original_text
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Policy: Authenticated users can read
CREATE POLICY "Authenticated users can read original_text"
ON original_text
FOR SELECT
TO authenticated
USING (true);

-- Policy: Anon users can read (optional - remove if you want auth required)
CREATE POLICY "Anonymous users can read original_text"
ON original_text
FOR SELECT
TO anon
USING (true);

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE original_text IS 'Original policy text chunks with embeddings for semantic search';
COMMENT ON COLUMN original_text.text_id IS 'Unique identifier (UUID)';
COMMENT ON COLUMN original_text.product_name IS 'Insurance product name';
COMMENT ON COLUMN original_text.text IS 'Text content of the chunk';
COMMENT ON COLUMN original_text.chunk_index IS 'Sequence number of chunk in document';
COMMENT ON COLUMN original_text.char_count IS 'Character count of chunk';
COMMENT ON COLUMN original_text.original_embedding IS 'Embedding vector (2000D) from text-embedding-3-large';
COMMENT ON COLUMN original_text.metadata IS 'Additional metadata (JSONB)';

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Uncomment to verify table creation:
-- SELECT table_name, column_name, data_type
-- FROM information_schema.columns
-- WHERE table_name = 'original_text';

-- Uncomment to view indexes:
-- SELECT indexname, indexdef
-- FROM pg_indexes
-- WHERE tablename = 'original_text';

-- Uncomment to test statistics function:
-- SELECT * FROM get_original_text_stats();
