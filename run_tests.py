#!/usr/bin/env python3
"""
Test runner for The Open Harbor application.

This script provides a comprehensive test harness that can run all tests
with detailed reporting and coverage analysis.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description, exit_on_error=True):
    """Run a command and handle the output."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"\n✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed with exit code {e.returncode}")
        if exit_on_error:
            sys.exit(1)
        return False
    except FileNotFoundError:
        print(f"\n❌ Command not found: {cmd[0]}")
        if 'pytest' in cmd[0]:
            print("   Try installing pytest: pip install pytest")
        if exit_on_error:
            sys.exit(1)
        return False


def check_dependencies():
    """Check that required testing dependencies are available."""
    print("Checking testing dependencies...")

    try:
        import pytest
        print(f"✅ pytest {pytest.__version__} found")
    except ImportError:
        print("❌ pytest not found. Install with: pip install pytest")
        return False

    try:
        import flask
        print(f"✅ Flask {flask.__version__} found")
    except ImportError:
        print("❌ Flask not found. Install with: pip install flask")
        return False

    return True


def run_linting(args):
    """Run code linting if requested."""
    if not args.lint:
        return True

    success = True

    # Try to run flake8 if available
    try:
        success &= run_command(
            ['python', '-m', 'flake8', 'app/', 'tests/'],
            "Linting with flake8",
            exit_on_error=False
        )
    except:
        print("📝 flake8 not available, skipping linting")

    return success


def run_type_checking(args):
    """Run type checking if requested."""
    if not args.typecheck:
        return True

    try:
        return run_command(
            ['python', '-m', 'mypy', 'app/', '--ignore-missing-imports'],
            "Type checking with mypy",
            exit_on_error=False
        )
    except:
        print("📝 mypy not available, skipping type checking")
        return True


def run_tests(args):
    """Run the test suite with pytest."""
    # Use virtual environment if available
    python_cmd = '.venv/bin/python' if os.path.exists('.venv/bin/python') else 'python'
    cmd = [python_cmd, '-m', 'pytest']

    # Add verbosity
    if args.verbose:
        cmd.extend(['-v'])

    # Add coverage if requested
    if args.coverage:
        try:
            import coverage
            cmd.extend(['--cov=app', '--cov-report=html', '--cov-report=term'])
            print("📊 Coverage reporting enabled")
        except ImportError:
            print("📝 coverage not available, skipping coverage reporting")

    # Add specific test file if provided
    if args.test_file:
        cmd.append(args.test_file)
    else:
        cmd.append('tests/')

    # Add any extra pytest arguments
    if args.pytest_args:
        cmd.extend(args.pytest_args.split())

    return run_command(cmd, "Running test suite")


def generate_report():
    """Generate a test report summary."""
    print(f"\n{'='*60}")
    print("Test Report Summary")
    print(f"{'='*60}")

    # Check if coverage html report was generated
    coverage_dir = Path("htmlcov")
    if coverage_dir.exists():
        print(f"📊 Coverage report generated: {coverage_dir.absolute()}/index.html")

    print("\n🎉 Test harness completed!")
    print("\nTo run specific tests:")
    print("  python run_tests.py --test-file tests/test_routes.py")
    print("\nTo run with coverage:")
    print("  python run_tests.py --coverage")
    print("\nTo run with linting:")
    print("  python run_tests.py --lint")


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="Test harness for The Open Harbor application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py --verbose          # Run with verbose output
  python run_tests.py --coverage         # Run with coverage reporting
  python run_tests.py --lint             # Run linting before tests
  python run_tests.py --typecheck        # Run type checking
  python run_tests.py --test-file tests/test_routes.py  # Run specific test file
        """
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Run tests with verbose output'
    )

    parser.add_argument(
        '--coverage', '-c',
        action='store_true',
        help='Run tests with coverage reporting'
    )

    parser.add_argument(
        '--lint', '-l',
        action='store_true',
        help='Run linting before tests'
    )

    parser.add_argument(
        '--typecheck', '-t',
        action='store_true',
        help='Run type checking before tests'
    )

    parser.add_argument(
        '--test-file',
        help='Run a specific test file'
    )

    parser.add_argument(
        '--pytest-args',
        help='Additional arguments to pass to pytest'
    )

    parser.add_argument(
        '--no-deps-check',
        action='store_true',
        help='Skip dependency checking'
    )

    args = parser.parse_args()

    print("🚀 The Open Harbor Test Harness")
    print(f"Working directory: {os.getcwd()}")

    # Check dependencies unless skipped
    if not args.no_deps_check and not check_dependencies():
        sys.exit(1)

    # Set environment variables for testing
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['TSH_SECRET_KEY'] = 'test-secret-key-for-testing-only'

    success = True

    # Run linting if requested
    success &= run_linting(args)

    # Run type checking if requested
    success &= run_type_checking(args)

    # Run the main test suite
    success &= run_tests(args)

    # Generate report
    generate_report()

    if not success:
        print("\n⚠️  Some tests or checks failed!")
        sys.exit(1)

    print("\n✅ All tests passed!")


if __name__ == '__main__':
    main()