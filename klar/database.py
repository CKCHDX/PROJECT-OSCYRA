"""
PostgreSQL Database Adapter (Optional)
Enables scaling to national level with relational database

Usage:
    # Enable in config.py:
    USE_DATABASE = True
    DATABASE_URL = "postgresql://user:pass@localhost/kse"
    
    # Use instead of pickle files:
    from database import DatabaseIndex
    index = DatabaseIndex()
    index.add_document(doc_info, terms)
    results = index.search(query_terms)
"""

import psycopg2
from psycopg2 import pool
from psycopg2.extras import execute_values
import hashlib
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

from config import DATABASE_URL, DATABASE_POOL_SIZE, INDEX_DIR
from indexer import DocumentInfo
from logger_config import setup_logger

logger = setup_logger('kse.database')


class DatabaseConnection:
    """Manage PostgreSQL connection pool"""
    
    def __init__(self, database_url: str, pool_size: int = 10):
        self.database_url = database_url
        self.pool_size = pool_size
        self._pool = None
    
    def initialize(self):
        """Initialize connection pool"""
        try:
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=self.pool_size,
                dsn=self.database_url
            )
            logger.info(f"Database connection pool initialized (size={self.pool_size})")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    def get_connection(self):
        """Get connection from pool"""
        if self._pool is None:
            self.initialize()
        return self._pool.getconn()
    
    def return_connection(self, conn):
        """Return connection to pool"""
        if self._pool:
            self._pool.putconn(conn)
    
    def close_all(self):
        """Close all connections"""
        if self._pool:
            self._pool.closeall()
            logger.info("Database connection pool closed")


class DatabaseIndex:
    """
    Database-backed inverted index
    Alternative to pickle-based index for production scale
    """
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or DATABASE_URL
        self.db = DatabaseConnection(self.database_url)
        self.db.initialize()
    
    def add_document(self, doc_info: DocumentInfo, terms: List[str]) -> bool:
        """
        Add document to database index
        
        Args:
            doc_info: Document metadata
            terms: List of processed terms
        
        Returns:
            True if successful
        """
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Insert document
            cursor.execute("""
                INSERT INTO documents 
                (doc_id, url, domain, title, snippet, word_count, crawled_at, authority_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (doc_id) DO UPDATE SET
                    url = EXCLUDED.url,
                    title = EXCLUDED.title,
                    crawled_at = EXCLUDED.crawled_at
                RETURNING id
            """, (
                doc_info.doc_id,
                doc_info.url,
                doc_info.domain,
                doc_info.title,
                doc_info.snippet,
                doc_info.word_count,
                doc_info.crawled_at,
                doc_info.authority_score
            ))
            
            document_id = cursor.fetchone()[0]
            
            # Count term frequencies
            from collections import Counter
            term_counts = Counter(terms)
            
            # Insert terms and document-term relationships
            for term, frequency in term_counts.items():
                # Insert term if not exists
                cursor.execute("""
                    INSERT INTO terms (term)
                    VALUES (%s)
                    ON CONFLICT (term) DO NOTHING
                    RETURNING id
                """, (term,))
                
                result = cursor.fetchone()
                if result:
                    term_id = result[0]
                else:
                    cursor.execute("SELECT id FROM terms WHERE term = %s", (term,))
                    term_id = cursor.fetchone()[0]
                
                # Insert document-term relationship
                cursor.execute("""
                    INSERT INTO document_terms (document_id, term_id, term_frequency)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (document_id, term_id) DO UPDATE SET
                        term_frequency = EXCLUDED.term_frequency
                """, (document_id, term_id, frequency))
            
            conn.commit()
            logger.debug(f"Added document to database: {doc_info.url}")
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to add document to database: {e}")
            return False
        finally:
            if conn:
                self.db.return_connection(conn)
    
    def calculate_idf(self):
        """Calculate IDF scores for all terms"""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Get total document count
            cursor.execute("SELECT COUNT(*) FROM documents WHERE status = 'active'")
            total_docs = cursor.fetchone()[0]
            
            if total_docs == 0:
                logger.warning("No documents in database, skipping IDF calculation")
                return
            
            # Calculate IDF for each term
            cursor.execute("""
                UPDATE terms t
                SET idf_score = LN((%s::REAL + 1.0) / (t.document_frequency + 1.0)),
                    document_frequency = (
                        SELECT COUNT(DISTINCT document_id)
                        FROM document_terms dt
                        WHERE dt.term_id = t.id
                    )
            """, (total_docs,))
            
            # Calculate TF-IDF scores
            cursor.execute("""
                UPDATE document_terms dt
                SET tf_idf_score = dt.term_frequency * t.idf_score
                FROM terms t
                WHERE dt.term_id = t.id
            """)
            
            conn.commit()
            logger.info(f"Calculated IDF scores for {cursor.rowcount} terms")
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to calculate IDF: {e}")
        finally:
            if conn:
                self.db.return_connection(conn)
    
    def search(self, query_terms: List[str], limit: int = 100) -> Dict[str, float]:
        """
        Search for documents matching query terms
        
        Args:
            query_terms: List of processed search terms
            limit: Maximum results to return
        
        Returns:
            Dictionary of doc_id -> relevance score
        """
        if not query_terms:
            return {}
        
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Search using TF-IDF scores
            query = """
                SELECT d.doc_id, SUM(dt.tf_idf_score * t.idf_score) AS score
                FROM documents d
                JOIN document_terms dt ON d.id = dt.document_id
                JOIN terms t ON dt.term_id = t.id
                WHERE t.term = ANY(%s) AND d.status = 'active'
                GROUP BY d.doc_id
                ORDER BY score DESC
                LIMIT %s
            """
            
            cursor.execute(query, (query_terms, limit))
            results = {row[0]: row[1] for row in cursor.fetchall()}
            
            logger.debug(f"Search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {}
        finally:
            if conn:
                self.db.return_connection(conn)
    
    def get_document(self, doc_id: str) -> Optional[DocumentInfo]:
        """Get document by ID"""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT doc_id, url, domain, title, snippet, word_count, 
                       crawled_at, authority_score
                FROM documents
                WHERE doc_id = %s
            """, (doc_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return DocumentInfo(
                doc_id=row[0],
                url=row[1],
                domain=row[2],
                title=row[3],
                snippet=row[4],
                word_count=row[5],
                crawled_at=row[6],
                authority_score=row[7]
            )
            
        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            return None
        finally:
            if conn:
                self.db.return_connection(conn)
    
    def get_statistics(self) -> Dict:
        """Get index statistics"""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM documents WHERE status = 'active'")
            num_documents = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM terms")
            num_terms = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM document_terms")
            num_entries = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM page_links")
            num_links = cursor.fetchone()[0]
            
            return {
                'num_documents': num_documents,
                'num_terms': num_terms,
                'index_entries': num_entries,
                'page_links': num_links
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
        finally:
            if conn:
                self.db.return_connection(conn)


# Migration utility
def migrate_pickle_to_database(pickle_path: str, database_url: str):
    """
    Migrate from pickle-based index to PostgreSQL
    
    Usage:
        migrate_pickle_to_database('data/index/search_index.pkl', DATABASE_URL)
    """
    import pickle
    from pathlib import Path
    
    logger.info(f"Migrating index from {pickle_path} to database...")
    
    # Load pickle index
    with open(pickle_path, 'rb') as f:
        old_index = pickle.load(f)
    
    # Create database index
    db_index = DatabaseIndex(database_url)
    
    # Migrate documents
    for doc_id, doc_info in old_index.documents.items():
        # Reconstruct terms for this document
        terms = []
        for term, doc_dict in old_index.index.items():
            if doc_id in doc_dict:
                frequency = doc_dict[doc_id]
                terms.extend([term] * frequency)
        
        db_index.add_document(doc_info, terms)
    
    # Calculate IDF
    db_index.calculate_idf()
    
    stats = db_index.get_statistics()
    logger.info(f"Migration complete: {stats['num_documents']} documents, {stats['num_terms']} terms")


if __name__ == '__main__':
    # Test database connection
    logger.info("Testing database connection...")
    
    try:
        db_index = DatabaseIndex("postgresql://kse:password@localhost/kse_test")
        stats = db_index.get_statistics()
        print(f"Database statistics: {stats}")
        print("Database connection test successful")
    except Exception as e:
        print(f"Database connection test failed: {e}")
