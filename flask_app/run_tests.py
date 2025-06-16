#!/usr/bin/env python3
"""
Test Runner Script for Credit Card Roadmap

This script runs all tests from both the core tests (/tests) and Flask app tests (/flask_app/tests).
It provides a unified way to execute the entire test suite with proper error handling and reporting.

Usage:
    python scripts/run_tests.py [options]

Options:
    --verbose, -v       Run tests with verbose output
    --coverage, -c      Run tests with coverage report
    --pattern, -k       Run only tests matching the given pattern
    --help, -h          Show this help message
"""

import sys
import subprocess
import argparse
import os
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return the result."""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"\n✅ {description} - PASSED")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} - FAILED (exit code: {e.returncode})")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Run all tests for Credit Card Roadmap",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="Run tests with verbose output"
    )
    parser.add_argument(
        "--coverage", "-c", 
        action="store_true", 
        help="Run tests with coverage report"
    )
    parser.add_argument(
        "--pattern", "-k", 
        type=str, 
        help="Run only tests matching the given pattern"
    )
    parser.add_argument(
        "--core-only", 
        action="store_true", 
        help="Run only core tests (/tests)"
    )
    parser.add_argument(
        "--flask-only", 
        action="store_true", 
        help="Run only Flask app tests (/flask_app/tests)"
    )
    parser.add_argument(
        "--cleanup", 
        action="store_true", 
        help="Clean up test database after running tests"
    )
    parser.add_argument(
        "--yes", "-y", 
        action="store_true", 
        help="Skip confirmation prompt"
    )
    
    args = parser.parse_args()
    
    # Ensure we're in the project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    print("🚀 Credit Card Roadmap Test Runner")
    print(f"📁 Working directory: {project_root}")
    
    # Safety warning
    test_db_path = project_root / "flask_app" / "test_creditcard_roadmap.db"
    print(f"\n⚠️  IMPORTANT: Tests will create/destroy a separate test database:")
    print(f"   📄 {test_db_path}")
    print(f"   🔒 Your development database will NOT be affected.")
    
    if not args.yes:
        response = input("\n❓ Continue with running tests? (Y/n): ").lower().strip()
        if response.startswith('n'):
            print("❌ Tests cancelled by user.")
            sys.exit(0)
    
    # Build pytest command
    base_cmd = [sys.executable, "-m", "pytest"]
    
    # Determine which test directories to run
    test_dirs = []
    if args.core_only:
        test_dirs = ["tests/"]
    elif args.flask_only:
        test_dirs = ["flask_app/tests/"]
    else:
        test_dirs = ["tests/", "flask_app/tests/"]
    
    base_cmd.extend(test_dirs)
    
    # Add optional flags
    if args.verbose:
        base_cmd.append("-v")
    
    if args.pattern:
        base_cmd.extend(["-k", args.pattern])
    
    if args.coverage:
        base_cmd.extend(["--cov=app", "--cov=scripts", "--cov-report=term-missing"])
    
    # Run the tests
    success = run_command(base_cmd, "Running All Tests")
    
    # Clean up test database if requested
    if args.cleanup and test_db_path.exists():
        try:
            test_db_path.unlink()
            print(f"🧹 Cleaned up test database: {test_db_path}")
        except Exception as e:
            print(f"⚠️  Could not clean up test database: {e}")
    
    # Summary
    print(f"\n{'='*60}")
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("Your code is looking good - time for a cuppa! ☕")
        if not args.cleanup and test_db_path.exists():
            print(f"💡 Tip: Use --cleanup to automatically remove the test database")
    else:
        print("💥 SOME TESTS FAILED!")
        print("Don't panic! Even the best code has off days. Check the output above.")
    print(f"{'='*60}")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 