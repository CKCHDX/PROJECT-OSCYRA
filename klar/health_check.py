#!/usr/bin/env python3
"""
System Health Check Script
Verify all components are ready for production deployment

Checks:
1. Python version and dependencies
2. Directory structure
3. Configuration validity
4. Index existence
5. Test suite status
6. Security configuration
7. Deployment readiness
"""

import sys
import subprocess
from pathlib import Path
import importlib.util

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def check(name, passed, message=""):
    """Print check result"""
    status = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
    print(f"{status} {name}")
    if message:
        print(f"  {message}")
    return passed

def main():
    print("=" * 80)
    print(f"{BLUE}Klar Search Engine - Enterprise Health Check{RESET}")
    print("=" * 80)
    print()
    
    all_passed = True
    
    # 1. Python version
    print(f"{BLUE}[1/10] Checking Python version...{RESET}")
    python_version = sys.version_info
    passed = python_version >= (3, 8)
    all_passed &= check(
        "Python Version",
        passed,
        f"Current: {python_version.major}.{python_version.minor}.{python_version.micro} (Required: 3.8+)"
    )
    print()
    
    # 2. Dependencies
    print(f"{BLUE}[2/10] Checking dependencies...{RESET}")
    required = {
        'flask': 'flask',
        'requests': 'requests',
        'beautifulsoup4': 'bs4',
        'nltk': 'nltk',
        'numpy': 'numpy',
        'psutil': 'psutil',
        'prometheus_client': 'prometheus_client',
        'pytest': 'pytest'
    }
    missing = []
    for package_name, import_name in required.items():
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing.append(package_name)
    
    passed = len(missing) == 0
    all_passed &= check(
        "Required Packages",
        passed,
        f"Missing: {', '.join(missing)}" if missing else "All packages installed"
    )
    print()
    
    # 3. Directory structure
    print(f"{BLUE}[3/10] Checking directory structure...{RESET}")
    required_dirs = [
        'data', 'data/index', 'data/crawled', 'data/cache', 'data/backups',
        'logs', 'tests', 'deploy', 'scripts', 'docs'
    ]
    missing_dirs = []
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            missing_dirs.append(dir_path)
    
    passed = len(missing_dirs) == 0
    all_passed &= check(
        "Directory Structure",
        passed,
        f"Missing: {', '.join(missing_dirs)}" if missing_dirs else "All directories exist"
    )
    print()
    
    # 4. Core files
    print(f"{BLUE}[4/10] Checking core files...{RESET}")
    required_files = [
        'config.py', 'crawler.py', 'indexer.py', 'nlp_processor.py',
        'ranker.py', 'api_server.py', 'swedish_domains.py'
    ]
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    passed = len(missing_files) == 0
    all_passed &= check(
        "Core Files",
        passed,
        f"Missing: {', '.join(missing_files)}" if missing_files else "All core files present"
    )
    print()
    
    # 5. Enterprise infrastructure
    print(f"{BLUE}[5/10] Checking enterprise infrastructure...{RESET}")
    enterprise_files = [
        'logger_config.py', 'recovery.py', 'security.py',
        'metrics.py', 'alerting.py', 'database.py'
    ]
    missing_enterprise = []
    for file_path in enterprise_files:
        if not Path(file_path).exists():
            missing_enterprise.append(file_path)
    
    passed = len(missing_enterprise) == 0
    all_passed &= check(
        "Enterprise Infrastructure",
        passed,
        f"Missing: {', '.join(missing_enterprise)}" if missing_enterprise else "All enterprise files present"
    )
    print()
    
    # 6. Tests
    print(f"{BLUE}[6/10] Checking test suite...{RESET}")
    test_files = list(Path('tests').glob('test_*.py')) if Path('tests').exists() else []
    passed = len(test_files) >= 4
    all_passed &= check(
        "Test Suite",
        passed,
        f"{len(test_files)} test files found (Expected: 4+)"
    )
    print()
    
    # 7. Deployment configs
    print(f"{BLUE}[7/10] Checking deployment configs...{RESET}")
    deploy_files = ['Dockerfile', 'docker-compose.yml', 'deploy/kse.service', 'deploy/nginx.conf']
    missing_deploy = []
    for file_path in deploy_files:
        if not Path(file_path).exists():
            missing_deploy.append(file_path)
    
    passed = len(missing_deploy) == 0
    all_passed &= check(
        "Deployment Configs",
        passed,
        f"Missing: {', '.join(missing_deploy)}" if missing_deploy else "All deployment files present"
    )
    print()
    
    # 8. Documentation
    print(f"{BLUE}[8/10] Checking documentation...{RESET}")
    doc_files = ['README.md', 'DEPLOYMENT.md', 'QUICKSTART.md', 'ENTERPRISE_STATUS.md']
    missing_docs = []
    for file_path in doc_files:
        if not Path(file_path).exists():
            missing_docs.append(file_path)
    
    passed = len(missing_docs) == 0
    all_passed &= check(
        "Documentation",
        passed,
        f"Missing: {', '.join(missing_docs)}" if missing_docs else "All documentation files present"
    )
    print()
    
    # 9. Configuration validity
    print(f"{BLUE}[9/10] Checking configuration...{RESET}")
    try:
        import config
        # Check critical config values
        checks = [
            hasattr(config, 'MAX_CONCURRENT_CRAWLS'),
            hasattr(config, 'API_HOST'),
            hasattr(config, 'API_PORT'),
            hasattr(config, 'SWEDISH_STOPWORDS'),
            hasattr(config, 'RANKING_WEIGHTS'),
        ]
        passed = all(checks)
        all_passed &= check(
            "Configuration",
            passed,
            "Configuration valid" if passed else "Configuration incomplete"
        )
    except Exception as e:
        all_passed &= check("Configuration", False, f"Error: {e}")
    print()
    
    # 10. Overall readiness
    print(f"{BLUE}[10/10] Production readiness assessment...{RESET}")
    readiness_score = 0
    
    # Check NLTK data
    try:
        import nltk
        try:
            nltk.data.find('tokenizers/punkt')
            readiness_score += 1
        except:
            print(f"  {YELLOW}⚠{RESET} NLTK data not downloaded (run init_kse.py)")
    except:
        pass
    
    # Check if index exists
    if Path('data/index/search_index.pkl').exists():
        readiness_score += 1
        print(f"  {GREEN}✓{RESET} Search index exists")
    else:
        print(f"  {YELLOW}⚠{RESET} Search index not built (run init_kse.py)")
    
    # Check crawled data
    crawled_files = list(Path('data/crawled').rglob('*.json')) if Path('data/crawled').exists() else []
    if len(crawled_files) > 0:
        readiness_score += 1
        print(f"  {GREEN}✓{RESET} Crawled data exists ({len(crawled_files)} files)")
    else:
        print(f"  {YELLOW}⚠{RESET} No crawled data (run init_kse.py)")
    
    print()
    print("=" * 80)
    
    if all_passed and readiness_score == 3:
        print(f"{GREEN}✅ SYSTEM STATUS: PRODUCTION READY{RESET}")
        print("All checks passed. System ready for deployment.")
        return 0
    elif all_passed:
        print(f"{YELLOW}⚠️  SYSTEM STATUS: SETUP REQUIRED{RESET}")
        print("All components present, but initial setup needed.")
        print("Run: python init_kse.py")
        return 1
    else:
        print(f"{RED}❌ SYSTEM STATUS: NOT READY{RESET}")
        print("Some checks failed. Review errors above.")
        return 2

if __name__ == '__main__':
    sys.exit(main())
