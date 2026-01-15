#!/usr/bin/env python3
"""
Test runner script for LearnAI booking system.
Run all tests with coverage reporting.
"""

import sys
import subprocess
import argparse


def run_tests(args):
    """Run pytest with specified options."""
    cmd = ['python', '-m', 'pytest']

    # Add verbosity
    if args.verbose:
        cmd.append('-v')

    # Add coverage
    if args.coverage:
        cmd.extend(['--cov=.', '--cov-report=html', '--cov-report=term-missing'])

    # Add specific test file or pattern
    if args.test:
        cmd.append(args.test)

    # Add markers
    if args.markers:
        cmd.extend(['-m', args.markers])

    # Run only failed tests
    if args.failed:
        cmd.append('--lf')

    # Stop on first failure
    if args.stop:
        cmd.append('-x')

    print(f"Running: {' '.join(cmd)}")
    print("-" * 60)

    result = subprocess.run(cmd)
    return result.returncode


def run_security_scan():
    """Run security scans with bandit and safety."""
    print("\n" + "=" * 60)
    print("Running Security Scans")
    print("=" * 60)

    # Run bandit
    print("\n[1/2] Running Bandit security scan...")
    bandit_result = subprocess.run([
        'python', '-m', 'bandit', '-r', '.',
        '-x', './tests,./venv,./.venv',
        '-f', 'json', '-o', 'bandit-report.json'
    ])

    if bandit_result.returncode == 0:
        print("Bandit scan completed. See bandit-report.json for details.")
    else:
        print("Bandit found potential security issues.")

    # Run safety
    print("\n[2/2] Running Safety dependency check...")
    safety_result = subprocess.run([
        'python', '-m', 'safety', 'check',
        '--json', '--output', 'safety-report.json'
    ])

    if safety_result.returncode == 0:
        print("Safety check passed. No known vulnerabilities.")
    else:
        print("Safety found vulnerable dependencies. See safety-report.json")

    return bandit_result.returncode or safety_result.returncode


def main():
    parser = argparse.ArgumentParser(description='Run LearnAI tests')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose output')
    parser.add_argument('-c', '--coverage', action='store_true',
                       help='Run with coverage reporting')
    parser.add_argument('-t', '--test', type=str,
                       help='Run specific test file or pattern')
    parser.add_argument('-m', '--markers', type=str,
                       help='Run tests with specific markers')
    parser.add_argument('-f', '--failed', action='store_true',
                       help='Run only failed tests from last run')
    parser.add_argument('-x', '--stop', action='store_true',
                       help='Stop on first failure')
    parser.add_argument('-s', '--security', action='store_true',
                       help='Run security scans')
    parser.add_argument('-a', '--all', action='store_true',
                       help='Run all tests with coverage and security')

    args = parser.parse_args()

    if args.all:
        args.verbose = True
        args.coverage = True

    # Run tests
    test_result = run_tests(args)

    # Run security scans if requested
    if args.security or args.all:
        security_result = run_security_scan()
        return test_result or security_result

    return test_result


if __name__ == '__main__':
    sys.exit(main())
