-- ============================================================================
-- Supabase Travel Insurance Taxonomy Schema
-- Optimized for AI Agentic Vector Search with Dual-Layer Intelligence
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================================
-- CORE TABLES (Denormalized for Read Performance)
-- ============================================================================

-- Products Master Table
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    product_name VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Layer 1: General Conditions (Denormalized)
CREATE TABLE IF NOT EXISTS general_conditions (
    id BIGSERIAL PRIMARY KEY,
    product_id INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    product_name VARCHAR(255) NOT NULL,  -- Denormalized for speed
    condition_name VARCHAR(150) NOT NULL,
    condition_type VARCHAR(50),  -- 'exclusion' or 'eligibility' (nullable for some conditions)
    condition_exist BOOLEAN NOT NULL,
    original_text TEXT,
    parameters JSONB DEFAULT '{}',
    -- Dual embeddings for different query types
    normalized_embedding vector(2000),  -- For structured comparison
    original_embedding vector(2000),    -- For explanation with policy text
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(product_name, condition_name)
);

-- Layer 2: Benefits (Denormalized)
CREATE TABLE IF NOT EXISTS benefits (
    id BIGSERIAL PRIMARY KEY,
    product_id INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    product_name VARCHAR(255) NOT NULL,  -- Denormalized for speed
    benefit_name VARCHAR(150) NOT NULL,
    benefit_exist BOOLEAN NOT NULL,
    coverage_limit JSONB,  -- Can be numeric, plan-tiered, or null
    sub_limits JSONB DEFAULT '{}',
    parameters JSONB DEFAULT '{}',
    original_text TEXT,
    -- Dual embeddings
    normalized_embedding vector(2000),
    original_embedding vector(2000),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(product_name, benefit_name)
);

-- Layer 3: Benefit-Specific Conditions (Denormalized)
CREATE TABLE IF NOT EXISTS benefit_conditions (
    id BIGSERIAL PRIMARY KEY,
    product_id INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    product_name VARCHAR(255) NOT NULL,  -- Denormalized
    benefit_name VARCHAR(150) NOT NULL,  -- Denormalized
    condition_name VARCHAR(150) NOT NULL,
    condition_type VARCHAR(50),  -- 'benefit_eligibility' or 'benefit_exclusion'
    condition_exist BOOLEAN NOT NULL,
    original_text TEXT,
    parameters JSONB DEFAULT '{}',
    -- Dual embeddings
    normalized_embedding vector(2000),
    original_embedding vector(2000),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(product_name, benefit_name, condition_name)
);

-- ============================================================================
-- PERFORMANCE INDEXES
-- ============================================================================

-- Vector Search Indexes (IVFFlat for cosine similarity)
-- Lists parameter: sqrt(total_rows) is a good heuristic
CREATE INDEX IF NOT EXISTS idx_general_conditions_normalized_vec
    ON general_conditions USING ivfflat (normalized_embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_general_conditions_original_vec
    ON general_conditions USING ivfflat (original_embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_benefits_normalized_vec
    ON benefits USING ivfflat (normalized_embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_benefits_original_vec
    ON benefits USING ivfflat (original_embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_benefit_conditions_normalized_vec
    ON benefit_conditions USING ivfflat (normalized_embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_benefit_conditions_original_vec
    ON benefit_conditions USING ivfflat (original_embedding vector_cosine_ops)
    WITH (lists = 100);

-- JSONB Indexes (GIN for structured queries)
CREATE INDEX IF NOT EXISTS idx_general_conditions_params
    ON general_conditions USING GIN (parameters jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_benefits_coverage
    ON benefits USING GIN (coverage_limit jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_benefits_sublimits
    ON benefits USING GIN (sub_limits jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_benefits_params
    ON benefits USING GIN (parameters jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_benefit_conditions_params
    ON benefit_conditions USING GIN (parameters jsonb_path_ops);

-- Composite B-Tree Indexes (For eligibility and scenario queries)
CREATE INDEX IF NOT EXISTS idx_general_conditions_type_product
    ON general_conditions (condition_type, product_name, condition_exist);

CREATE INDEX IF NOT EXISTS idx_benefits_product_exist
    ON benefits (product_name, benefit_exist);

CREATE INDEX IF NOT EXISTS idx_benefit_conditions_type_product
    ON benefit_conditions (benefit_name, condition_type, product_name, condition_exist);

-- Text Search Indexes (For fuzzy matching)
CREATE INDEX IF NOT EXISTS idx_general_conditions_name_trgm
    ON general_conditions USING gin (condition_name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_benefits_name_trgm
    ON benefits USING gin (benefit_name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_benefit_conditions_name_trgm
    ON benefit_conditions USING gin (condition_name gin_trgm_ops);

-- ============================================================================
-- OPTIMIZED VIEWS FOR COMMON QUERY PATTERNS
-- ============================================================================

-- View 1: Comparison View (Side-by-Side Product Comparison)
CREATE OR REPLACE VIEW comparison_view AS
SELECT
    'benefit' AS item_type,
    benefit_name AS item_name,
    product_name,
    benefit_exist AS exists,
    coverage_limit,
    sub_limits,
    parameters
FROM benefits
WHERE benefit_exist = true
UNION ALL
SELECT
    'condition' AS item_type,
    condition_name AS item_name,
    product_name,
    condition_exist AS exists,
    NULL AS coverage_limit,
    NULL AS sub_limits,
    parameters
FROM general_conditions
WHERE condition_exist = true
ORDER BY item_type, item_name, product_name;

-- View 2: Eligibility View (Rule-Based Assessment)
CREATE OR REPLACE VIEW eligibility_view AS
SELECT
    gc.product_name,
    gc.condition_name,
    gc.condition_type,
    gc.parameters,
    gc.original_text,
    CASE
        WHEN gc.condition_type = 'exclusion' THEN 'excluded'
        WHEN gc.condition_type = 'eligibility' THEN 'eligible'
        ELSE 'unknown'
    END AS eligibility_status
FROM general_conditions gc
WHERE gc.condition_exist = true

UNION ALL

SELECT
    bc.product_name,
    bc.benefit_name || ': ' || bc.condition_name AS condition_name,
    bc.condition_type,
    bc.parameters,
    bc.original_text,
    CASE
        WHEN bc.condition_type = 'benefit_exclusion' THEN 'excluded'
        WHEN bc.condition_type = 'benefit_eligibility' THEN 'eligible'
        ELSE 'unknown'
    END AS eligibility_status
FROM benefit_conditions bc
WHERE bc.condition_exist = true;

-- View 3: Scenario View (Multi-Benefit Coverage Analysis)
CREATE OR REPLACE VIEW scenario_view AS
SELECT
    b.product_name,
    b.benefit_name,
    b.benefit_exist,
    b.coverage_limit,
    b.sub_limits,
    b.original_text AS benefit_text,
    jsonb_agg(
        jsonb_build_object(
            'condition_name', bc.condition_name,
            'condition_type', bc.condition_type,
            'parameters', bc.parameters,
            'original_text', bc.original_text
        )
    ) FILTER (WHERE bc.id IS NOT NULL) AS related_conditions
FROM benefits b
LEFT JOIN benefit_conditions bc
    ON b.product_name = bc.product_name
    AND b.benefit_name = bc.benefit_name
    AND bc.condition_exist = true
WHERE b.benefit_exist = true
GROUP BY b.id, b.product_name, b.benefit_name, b.benefit_exist,
         b.coverage_limit, b.sub_limits, b.original_text;

-- ============================================================================
-- HELPER FUNCTIONS FOR VECTOR SEARCH
-- ============================================================================

-- Function: Find similar conditions using normalized embeddings
CREATE OR REPLACE FUNCTION find_similar_conditions(
    query_embedding vector(2000),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    condition_name VARCHAR,
    product_name VARCHAR,
    condition_type VARCHAR,
    similarity float,
    parameters JSONB,
    original_text TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        gc.condition_name,
        gc.product_name,
        gc.condition_type,
        1 - (gc.normalized_embedding <=> query_embedding) AS similarity,
        gc.parameters,
        gc.original_text
    FROM general_conditions gc
    WHERE gc.condition_exist = true
        AND 1 - (gc.normalized_embedding <=> query_embedding) > match_threshold
    ORDER BY gc.normalized_embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Function: Find similar benefits using normalized embeddings
CREATE OR REPLACE FUNCTION find_similar_benefits(
    query_embedding vector(2000),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    benefit_name VARCHAR,
    product_name VARCHAR,
    similarity float,
    coverage_limit JSONB,
    sub_limits JSONB,
    original_text TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        b.benefit_name,
        b.product_name,
        1 - (b.normalized_embedding <=> query_embedding) AS similarity,
        b.coverage_limit,
        b.sub_limits,
        b.original_text
    FROM benefits b
    WHERE b.benefit_exist = true
        AND 1 - (b.normalized_embedding <=> query_embedding) > match_threshold
    ORDER BY b.normalized_embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Function: Explain coverage using original text embeddings
CREATE OR REPLACE FUNCTION explain_coverage(
    query_embedding vector(2000),
    match_count int DEFAULT 5
)
RETURNS TABLE (
    item_type VARCHAR,
    item_name VARCHAR,
    product_name VARCHAR,
    similarity float,
    original_text TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        'benefit'::VARCHAR AS item_type,
        b.benefit_name AS item_name,
        b.product_name,
        1 - (b.original_embedding <=> query_embedding) AS similarity,
        b.original_text
    FROM benefits b
    WHERE b.benefit_exist = true
        AND b.original_embedding IS NOT NULL
    ORDER BY b.original_embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- UPDATE TRIGGERS
-- ============================================================================

-- Trigger function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to all tables
CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_general_conditions_updated_at BEFORE UPDATE ON general_conditions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_benefits_updated_at BEFORE UPDATE ON benefits
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_benefit_conditions_updated_at BEFORE UPDATE ON benefit_conditions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ANALYTICS MATERIALIZED VIEW
-- ============================================================================

-- Materialized view for fast analytics queries
CREATE MATERIALIZED VIEW IF NOT EXISTS taxonomy_stats AS
SELECT
    p.product_name,
    COUNT(DISTINCT gc.condition_name) AS total_general_conditions,
    COUNT(DISTINCT CASE WHEN gc.condition_type = 'exclusion' THEN gc.condition_name END) AS exclusion_count,
    COUNT(DISTINCT CASE WHEN gc.condition_type = 'eligibility' THEN gc.condition_name END) AS eligibility_count,
    COUNT(DISTINCT b.benefit_name) AS total_benefits,
    COUNT(DISTINCT bc.condition_name) AS total_benefit_conditions,
    COUNT(DISTINCT CASE WHEN bc.condition_type = 'benefit_exclusion' THEN bc.condition_name END) AS benefit_exclusion_count,
    COUNT(DISTINCT CASE WHEN bc.condition_type = 'benefit_eligibility' THEN bc.condition_name END) AS benefit_eligibility_count
FROM products p
LEFT JOIN general_conditions gc ON p.id = gc.product_id AND gc.condition_exist = true
LEFT JOIN benefits b ON p.id = b.product_id AND b.benefit_exist = true
LEFT JOIN benefit_conditions bc ON p.id = bc.product_id AND bc.condition_exist = true
GROUP BY p.product_name;

-- Index for materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_taxonomy_stats_product
    ON taxonomy_stats (product_name);

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE products IS 'Master product registry for all insurance policies';
COMMENT ON TABLE general_conditions IS 'Layer 1: General eligibility and exclusion conditions (denormalized)';
COMMENT ON TABLE benefits IS 'Layer 2: Policy benefits with coverage limits (denormalized)';
COMMENT ON TABLE benefit_conditions IS 'Layer 3: Benefit-specific eligibility and exclusion conditions (denormalized)';

COMMENT ON COLUMN general_conditions.normalized_embedding IS 'Vector embedding of structured parameters for comparison queries';
COMMENT ON COLUMN general_conditions.original_embedding IS 'Vector embedding of original policy text for explanation queries';
COMMENT ON COLUMN benefits.coverage_limit IS 'JSONB: Can be numeric, plan-tiered object, or null';
COMMENT ON COLUMN benefits.sub_limits IS 'JSONB: Nested coverage limits by category, time period, or plan tier';

-- ============================================================================
-- GRANT PERMISSIONS (Adjust based on your Supabase roles)
-- ============================================================================

-- Grant read access to authenticated users
GRANT SELECT ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Grant write access to service role (for data loading)
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
