#!/usr/bin/env python3
"""
Format and lint Python source code.

This script runs:
1. isort - to sort imports
2. blue - to format code (Black variant)
3. pyright - to check types

Usage:
    python format-and-lint.py
"""

import subprocess
import sys
import os


def run_command(cmd, description):
    """Run a command and report results."""
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )

        if result.stdout:
            print(result.stdout)

        if result.stderr:
            print(result.stderr, file=sys.stderr)

        if result.returncode != 0:
            print(f"[FAIL] {description} failed with exit code {result.returncode}")
            return False
        else:
            print(f"[PASS] {description} completed successfully")
            return True

    except FileNotFoundError:
        print(f"[ERROR] Command not found: {cmd[0]}")
        print(f"Please install it with: pip install {cmd[0]}")
        return False
    except Exception as e:
        print(f"[ERROR] Error running {description}: {e}")
        return False


def main():
    """Run all formatting and linting tools."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    target_file = os.path.join(script_dir, 'analyze-pages.py')

    if not os.path.exists(target_file):
        print(f"Error: File not found: {target_file}")
        sys.exit(1)

    print("Starting code formatting and linting...")
    print(f"Target file: analyze-pages.py")
    print()

    # Step 1: Sort imports with isort
    isort_success = run_command(
        [sys.executable, '-m', 'isort', target_file],
        "Sorting imports with isort"
    )
    print()

    # Step 2: Format code with blue
    blue_success = run_command(
        [sys.executable, '-m', 'blue', target_file],
        "Formatting code with blue"
    )
    print()

    # Step 3: Type check with pyright
    pyright_success = run_command(
        [sys.executable, '-m', 'pyright', target_file],
        "Type checking with pyright"
    )
    print()

    # Summary
    print("SUMMARY")
    print(f"isort:   {'[PASS]' if isort_success else '[FAIL]'}")
    print(f"blue:    {'[PASS]' if blue_success else '[FAIL]'}")
    print(f"pyright: {'[PASS]' if pyright_success else '[FAIL]'}")
    print()

    if all([isort_success, blue_success, pyright_success]):
        print("[SUCCESS] All checks passed!")
        sys.exit(0)
    else:
        print("[WARNING] Some checks failed. Please review the errors above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
