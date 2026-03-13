"""
Klar Search Engine - 7-Factor Ranking Algorithm
Enterprise-Grade Ranking to Outperform Google for Swedish Queries

Factors (Total: 100%):
1. TF-IDF Relevance: 25% - How well document matches query terms
2. PageRank: 20% - Link popularity and authority
3. Domain Authority: 15% - Trust score (.gov.se = highest)
4. Recency: 15% - Content freshness (newer = better)
5. Keyword Density: 10% - Term importance and placement
6. Link Structure: 10% - Quality of internal/external links
7. Swedish Boost: 5% - Swedish language/domain relevance

Result: Final score 0-100 for each document
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict

import numpy as np

from config import (
    RANKING_WEIGHTS, 
    SWEDISH_AUTHORITY_BOOST,
    PAGERANK_ITERATIONS,
    PAGERANK_DAMPING,
    RECENCY_DECAY_DAYS
)

logger = logging.getLogger(__name__)


@dataclass
class RankingSignals:
    """All ranking signals for a document"""
    doc_id: str
    url: str
    title: str
    
    # Factor 1: TF-IDF (25%)
    tf_idf_score: float
    
    # Factor 2: PageRank (20%)
    pagerank_score: float
    
    # Factor 3: Domain Authority (15%)
    authority_score: float
    
    # Factor 4: Recency (15%)
    recency_score: float
    
    # Factor 5: Keyword Density (10%)
    density_score: float
    
    # Factor 6: Link Structure (10%)
    structure_score: float
    
    # Factor 7: Swedish Boost (5%)
    swedish_score: float
    
    # Final combined score (0-100)
    final_score: float = 0.0
    
    def calculate_final_score(self):
        """Calculate weighted final score"""
        self.final_score = (
            self.tf_idf_score * (RANKING_WEIGHTS['tf_idf'] / 100) +
            self.pagerank_score * (RANKING_WEIGHTS['pagerank'] / 100) +
            self.authority_score * (RANKING_WEIGHTS['authority'] / 100) +
            self.recency_score * (RANKING_WEIGHTS['recency'] / 100) +
            self.density_score * (RANKING_WEIGHTS['density'] / 100) +
            self.structure_score * (RANKING_WEIGHTS['structure'] / 100) +
            self.swedish_score * (RANKING_WEIGHTS['swedish_boost'] / 100)
        )
        
        # Normalize to 0-100
        self.final_score = min(100, max(0, self.final_score * 100))


class PageRankCalculator:
    """Calculate PageRank for all documents"""
    
    def __init__(self, damping: float = PAGERANK_DAMPING, iterations: int = PAGERANK_ITERATIONS):
        self.damping = damping
        self.iterations = iterations
        self.pagerank_scores: Dict[str, float] = {}
    
    def calculate(self, link_graph: Dict[str, List[str]]) -> Dict[str, float]:
        """
        Calculate PageRank for all pages
        link_graph: {doc_id: [linked_doc_ids]}
        """
        if not link_graph:
            return {}
        
        logger.info(f"Calculating PageRank for {len(link_graph)} documents")
        
        # Initialize PageRank scores
        num_pages = len(link_graph)
        pagerank = {doc_id: 1.0 / num_pages for doc_id in link_graph}
        
        # Build incoming links map
        incoming = defaultdict(list)
        for doc_id, outgoing in link_graph.items():
            for target in outgoing:
                if target in link_graph:  # Only count links to indexed pages
                    incoming[target].append(doc_id)
        
        # Iterate PageRank algorithm
        for iteration in range(self.iterations):
            new_pagerank = {}
            
            for doc_id in link_graph:
                # Sum contributions from incoming links
                rank_sum = 0.0
                for source in incoming[doc_id]:
                    num_outgoing = len(link_graph[source])
                    if num_outgoing > 0:
                        rank_sum += pagerank[source] / num_outgoing
                
                # PageRank formula: (1-d)/N + d * sum(PR(incoming) / outgoing_count)
                new_pagerank[doc_id] = (1 - self.damping) / num_pages + self.damping * rank_sum
            
            pagerank = new_pagerank
            
            if (iteration + 1) % 5 == 0:
                logger.debug(f"PageRank iteration {iteration + 1}/{self.iterations}")
        
        # Normalize to 0-1 range
        max_pr = max(pagerank.values()) if pagerank else 1.0
        if max_pr > 0:
            pagerank = {doc_id: score / max_pr for doc_id, score in pagerank.items()}
        
        self.pagerank_scores = pagerank
        logger.info(f"✓ PageRank calculated")
        
        return pagerank


class RankingEngine:
    """Main ranking engine combining all 7 factors"""
    
    def __init__(self, index, link_graph: Dict[str, List[str]] = None):
        self.index = index
        self.link_graph = link_graph or {}
        
        # Calculate PageRank once
        self.pagerank_calc = PageRankCalculator()
        if self.link_graph:
            self.pagerank_scores = self.pagerank_calc.calculate(self.link_graph)
        else:
            self.pagerank_scores = {}
        
        logger.info("Ranking Engine initialized")
    
    def _calculate_tf_idf_score(self, doc_id: str, query_terms: List[str]) -> float:
        """Factor 1: TF-IDF relevance (25%)"""
        score = 0.0
        for term in query_terms:
            score += self.index.calculate_tf_idf(term, doc_id)
        
        # Normalize by query length
        if query_terms:
            score /= len(query_terms)
        
        return min(1.0, score / 10)  # Normalize to 0-1
    
    def _calculate_pagerank_score(self, doc_id: str) -> float:
        """Factor 2: PageRank authority (20%)"""
        return self.pagerank_scores.get(doc_id, 0.1)  # Default low score if no links
    
    def _calculate_authority_score(self, domain: str) -> float:
        """Factor 3: Domain authority (15%)"""
        # Check exact domain match
        if domain in SWEDISH_AUTHORITY_BOOST:
            boost = SWEDISH_AUTHORITY_BOOST[domain]
        else:
            # Check suffix match
            boost = 1.0
            for suffix, score in SWEDISH_AUTHORITY_BOOST.items():
                if domain.endswith(suffix):
                    boost = max(boost, score)
                    break
        
        # Normalize to 0-1 (max boost is 3.5)
        return min(1.0, boost / 3.5)
    
    def _calculate_recency_score(self, crawled_at: str) -> float:
        """Factor 4: Recency/freshness (15%)"""
        try:
            crawl_date = datetime.fromisoformat(crawled_at)
            now = datetime.now()
            age_days = (now - crawl_date).days
            
            # Exponential decay: score = e^(-age / decay_constant)
            decay_constant = RECENCY_DECAY_DAYS
            score = math.exp(-age_days / decay_constant)
            
            return score
        except:
            return 0.5  # Default to middle if date parsing fails
    
    def _calculate_density_score(self, doc_id: str, query_terms: List[str]) -> float:
        """Factor 5: Keyword density and placement (10%)"""
        doc_info = self.index.get_document(doc_id)
        if not doc_info:
            return 0.0
        
        score = 0.0
        
        # Check title (weight: 3x)
        title_lower = doc_info.title.lower()
        for term in query_terms:
            if term in title_lower:
                score += 3.0
        
        # Check snippet (weight: 1x)
        snippet_lower = doc_info.snippet.lower()
        for term in query_terms:
            if term in snippet_lower:
                score += 1.0
        
        # Normalize
        max_score = len(query_terms) * 4  # 3 from title + 1 from snippet
        if max_score > 0:
            score = score / max_score
        
        return min(1.0, score)
    
    def _calculate_structure_score(self, doc_id: str) -> float:
        """Factor 6: Link structure quality (10%)"""
        # Number of outgoing links (indicates comprehensive content)
        if doc_id in self.link_graph:
            num_outgoing = len(self.link_graph[doc_id])
            # Optimal range: 5-50 links
            if 5 <= num_outgoing <= 50:
                score = 1.0
            elif num_outgoing < 5:
                score = num_outgoing / 5.0
            else:
                score = 50.0 / num_outgoing
        else:
            score = 0.3  # Default for pages with no link data
        
        return score
    
    def _calculate_swedish_score(self, doc_info) -> float:
        """Factor 7: Swedish language/domain boost (5%)"""
        score = 0.0
        
        # .se domain bonus
        if doc_info.domain.endswith('.se'):
            score += 0.5
        
        # Swedish language bonus (if detected)
        if doc_info.title:
            # Simple heuristic: check for Swedish characters
            swedish_chars = ['å', 'ä', 'ö', 'Å', 'Ä', 'Ö']
            if any(char in doc_info.title for char in swedish_chars):
                score += 0.3
        
        # Government domain extra bonus
        if '.gov.se' in doc_info.domain or 'riksdag' in doc_info.domain:
            score += 0.2
        
        return min(1.0, score)
    
    def rank(self, query_terms: List[str], candidate_docs: Dict[str, float], limit: int = 10) -> List[RankingSignals]:
        """
        Rank candidate documents using all 7 factors
        candidate_docs: {doc_id: initial_score} from index search
        Returns: Sorted list of RankingSignals with final scores
        """
        logger.debug(f"Ranking {len(candidate_docs)} candidate documents")
        
        ranked_docs = []
        
        for doc_id, tf_idf_base in candidate_docs.items():
            doc_info = self.index.get_document(doc_id)
            if not doc_info:
                continue
            
            # Calculate all 7 ranking factors
            signals = RankingSignals(
                doc_id=doc_id,
                url=doc_info.url,
                title=doc_info.title,
                tf_idf_score=self._calculate_tf_idf_score(doc_id, query_terms),
                pagerank_score=self._calculate_pagerank_score(doc_id),
                authority_score=self._calculate_authority_score(doc_info.domain),
                recency_score=self._calculate_recency_score(doc_info.crawled_at),
                density_score=self._calculate_density_score(doc_id, query_terms),
                structure_score=self._calculate_structure_score(doc_id),
                swedish_score=self._calculate_swedish_score(doc_info)
            )
            
            # Calculate final weighted score
            signals.calculate_final_score()
            
            ranked_docs.append(signals)
        
        # Sort by final score (descending)
        ranked_docs.sort(key=lambda x: x.final_score, reverse=True)
        
        # Return top results
        return ranked_docs[:limit]
    
    def search_and_rank(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Complete search pipeline: query → processed → search → rank
        Returns: List of ranked results ready for API response
        """
        # Import here to avoid circular dependency
        from nlp_processor import nlp_processor
        
        # Process query
        processed_query = nlp_processor.process_query(query)

        # Combine stems, compound parts, and synonyms for better recall
        stems = processed_query.get('stems', [])
        compounds = processed_query.get('compounds', [])
        expanded_terms = processed_query.get('expanded_terms', [])

        combined = []
        seen = set()
        for term in stems + compounds + expanded_terms:
            if term not in seen:
                combined.append(term)
                seen.add(term)

        # Cap terms to keep search fast on large indexes
        max_terms = 12
        if len(combined) > max_terms:
            query_terms = stems[:max_terms]
        else:
            query_terms = combined
        
        logger.info(f"Query: '{query}' → Terms: {query_terms}")
        
        # Search index with a larger candidate pool, capped for speed
        candidate_limit = min(500, max(100, limit * 50))
        candidate_docs = self.index.search(query_terms, limit=candidate_limit)
        
        if not candidate_docs:
            logger.info("No matching documents found")
            return []
        
        logger.info(f"Found {len(candidate_docs)} candidates")
        
        # Rank results
        ranked = self.rank(query_terms, candidate_docs, limit=limit)
        
        # Format for API response
        results = []
        for rank_signals in ranked:
            doc_info = self.index.get_document(rank_signals.doc_id)
            results.append({
                'url': doc_info.url,
                'title': doc_info.title,
                'snippet': doc_info.snippet,
                'score': round(rank_signals.final_score, 2),
                'domain': doc_info.domain,
                # Include factor breakdown for debugging
                'factors': {
                    'tf_idf': round(rank_signals.tf_idf_score * 100, 1),
                    'pagerank': round(rank_signals.pagerank_score * 100, 1),
                    'authority': round(rank_signals.authority_score * 100, 1),
                    'recency': round(rank_signals.recency_score * 100, 1),
                    'density': round(rank_signals.density_score * 100, 1),
                    'structure': round(rank_signals.structure_score * 100, 1),
                    'swedish': round(rank_signals.swedish_score * 100, 1),
                }
            })
        
        logger.info(f"Returning {len(results)} ranked results")
        return results


def build_link_graph_from_crawled_data(crawl_directory) -> Dict[str, List[str]]:
    """Build link graph from crawled pages for PageRank calculation"""
    import json
    from pathlib import Path
    
    logger.info("Building link graph...")
    
    link_graph = {}
    url_to_id = {}  # Map URLs to doc IDs
    
    # First pass: build URL → doc_id mapping
    for domain_dir in Path(crawl_directory).iterdir():
        if not domain_dir.is_dir():
            continue
        for json_file in domain_dir.glob('*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    page = json.load(f)
                    url_to_id[page['url']] = page['content_hash']
            except:
                pass
    
    # Second pass: build link graph
    for domain_dir in Path(crawl_directory).iterdir():
        if not domain_dir.is_dir():
            continue
        for json_file in domain_dir.glob('*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    page = json.load(f)
                    doc_id = page['content_hash']
                    
                    # Convert URLs to doc IDs
                    linked_ids = []
                    for link_url in page.get('links', []):
                        if link_url in url_to_id:
                            linked_ids.append(url_to_id[link_url])
                    
                    link_graph[doc_id] = linked_ids
            except:
                pass
    
    logger.info(f"✓ Link graph built: {len(link_graph)} pages with links")
    return link_graph


def main():
    """Test ranking engine"""
    from indexer import InvertedIndex
    from config import INDEX_DIR, CRAWL_DIR
    
    logger.info("Loading index...")
    index = InvertedIndex.load(INDEX_DIR / "search_index.pkl")
    
    logger.info("Building link graph...")
    link_graph = build_link_graph_from_crawled_data(CRAWL_DIR)
    
    logger.info("Initializing ranking engine...")
    ranker = RankingEngine(index, link_graph)
    
    # Test query
    test_query = "svenska nyheter"
    logger.info(f"\nTest query: '{test_query}'")
    results = ranker.search_and_rank(test_query, limit=10)
    
    logger.info("\n" + "=" * 80)
    logger.info("SEARCH RESULTS")
    logger.info("=" * 80)
    for i, result in enumerate(results, 1):
        logger.info(f"\n{i}. {result['title']} (Score: {result['score']}/100)")
        logger.info(f"   {result['url']}")
        logger.info(f"   {result['snippet'][:100]}...")
        logger.info(f"   Factors: {result['factors']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
