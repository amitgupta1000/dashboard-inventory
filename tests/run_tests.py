#!/usr/bin/env python
"""
Test Runner Script for Inventory Management Dashboard

This script runs all tests (backend and frontend) and generates a report.

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py backend      # Run only backend tests
    python run_tests.py frontend     # Run only frontend tests
    python run_tests.py --coverage   # Run with coverage reports
    python run_tests.py --watch      # Run in watch mode (requires pytest-watch)
"""

import subprocess
import sys
import os
from pathlib import Path

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}")
    print(f"{text}".center(60))
    print(f"{'='*60}{Colors.END}\n")

def print_section(text):
    print(f"\n{Colors.CYAN}{Colors.BOLD}➜ {text}{Colors.END}")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def run_backend_tests(coverage=False, watch=False):
    """Run backend tests."""
    print_section("Running Backend Tests (Python)")
    
    cmd = ['pytest', 'test_api.py', '-v', '--tb=short']
    
    if coverage:
        cmd.extend(['--cov=main', '--cov-report=html', '--cov-report=term'])
        print("  Coverage report will be saved to htmlcov/")
    
    if watch:
        cmd = ['ptw'] + cmd
        print("  Watch mode enabled (tests will re-run on file changes)")
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode == 0

def run_frontend_tests(coverage=False, watch=False):
    """Run frontend tests."""
    print_section("Running Frontend Tests (TypeScript/React)")
    
    frontend_dir = Path(__file__).parent / 'frontend'
    
    # Check if dependencies are installed
    node_modules = frontend_dir / 'node_modules'
    if not node_modules.exists():
        print_error("Node modules not found. Installing dependencies...")
        install_result = subprocess.run(['npm', 'install'], cwd=frontend_dir)
        if install_result.returncode != 0:
            print_error("Failed to install dependencies")
            return False
    
    # Check if vitest is installed
    vitest_path = frontend_dir / 'node_modules' / '.bin' / 'vitest'
    if not vitest_path.exists():
        print_error("Vitest not found. Installing test dependencies...")
        install_result = subprocess.run(
            ['npm', 'install', '--save-dev', 'vitest', '@testing-library/react', '@testing-library/jest-dom'],
            cwd=frontend_dir
        )
        if install_result.returncode != 0:
            print_error("Failed to install test dependencies")
            return False
    
    cmd = ['npm', 'test']
    
    if coverage:
        cmd.append('--')
        cmd.append('--coverage')
    
    if watch:
        cmd.append('--')
        cmd.append('--watch')
    
    result = subprocess.run(cmd, cwd=frontend_dir)
    return result.returncode == 0

def main():
    """Main test runner."""
    print_header("Inventory Management Dashboard - Test Suite")
    
    # Parse arguments
    backend = True
    frontend = True
    coverage = False
    watch = False
    
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg == 'backend':
                frontend = False
            elif arg == 'frontend':
                backend = False
            elif arg == '--coverage':
                coverage = True
            elif arg == '--watch':
                watch = True
            elif arg == '--help':
                print(__doc__)
                sys.exit(0)
    
    results = {}
    
    # Run backend tests
    if backend:
        try:
            results['backend'] = run_backend_tests(coverage, watch)
        except Exception as e:
            print_error(f"Error running backend tests: {e}")
            results['backend'] = False
    
    # Run frontend tests
    if frontend:
        try:
            results['frontend'] = run_frontend_tests(coverage, watch)
        except Exception as e:
            print_error(f"Error running frontend tests: {e}")
            results['frontend'] = False
    
    # Print summary
    print_header("Test Summary")
    
    total_passed = 0
    total_failed = 0
    
    if 'backend' in results:
        if results['backend']:
            print_success("Backend Tests: All tests passed ✓")
        else:
            print_error("Backend Tests: Some tests failed ✗")
    
    if 'frontend' in results:
        if results['frontend']:
            print_success("Frontend Tests: All tests passed ✓")
        else:
            print_error("Frontend Tests: Some tests failed ✗")
    
    # Overall result
    all_passed = all(results.values()) if results else False
    
    if all_passed:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ All tests passed!{Colors.END}")
        sys.exit(0)
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ Some tests failed.{Colors.END}")
        sys.exit(1)

if __name__ == '__main__':
    main()
