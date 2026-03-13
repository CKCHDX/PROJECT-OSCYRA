"""
Klar Search Engine - Web Crawler
Enterprise-Grade Parallel Crawler with Dynamic Speed Adjustment

Features:
- Crawls 10 domains simultaneously for maximum speed
- Dynamic timeout adjustment (avoids timeouts, adapts to slow sites)
- Respects robots.txt (polite crawling)
- Comprehensive error handling
- Content extraction (HTML, text, links, metadata)
- Recrawl scheduling (30-day cycle)
"""

import time
import logging
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.robotparser import RobotFileParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from collections import deque

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

# Suppress SSL warnings for Swedish gov domains with cert issues
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from config import *
from swedish_domains import ALL_DOMAINS

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'crawler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Suppress verbose third-party warnings
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('requests').setLevel(logging.ERROR)
logging.getLogger('boto3').setLevel(logging.ERROR)
logging.getLogger('botocore').setLevel(logging.ERROR)

# Load skip domains configuration
SKIP_DOMAINS = set()
try:
    from load_settings import load_settings
    settings = load_settings()
    skip_str = settings.get('SYSTEM', {}).get('SKIP_DOMAINS', '')
    if skip_str:
        SKIP_DOMAINS = set(d.strip() for d in skip_str.split(',') if d.strip())
        if SKIP_DOMAINS:
            logger.info(f"Configured to skip {len(SKIP_DOMAINS)} domains: {', '.join(sorted(SKIP_DOMAINS))}")
except Exception as e:
    logger.debug(f"Could not load skip domains: {e}")

# User agent rotation
ua = UserAgent()


@dataclass
class CrawledPage:
    """Represents a crawled web page with all metadata"""
    url: str
    domain: str
    title: str
    content: str  # Main text content
    html: str  # Raw HTML
    links: List[str]
    meta_description: str
    meta_keywords: str
    language: str
    status_code: int
    crawled_at: str  # ISO format timestamp
    content_hash: str
    word_count: int
    headers: Dict[str, str]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    def save(self, directory: Path):
        """Save crawled page to disk"""
        # Create domain-specific directory
        domain_dir = directory / self.domain.replace('.', '_')
        domain_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename from URL hash
        url_hash = hashlib.md5(self.url.encode()).hexdigest()
        filepath = domain_dir / f"{url_hash}.json"
        
        # Save as JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        
        return filepath


class RobotsTxtCache:
    """Cache for robots.txt files to avoid repeated requests"""
    
    def __init__(self):
        self.cache: Dict[str, RobotFileParser] = {}
    
    def can_fetch(self, url: str, user_agent: str) -> bool:
        """Check if URL can be fetched according to robots.txt"""
        if not RESPECT_ROBOTS_TXT:
            return True
        
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        
        # Check cache
        if domain not in self.cache:
            robots_url = urljoin(domain, '/robots.txt')
            rp = RobotFileParser()
            rp.set_url(robots_url)
            try:
                verify_ssl = not parsed.netloc.endswith('.se')
                response = requests.get(
                    robots_url,
                    headers={'User-Agent': USER_AGENT},
                    timeout=min(10, CRAWL_TIMEOUT),
                    allow_redirects=True,
                    verify=verify_ssl
                )
                if response.status_code >= 400:
                    logger.warning(f"robots.txt returned {response.status_code} for {domain}; allowing crawl")
                    return True
                rp.parse(response.text.splitlines())
            except requests.exceptions.RequestException as e:
                logger.warning(f"Could not read robots.txt for {domain}: {e}")
                # If robots.txt doesn't exist or can't be read, allow crawling
                return True
            self.cache[domain] = rp
        
        return self.cache[domain].can_fetch(user_agent, url)


class DomainCrawler:
    """Crawler for a single domain with dynamic speed adjustment"""
    
    def __init__(self, domain: str, robots_cache: RobotsTxtCache):
        self.domain = domain
        self.start_url = self._resolve_domain_url(domain)
        self.visited: Set[str] = set()
        self.to_visit: deque = deque([self.start_url])
        self.pages_crawled = 0
        self.robots_cache = robots_cache
        self.timeout = CRAWL_TIMEOUT
        self.timeout_failures = 0
        self.success_count = 0
        
        # Session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=RETRY_DELAY,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def _resolve_domain_url(self, domain: str) -> str:
        """Intelligently resolve domain URL with multiple fallback strategies"""
        if domain.startswith('http'):
            return domain
        
        # Strategy 1: Try https://www.domain first
        www_url = f"https://www.{domain}"
        try:
            response = requests.head(www_url, timeout=5, allow_redirects=True, verify=False)
            if response.status_code < 400:
                logger.debug(f"{domain}: Using www subdomain (https)")
                return www_url
        except Exception:
            pass
        
        # Strategy 2: Try https://bare.domain
        bare_https = f"https://{domain}"
        try:
            response = requests.head(bare_https, timeout=5, allow_redirects=True, verify=False)
            if response.status_code < 400:
                logger.info(f"{domain}: Using bare domain (https)")
                return bare_https
        except Exception:
            pass
        
        # Strategy 3: Try http://www.domain (HTTP fallback)
        www_http = f"http://www.{domain}"
        try:
            response = requests.head(www_http, timeout=5, allow_redirects=True, verify=False)
            if response.status_code < 400:
                logger.info(f"{domain}: Using www domain (http fallback)")
                return www_http
        except Exception:
            pass
        
        # Strategy 4: Try http://bare.domain
        bare_http = f"http://{domain}"
        try:
            response = requests.head(bare_http, timeout=5, allow_redirects=True, verify=False)
            if response.status_code < 400:
                logger.info(f"{domain}: Using bare domain (http fallback)")
                return bare_http
        except Exception:
            pass
        
        # Strategy 5: Return www.domain and let crawl_url handle errors gracefully
        logger.warning(f"{domain}: All resolution strategies failed, trying www (will retry on crawl failure)")
        return www_url
    
    def adjust_timeout(self, success: bool):
        """Dynamically adjust timeout based on success/failure"""
        if success:
            self.success_count += 1
            self.timeout_failures = 0
            # After 5 successes, try reducing timeout slightly
            if self.success_count >= 5 and self.timeout > MIN_CRAWL_TIMEOUT:
                self.timeout = max(MIN_CRAWL_TIMEOUT, self.timeout - 2)
                self.success_count = 0
                logger.debug(f"{self.domain}: Reduced timeout to {self.timeout}s")
        else:
            self.timeout_failures += 1
            self.success_count = 0
            # After 2 failures, increase timeout
            if self.timeout_failures >= 2 and self.timeout < MAX_CRAWL_TIMEOUT:
                self.timeout = min(MAX_CRAWL_TIMEOUT, self.timeout + 5)
                self.timeout_failures = 0
                logger.debug(f"{self.domain}: Increased timeout to {self.timeout}s")
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL should be crawled"""
        if not url:
            return False
        
        parsed = urlparse(url)
        
        # Must be same domain
        if self.domain not in parsed.netloc:
            return False
        
        # Skip non-web protocols
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # Skip common non-content files
        skip_extensions = [
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.zip', '.rar', '.tar', '.gz', '.jpg', '.jpeg', '.png', '.gif',
            '.mp3', '.mp4', '.avi', '.mov', '.css', '.js', '.xml', '.json'
        ]
        if any(url.lower().endswith(ext) for ext in skip_extensions):
            return False
        
        return True
    
    def extract_content(self, html: str, url: str) -> Optional[CrawledPage]:
        """Extract relevant content from HTML"""
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # Remove script and style elements
            for script in soup(["script", "style", "noscript"]):
                script.decompose()
            
            # Extract title
            title = soup.title.string if soup.title else ""
            title = title.strip() if title else "Untitled"
            
            # Extract meta description
            meta_desc = soup.find("meta", attrs={"name": "description"})
            description = meta_desc.get("content", "") if meta_desc else ""
            
            # Extract meta keywords
            meta_keys = soup.find("meta", attrs={"name": "keywords"})
            keywords = meta_keys.get("content", "") if meta_keys else ""
            
            # Extract language
            lang = soup.html.get('lang', 'sv') if soup.html else 'sv'
            
            # Extract main text content
            # Prioritize main content areas
            main_content = (
                soup.find('main') or 
                soup.find('article') or 
                soup.find('div', class_='content') or
                soup.find('body')
            )
            
            if main_content:
                text = main_content.get_text(separator=' ', strip=True)
            else:
                text = soup.get_text(separator=' ', strip=True)
            
            # Clean text
            text = ' '.join(text.split())  # Normalize whitespace
            
            # Extract links
            links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                absolute_url = urljoin(url, href)
                # Remove fragment
                absolute_url, _ = urldefrag(absolute_url)
                if self.is_valid_url(absolute_url):
                    links.append(absolute_url)
            
            # Create hash of content for change detection
            content_hash = hashlib.md5(text.encode()).hexdigest()
            
            # Count words
            word_count = len(text.split())
            
            return CrawledPage(
                url=url,
                domain=self.domain,
                title=title,
                content=text,
                html=html,
                links=list(set(links)),  # Remove duplicates
                meta_description=description,
                meta_keywords=keywords,
                language=lang,
                status_code=200,
                crawled_at=datetime.now().isoformat(),
                content_hash=content_hash,
                word_count=word_count,
                headers={}
            )
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            return None
    
    def crawl_url(self, url: str) -> Optional[CrawledPage]:
        """Crawl a single URL"""
        # Check if already visited
        if url in self.visited:
            return None
        
        self.visited.add(url)
        
        # Check robots.txt
        if not self.robots_cache.can_fetch(url, USER_AGENT):
            logger.warning(f"[BLOCKED] robots.txt disallows: {url}")
            return None
        
        try:
            # Fetch page
            headers = {'User-Agent': USER_AGENT}
            
            # Disable SSL verification for .se domains (many gov certs have issues)
            verify_ssl = not self.domain.endswith('.se')
            
            response = self.session.get(
                url, 
                headers=headers, 
                timeout=self.timeout,
                allow_redirects=True,
                verify=verify_ssl
            )
            
            # Check if successful
            if response.status_code != 200:
                logger.warning(f"[HTTP] {url} returned {response.status_code}")
                self.adjust_timeout(False)
                return None
            
            # Extract content
            page = self.extract_content(response.text, url)
            
            if page:
                # Add new links to queue
                for link in page.links:
                    if link not in self.visited and len(self.to_visit) < MAX_PAGES_PER_DOMAIN:
                        self.to_visit.append(link)
                
                self.pages_crawled += 1
                self.adjust_timeout(True)
                logger.info(f"[CRAWL] {url} ({self.pages_crawled}/{MAX_PAGES_PER_DOMAIN})")
                
            return page
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout for {url} (timeout={self.timeout}s)")
            self.adjust_timeout(False)
            return None
        except requests.exceptions.SSLError as e:
            logger.warning(f"SSL error for {url}: {e}")
            self.adjust_timeout(False)
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error for {url}: {e}")
            self.adjust_timeout(False)
            return None
        except Exception as e:
            logger.error(f"Unexpected error crawling {url}: {e}")
            self.adjust_timeout(False)
            return None
        finally:
            # Politeness delay
            time.sleep(CRAWL_DELAY)
    
    def crawl(self) -> List[CrawledPage]:
        """Crawl entire domain (up to MAX_PAGES_PER_DOMAIN)"""
        logger.info(f"Starting crawl of {self.domain}")
        pages = []
        
        while self.to_visit and self.pages_crawled < MAX_PAGES_PER_DOMAIN:
            url = self.to_visit.popleft()
            page = self.crawl_url(url)
            if page:
                pages.append(page)
        
        logger.info(f"[DONE] {self.domain}: {len(pages)} pages crawled")
        if len(pages) == 0:
            logger.warning(f"[ZERO] {self.domain}: 0 pages (start={self.start_url})")
        return pages


class ParallelCrawler:
    """Manages parallel crawling of multiple domains"""
    
    def __init__(self, domains: List[str], max_workers: int = MAX_CONCURRENT_CRAWLS):
        self.domains = domains
        self.max_workers = max_workers
        self.robots_cache = RobotsTxtCache()
        self.crawled_pages: List[CrawledPage] = []
        self.start_time = None
        self.end_time = None
        self.state_file = CRAWL_DIR / 'crawler_state.json'
        self.completed_domains = set()
        
        # Load previous state if resuming
        if RESUME_CRAWLING:
            self._load_state()
    
    def _load_state(self):
        """Load previous crawl state to resume"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.completed_domains = set(state.get('completed_domains', []))
                    if self.completed_domains:
                        logger.info(f"[RESUME] Found {len(self.completed_domains)} completed domains")
                        logger.info(f"[RESUME] Continuing from last session")
            except Exception as e:
                logger.warning(f"Could not load state: {e}")
    
    def _save_state(self):
        """Save current crawl state"""
        try:
            state = {
                'completed_domains': list(self.completed_domains),
                'last_updated': datetime.now().isoformat(),
                'total_pages': len(self.crawled_pages)
            }
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Could not save state: {e}")
    
    def crawl_domain(self, domain: str) -> List[CrawledPage]:
        """Crawl a single domain (wrapper for thread executor)"""
        # Skip if in skip list
        if domain in SKIP_DOMAINS:
            logger.info(f"[SKIP] {domain} - In skip list (unreachable/problematic)")
            self.completed_domains.add(domain)
            self._save_state()
            return []
        
        # Skip if already completed
        if domain in self.completed_domains:
            logger.info(f"[SKIP] {domain} - Already completed in previous run")
            return []
        
        try:
            crawler = DomainCrawler(domain, self.robots_cache)
            pages = crawler.crawl()
            
            # Mark as completed and save state
            self.completed_domains.add(domain)
            self._save_state()
            
            return pages
        except Exception as e:
            logger.error(f"Fatal error crawling {domain}: {e}")
            return []
    
    def crawl_all(self) -> List[CrawledPage]:
        """Crawl all domains in parallel"""
        self.start_time = datetime.now()
        logger.info(f"Starting parallel crawl of {len(self.domains)} domains with {self.max_workers} workers")
        
        all_pages = []
        completed_domains = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all crawl tasks
            future_to_domain = {
                executor.submit(self.crawl_domain, domain): domain 
                for domain in self.domains
            }
            
            # Process completed crawls
            for future in as_completed(future_to_domain):
                domain = future_to_domain[future]
                try:
                    # Enforce per-domain timeout (prevents hanging indefinitely)
                    pages = future.result(timeout=PER_DOMAIN_TIMEOUT)
                    all_pages.extend(pages)
                    completed_domains += 1
                    
                    logger.info(
                        f"Progress: {completed_domains}/{len(self.domains)} domains "
                        f"({len(all_pages)} total pages)"
                    )
                except TimeoutError:
                    logger.error(f"{domain}: Timeout after {PER_DOMAIN_TIMEOUT}s - skipping")
                    logger.info(f"[SKIP] {domain} - Timeout (hung > {PER_DOMAIN_TIMEOUT//60} minutes)")
                    self.completed_domains.add(domain)
                    self._save_state()
                    completed_domains += 1
                    
                    logger.info(
                        f"Progress: {completed_domains}/{len(self.domains)} domains "
                        f"({len(all_pages)} total pages)"
                    )
                except Exception as e:
                    logger.error(f"Error processing {domain}: {e}")
                    completed_domains += 1
                    
                    logger.info(
                        f"Progress: {completed_domains}/{len(self.domains)} domains "
                        f"({len(all_pages)} total pages)"
                    )
        
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        
        logger.info(f"[DONE] Crawl complete: {len(all_pages)} pages from {completed_domains} domains in {duration:.1f}s")
        
        self.crawled_pages = all_pages
        return all_pages
    
    def save_all(self, directory: Path = CRAWL_DIR):
        """Save all crawled pages to disk"""
        logger.info(f"Saving {len(self.crawled_pages)} pages to {directory}")
        
        for page in self.crawled_pages:
            try:
                page.save(directory)
            except Exception as e:
                logger.error(f"Error saving {page.url}: {e}")
        
        # Save crawl metadata
        metadata = {
            'total_domains': len(self.domains),
            'total_pages': len(self.crawled_pages),
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else 0,
                    'completed_domains': len(self.completed_domains),
        }
        
        metadata_file = directory / 'crawl_metadata.json'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"[DONE] All pages saved to {directory}")
        
        # Clear state file after successful completion
        if self.state_file.exists():
            self.state_file.unlink()


def main():
    """Main crawler entry point"""
    logger.info("=" * 80)
    logger.info("KLAR SEARCH ENGINE - WEB CRAWLER")
    logger.info("=" * 80)
    logger.info(f"Total domains to crawl: {len(ALL_DOMAINS)}")
    logger.info(f"Max concurrent crawls: {MAX_CONCURRENT_CRAWLS}")
    logger.info(f"Max pages per domain: {MAX_PAGES_PER_DOMAIN}")
    logger.info("=" * 80)
    
    # Create crawler
    crawler = ParallelCrawler(ALL_DOMAINS, max_workers=MAX_CONCURRENT_CRAWLS)
    
    # Crawl all domains
    pages = crawler.crawl_all()
    
    # Save results
    crawler.save_all()
    
    logger.info("=" * 80)
    logger.info("CRAWL COMPLETE")
    logger.info(f"Total pages crawled: {len(pages)}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
