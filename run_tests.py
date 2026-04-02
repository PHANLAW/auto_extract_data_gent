"""
Run all tests
"""

import subprocess
import sys


def run_tests():
    """Run pytest with coverage"""
    cmd = [
        "pytest",
        "tests/",
        "-v",
        "--cov=app",
        "--cov-report=html",
        "--cov-report=term",
        "--tb=short"
    ]
    
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
