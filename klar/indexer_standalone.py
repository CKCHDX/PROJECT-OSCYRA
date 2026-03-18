"""
Klar Search Engine - Standalone Indexer
Builds search index from crawled data
"""

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/indexer.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Build search index"""
    try:
        from indexer import IndexBuilder
        from config import INDEX_DIR
        
        logger.info("Klar Search Engine - Index Builder")
        logger.info("=" * 80)
        
        # Build index
        builder = IndexBuilder()
        builder.build()
        
        # Save index
        index_file = INDEX_DIR / "search_index.pkl"
        builder.index.save(index_file)
        
        logger.info("=" * 80)
        logger.info("INDEX BUILD COMPLETE")
        logger.info("=" * 80)
        
        return 0
        
    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
