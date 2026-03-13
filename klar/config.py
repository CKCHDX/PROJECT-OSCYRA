"""
Klar Search Engine - Configuration
Enterprise-Grade Configuration for Swedish National Search Infrastructure
"""

import os
from pathlib import Path

# Load user-configurable settings
try:
    from load_settings import (
        MAX_PAGES_PER_DOMAIN as USER_MAX_PAGES,
        MAX_CONCURRENT_CRAWLS as USER_MAX_CONCURRENT,
        CRAWL_DELAY as USER_CRAWL_DELAY,
        CRAWL_TIMEOUT as USER_CRAWL_TIMEOUT,
        INDEX_LOG_FREQUENCY,
        RESUME_CRAWLING,
        PER_DOMAIN_TIMEOUT as USER_PER_DOMAIN_TIMEOUT
    )
    SETTINGS_LOADED = True
except ImportError:
    SETTINGS_LOADED = False
    USER_PER_DOMAIN_TIMEOUT = None

# ============================================================================
# PROJECT PATHS
# ============================================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
INDEX_DIR = DATA_DIR / "index"
CRAWL_DIR = DATA_DIR / "crawled"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
INDEX_DIR.mkdir(exist_ok=True)
CRAWL_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ============================================================================
# CRAWLER CONFIGURATION
# ============================================================================

# Parallel crawling - 10 domains simultaneously for speed
MAX_CONCURRENT_CRAWLS = USER_MAX_CONCURRENT if SETTINGS_LOADED else 10

# Dynamic timeout adjustment (starts at 30s, can adjust down)
CRAWL_TIMEOUT = USER_CRAWL_TIMEOUT if SETTINGS_LOADED else 30
MIN_CRAWL_TIMEOUT = 10
MAX_CRAWL_TIMEOUT = 60

# Politeness delay between requests to same domain
CRAWL_DELAY = USER_CRAWL_DELAY if SETTINGS_LOADED else 1.0  # seconds

# Max pages per domain (to prevent infinite crawls)
MAX_PAGES_PER_DOMAIN = USER_MAX_PAGES if SETTINGS_LOADED else 1000

# Max depth of crawling from start URL
MAX_CRAWL_DEPTH = 5

# Respect robots.txt
RESPECT_ROBOTS_TXT = True

# User agent string
USER_AGENT = "KlarBot/1.0 (+https://oscyra.solutions/klar; Swedish National Search Engine)"

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Per-domain timeout (prevents hanging on stuck domains)
PER_DOMAIN_TIMEOUT = USER_PER_DOMAIN_TIMEOUT if SETTINGS_LOADED and USER_PER_DOMAIN_TIMEOUT else 120

# Recrawl interval (days)
RECRAWL_INTERVAL_DAYS = 30

# ============================================================================
# NLP CONFIGURATION (SWEDISH)
# ============================================================================

# Swedish stopwords (common words to ignore)
SWEDISH_STOPWORDS = {
    'och', 'i', 'att', 'det', 'som', 'på', 'är', 'av', 'för', 'med', 'till',
    'den', 'har', 'de', 'ett', 'om', 'var', 'än', 'från', 'vid', 'så',
    'han', 'hon', 'kan', 'nu', 'men', 'inte', 'eller', 'ska', 'alla', 'när',
    'över', 'under', 'efter', 'utan', 'också', 'varje', 'många', 'mycket',
    'denna', 'detta', 'dessa', 'samma', 'vilken', 'vilket', 'vilka', 'bara',
    'här', 'där', 'då', 'ju', 'väl', 'nog', 'någon', 'något', 'några'
}

# Minimum word length for indexing
MIN_WORD_LENGTH = 2

# Maximum word length (to filter noise)
MAX_WORD_LENGTH = 45

# Swedish compound word markers
SWEDISH_COMPOUND_MARKERS = ['s', 'e', 'o']

# ============================================================================
# INDEXER CONFIGURATION
# ============================================================================

# Index format
INDEX_FORMAT = "inverted"  # inverted index structure

# Index compression
COMPRESS_INDEX = True

# Term frequency calculation
USE_TF_IDF = True

# Maximum terms to index per page
MAX_TERMS_PER_PAGE = 5000

# Update index frequency
INDEX_UPDATE_BATCH_SIZE = 100  # pages

# ============================================================================
# RANKING ALGORITHM (7 FACTORS)
# ============================================================================

# Weight distribution (must sum to 100)
RANKING_WEIGHTS = {
    'tf_idf': 25,        # Term frequency-inverse document frequency
    'pagerank': 20,      # Link authority
    'authority': 15,     # Domain authority score
    'recency': 15,       # Content freshness
    'density': 10,       # Keyword density and placement
    'structure': 10,     # Link structure quality
    'swedish_boost': 5   # Swedish relevance boost
}

# Swedish domain authority boosts
SWEDISH_AUTHORITY_BOOST = {
    # Government (highest authority)
    '.gov.se': 3.5,
    'riksdagen.se': 3.5,
    'regeringen.se': 3.5,
    'skatteverket.se': 3.0,
    'migrationsverket.se': 3.0,
    'forsakringskassan.se': 3.0,
    'arbetsformedlingen.se': 3.0,
    'folkhalsomyndigheten.se': 3.0,
    
    # Public service media
    'svt.se': 2.5,
    'sr.se': 2.5,
    'ur.se': 2.5,
    
    # Major news outlets
    'dn.se': 2.0,
    'svd.se': 2.0,
    'aftonbladet.se': 1.8,
    'expressen.se': 1.8,
    'gp.se': 1.8,
    'sydsvenskan.se': 1.8,
    
    # Universities
    '.su.se': 1.8,
    '.uu.se': 1.8,
    '.lu.se': 1.8,
    '.kth.se': 1.8,
    '.chalmers.se': 1.8,
    '.liu.se': 1.8,
    '.gu.se': 1.8,
    
    # Other .se domains
    '.se': 1.2,
}

# PageRank configuration
PAGERANK_ITERATIONS = 20
PAGERANK_DAMPING = 0.85

# Recency decay (how fast old content loses relevance)
RECENCY_DECAY_DAYS = 365  # 1 year

# ============================================================================
# API SERVER CONFIGURATION
# ============================================================================

# Server binding
API_HOST = "127.0.0.1"  # Loopback only — external access via Caddy reverse proxy
API_PORT = 4271

# CORS (restrictive origins — CSH reverse proxy handles external access)
CORS_ORIGINS = [
    "https://klar.oscyra.solutions",
    "https://csh.oscyra.solutions",
    "https://oscyra.solutions",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
]

# Request limits (to prevent abuse)
MAX_QUERY_LENGTH = 500
MAX_RESULTS_PER_PAGE = 50
DEFAULT_RESULTS = 10

# Performance targets
TARGET_RESPONSE_TIME_MS = 500  # < 500ms goal

# Cache configuration
ENABLE_QUERY_CACHE = True
CACHE_SIZE = 10000  # cache 10k most common queries
CACHE_TTL_SECONDS = 3600  # 1 hour

# Privacy (no tracking)
LOG_QUERIES = False  # Do NOT log user queries
LOG_RESULTS = False  # Do NOT log what users clicked
STORE_USER_DATA = False  # NEVER store user information

# ============================================================================
# MONITORING & HEALTH
# ============================================================================

# Health check endpoint
ENABLE_HEALTH_CHECK = True

# Metrics collection
COLLECT_METRICS = True
METRICS_INTERVAL = 60  # seconds

# Logging level
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# ============================================================================
# PERFORMANCE TUNING
# ============================================================================

# Thread pool size
WORKER_THREADS = 20

# Connection pool
CONNECTION_POOL_SIZE = 50

# Memory limits
MAX_MEMORY_MB = 8192  # 8GB max memory usage

# Disk cache
ENABLE_DISK_CACHE = True
DISK_CACHE_SIZE_GB = 50

# ============================================================================
# SECURITY
# ============================================================================

# Rate limiting (requests per IP per minute)
RATE_LIMIT_ENABLED = True
RATE_LIMIT_REQUESTS = 60
RATE_LIMIT_WINDOW = 60  # seconds

# Allowed query patterns (to prevent injection)
ALLOWED_QUERY_CHARS = "abcdefghijklmnopqrstuvwxyzåäöABCDEFGHIJKLMNOPQRSTUVWXYZÅÄÖ0123456789 .-_?!"

# ============================================================================
# DATABASE (OPTIONAL - FOR NATIONAL SCALE)
# ============================================================================

# Enable database backend (instead of pickle files)
USE_DATABASE = os.getenv("KSE_USE_DATABASE", "false").lower() == "true"

# PostgreSQL connection string
DATABASE_URL = os.getenv(
    "KSE_DATABASE_URL",
    "postgresql://kse:password@localhost:5432/kse"
)

# Database connection pool
DATABASE_POOL_SIZE = int(os.getenv("KSE_DATABASE_POOL_SIZE", "10"))
DATABASE_POOL_MAX = int(os.getenv("KSE_DATABASE_POOL_MAX", "20"))

# ============================================================================
# DEPLOYMENT
# ============================================================================

# Production mode
PRODUCTION = os.getenv("KSE_PRODUCTION", "false").lower() == "true"

# Debug mode
DEBUG = not PRODUCTION

# Number of workers (for gunicorn)
WORKERS = int(os.getenv("KSE_WORKERS", "4" if PRODUCTION else "1"))

# SSL/TLS (for HTTPS)
SSL_CERT = os.getenv("KSE_SSL_CERT", None)
SSL_KEY = os.getenv("KSE_SSL_KEY", None)

# Server name
SERVER_NAME = os.getenv("KSE_SERVER_NAME", "klar.oscyra.solutions")
