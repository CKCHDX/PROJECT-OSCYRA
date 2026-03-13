"""
Klar Search Engine - Settings Loader
Loads configuration from kse_settings.ini
"""

import configparser
from pathlib import Path

# Load settings from INI file
settings_file = Path(__file__).parent / "kse_settings.ini"
config = configparser.ConfigParser()

# Default values
DEFAULTS = {
    'CRAWLER': {
        'MAX_PAGES_PER_DOMAIN': '1000',
        'MAX_CONCURRENT_CRAWLS': '10',
        'CRAWL_DELAY': '1.0',
        'CRAWL_TIMEOUT': '30'
    },
    'INDEXER': {
        'INDEX_LOG_FREQUENCY': '100',
        'COMPRESS_INDEX': 'true'
    },
    'API': {
        'API_PORT': '5000',
        'DEBUG': 'false',
        'CORS_ENABLED': 'true'
    },
    'SYSTEM': {
        'RESUME_CRAWLING': 'true',
        'AUTO_RESTART': 'true',
        'LOG_RETENTION_DAYS': '30'
    }
}

# Read settings file if exists, otherwise use defaults
if settings_file.exists():
    config.read(settings_file)
else:
    # Create default settings file
    for section, values in DEFAULTS.items():
        config[section] = values
    with open(settings_file, 'w') as f:
        config.write(f)

def load_settings():
    """Load and return all settings as a dictionary"""
    return {
        'CRAWLER': {
            'MAX_PAGES_PER_DOMAIN': config.getint('CRAWLER', 'MAX_PAGES_PER_DOMAIN', fallback=1000),
            'MAX_CONCURRENT_CRAWLS': config.getint('CRAWLER', 'MAX_CONCURRENT_CRAWLS', fallback=10),
            'CRAWL_DELAY': config.getfloat('CRAWLER', 'CRAWL_DELAY', fallback=1.0),
            'CRAWL_TIMEOUT': config.getint('CRAWLER', 'CRAWL_TIMEOUT', fallback=30),
            'MAX_CRAWL_DEPTH': config.getint('CRAWLER', 'MAX_CRAWL_DEPTH', fallback=5),
        },
        'INDEXER': {
            'INDEX_LOG_FREQUENCY': config.getint('INDEXER', 'INDEX_LOG_FREQUENCY', fallback=100),
        },
        'API': {
            'API_PORT': config.getint('API', 'API_PORT', fallback=5000),
        },
        'SYSTEM': {
            'SKIP_DOMAINS': config.get('SYSTEM', 'SKIP_DOMAINS', fallback=''),
            'PER_DOMAIN_TIMEOUT': config.getint('SYSTEM', 'PER_DOMAIN_TIMEOUT', fallback=600),
        }
    }

# Export settings as variables
MAX_PAGES_PER_DOMAIN = config.getint('CRAWLER', 'MAX_PAGES_PER_DOMAIN', fallback=1000)
MAX_CONCURRENT_CRAWLS = config.getint('CRAWLER', 'MAX_CONCURRENT_CRAWLS', fallback=10)
CRAWL_DELAY = config.getfloat('CRAWLER', 'CRAWL_DELAY', fallback=1.0)
MAX_CRAWL_DEPTH = config.getint('CRAWLER', 'MAX_CRAWL_DEPTH', fallback=5)
CRAWL_TIMEOUT = config.getint('CRAWLER', 'CRAWL_TIMEOUT', fallback=30)

INDEX_LOG_FREQUENCY = config.getint('INDEXER', 'INDEX_LOG_FREQUENCY', fallback=100)
COMPRESS_INDEX = config.getboolean('INDEXER', 'COMPRESS_INDEX', fallback=True)

API_PORT = config.getint('API', 'API_PORT', fallback=5000)
DEBUG = config.getboolean('API', 'DEBUG', fallback=False)
CORS_ENABLED = config.getboolean('API', 'CORS_ENABLED', fallback=True)

RESUME_CRAWLING = config.getboolean('SYSTEM', 'RESUME_CRAWLING', fallback=True)
AUTO_RESTART = config.getboolean('SYSTEM', 'AUTO_RESTART', fallback=True)
LOG_RETENTION_DAYS = config.getint('SYSTEM', 'LOG_RETENTION_DAYS', fallback=30)
PER_DOMAIN_TIMEOUT = config.getint('SYSTEM', 'PER_DOMAIN_TIMEOUT', fallback=120)
