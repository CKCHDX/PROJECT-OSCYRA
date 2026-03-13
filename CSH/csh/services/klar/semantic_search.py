"""
Klar Search Engine - Semantic Search Engine
Vector embeddings for intent-based semantic matching

Uses Swedish-optimized sentence transformers to capture semantic meaning
beyond keyword matching. Critical for national scale deployment.

Features:
- Swedish sentence embeddings (KB-BERT, multilingual models)
- Semantic similarity scoring (cosine similarity)
- Intent-based query expansion
- Fallback to BM25 when embeddings unavailable
- Efficient vector storage and retrieval
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)

# Check if sentence-transformers is available
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    logger.warning("sentence-transformers not installed. Semantic search disabled.")
    logger.warning("Install with: pip install sentence-transformers")
    EMBEDDINGS_AVAILABLE = False


@dataclass
class SemanticMatch:
    """Semantic search result"""
    doc_id: str
    similarity_score: float  # 0-1 cosine similarity
    query_embedding: np.ndarray
    doc_embedding: np.ndarray


class SwedishSemanticEngine:
    """
    Semantic search engine for Swedish queries
    
    Uses pre-trained multilingual models with strong Swedish performance:
    - paraphrase-multilingual-MiniLM-L12-v2 (fast, 384 dims)
    - distiluse-base-multilingual-cased-v1 (balanced, 512 dims)
    - KB/bert-base-swedish-cased (Swedish-specific, requires more resources)
    """
    
    def __init__(self, model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2'):
        """
        Initialize semantic search engine
        
        Args:
            model_name: HuggingFace model name for embeddings
        """
        self.model_name = model_name
        self.model = None
        self.document_embeddings: Dict[str, np.ndarray] = {}
        self.embedding_dim = 384  # Default for MiniLM
        
        if EMBEDDINGS_AVAILABLE:
            try:
                logger.info(f"Loading semantic model: {model_name}")
                self.model = SentenceTransformer(model_name)
                self.embedding_dim = self.model.get_sentence_embedding_dimension()
                logger.info(f"Semantic model loaded. Embedding dimension: {self.embedding_dim}")
            except Exception as e:
                logger.error(f"Failed to load semantic model: {e}")
                logger.warning("Semantic search will be disabled")
                self.model = None
        else:
            logger.warning("Semantic search disabled (sentence-transformers not installed)")
    
    def encode_query(self, query: str) -> Optional[np.ndarray]:
        """
        Encode search query into vector embedding
        
        Args:
            query: User search query
            
        Returns:
            Query embedding vector or None if unavailable
        """
        if not self.model:
            return None
        
        try:
            embedding = self.model.encode(query, convert_to_numpy=True)
            return embedding
        except Exception as e:
            logger.error(f"Failed to encode query: {e}")
            return None
    
    def encode_document(self, doc_id: str, text: str, cache: bool = True) -> Optional[np.ndarray]:
        """
        Encode document into vector embedding
        
        Args:
            doc_id: Document identifier
            text: Document text (title + content)
            cache: Whether to cache the embedding
            
        Returns:
            Document embedding vector or None if unavailable
        """
        if not self.model:
            return None
        
        # Check cache first
        if doc_id in self.document_embeddings:
            return self.document_embeddings[doc_id]
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            
            if cache:
                self.document_embeddings[doc_id] = embedding
            
            return embedding
        except Exception as e:
            logger.error(f"Failed to encode document {doc_id}: {e}")
            return None
    
    def batch_encode_documents(self, documents: Dict[str, str], batch_size: int = 32) -> Dict[str, np.ndarray]:
        """
        Encode multiple documents efficiently in batches
        
        Args:
            documents: Dict of {doc_id: text}
            batch_size: Number of documents per batch
            
        Returns:
            Dict of {doc_id: embedding}
        """
        if not self.model:
            return {}
        
        try:
            doc_ids = list(documents.keys())
            texts = [documents[doc_id] for doc_id in doc_ids]
            
            logger.info(f"Encoding {len(texts)} documents in batches of {batch_size}")
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=True,
                convert_to_numpy=True
            )
            
            # Store in cache
            result = {}
            for doc_id, embedding in zip(doc_ids, embeddings):
                self.document_embeddings[doc_id] = embedding
                result[doc_id] = embedding
            
            logger.info(f"Successfully encoded {len(result)} documents")
            return result
            
        except Exception as e:
            logger.error(f"Failed to batch encode documents: {e}")
            return {}
    
    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Similarity score (0-1, higher is more similar)
        """
        # Normalize vectors
        vec1_norm = vec1 / np.linalg.norm(vec1)
        vec2_norm = vec2 / np.linalg.norm(vec2)
        
        # Calculate cosine similarity
        similarity = np.dot(vec1_norm, vec2_norm)
        
        # Ensure result is in [0, 1] range
        return max(0.0, min(1.0, float(similarity)))
    
    def search(self, query: str, top_k: int = 100) -> List[SemanticMatch]:
        """
        Semantic search across all indexed documents
        
        Args:
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            List of semantic matches sorted by similarity
        """
        if not self.model or not self.document_embeddings:
            logger.warning("Semantic search not available (no model or embeddings)")
            return []
        
        # Encode query
        query_embedding = self.encode_query(query)
        if query_embedding is None:
            return []
        
        # Calculate similarities
        matches = []
        for doc_id, doc_embedding in self.document_embeddings.items():
            similarity = self.cosine_similarity(query_embedding, doc_embedding)
            matches.append(SemanticMatch(
                doc_id=doc_id,
                similarity_score=similarity,
                query_embedding=query_embedding,
                doc_embedding=doc_embedding
            ))
        
        # Sort by similarity (descending)
        matches.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return matches[:top_k]
    
    def save_embeddings(self, filepath: str):
        """Save document embeddings to disk"""
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(self.document_embeddings, f)
            logger.info(f"Saved {len(self.document_embeddings)} embeddings to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save embeddings: {e}")
    
    def load_embeddings(self, filepath: str) -> bool:
        """Load document embeddings from disk"""
        try:
            if not Path(filepath).exists():
                logger.warning(f"Embeddings file not found: {filepath}")
                return False
            
            with open(filepath, 'rb') as f:
                self.document_embeddings = pickle.load(f)
            
            logger.info(f"Loaded {len(self.document_embeddings)} embeddings from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to load embeddings: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Get semantic engine statistics"""
        return {
            'model_name': self.model_name,
            'model_loaded': self.model is not None,
            'embedding_dim': self.embedding_dim,
            'num_documents': len(self.document_embeddings),
            'embeddings_available': EMBEDDINGS_AVAILABLE
        }


class HybridSearchRanker:
    """
    Combines BM25 keyword search with semantic search
    
    Strategy:
    - BM25 for exact keyword matching (fast, precise)
    - Semantic for intent and synonym matching (comprehensive)
    - Weighted combination based on query type
    """
    
    def __init__(self, semantic_weight: float = 0.3, keyword_weight: float = 0.7):
        """
        Initialize hybrid ranker
        
        Args:
            semantic_weight: Weight for semantic similarity (0-1)
            keyword_weight: Weight for keyword matching (0-1)
        """
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight
        
        # Normalize weights
        total = semantic_weight + keyword_weight
        self.semantic_weight /= total
        self.keyword_weight /= total
    
    def combine_scores(self, 
                      bm25_scores: Dict[str, float],
                      semantic_matches: List[SemanticMatch]) -> Dict[str, float]:
        """
        Combine BM25 and semantic scores
        
        Args:
            bm25_scores: Dict of {doc_id: bm25_score}
            semantic_matches: List of semantic matches
            
        Returns:
            Combined scores {doc_id: hybrid_score}
        """
        # Normalize BM25 scores to 0-1
        if bm25_scores:
            max_bm25 = max(bm25_scores.values())
            if max_bm25 > 0:
                bm25_normalized = {doc_id: score / max_bm25 
                                  for doc_id, score in bm25_scores.items()}
            else:
                bm25_normalized = bm25_scores
        else:
            bm25_normalized = {}
        
        # Convert semantic matches to dict
        semantic_scores = {match.doc_id: match.similarity_score 
                          for match in semantic_matches}
        
        # Combine scores
        combined = {}
        all_doc_ids = set(bm25_normalized.keys()) | set(semantic_scores.keys())
        
        for doc_id in all_doc_ids:
            bm25_score = bm25_normalized.get(doc_id, 0.0)
            semantic_score = semantic_scores.get(doc_id, 0.0)
            
            # Weighted combination
            combined[doc_id] = (
                self.keyword_weight * bm25_score +
                self.semantic_weight * semantic_score
            )
        
        return combined
    
    def adjust_weights_by_query_type(self, query: str):
        """
        Dynamically adjust weights based on query characteristics
        
        - Short queries (1-2 words): More semantic (understand intent)
        - Long queries (5+ words): More keyword (specific information)
        - Question queries: More semantic (understand what they're asking)
        """
        words = query.split()
        num_words = len(words)
        
        # Question patterns (Swedish)
        question_words = ['hur', 'vad', 'var', 'när', 'varför', 'vem', 'vilken', 'vilket']
        is_question = any(word.lower() in question_words for word in words[:2])
        
        if num_words <= 2:
            # Short query - rely more on semantics
            self.semantic_weight = 0.6
            self.keyword_weight = 0.4
        elif num_words >= 5:
            # Long query - rely more on keywords
            self.semantic_weight = 0.2
            self.keyword_weight = 0.8
        elif is_question:
            # Question - balanced but slightly semantic
            self.semantic_weight = 0.45
            self.keyword_weight = 0.55
        else:
            # Default
            self.semantic_weight = 0.3
            self.keyword_weight = 0.7


# Singleton instance (lazy loading)
_semantic_engine = None

def get_semantic_engine() -> SwedishSemanticEngine:
    """Get or create semantic engine singleton"""
    global _semantic_engine
    if _semantic_engine is None:
        _semantic_engine = SwedishSemanticEngine()
    return _semantic_engine
