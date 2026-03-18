"""
KLAR Crawler Wrapper - Live-updating terminal UI with 3 segments
"""

import subprocess
import sys
import re
import time
from pathlib import Path
from collections import deque
from datetime import datetime

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, BarColumn, DownloadColumn, TimeRemainingColumn
    from rich.table import Table
    from rich.layout import Layout
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

class CrawlerMonitor:
    def __init__(self):
        self.recent_crawls = deque(maxlen=5)  # For live display
        self.skipped_domains = deque(maxlen=5)  # For live display
        self.all_crawled = []  # Store all crawled domains
        self.all_skipped = []  # Store all skipped with reasons
        self.total_pages = 0
        self.total_domains = 0
        self.total_skipped = 0
        self.start_time = time.time()
        self.current_progress = (0, 99)  # (current, total)
        self.last_domains = 0
        self.last_pages = 0
        self.console = Console() if HAS_RICH else None
        
    def parse_line(self, line):
        """Parse crawler log lines and extract meaningful data"""
        
        if not line.strip():
            return
        
        # Match: "[SKIP] domain.se - reason"
        if '[SKIP]' in line:
            match = re.search(r'\[SKIP\]\s+(\S+)\s+-\s+(.+)', line)
            if match:
                domain = match.group(1)
                reason = match.group(2)
                self.skipped_domains.append(domain)
                self.all_skipped.append((domain, reason))
                self.total_skipped += 1
        
        # Match: Timeout errors
        elif 'Timeout after' in line and 'skipping' in line:
            match = re.search(r'(\S+):\s+Timeout after \d+s', line)
            if match:
                domain = match.group(1)
                self.skipped_domains.append(domain)
                self.all_skipped.append((domain, "Timeout (hung > 10 minutes)"))
                self.total_skipped += 1
        
        # Match: "[DONE] domain.se: X pages crawled"
        elif '[DONE]' in line and 'pages crawled' in line:
            match = re.search(r'\[DONE\]\s+(\S+):\s+(\d+)\s+pages', line)
            if match:
                domain = match.group(1)
                pages = int(match.group(2))
                self.recent_crawls.append((domain, pages))
                self.all_crawled.append((domain, pages))
                self.total_pages += pages
                self.total_domains += 1
        
        # Match: "Progress: X/99 domains (Y total pages)"
        elif 'Progress:' in line and 'domains' in line:
            match = re.search(r'Progress:\s+(\d+)/(\d+)\s+domains\s+\((\d+)\s+total', line)
            if match:
                current_dom = int(match.group(1))
                total_dom = int(match.group(2))
                total_pgs = int(match.group(3))
                
                self.current_progress = (current_dom, total_dom)
                self.last_domains = current_dom
                self.last_pages = total_pgs
    
    def build_display(self):
        """Build the complete 3-segment display"""
        
        output = "\n" + "="*80 + "\n"
        output += "SEGMENT 1: CURRENT CRAWL ACTIVITY\n"
        output += "="*80 + "\n"
        
        # Show crawled domains
        if self.recent_crawls:
            output += "  Crawled:\n"
            for domain, pages in list(self.recent_crawls):
                if pages == 0:
                    status = "0 pages"
                else:
                    status = f"{pages} pages"
                output += f"    ✓ {domain:<28} → {status}\n"
        else:
            output += "  (waiting for crawl to start...)\n"
        
        # Show skipped domains
        if self.skipped_domains:
            output += "\n  Skipped:\n"
            for domain in list(self.skipped_domains):
                output += f"    ⊘ {domain:<28} → unreachable\n"
        
        output += "\n" + "="*80 + "\n"
        output += "SEGMENT 2: CRAWL PROGRESS & STATUS\n"
        output += "="*80 + "\n"
        
        current, total = self.current_progress
        elapsed = int(time.time() - self.start_time)
        elapsed_str = f"{elapsed // 60}m {elapsed % 60}s"
        
        if current > 0:
            time_per_domain = elapsed / current
            remaining_domains = total - current
            estimated_remaining = int(time_per_domain * remaining_domains)
            est_str = f"{estimated_remaining // 60}m {estimated_remaining % 60}s"
        else:
            est_str = "calculating..."
        
        progress_pct = int((current / total) * 100) if total > 0 else 0
        bar_filled = int(progress_pct / 5)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)
        
        output += f"  Domains: {current}/{total:<3} [{bar}] {progress_pct}%\n"
        output += f"  Pages:   {self.last_pages:<5} total\n"
        output += f"  Time:    {elapsed_str} elapsed | Est: {est_str} remaining\n"
        
        output += "\n" + "="*80 + "\n"
        output += "SEGMENT 3: SUMMARY & STATUS\n"
        output += "="*80 + "\n"
        
        if current > 0:
            pages_per_min = int(self.last_pages / (elapsed / 60)) if elapsed > 0 else 0
            output += f"  ✓ Domains processed: {current}\n"
            output += f"  ✓ Domains skipped:   {self.total_skipped}\n"
            output += f"  ✓ Total pages:       {self.last_pages}\n"
            output += f"  ✓ Pages/minute:      {pages_per_min}\n"
            output += f"  ✓ Elapsed:           {elapsed_str}\n"
        
        return output

def clear_screen():
    """Clear terminal screen"""
    sys.stdout.write('\033[2J\033[H')
    sys.stdout.flush()

def main():
    """Run crawler with live-updating display"""
    
    monitor = CrawlerMonitor()
    
    # Run crawler subprocess with unbuffered output
    process = subprocess.Popen(
        [sys.executable, '-u', 'crawler.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    
    last_update = time.time()
    update_interval = 0.5  # Update display every 0.5 seconds
    
    try:
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
                
            monitor.parse_line(line)
            
            # Update display periodically
            now = time.time()
            if now - last_update >= update_interval:
                clear_screen()
                print(monitor.build_display(), end='', flush=True)
                last_update = now
    
    except KeyboardInterrupt:
        print("\n\n[WARNING] Crawling interrupted by user")
        process.terminate()
        return 1
    finally:
        process.wait()
        
        # Final display - clear screen one last time
        clear_screen()
        print(monitor.build_display(), end='', flush=True)
        
        # === SEGMENT 1: Show all crawled domains ===
        clear_screen()
        print("\n" + "="*80)
        print("CRAWL COMPLETE - SEGMENT 1: ALL CRAWLED DOMAINS")
        print("="*80 + "\n")
        
        if monitor.all_crawled:
            print(f"  Total domains crawled: {len(monitor.all_crawled)}\n")
            for domain, pages in monitor.all_crawled:
                pages_str = f"{pages} pages" if pages > 0 else "0 pages"
                print(f"  ✓ {domain:<35} → {pages_str}")
        else:
            print("  (No domains were crawled)")
        
        input("\n\nPress ENTER to continue to skipped domains...")
        
        # === SEGMENT 2: Show all skipped domains ===
        clear_screen()
        print("\n" + "="*80)
        print("CRAWL COMPLETE - SEGMENT 2: SKIPPED DOMAINS")
        print("="*80 + "\n")
        
        if monitor.all_skipped:
            print(f"  Total domains skipped: {len(monitor.all_skipped)}\n")
            for domain, reason in monitor.all_skipped:
                print(f"  ⊘ {domain:<35} → {reason}")
        else:
            print("  (No domains were skipped)")
        
        input("\n\nPress ENTER to continue to summary...")
        
        # === SEGMENT 3: Show summary results ===
        clear_screen()
        print("\n" + "="*80)
        print("CRAWL COMPLETE - SEGMENT 3: SUMMARY & RESULTS")
        print("="*80 + "\n")
        
        elapsed_total = int(time.time() - monitor.start_time)
        elapsed_str = f"{elapsed_total // 60}m {elapsed_total % 60}s"
        pages_per_min = int(monitor.last_pages / (elapsed_total / 60)) if elapsed_total > 0 else 0
        
        crawled_dir = Path('data/crawled')
        json_files = list(crawled_dir.glob('*.json')) if crawled_dir.exists() else []
        
        print(f"  ✓ Domains crawled:   {len(monitor.all_crawled)}")
        print(f"  ✓ Domains skipped:   {len(monitor.all_skipped)}")
        print(f"  ✓ Total pages:       {monitor.last_pages}")
        print(f"  ✓ Files created:     {len(json_files)}")
        print(f"  ✓ Time taken:        {elapsed_str}")
        print(f"  ✓ Pages/minute:      {pages_per_min}")
        
        if json_files:
            print(f"\n  ✓ Status: CRAWLING COMPLETE ✓")
            print(f"\n  Data ready for: Indexing → Ranking → API Deploy")
        else:
            print(f"\n  ⚠ Status: No pages crawled")
            print(f"  → Check logs/crawler.log for details")
        
        # Ask about starting server
        print("\n" + "="*80)
        start_server = input("\nStart API server now? (Y/N): ").strip().upper()
        
        if start_server == 'Y':
            print("\n[INFO] Starting API server...")
            print("[INFO] Run 'python api_server.py' in a new terminal")
            print("[INFO] Or let the deployment script continue...")
        else:
            print("\n[INFO] You can start the server later with: python api_server.py")
    
    return process.returncode

if __name__ == '__main__':
    sys.exit(main())


