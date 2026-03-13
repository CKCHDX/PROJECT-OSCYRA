#!/usr/bin/env python3
"""
Run All Tests
Enterprise test suite execution script

Usage:
    python run_tests.py
    python run_tests.py --verbose
    python run_tests.py --coverage
"""

import sys
import subprocess
from pathlib import Path

def run_tests(verbose=False, coverage=False):
    """Run the test suite"""
    
    # Change to project directory
    project_dir = Path(__file__).parent
    
    # Build pytest command
    cmd = ["pytest", "tests/"]
    
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    if coverage:
        cmd.extend(["--cov=.", "--cov-report=html", "--cov-report=term"])
    
    cmd.append("--tb=short")
    
    print("=" * 80)
    print("Klar Search Engine - Test Suite")
    print("=" * 80)
    print(f"Running: {' '.join(cmd)}")
    print("=" * 80)
    
    # Run tests
    try:
        result = subprocess.run(cmd, cwd=project_dir)
        return result.returncode
    except FileNotFoundError:
        print("ERROR: pytest not found. Install with: pip install pytest pytest-cov")
        return 1

if __name__ == '__main__':
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    coverage = '--coverage' in sys.argv or '--cov' in sys.argv
    
    exit_code = run_tests(verbose=verbose, coverage=coverage)
    
    if exit_code == 0:
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ TESTS FAILED")
        print("=" * 80)
    
    sys.exit(exit_code)
