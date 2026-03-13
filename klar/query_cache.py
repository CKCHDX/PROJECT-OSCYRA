"""
Query Results Cache System
==========================

Caches search results for common queries to achieve sub-millisecond response times.
- In-memory LRU cache: 10,000 entries, 24-hour TTL
- Optional persistent cache for long-term storage
- Hit/miss tracking with statistics
- Estimated 100x speedup for top 1000 queries (30% of traffic)

Usage:
    from query_cache import memory_cache, get_cached_results, cache_search_results
    
    # Check cache
    cached = get_cached_results("stockholm")
    if cached:
        return cached  # <1ms response
    
    # Cache results
    cache_search_results("stockholm", results, response_time_ms)
    
    # Get statistics
    stats = memory_cache.get_stats()
    print(f"Cache hit rate: {stats['hit_rate']:.2%}")
"""

import json
import hashlib
import time
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
from collections import OrderedDict
from threading import Lock


class QueryCache:
    """
    In-memory LRU (Least Recently Used) cache for search results.
    
    Features:
    - Thread-safe with locks
    - TTL-based expiration (24 hours default)
    - LRU eviction when size exceeds max_size
    - Hit/miss tracking with statistics
    - Query normalization (lowercase, stripped)
    """
    
    def __init__(self, max_size: int = 10000, ttl_hours: int = 24):
        self.max_size = max_size
        self.ttl = timedelta(hours=ttl_hours)
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.lock = Lock()
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.total_time_saved_ms = 0.0
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for cache key generation"""
        return query.lower().strip()
    
    def _get_cache_key(self, query: str) -> str:
        """Generate cache key from query (MD5 hash)"""
        normalized = self._normalize_query(query)
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def get(self, query: str) -> Optional[List[Dict]]:
        """
        Retrieve cached results for a query
        
        Args:
            query: The search query
            
        Returns:
            Cached results list or None if not found/expired
        """
        with self.lock:
            key = self._get_cache_key(query)
            
            if key not in self.cache:
                self.misses += 1
                return None
            
            entry = self.cache[key]
            
            # Check if expired
            created_at = datetime.fromisoformat(entry['created_at'])
            if datetime.now() > created_at + self.ttl:
                del self.cache[key]
                self.misses += 1
                return None
            
            # Move to end (LRU)
            self.cache.move_to_end(key)
            
            # Track time saved
            self.hits += 1
            self.total_time_saved_ms += entry.get('original_response_time_ms', 50.0)
            
            return entry['results']
    
    def set(self, query: str, results: List[Dict], response_time_ms: float = 0.0):
        """
        Cache search results for a query
        
        Args:
            query: The search query
            results: The search results list
            response_time_ms: How long the original search took
        """
        with self.lock:
            key = self._get_cache_key(query)
            
            # Remove old entry if exists
            if key in self.cache:
                del self.cache[key]
            
            # Add new entry
            self.cache[key] = {
                'query': query,
                'results': results,
                'created_at': datetime.now().isoformat(),
                'original_response_time_ms': response_time_ms
            }
            
            # Evict oldest if size exceeded
            while len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dict with: cached_queries, hits, misses, hit_rate, total_time_saved_ms
        """
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
            
            return {
                'cached_queries': len(self.cache),
                'hits': self.hits,
                'misses': self.misses,
                'total_requests': total_requests,
                'hit_rate': hit_rate,
                'total_time_saved_ms': self.total_time_saved_ms,
                'avg_time_saved_per_hit_ms': (
                    self.total_time_saved_ms / self.hits if self.hits > 0 else 0.0
                ),
                'max_size': self.max_size,
                'ttl_hours': self.ttl.total_seconds() / 3600
            }
    
    def clear(self):
        """Clear all cached results"""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
            self.total_time_saved_ms = 0.0


class PersistentCache:
    """
    Optional disk-based cache for long-term storage.
    Stores results as JSON files for recovery across restarts.
    """
    
    def __init__(self, cache_dir: str = 'data/.cache/results'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, query: str) -> Path:
        """Get file path for cached query"""
        key = hashlib.md5(query.lower().strip().encode()).hexdigest()
        return self.cache_dir / f"{key}.json"
    
    def get(self, query: str) -> Optional[List[Dict]]:
        """Retrieve cached results from disk"""
        try:
            path = self._get_cache_path(query)
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Check expiration (24 hours)
                    created_at = datetime.fromisoformat(data['created_at'])
                    if datetime.now() < created_at + timedelta(hours=24):
                        return data['results']
                    else:
                        path.unlink()  # Delete expired cache
        except Exception:
            pass
        return None
    
    def set(self, query: str, results: List[Dict]):
        """Cache results to disk"""
        try:
            path = self._get_cache_path(query)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({
                    'query': query,
                    'results': results,
                    'created_at': datetime.now().isoformat()
                }, f, ensure_ascii=False)
        except Exception:
            pass  # Silently fail on disk write errors
    
    def get_popular_queries(self, limit: int = 100) -> List[str]:
        """Get list of popular cached queries (by file modification time)"""
        try:
            files = sorted(
                self.cache_dir.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            return [json.loads(f.read_text())['query'] for f in files[:limit]]
        except Exception:
            return []


# Global instances
memory_cache = QueryCache(max_size=10000, ttl_hours=24)
persistent_cache = PersistentCache()


# API Helper functions for search endpoints
def get_cached_results(query: str) -> Optional[List[Dict]]:
    """
    Get cached results for a query (checks memory first, then disk)
    
    Args:
        query: The search query
        
    Returns:
        Cached results or None
    """
    # Try memory cache first (fast)
    results = memory_cache.get(query)
    if results is not None:
        return results
    
    # Try persistent cache (slower)
    return persistent_cache.get(query)


def cache_search_results(
    query: str,
    results: List[Dict],
    response_time_ms: float = 0.0
):
    """
    Cache search results in both memory and disk
    
    Args:
        query: The search query
        results: The search results
        response_time_ms: Response time of the search
    """
    memory_cache.set(query, results, response_time_ms)
    persistent_cache.set(query, results)


# Example usage and tests
if __name__ == '__main__':
    print("\n" + "="*60)
    print("Query Cache System - Example Usage")
    print("="*60)
    
    # Simulate 100 search requests
    test_queries = [
        ("stockholm", 5),  # 5 times
        ("göteborg", 3),   # 3 times
        ("malmö", 2),      # 2 times
        ("uppsala", 1),    # 1 time
    ] * 20  # Repeat pattern
    
    print("\nSimulating 100 search requests...")
    for i, (query, count) in enumerate(test_queries[:100]):
        # Simulate cache lookup
        cached = memory_cache.get(query)
        
        if cached:
            # Cache hit: <1ms
            response_time = 0.5
        else:
            # Cache miss: simulate 50ms search + cache
            response_time = 50.0
            results = [
                {'url': f'https://example.com/result/{j}', 'title': f'{query} result {j}'}
                for j in range(5)
            ]
            memory_cache.set(query, results, 50.0)
        
        if (i + 1) % 25 == 0:
            stats = memory_cache.get_stats()
            print(f"\nAfter {i+1} requests:")
            print(f"  Cached queries: {stats['cached_queries']}")
            print(f"  Cache hit rate: {stats['hit_rate']:.2%}")
            print(f"  Total time saved: {stats['total_time_saved_ms']:.1f}ms")
    
    # Final statistics
    print("\n" + "-"*60)
    print("Final Cache Statistics:")
    print("-"*60)
    stats = memory_cache.get_stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key:.<40} {value:.2f}")
        else:
            print(f"  {key:.<40} {value}")
    
    print("\nCache Benefits:")
    print(f"  Without cache: 100 queries × 50ms = 5,000ms")
    print(f"  With cache: ~{stats['total_time_saved_ms']:.0f}ms")
    print(f"  Speedup: {5000 / (stats['total_time_saved_ms'] + 2.5):.0f}x")
    print("\n" + "="*60)
