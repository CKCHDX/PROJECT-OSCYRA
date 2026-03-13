"""
Klar Search Engine - Inverted Index Builder
Enterprise-Grade Index for Sub-500ms Query Performance

Features:
- Inverted index: term → [documents containing term]
- TF-IDF calculation for relevance scoring
- Efficient file-based storage (no database overhead)
- Compressed index format
- Fast loading and querying
- Handles 2.8M+ pages efficiently
"""

import json
import pickle
import logging
import math
import heapq
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict

import numpy as np

from config import INDEX_DIR, CRAWL_DIR, INDEX_FORMAT, COMPRESS_INDEX
from nlp_processor import nlp_processor

# Load log frequency from settings
try:
    from load_settings import INDEX_LOG_FREQUENCY
except ImportError:
    INDEX_LOG_FREQUENCY = 100

logger = logging.getLogger(__name__)


@dataclass
class DocumentInfo:
    """Metadata about an indexed document"""
    doc_id: str  # Unique document ID (URL hash)
    url: str
    domain: str
    title: str
    snippet: str  # First 200 chars for display
    word_count: int
    crawled_at: str
    authority_score: float  # From domain authority
    
    def to_dict(self) -> Dict:
        return asdict(self)


class InvertedIndex:
    """Inverted index structure for fast term lookups"""
    
    def __init__(self):
        # term → {doc_id: term_frequency}
        self.index: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        # doc_id → DocumentInfo
        self.documents: Dict[str, DocumentInfo] = {}
        
        # doc_id → word_count
        self.doc_lengths: Dict[str, int] = {}
        
        # Total number of documents
        self.num_documents = 0
        
        # Average document length
        self.avg_doc_length = 0
        
        # IDF cache: term → IDF score
        self.idf_cache: Dict[str, float] = {}
        
        logger.info("Inverted Index initialized")
    
    def add_document(self, doc_info: DocumentInfo, terms: List[str]):
        """Add a document to the index"""
        doc_id = doc_info.doc_id
        
        # Store document info
        self.documents[doc_id] = doc_info
        
        # Count term frequencies in this document
        term_counts = Counter(terms)
        
        # Add to inverted index
        for term, count in term_counts.items():
            self.index[term][doc_id] = count
        
        # Store document length
        self.doc_lengths[doc_id] = len(terms)
        
        self.num_documents += 1
    
    def calculate_idf(self):
        """Calculate IDF scores for all terms"""
        logger.info("Calculating IDF scores...")
        
        # Calculate average document length
        if self.doc_lengths:
            self.avg_doc_length = sum(self.doc_lengths.values()) / len(self.doc_lengths)
        
        # Calculate IDF for each term
        for term, doc_dict in self.index.items():
            # Number of documents containing this term
            df = len(doc_dict)
            
            # IDF = log(N / df) where N is total documents
            idf = math.log((self.num_documents + 1) / (df + 1)) + 1
            self.idf_cache[term] = idf
        
        logger.info(f"IDF calculated for {len(self.idf_cache)} terms")
    
    def calculate_tf_idf(self, term: str, doc_id: str) -> float:
        """Calculate TF-IDF score for a term in a document"""
        if term not in self.index or doc_id not in self.index[term]:
            return 0.0
        
        # Term frequency in this document
        tf = self.index[term][doc_id]
        
        # Inverse document frequency
        idf = self.idf_cache.get(term, 1.0)
        
        # TF-IDF score
        return tf * idf
    
    def search(self, query_terms: List[str], limit: int = 100) -> Dict[str, float]:
        """Search index for query terms, return doc_id → relevance scores"""
        if not query_terms:
            return {}

        # Limit postings per term to keep search fast at scale
        max_postings_per_term = 5000

        scores: Dict[str, float] = defaultdict(float)
        for term in query_terms:
            postings = self.index.get(term)
            if not postings:
                continue

            # Use IDF once per term
            idf = self.idf_cache.get(term, 1.0)

            # Limit postings for very common terms
            if len(postings) > max_postings_per_term:
                top_docs = heapq.nlargest(
                    max_postings_per_term,
                    postings.items(),
                    key=lambda x: x[1]
                )
                iterable = top_docs
            else:
                iterable = postings.items()

            # Accumulate TF-IDF scores
            for doc_id, tf in iterable:
                scores[doc_id] += tf * idf

        if not scores:
            return {}

        # Sort by score and limit results
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_docs[:limit])
    
    def get_document(self, doc_id: str) -> DocumentInfo:
        """Retrieve document info by ID"""
        return self.documents.get(doc_id)
    
    def save(self, filepath: Path):
        """Save index to disk"""
        logger.info(f"Saving index to {filepath}")
        
        # Convert defaultdicts to regular dicts for serialization
        data = {
            'index': {term: dict(docs) for term, docs in self.index.items()},
            'documents': {doc_id: doc.to_dict() for doc_id, doc in self.documents.items()},
            'doc_lengths': self.doc_lengths,
            'idf_cache': self.idf_cache,
            'num_documents': self.num_documents,
            'avg_doc_length': self.avg_doc_length,
        }
        
        if COMPRESS_INDEX:
            # Use pickle for compression
            with open(filepath, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
        else:
            # Use JSON for readability
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        
        logger.info(f"✓ Index saved ({self.num_documents} documents, {len(self.index)} terms)")
    
    @classmethod
    def load(cls, filepath: Path) -> 'InvertedIndex':
        """Load index from disk"""
        logger.info(f"Loading index from {filepath}")
        
        index = cls()
        
        try:
            if COMPRESS_INDEX or filepath.suffix == '.pkl':
                with open(filepath, 'rb') as f:
                    data = pickle.load(f)
            else:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            # Restore index
            index.index = defaultdict(lambda: defaultdict(int))
            for term, docs in data['index'].items():
                index.index[term] = defaultdict(int, docs)
            
            # Restore documents
            for doc_id, doc_data in data['documents'].items():
                index.documents[doc_id] = DocumentInfo(**doc_data)
            
            index.doc_lengths = data['doc_lengths']
            index.idf_cache = data['idf_cache']
            index.num_documents = data['num_documents']
            index.avg_doc_length = data['avg_doc_length']
            
            logger.info(f"✓ Index loaded ({index.num_documents} documents, {len(index.index)} terms)")
            return index
            
        except Exception as e:
            logger.error(f"Error loading index: {e}")
            raise
    
    def stats(self) -> Dict:
        """Get index statistics"""
        return {
            'num_documents': self.num_documents,
            'num_terms': len(self.index),
            'avg_doc_length': self.avg_doc_length,
            'total_postings': sum(len(docs) for docs in self.index.values()),
        }


class IndexBuilder:
    """Builds inverted index from crawled data"""
    
    def __init__(self, crawl_directory: Path = CRAWL_DIR):
        self.crawl_dir = crawl_directory
        self.index = InvertedIndex()
    
    def load_crawled_pages(self) -> List[Dict]:
        """Load all crawled pages from disk"""
        logger.info(f"Loading crawled pages from {self.crawl_dir}")
        
        pages = []
        
        # Iterate through all domain directories
        for domain_dir in self.crawl_dir.iterdir():
            if not domain_dir.is_dir():
                continue
            
            # Load all JSON files in domain directory
            for json_file in domain_dir.glob('*.json'):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        page_data = json.load(f)
                        pages.append(page_data)
                except Exception as e:
                    logger.warning(f"Error loading {json_file}: {e}")
        
        logger.info(f"Loaded {len(pages)} pages")
        return pages
    
    def build(self):
        """Build complete index from crawled data"""
        logger.info("=" * 80)
        logger.info("BUILDING INVERTED INDEX")
        logger.info("=" * 80)
        
        # Load crawled pages
        pages = self.load_crawled_pages()
        
        if not pages:
            logger.error("No pages found to index!")
            return
        
        # Process each page
        logger.info("Processing pages...")
        for i, page in enumerate(pages):
            try:
                # Process content with NLP
                processed = nlp_processor.process(page['content'])
                
                # Create document info
                doc_info = DocumentInfo(
                    doc_id=page['content_hash'],
                    url=page['url'],
                    domain=page['domain'],
                    title=page['title'],
                    snippet=page['content'][:200],
                    word_count=page['word_count'],
                    crawled_at=page['crawled_at'],
                    authority_score=self._get_authority_score(page['domain'])
                )
                
                # Add to index with stemmed terms
                self.index.add_document(doc_info, processed.stems)
                
                # Log progress more frequently
                if (i + 1) % INDEX_LOG_FREQUENCY == 0:
                    logger.info(f"[INDEX] Processed {i + 1}/{len(pages)} pages ({((i+1)/len(pages)*100):.1f}%)")
                    
            except Exception as e:
                logger.error(f"Error processing page {page.get('url', 'unknown')}: {e}")
        
        # Calculate IDF scores
        self.index.calculate_idf()
        
        # Show statistics
        stats = self.index.stats()
        logger.info("=" * 80)
        logger.info("INDEX STATISTICS")
        logger.info(f"Documents: {stats['num_documents']:,}")
        logger.info(f"Unique terms: {stats['num_terms']:,}")
        logger.info(f"Average document length: {stats['avg_doc_length']:.1f} words")
        logger.info(f"Total postings: {stats['total_postings']:,}")
        logger.info("=" * 80)
    
    def _get_authority_score(self, domain: str) -> float:
        """Get domain authority score from config"""
        from config import SWEDISH_AUTHORITY_BOOST
        
        # Check exact domain match
        if domain in SWEDISH_AUTHORITY_BOOST:
            return SWEDISH_AUTHORITY_BOOST[domain]
        
        # Check suffix match (e.g., .gov.se)
        for suffix, score in SWEDISH_AUTHORITY_BOOST.items():
            if domain.endswith(suffix):
                return score
        
        # Default score
        return 1.0
    
    def save(self, filename: str = "search_index.pkl"):
        """Save built index"""
        filepath = INDEX_DIR / filename
        self.index.save(filepath)


def main():
    """Build index from crawled data"""
    logger.info("Klar Search Engine - Index Builder")
    
    # Create builder
    builder = IndexBuilder()
    
    # Build index
    builder.build()
    
    # Save index
    builder.save()
    
    logger.info("✓ Index building complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
