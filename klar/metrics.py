"""
Prometheus Metrics and Monitoring
Enterprise-Grade Observability for KSE

Metrics collected:
- Request counts by endpoint
- Response times (latency percentiles)
- Search query performance
- Index size and statistics
- Crawler progress
- System resources (CPU, memory, disk)
- Error rates
"""

from prometheus_client import Counter, Histogram, Gauge, Summary, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import CollectorRegistry
from flask import Response
import time
import psutil
from functools import wraps
from typing import Callable
import logging

from config import INDEX_DIR, CRAWL_DIR, DATA_DIR
from logger_config import setup_logger

logger = setup_logger('kse.metrics')

# Create registry
registry = CollectorRegistry()

# ============================================================================
# HTTP Metrics
# ============================================================================

# Request counter by endpoint and method
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

# Request latency histogram
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0],
    registry=registry
)

# ============================================================================
# Search Metrics
# ============================================================================

# Search query counter
search_queries_total = Counter(
    'search_queries_total',
    'Total search queries',
    ['category', 'intent'],
    registry=registry
)

# Search latency
search_duration_seconds = Histogram(
    'search_duration_seconds',
    'Search query duration',
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0],
    registry=registry
)

# Search results count
search_results_count = Summary(
    'search_results_count',
    'Number of results returned per query',
    registry=registry
)

# Query cache hits
query_cache_hits = Counter(
    'query_cache_hits_total',
    'Total query cache hits',
    registry=registry
)

query_cache_misses = Counter(
    'query_cache_misses_total',
    'Total query cache misses',
    registry=registry
)

# ============================================================================
# Index Metrics
# ============================================================================

# Index size (documents)
index_documents_total = Gauge(
    'index_documents_total',
    'Total documents in index',
    registry=registry
)

# Index size (terms)
index_terms_total = Gauge(
    'index_terms_total',
    'Total unique terms in index',
    registry=registry
)

# Index size (bytes)
index_size_bytes = Gauge(
    'index_size_bytes',
    'Index size in bytes',
    registry=registry
)

# Last index build time
index_last_build_timestamp = Gauge(
    'index_last_build_timestamp',
    'Timestamp of last index build',
    registry=registry
)

# ============================================================================
# Crawler Metrics
# ============================================================================

# Pages crawled
crawler_pages_total = Counter(
    'crawler_pages_total',
    'Total pages crawled',
    ['domain', 'status'],
    registry=registry
)

# Crawl duration
crawler_duration_seconds = Histogram(
    'crawler_duration_seconds',
    'Time to crawl a domain',
    ['domain'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
    registry=registry
)

# Crawler errors
crawler_errors_total = Counter(
    'crawler_errors_total',
    'Total crawler errors',
    ['error_type'],
    registry=registry
)

# Active crawlers
crawler_active = Gauge(
    'crawler_active',
    'Number of active crawler threads',
    registry=registry
)

# ============================================================================
# System Metrics
# ============================================================================

# CPU usage
system_cpu_usage = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage',
    registry=registry
)

# Memory usage
system_memory_usage_bytes = Gauge(
    'system_memory_usage_bytes',
    'System memory usage in bytes',
    registry=registry
)

# Disk usage
system_disk_usage_bytes = Gauge(
    'system_disk_usage_bytes',
    'System disk usage in bytes',
    ['path'],
    registry=registry
)

# Application uptime
application_uptime_seconds = Gauge(
    'application_uptime_seconds',
    'Application uptime in seconds',
    registry=registry
)

# ============================================================================
# Error Metrics
# ============================================================================

# Error counter
errors_total = Counter(
    'errors_total',
    'Total errors',
    ['component', 'error_type'],
    registry=registry
)

# ============================================================================
# Metric Collection Functions
# ============================================================================

_start_time = time.time()

def update_system_metrics():
    """Update system resource metrics"""
    try:
        # CPU
        system_cpu_usage.set(psutil.cpu_percent(interval=1))
        
        # Memory
        memory = psutil.virtual_memory()
        system_memory_usage_bytes.set(memory.used)
        
        # Disk
        disk = psutil.disk_usage(str(DATA_DIR))
        system_disk_usage_bytes.labels(path=str(DATA_DIR)).set(disk.used)
        
        # Uptime
        application_uptime_seconds.set(time.time() - _start_time)
        
    except Exception as e:
        logger.error(f"Failed to update system metrics: {e}")


def update_index_metrics():
    """Update index-related metrics"""
    try:
        from indexer import InvertedIndex
        
        index_path = INDEX_DIR / "search_index.pkl"
        if index_path.exists():
            # Load index
            index = InvertedIndex.load(index_path)
            
            # Update metrics
            index_documents_total.set(index.num_documents)
            index_terms_total.set(len(index.index))
            index_size_bytes.set(index_path.stat().st_size)
            index_last_build_timestamp.set(index_path.stat().st_mtime)
            
    except Exception as e:
        logger.error(f"Failed to update index metrics: {e}")


def update_crawler_metrics():
    """Update crawler-related metrics"""
    try:
        import json
        
        # Count crawled pages
        crawled_pages = 0
        for domain_dir in CRAWL_DIR.iterdir():
            if domain_dir.is_dir():
                crawled_pages += len(list(domain_dir.glob("*.json")))
        
        # Note: Individual page metrics are updated during crawl
        
    except Exception as e:
        logger.error(f"Failed to update crawler metrics: {e}")


# ============================================================================
# Decorators for Automatic Metric Collection
# ============================================================================

def track_search_metrics(func: Callable) -> Callable:
    """Decorator to track search query metrics"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            
            # Track metrics from result
            if isinstance(result, dict):
                duration = time.time() - start_time
                search_duration_seconds.observe(duration)
                
                if 'count' in result:
                    search_results_count.observe(result['count'])
                
                if 'category' in result and 'intent' in result:
                    search_queries_total.labels(
                        category=result.get('category', 'unknown'),
                        intent=result.get('intent', 'unknown')
                    ).inc()
            
            return result
            
        except Exception as e:
            errors_total.labels(component='search', error_type=type(e).__name__).inc()
            raise
    
    return wrapper


def track_http_metrics(func: Callable) -> Callable:
    """Decorator to track HTTP request metrics"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        from flask import request
        
        start_time = time.time()
        endpoint = request.endpoint or 'unknown'
        method = request.method
        
        try:
            result = func(*args, **kwargs)
            
            # Extract status code
            if isinstance(result, tuple):
                status = result[1] if len(result) > 1 else 200
            else:
                status = 200
            
            # Track metrics
            duration = time.time() - start_time
            http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
            http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
            
            return result
            
        except Exception as e:
            http_requests_total.labels(method=method, endpoint=endpoint, status=500).inc()
            errors_total.labels(component='api', error_type=type(e).__name__).inc()
            raise
    
    return wrapper


# ============================================================================
# Flask Endpoint for Prometheus
# ============================================================================

def metrics_endpoint():
    """
    Flask endpoint to expose Prometheus metrics
    
    Usage:
        @app.route('/metrics')
        def metrics():
            return metrics_endpoint()
    """
    # Update metrics before serving
    update_system_metrics()
    update_index_metrics()
    
    return Response(generate_latest(registry), mimetype=CONTENT_TYPE_LATEST)


# ============================================================================
# Background Metric Updater
# ============================================================================

class MetricsUpdater:
    """Background thread to update metrics periodically"""
    
    def __init__(self, interval: int = 60):
        self.interval = interval
        self.running = False
        self._thread = None
    
    def start(self):
        """Start background metric updates"""
        import threading
        
        if self.running:
            logger.warning("Metrics updater already running")
            return
        
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info(f"Metrics updater started (interval={self.interval}s)")
    
    def stop(self):
        """Stop background updates"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Metrics updater stopped")
    
    def _run(self):
        """Background update loop"""
        while self.running:
            try:
                update_system_metrics()
                update_index_metrics()
                update_crawler_metrics()
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
            
            time.sleep(self.interval)


# Global metrics updater instance
metrics_updater = MetricsUpdater(interval=60)


if __name__ == '__main__':
    print("Testing Prometheus metrics...")
    
    # Update metrics
    update_system_metrics()
    update_index_metrics()
    
    # Generate output
    metrics_output = generate_latest(registry).decode('utf-8')
    print("\nSample metrics output:")
    print(metrics_output[:500])
    print("...")
    
    print("\nMetrics test completed")
