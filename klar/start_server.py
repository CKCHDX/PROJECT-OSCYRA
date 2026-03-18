"""
Klar Search Engine - Server Startup Script
Start the KSE API server (production-grade)

Usage:
    python start_server.py          # Development mode (Flask built-in)
    python start_server.py --prod   # Production mode (recommended)
"""

import sys
import os
import logging
import subprocess
import socket
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print startup banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║            KLAR SEARCH ENGINE - API SERVER                   ║
    ║                                                              ║
    ║        Privacy-First Swedish Search Infrastructure           ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def get_local_ip():
    """Get local IP address for LAN access"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "localhost"


def check_index_exists():
    """Verify search index is built"""
    from config import INDEX_DIR
    
    index_file = INDEX_DIR / "search_index.pkl"
    if not index_file.exists():
        logger.error("=" * 80)
        logger.error("ERROR: Search index not found!")
        logger.error("=" * 80)
        logger.error("\nYou must initialize the search engine first:")
        logger.error("  python init_kse.py")
        logger.error("\nThis will:")
        logger.error("  1. Crawl Swedish domains")
        logger.error("  2. Build search index")
        logger.error("  3. Prepare the system")
        logger.error("\n" + "=" * 80)
        sys.exit(1)
    
    logger.info(f"✓ Search index found: {index_file}")


def start_development_server():
    """Start Flask development server"""
    logger.info("Starting in DEVELOPMENT mode...")
    logger.info("(Use --prod for production deployment)")
    
    from config import API_HOST, API_PORT
    local_ip = get_local_ip()
    
    logger.info("\n" + "=" * 80)
    logger.info("Server will be accessible at:")
    logger.info(f"  Local:    http://localhost:{API_PORT}")
    logger.info(f"  Network:  http://{local_ip}:{API_PORT}")
    logger.info(f"  External: http://YOUR_PUBLIC_IP:{API_PORT}")
    logger.info("=" * 80)
    logger.info("\nPress Ctrl+C to stop the server\n")
    
    # Import and run server
    from api_server import run_server
    run_server()


def start_production_server():
    """Start Gunicorn production server"""
    logger.info("Starting in PRODUCTION mode...")
    
    from config import API_HOST, API_PORT, WORKERS
    
    # Gunicorn configuration
    workers = WORKERS
    bind_address = f"{API_HOST}:{API_PORT}"
    
    local_ip = get_local_ip()
    
    logger.info("\n" + "=" * 80)
    logger.info("Production Server Configuration:")
    logger.info(f"  Workers: {workers}")
    logger.info(f"  Binding: {bind_address}")
    logger.info(f"  Local:    http://localhost:{API_PORT}")
    logger.info(f"  Network:  http://{local_ip}:{API_PORT}")
    logger.info("=" * 80)
    logger.info("\nPress Ctrl+C to stop the server\n")
    
    # Start Gunicorn
    cmd = [
        "gunicorn",
        "--workers", str(workers),
        "--bind", bind_address,
        "--timeout", "120",
        "--worker-class", "gevent",
        "--access-logfile", "logs/access.log",
        "--error-logfile", "logs/error.log",
        "--log-level", "info",
        "api_server:app"
    ]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        logger.info("\nServer stopped by user")
    except FileNotFoundError:
        logger.error("Gunicorn not found! Install with: pip install gunicorn gevent")
        logger.info("Falling back to development server...")
        start_development_server()


def show_configuration():
    """Show server configuration"""
    from config import (
        API_HOST, API_PORT, MAX_CONCURRENT_CRAWLS,
        MAX_PAGES_PER_DOMAIN, TARGET_RESPONSE_TIME_MS,
        ENABLE_QUERY_CACHE, RATE_LIMIT_ENABLED
    )
    
    logger.info("\nConfiguration:")
    logger.info(f"  Port: {API_PORT}")
    logger.info(f"  Cache: {'Enabled' if ENABLE_QUERY_CACHE else 'Disabled'}")
    logger.info(f"  Rate Limiting: {'Enabled' if RATE_LIMIT_ENABLED else 'Disabled'}")
    logger.info(f"  Target Response: <{TARGET_RESPONSE_TIME_MS}ms")


def main():
    """Main startup routine"""
    print_banner()
    
    # Check if production mode requested
    production = '--prod' in sys.argv or '--production' in sys.argv
    
    # Verify index exists
    check_index_exists()
    
    # Show configuration
    show_configuration()
    
    # Start appropriate server
    try:
        if production:
            start_production_server()
        else:
            start_development_server()
    except KeyboardInterrupt:
        logger.info("\n\nServer stopped")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
