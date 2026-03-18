"""
Klar Search Engine - Initialization Script
First-time setup: Crawl → Index → Ready to serve

Run this script to set up the search engine for the first time.
It will:
1. Install dependencies
2. Download NLTK data
3. Crawl Swedish domains (parallel, 10 at a time)
4. Build inverted index
5. Calculate PageRank
6. Verify system is ready

Estimated time: 2-4 hours (depending on network speed and # of domains)
"""

import sys
import subprocess
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/init.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print startup banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║            KLAR SEARCH ENGINE - INITIALIZATION               ║
    ║                                                              ║
    ║        Swedish National Search Infrastructure v1.0           ║
    ║                                                              ║
    ║        Enterprise-Grade • Privacy-First • Sub-500ms          ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def step(number: int, title: str):
    """Print step header"""
    print("\n" + "=" * 80)
    print(f"STEP {number}: {title}")
    print("=" * 80)


def check_python_version():
    """Ensure Python 3.8+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        logger.error("Python 3.8 or higher required")
        sys.exit(1)
    logger.info(f"[OK] Python {version.major}.{version.minor}.{version.micro}")


def install_dependencies():
    """Install required packages"""
    step(1, "Installing Dependencies")
    
    logger.info("Installing Python packages from requirements.txt...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--upgrade"
        ])
        logger.info("[OK] All dependencies installed")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        sys.exit(1)


def download_nltk_data():
    """Download required NLTK data"""
    step(2, "Downloading NLP Data")
    
    import nltk
    
    logger.info("Downloading NLTK data...")
    try:
        nltk.download('punkt', quiet=False)
        nltk.download('stopwords', quiet=False)
        logger.info("[OK] NLTK data downloaded")
    except Exception as e:
        logger.warning(f"NLTK download warning: {e}")
        # Continue anyway, may not be critical


def create_directories():
    """Create necessary directories"""
    step(3, "Creating Directory Structure")
    
    from config import DATA_DIR, INDEX_DIR, CRAWL_DIR, LOGS_DIR
    
    directories = [DATA_DIR, INDEX_DIR, CRAWL_DIR, LOGS_DIR]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"[OK] {directory}")
    
    logger.info("[OK] All directories created")


def verify_domains():
    """Verify domain list is loaded"""
    step(4, "Verifying Domain List")
    
    from swedish_domains import ALL_DOMAINS, TOTAL_DOMAINS
    
    logger.info(f"Loaded {TOTAL_DOMAINS} Swedish domains")
    logger.info(f"Sample domains: {ALL_DOMAINS[:5]}")
    logger.info("[OK] Domain list verified")


def run_crawler():
    """Run web crawler"""
    step(5, "Crawling Swedish Web (10 domains in parallel)")
    
    logger.info("This will take 1-3 hours depending on network speed...")
    logger.info("You can monitor progress in logs/crawler.log")
    
    try:
        from crawler import main as crawler_main
        crawler_main()
        logger.info("✓ Crawling complete")
    except Exception as e:
        logger.error(f"Crawler failed: {e}", exc_info=True)
        sys.exit(1)


def build_index():
    """Build inverted index"""
    step(6, "Building Inverted Index")
    
    logger.info("Processing crawled pages and building index...")
    logger.info("This will take 10-30 minutes...")
    
    try:
        from indexer import main as indexer_main
        indexer_main()
        logger.info("✓ Index built successfully")
    except Exception as e:
        logger.error(f"Index building failed: {e}", exc_info=True)
        sys.exit(1)


def verify_system():
    """Verify system is ready"""
    step(7, "Verifying System")
    
    from config import INDEX_DIR, CRAWL_DIR
    
    # Check index exists
    index_file = INDEX_DIR / "search_index.pkl"
    if not index_file.exists():
        logger.error("Index file not found!")
        sys.exit(1)
    logger.info(f"✓ Index file: {index_file}")
    
    # Check crawled data
    crawl_metadata = CRAWL_DIR / "crawl_metadata.json"
    if crawl_metadata.exists():
        import json
        with open(crawl_metadata, 'r') as f:
            metadata = json.load(f)
        logger.info(f"✓ Crawled pages: {metadata.get('total_pages', 0):,}")
        logger.info(f"✓ Crawled domains: {metadata.get('total_domains', 0)}")
    else:
        logger.warning("Crawl metadata not found")
    
    # Load index and verify
    logger.info("Testing index loading...")
    try:
        from indexer import InvertedIndex
        index = InvertedIndex.load(index_file)
        stats = index.stats()
        logger.info(f"✓ Index documents: {stats['num_documents']:,}")
        logger.info(f"✓ Index terms: {stats['num_terms']:,}")
    except Exception as e:
        logger.error(f"Index verification failed: {e}")
        sys.exit(1)
    
    logger.info("✓ System verified and ready!")


def print_next_steps():
    """Print instructions for starting the server"""
    print("\n" + "=" * 80)
    print("INITIALIZATION COMPLETE!")
    print("=" * 80)
    print("\nYour Klar Search Engine is now ready to start.")
    print("\nNext steps:")
    print("\n1. Start the server:")
    print("   python api_server.py")
    print("\n2. Or use the startup script:")
    print("   python start_server.py")
    print("\n3. Test the search:")
    print("   Open browser: http://localhost:5000/api/health")
    print("   Search: http://localhost:5000/api/search?q=svenska+nyheter")
    print("\n4. Connect Klar Browser:")
    print("   Point browser to: http://YOUR_IP:5000")
    print("   Or configure DNS: klar.oscyra.solutions → YOUR_IP")
    print("\n" + "=" * 80)
    print(f"\nInitialization completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")


def main():
    """Run full initialization"""
    start_time = datetime.now()
    
    print_banner()
    
    try:
        check_python_version()
        install_dependencies()
        download_nltk_data()
        create_directories()
        verify_domains()
        run_crawler()
        build_index()
        verify_system()
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info(f"\n✓ Total initialization time: {duration}")
        
        print_next_steps()
        
    except KeyboardInterrupt:
        logger.warning("\nInitialization cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\nInitialization failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
