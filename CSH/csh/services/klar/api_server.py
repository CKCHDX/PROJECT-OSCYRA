"""
Klar Search Engine - REST API Server
Enterprise-Grade API for Klar Browser Connection

Endpoints:
- GET  /api/search?q=query      - Main search endpoint
- GET  /api/suggest?q=query     - Autocomplete suggestions
- GET  /api/health              - Health check
- GET  /api/stats               - System statistics
- GET  /api/check-domain        - Domain whitelist check

Features:
- Sub-500ms response time
- CORS enabled for browser
- No tracking (privacy-first)
- Rate limiting
- Query caching (100x faster for common queries)
- Intent detection (GUIDE, DEFINITION, NEWS, PRACTICAL_INFO)
- Comprehensive error handling
"""

import time
import logging
from datetime import datetime
from typing import Dict, List
from functools import lru_cache
from collections import defaultdict

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from config import (
    API_HOST, API_PORT, CORS_ORIGINS,
    MAX_QUERY_LENGTH, MAX_RESULTS_PER_PAGE, DEFAULT_RESULTS,
    ENABLE_QUERY_CACHE, CACHE_SIZE,
    RATE_LIMIT_ENABLED, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW,
    INDEX_DIR, CRAWL_DIR, LOG_QUERIES, PRODUCTION
)
from indexer import InvertedIndex
from ranker import RankingEngine, build_link_graph_from_crawled_data
from query_cache import memory_cache, get_cached_results, cache_search_results
from query_intent_detector import detect_query_intent
from nlp_processor import nlp_processor

# Setup logging
logging.basicConfig(
    level=logging.INFO if PRODUCTION else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Enable CORS for browser connection
CORS(app, origins=CORS_ORIGINS)

# Enable Gzip compression for faster remote responses
from flask_compress import Compress
Compress(app)

# Global state
search_engine = None  # RankingEngine instance
request_times = defaultdict(list)  # For rate limiting


class SearchEngineAPI:
    """Wrapper for search engine with caching"""
    
    def __init__(self):
        self.ranker = None
        self.index = None
        self.initialized = False
        self.stats = {
            'total_queries': 0,
            'total_results_returned': 0,
            'avg_response_time_ms': 0,
            'start_time': datetime.now().isoformat(),
        }
        
        self.initialize()
    
    def initialize(self):
        """Load index and initialize ranking engine"""
        try:
            logger.info("=" * 80)
            logger.info("KLAR SEARCH ENGINE - API SERVER STARTUP")
            logger.info("=" * 80)
            
            # Load inverted index
            logger.info("Loading search index...")
            index_path = INDEX_DIR / "search_index.pkl"
            
            if not index_path.exists():
                logger.error(f"Index not found at {index_path}")
                logger.error("Please run crawler.py and indexer.py first!")
                raise FileNotFoundError("Search index not built yet")
            
            self.index = InvertedIndex.load(index_path)
            logger.info(f"✓ Index loaded: {self.index.num_documents:,} documents")
            
            # Build link graph for PageRank
            logger.info("Building link graph...")
            link_graph = build_link_graph_from_crawled_data(CRAWL_DIR)
            logger.info(f"✓ Link graph built: {len(link_graph):,} pages")
            
            # Initialize ranking engine
            logger.info("Initializing ranking engine...")
            self.ranker = RankingEngine(self.index, link_graph)
            logger.info("✓ Ranking engine ready")
            
            self.initialized = True
            
            logger.info("=" * 80)
            logger.info("✓ SEARCH ENGINE READY")
            logger.info(f"Listening on http://{API_HOST}:{API_PORT}")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"Failed to initialize search engine: {e}")
            raise
    
    @lru_cache(maxsize=CACHE_SIZE if ENABLE_QUERY_CACHE else 0)
    def search(self, query: str, limit: int = DEFAULT_RESULTS) -> List[Dict]:
        """Search with caching"""
        if not self.initialized:
            raise RuntimeError("Search engine not initialized")
        
        start_time = time.time()
        
        # Perform search
        results = self.ranker.search_and_rank(query, limit=limit)
        
        # Update stats
        response_time = (time.time() - start_time) * 1000  # Convert to ms
        self.stats['total_queries'] += 1
        self.stats['total_results_returned'] += len(results)
        
        # Update average response time
        total = self.stats['total_queries']
        current_avg = self.stats['avg_response_time_ms']
        self.stats['avg_response_time_ms'] = (current_avg * (total - 1) + response_time) / total
        
        logger.info(f"Query: '{query}' → {len(results)} results in {response_time:.1f}ms")
        
        return results
    
    def get_stats(self) -> Dict:
        """Get system statistics"""
        return {
            **self.stats,
            'index_stats': self.index.stats() if self.index else {},
            'cache_info': {
                'enabled': ENABLE_QUERY_CACHE,
                'size': CACHE_SIZE if ENABLE_QUERY_CACHE else 0,
                'hits': self.search.cache_info().hits if ENABLE_QUERY_CACHE else 0,
                'misses': self.search.cache_info().misses if ENABLE_QUERY_CACHE else 0,
            } if ENABLE_QUERY_CACHE else {},
        }


# Rate limiting
def check_rate_limit(ip_address: str) -> bool:
    """Check if IP address has exceeded rate limit"""
    if not RATE_LIMIT_ENABLED:
        return True
    
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    
    # Clean old requests
    request_times[ip_address] = [t for t in request_times[ip_address] if t > window_start]
    
    # Check limit
    if len(request_times[ip_address]) >= RATE_LIMIT_REQUESTS:
        return False
    
    # Add current request
    request_times[ip_address].append(now)
    return True


def validate_query(query: str) -> tuple:
    """Validate search query"""
    if not query:
        return False, "Query parameter 'q' is required"
    
    if len(query) > MAX_QUERY_LENGTH:
        return False, f"Query too long (max {MAX_QUERY_LENGTH} characters)"
    
    # Basic security check (prevent injection)
    from config import ALLOWED_QUERY_CHARS
    if not all(c in ALLOWED_QUERY_CHARS or c.isalnum() or c.isspace() for c in query):
        return False, "Query contains invalid characters"
    
    return True, None


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/search', methods=['GET'])
def search():
    """
    Main search endpoint with caching and intent detection
    
    Query Parameters:
        q (str): Search query (required)
        limit (int): Number of results (default: 10, max: 50)
    
    Returns:
        JSON: {
            "results": [...],
            "count": 10,
            "query": "original query",
            "intent": "PRACTICAL_INFO",
            "time_ms": 247,
            "cached": false
        }
    """
    start_time = time.time()
    
    # Rate limiting
    ip_address = request.remote_addr
    if not check_rate_limit(ip_address):
        return jsonify({
            'error': 'Rate limit exceeded',
            'message': f'Maximum {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds'
        }), 429
    
    # Get query parameter
    query = request.args.get('q', '').strip()
    
    # Validate query
    valid, error_msg = validate_query(query)
    if not valid:
        return jsonify({'error': error_msg}), 400
    
    # Get limit parameter
    try:
        limit = int(request.args.get('limit', DEFAULT_RESULTS))
        limit = min(limit, MAX_RESULTS_PER_PAGE)  # Cap at max
    except ValueError:
        limit = DEFAULT_RESULTS
    
    # CHECK CACHE FIRST (using both original and optimized)
    cached_results = get_cached_results(query)
    if cached_results:
        processed_query = nlp_processor.process_query(query)
        response_terms = processed_query.get('stems', [])[:12]
        response_time = (time.time() - start_time) * 1000
        return jsonify({
            'results': cached_results[:limit],
            'count': len(cached_results[:limit]),
            'total_matches': len(cached_results),
            'query': query,
            'optimized_query': query,
            'search_terms': response_terms,
            'time_ms': f"{response_time:.1f}",
            'cached': True,
        })
    
    try:
        # Detect query intent
        intent, confidence = detect_query_intent(query)

        # Lightweight cached NLP terms for response diagnostics
        processed_query = nlp_processor.process_query(query)
        response_terms = processed_query.get('stems', [])[:12]

        # Perform search once (ranking engine handles NLP expansion)
        search_results = search_engine.search(query, limit=limit)
        
        response_time = (time.time() - start_time) * 1000
        
        # CACHE RESULTS
        cache_search_results(query, search_results, response_time)
        
        # Format response
        return jsonify({
            'results': search_results[:limit],
            'count': len(search_results[:limit]),
            'total_matches': len(search_results),
            'query': query,
            'optimized_query': query,
            'search_terms': response_terms,
            'intent': intent.value,
            'intent_confidence': f"{confidence:.2f}",
            'time_ms': f"{response_time:.1f}",
            'cached': False,
        })
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
        # Perform search
        results = search_engine.search(query, limit=limit)
        
        # Calculate response time
        response_time = (time.time() - start_time) * 1000
        
        # Return results
        return jsonify({
            'results': results,
            'count': len(results),
            'query': query,
            'time_ms': round(response_time, 1)
        })
        
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return jsonify({
            'error': 'Internal server error',
            'message': 'An error occurred while processing your search'
        }), 500


@app.route('/api/suggest', methods=['GET'])
def suggest():
    """
    Autocomplete suggestions endpoint
    
    Query Parameters:
        q (str): Partial query (required)
        limit (int): Number of suggestions (default: 5, max: 10)
    
    Returns:
        JSON: {
            "suggestions": ["query 1", "query 2", ...],
            "count": 5
        }
    """
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 2:
        return jsonify({'suggestions': [], 'count': 0})
    
    try:
        limit = int(request.args.get('limit', 5))
        limit = min(limit, 10)
    except ValueError:
        limit = 5
    
    # Simple suggestion based on common Swedish queries
    # In production, this would use query logs or a suggestion database
    common_suggestions = [
        'svenska nyheter',
        'arbetsförmedlingen',
        'migrationsverket',
        'skatteverket',
        'försäkringskassan',
        'csn',
        'jobb stockholm',
        'restauranger göteborg',
        'svenska universitet',
        'regeringen',
        'riksdagen',
        'systembolaget',
        'svt nyheter',
        'dn senaste',
        'expressen',
    ]
    
    # Filter suggestions that start with query
    suggestions = [s for s in common_suggestions if s.lower().startswith(query.lower())]
    
    return jsonify({
        'suggestions': suggestions[:limit],
        'count': len(suggestions[:limit])
    })


@app.route('/api/health', methods=['GET'])
def health():
    """
    Health check endpoint
    
    Returns:
        JSON: {
            "status": "healthy",
            "timestamp": "2026-02-05T...",
            "version": "1.0.0"
        }
    """
    return jsonify({
        'status': 'healthy' if search_engine and search_engine.initialized else 'initializing',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'engine': 'Klar Search Engine'
    })


@app.route('/api/stats', methods=['GET'])
def stats():
    """
    System statistics endpoint
    
    Returns:
        JSON: System statistics including query counts, response times, cache stats
    """
    if not search_engine:
        return jsonify({'error': 'Search engine not initialized'}), 503
    
    stats = search_engine.get_stats()
    
    # Add cache statistics
    stats['cache'] = memory_cache.get_stats()
    
    return jsonify(stats)


@app.route('/api/check-domain', methods=['GET'])
def check_domain():
    """
    Check if a domain is allowed (whitelisted for crawling)
    
    Query params:
        domain: Domain to check (e.g., "svt.se")
    
    Returns:
        JSON: {"allowed": true/false, "domain": "svt.se"}
    """
    domain = request.args.get('domain', '').lower().strip()
    
    if not domain:
        return jsonify({'error': 'Domain parameter required'}), 400
    
    # Load allowed domains from configuration
    try:
        from swedish_domains import ALL_DOMAINS
        
        # Normalize domain (remove www., http://, etc.)
        clean_domain = domain.replace('www.', '').replace('http://', '').replace('https://', '').split('/')[0]
        
        # Check if domain is in whitelist
        allowed = clean_domain in ALL_DOMAINS or any(clean_domain.endswith(d) for d in ALL_DOMAINS)
        
        return jsonify({
            'allowed': allowed,
            'domain': clean_domain,
            'message': 'Domain is allowed' if allowed else f'Domain not in whitelist. Allowed domains: {len(ALL_DOMAINS)}'
        })
        
    except Exception as e:
        logger.error(f"Error checking domain: {e}")
        return jsonify({'error': 'Failed to check domain', 'allowed': False}), 500


@app.route('/', methods=['GET'])
def index():
    """Root endpoint - API info"""
    return jsonify({
        'name': 'Klar Search Engine API',
        'version': '1.0.0',
        'description': 'Privacy-first Swedish search engine',
        'endpoints': {
            'search': '/api/search?q=query',
            'suggest': '/api/suggest?q=partial',
            'health': '/api/health',
            'stats': '/api/stats'
        },
        'documentation': 'https://oscyra.solutions/klar/api'
    })


# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal error: {e}", exc_info=True)
    return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all unhandled exceptions"""
    if isinstance(e, HTTPException):
        return e
    
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# STARTUP
# ============================================================================

def run_server():
    """Start the API server"""
    global search_engine
    
    # Initialize search engine
    search_engine = SearchEngineAPI()
    
    # Run Flask server
    if PRODUCTION:
        # Production: use gunicorn (see startup script)
        app.run(host=API_HOST, port=API_PORT, debug=False)
    else:
        # Development: use Flask's built-in server
        app.run(host=API_HOST, port=API_PORT, debug=True, threaded=True)


if __name__ == "__main__":
    run_server()
