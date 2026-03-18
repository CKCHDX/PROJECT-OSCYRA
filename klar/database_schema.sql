"""
Database Schema for PostgreSQL (Optional)
Enables scaling beyond pickle files for national deployment

Tables:
- documents: Indexed documents with metadata
- terms: Search terms
- document_terms: Many-to-many relationship with TF-IDF scores
- search_queries: Query log for analytics (optional, privacy-aware)
- page_links: Link graph for PageRank calculation
"""

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- For fuzzy text search
CREATE EXTENSION IF NOT EXISTS btree_gin;  -- For efficient indexing

-- Documents table
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    doc_id VARCHAR(64) UNIQUE NOT NULL,  -- Hash of URL
    url TEXT NOT NULL,
    domain VARCHAR(255) NOT NULL,
    title TEXT,
    snippet TEXT,
    content TEXT,
    word_count INTEGER,
    crawled_at TIMESTAMP NOT NULL,
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    authority_score REAL DEFAULT 1.0,
    pagerank_score REAL DEFAULT 0.0,
    language VARCHAR(10) DEFAULT 'sv',
    status VARCHAR(20) DEFAULT 'active',  -- active, archived, deleted
    CONSTRAINT valid_scores CHECK (authority_score >= 0 AND pagerank_score >= 0)
);

-- Terms table (vocabulary)
CREATE TABLE terms (
    id SERIAL PRIMARY KEY,
    term VARCHAR(255) UNIQUE NOT NULL,
    idf_score REAL,
    document_frequency INTEGER DEFAULT 0,
    CONSTRAINT valid_idf CHECK (idf_score >= 0)
);

-- Document-Terms relationship (inverted index)
CREATE TABLE document_terms (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    term_id INTEGER NOT NULL REFERENCES terms(id) ON DELETE CASCADE,
    term_frequency INTEGER NOT NULL,
    tf_idf_score REAL,
    position_first INTEGER,  -- First occurrence position
    UNIQUE(document_id, term_id),
    CONSTRAINT valid_frequency CHECK (term_frequency > 0)
);

-- Page links (for PageRank)
CREATE TABLE page_links (
    id SERIAL PRIMARY KEY,
    source_doc_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    target_doc_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    anchor_text TEXT,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_doc_id, target_doc_id)
);

-- Search queries (optional, for analytics - privacy-aware)
-- Note: Only aggregate data, no user identification
CREATE TABLE search_analytics (
    id SERIAL PRIMARY KEY,
    query_hash VARCHAR(64) NOT NULL,  -- Hashed query (not plaintext)
    result_count INTEGER,
    response_time_ms REAL,
    category VARCHAR(50),
    intent VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- No IP address, no user ID, privacy-first
    INDEX idx_timestamp (timestamp)
);

-- Create indexes for performance
CREATE INDEX idx_documents_domain ON documents(domain);
CREATE INDEX idx_documents_crawled_at ON documents(crawled_at);
CREATE INDEX idx_documents_authority ON documents(authority_score DESC);
CREATE INDEX idx_documents_pagerank ON documents(pagerank_score DESC);
CREATE INDEX idx_documents_status ON documents(status);

CREATE INDEX idx_terms_term ON terms(term);
CREATE INDEX idx_terms_idf ON terms(idf_score DESC);

CREATE INDEX idx_document_terms_doc ON document_terms(document_id);
CREATE INDEX idx_document_terms_term ON document_terms(term_id);
CREATE INDEX idx_document_terms_tfidf ON document_terms(tf_idf_score DESC);

CREATE INDEX idx_page_links_source ON page_links(source_doc_id);
CREATE INDEX idx_page_links_target ON page_links(target_doc_id);

CREATE INDEX idx_analytics_timestamp ON search_analytics(timestamp);
CREATE INDEX idx_analytics_category ON search_analytics(category);

-- Full-text search index on document content
CREATE INDEX idx_documents_content_fts ON documents USING GIN (to_tsvector('swedish', content));
CREATE INDEX idx_documents_title_fts ON documents USING GIN (to_tsvector('swedish', title));

-- Trigram indexes for fuzzy matching
CREATE INDEX idx_terms_trigram ON terms USING GIN (term gin_trgm_ops);

-- Views for common queries
CREATE VIEW v_top_documents AS
SELECT 
    doc_id,
    url,
    domain,
    title,
    authority_score,
    pagerank_score,
    (authority_score * 0.5 + pagerank_score * 0.5) AS combined_score
FROM documents
WHERE status = 'active'
ORDER BY combined_score DESC;

CREATE VIEW v_term_statistics AS
SELECT 
    t.term,
    t.document_frequency,
    t.idf_score,
    COUNT(dt.id) AS index_entries,
    AVG(dt.tf_idf_score) AS avg_tfidf
FROM terms t
LEFT JOIN document_terms dt ON t.id = dt.term_id
GROUP BY t.id, t.term, t.document_frequency, t.idf_score;

-- Functions for search optimization
CREATE OR REPLACE FUNCTION calculate_bm25(
    term_freq INTEGER,
    doc_length INTEGER,
    avg_doc_length REAL,
    doc_frequency INTEGER,
    total_docs INTEGER,
    k1 REAL DEFAULT 1.5,
    b REAL DEFAULT 0.75
) RETURNS REAL AS $$
DECLARE
    idf REAL;
    tf_component REAL;
BEGIN
    -- Calculate IDF
    idf := LN((total_docs - doc_frequency + 0.5) / (doc_frequency + 0.5) + 1.0);
    
    -- Calculate TF component
    tf_component := (term_freq * (k1 + 1.0)) / 
                    (term_freq + k1 * (1.0 - b + b * (doc_length / avg_doc_length)));
    
    RETURN idf * tf_component;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Maintenance functions
CREATE OR REPLACE FUNCTION cleanup_old_analytics(days_to_keep INTEGER DEFAULT 90) 
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM search_analytics 
    WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '1 day' * days_to_keep;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Update statistics trigger
CREATE OR REPLACE FUNCTION update_term_statistics() 
RETURNS TRIGGER AS $$
BEGIN
    UPDATE terms 
    SET document_frequency = (
        SELECT COUNT(DISTINCT document_id) 
        FROM document_terms 
        WHERE term_id = NEW.term_id
    )
    WHERE id = NEW.term_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_term_stats
AFTER INSERT OR UPDATE ON document_terms
FOR EACH ROW
EXECUTE FUNCTION update_term_statistics();

-- Comments for documentation
COMMENT ON TABLE documents IS 'Indexed web documents with metadata';
COMMENT ON TABLE terms IS 'Search term vocabulary with IDF scores';
COMMENT ON TABLE document_terms IS 'Inverted index: maps terms to documents with TF-IDF';
COMMENT ON TABLE page_links IS 'Link graph between pages for PageRank calculation';
COMMENT ON TABLE search_analytics IS 'Aggregate search analytics (privacy-aware, no user data)';

COMMENT ON FUNCTION calculate_bm25 IS 'Calculate BM25 relevance score for term-document pair';
COMMENT ON FUNCTION cleanup_old_analytics IS 'Remove analytics data older than specified days';

-- Sample queries for testing
-- 1. Search for documents containing term
-- SELECT d.* FROM documents d
-- JOIN document_terms dt ON d.id = dt.document_id
-- JOIN terms t ON dt.term_id = t.id
-- WHERE t.term = 'riksdag'
-- ORDER BY dt.tf_idf_score DESC
-- LIMIT 10;

-- 2. Full-text search with ranking
-- SELECT doc_id, url, title,
--        ts_rank(to_tsvector('swedish', content), query) AS rank
-- FROM documents, to_tsquery('swedish', 'riksdag & lag') query
-- WHERE to_tsvector('swedish', content) @@ query
-- ORDER BY rank DESC
-- LIMIT 10;

-- 3. Find pages linking to a document
-- SELECT d.url, d.title, pl.anchor_text
-- FROM documents d
-- JOIN page_links pl ON d.id = pl.source_doc_id
-- WHERE pl.target_doc_id = (SELECT id FROM documents WHERE doc_id = 'target_doc_hash')
-- ORDER BY d.pagerank_score DESC;
