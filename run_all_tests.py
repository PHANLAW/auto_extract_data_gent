"""
Run all tests and ensure 100% pass rate
"""

import subprocess
import sys
import os

def run_tests():
    """Run all tests"""
    print("=" * 80)
    print("Running All Tests")
    print("=" * 80)
    print()
    
    # Check if cv2 is available
    try:
        import cv2
        print("✅ cv2 (opencv-python) is installed")
    except ImportError:
        print("❌ cv2 (opencv-python) is NOT installed")
        print("Installing opencv-python...")
        subprocess.run([sys.executable, "-m", "pip", "install", "opencv-python", "-q"], check=True)
        print("✅ opencv-python installed")
    
    # Check if azure-storage-blob is available
    try:
        import azure.storage.blob
        print("✅ azure-storage-blob is installed")
    except ImportError:
        print("❌ azure-storage-blob is NOT installed")
        print("Installing azure-storage-blob...")
        subprocess.run([sys.executable, "-m", "pip", "install", "azure-storage-blob", "-q"], check=True)
        print("✅ azure-storage-blob installed")
    
    print()
    print("Running unit tests...")
    print("-" * 80)
    
    # Run unit tests
    unit_tests = [
        "tests/unit/test_folder_parser.py",
        "tests/unit/test_error_handler.py",
        "tests/unit/test_sport_api.py",
        "tests/unit/test_config.py",
        "tests/unit/test_prompt_loader.py",
    ]
    
    result_unit = subprocess.run(
        [sys.executable, "-m", "pytest"] + unit_tests + ["-v", "--no-cov", "--tb=short"],
        capture_output=True,
        text=True
    )
    
    print(result_unit.stdout)
    if result_unit.stderr:
        print("STDERR:", result_unit.stderr)
    
    print()
    print("Running integration tests...")
    print("-" * 80)
    
    # Run integration tests (may need mocks)
    integration_tests = [
        "tests/integration/test_workflow.py",
    ]
    
    result_integration = subprocess.run(
        [sys.executable, "-m", "pytest"] + integration_tests + ["-v", "--no-cov", "--tb=short"],
        capture_output=True,
        text=True
    )
    
    print(result_integration.stdout)
    if result_integration.stderr:
        print("STDERR:", result_integration.stderr)
    
    print()
    print("=" * 80)
    print("Test Summary")
    print("=" * 80)
    
    unit_passed = result_unit.returncode == 0
    integration_passed = result_integration.returncode == 0
    
    if unit_passed:
        print("✅ Unit tests: PASSED")
    else:
        print("❌ Unit tests: FAILED")
    
    if integration_passed:
        print("✅ Integration tests: PASSED")
    else:
        print("❌ Integration tests: FAILED")
    
    if unit_passed and integration_passed:
        print()
        print("🎉 All tests PASSED!")
        return 0
    else:
        print()
        print("⚠️  Some tests FAILED. Check output above.")
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
