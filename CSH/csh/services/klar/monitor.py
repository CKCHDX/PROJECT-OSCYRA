"""
Klar Search Engine - System Monitor
Real-time monitoring and health checks for KSE

Usage:
    python monitor.py              # Run continuous monitoring
    python monitor.py --once       # Single status check
    python monitor.py --check-all  # Comprehensive system check
"""

import sys
import time
import psutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict

import requests

from config import (
    API_PORT, INDEX_DIR, CRAWL_DIR, LOGS_DIR,
    TARGET_RESPONSE_TIME_MS
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SystemMonitor:
    """Monitor KSE system health"""
    
    def __init__(self):
        self.api_url = f"http://localhost:{API_PORT}"
    
    def check_api_health(self) -> Dict:
        """Check if API server is responding"""
        try:
            response = requests.get(f"{self.api_url}/api/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    'status': 'healthy',
                    'response_time_ms': response.elapsed.total_seconds() * 1000,
                    'server_data': data
                }
            else:
                return {
                    'status': 'unhealthy',
                    'error': f'HTTP {response.status_code}'
                }
        except requests.exceptions.ConnectionError:
            return {
                'status': 'down',
                'error': 'Cannot connect to API server'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def check_search_performance(self) -> Dict:
        """Test search performance"""
        test_queries = [
            'svenska nyheter',
            'regeringen',
            'stockholm',
        ]
        
        results = []
        for query in test_queries:
            try:
                start = time.time()
                response = requests.get(
                    f"{self.api_url}/api/search",
                    params={'q': query},
                    timeout=10
                )
                elapsed_ms = (time.time() - start) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    results.append({
                        'query': query,
                        'status': 'ok',
                        'response_time_ms': elapsed_ms,
                        'result_count': data.get('count', 0),
                        'meets_target': elapsed_ms < TARGET_RESPONSE_TIME_MS
                    })
                else:
                    results.append({
                        'query': query,
                        'status': 'error',
                        'response_time_ms': elapsed_ms,
                        'error': response.status_code
                    })
            except Exception as e:
                results.append({
                    'query': query,
                    'status': 'failed',
                    'error': str(e)
                })
        
        # Calculate average
        successful = [r for r in results if r['status'] == 'ok']
        avg_time = sum(r['response_time_ms'] for r in successful) / len(successful) if successful else 0
        
        return {
            'queries_tested': len(test_queries),
            'successful': len(successful),
            'average_time_ms': avg_time,
            'meets_target': avg_time < TARGET_RESPONSE_TIME_MS,
            'details': results
        }
    
    def check_index_status(self) -> Dict:
        """Check index file status"""
        index_file = INDEX_DIR / "search_index.pkl"
        
        if not index_file.exists():
            return {
                'status': 'missing',
                'error': 'Index file not found'
            }
        
        # Get file info
        stat = index_file.stat()
        size_mb = stat.st_size / (1024 * 1024)
        modified = datetime.fromtimestamp(stat.st_mtime)
        age_days = (datetime.now() - modified).days
        
        return {
            'status': 'exists',
            'path': str(index_file),
            'size_mb': round(size_mb, 2),
            'modified': modified.isoformat(),
            'age_days': age_days,
            'needs_update': age_days > 30
        }
    
    def check_crawl_data(self) -> Dict:
        """Check crawled data status"""
        if not CRAWL_DIR.exists():
            return {
                'status': 'missing',
                'error': 'Crawl directory not found'
            }
        
        # Count domain directories
        domain_dirs = [d for d in CRAWL_DIR.iterdir() if d.is_dir()]
        
        # Count total pages
        total_pages = 0
        for domain_dir in domain_dirs:
            total_pages += len(list(domain_dir.glob('*.json')))
        
        # Check metadata
        metadata_file = CRAWL_DIR / 'crawl_metadata.json'
        metadata = {}
        if metadata_file.exists():
            import json
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        
        return {
            'status': 'exists',
            'domains_crawled': len(domain_dirs),
            'total_pages': total_pages,
            'metadata': metadata
        }
    
    def check_system_resources(self) -> Dict:
        """Check system resource usage"""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory
        memory = psutil.virtual_memory()
        memory_used_gb = memory.used / (1024 ** 3)
        memory_total_gb = memory.total / (1024 ** 3)
        
        # Disk
        disk = psutil.disk_usage(str(Path.cwd()))
        disk_used_gb = disk.used / (1024 ** 3)
        disk_total_gb = disk.total / (1024 ** 3)
        
        return {
            'cpu_percent': cpu_percent,
            'memory': {
                'used_gb': round(memory_used_gb, 2),
                'total_gb': round(memory_total_gb, 2),
                'percent': memory.percent
            },
            'disk': {
                'used_gb': round(disk_used_gb, 2),
                'total_gb': round(disk_total_gb, 2),
                'percent': disk.percent
            }
        }
    
    def check_logs(self) -> Dict:
        """Check log file status"""
        logs = {}
        
        for log_file in LOGS_DIR.glob('*.log'):
            stat = log_file.stat()
            size_mb = stat.st_size / (1024 * 1024)
            
            # Read last 10 lines
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                last_lines = lines[-10:] if len(lines) > 10 else lines
            
            # Count errors
            error_count = sum(1 for line in last_lines if 'ERROR' in line)
            
            logs[log_file.name] = {
                'size_mb': round(size_mb, 2),
                'recent_errors': error_count,
                'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
        
        return logs
    
    def get_comprehensive_status(self) -> Dict:
        """Get complete system status"""
        return {
            'timestamp': datetime.now().isoformat(),
            'api': self.check_api_health(),
            'performance': self.check_search_performance(),
            'index': self.check_index_status(),
            'crawl_data': self.check_crawl_data(),
            'system': self.check_system_resources(),
            'logs': self.check_logs()
        }
    
    def print_status(self, status: Dict):
        """Print formatted status"""
        print("\n" + "=" * 80)
        print(f"KLAR SEARCH ENGINE - SYSTEM STATUS")
        print(f"Timestamp: {status['timestamp']}")
        print("=" * 80)
        
        # API Health
        api = status['api']
        print(f"\n📡 API Server: {api['status'].upper()}")
        if api['status'] == 'healthy':
            print(f"   Response Time: {api['response_time_ms']:.1f}ms")
        elif 'error' in api:
            print(f"   Error: {api['error']}")
        
        # Performance
        perf = status['performance']
        print(f"\n⚡ Search Performance:")
        print(f"   Queries Tested: {perf['queries_tested']}")
        print(f"   Successful: {perf['successful']}")
        print(f"   Average Time: {perf['average_time_ms']:.1f}ms")
        print(f"   Meets Target (<{TARGET_RESPONSE_TIME_MS}ms): {'✓ Yes' if perf['meets_target'] else '✗ No'}")
        
        # Index
        index = status['index']
        print(f"\n📚 Search Index: {index['status'].upper()}")
        if index['status'] == 'exists':
            print(f"   Size: {index['size_mb']} MB")
            print(f"   Age: {index['age_days']} days")
            if index['needs_update']:
                print(f"   ⚠️  Index is over 30 days old - consider recrawling")
        
        # Crawl Data
        crawl = status['crawl_data']
        print(f"\n🕷️  Crawled Data: {crawl['status'].upper()}")
        if crawl['status'] == 'exists':
            print(f"   Domains: {crawl['domains_crawled']}")
            print(f"   Total Pages: {crawl['total_pages']:,}")
        
        # System Resources
        system = status['system']
        print(f"\n💻 System Resources:")
        print(f"   CPU: {system['cpu_percent']}%")
        print(f"   Memory: {system['memory']['used_gb']:.1f}/{system['memory']['total_gb']:.1f} GB ({system['memory']['percent']}%)")
        print(f"   Disk: {system['disk']['used_gb']:.1f}/{system['disk']['total_gb']:.1f} GB ({system['disk']['percent']}%)")
        
        # Logs
        logs = status['logs']
        print(f"\n📝 Logs:")
        for log_name, log_info in logs.items():
            error_indicator = f" ⚠️ {log_info['recent_errors']} recent errors" if log_info['recent_errors'] > 0 else ""
            print(f"   {log_name}: {log_info['size_mb']} MB{error_indicator}")
        
        print("\n" + "=" * 80 + "\n")
    
    def monitor_continuous(self, interval: int = 60):
        """Continuous monitoring with updates every interval seconds"""
        logger.info(f"Starting continuous monitoring (updates every {interval}s)")
        logger.info("Press Ctrl+C to stop")
        
        try:
            while True:
                status = self.get_comprehensive_status()
                self.print_status(status)
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("\nMonitoring stopped by user")


def main():
    """Main monitoring entry point"""
    monitor = SystemMonitor()
    
    if '--once' in sys.argv:
        # Single check
        status = monitor.get_comprehensive_status()
        monitor.print_status(status)
    
    elif '--check-all' in sys.argv:
        # Comprehensive check with detailed output
        status = monitor.get_comprehensive_status()
        monitor.print_status(status)
        
        # Also print detailed performance results
        print("\n📊 DETAILED PERFORMANCE RESULTS:")
        print("=" * 80)
        for result in status['performance']['details']:
            print(f"\nQuery: '{result['query']}'")
            print(f"  Status: {result['status']}")
            if 'response_time_ms' in result:
                print(f"  Response Time: {result['response_time_ms']:.1f}ms")
                print(f"  Results: {result.get('result_count', 0)}")
            if 'error' in result:
                print(f"  Error: {result['error']}")
    
    else:
        # Continuous monitoring (default)
        monitor.monitor_continuous(interval=60)


if __name__ == "__main__":
    main()
