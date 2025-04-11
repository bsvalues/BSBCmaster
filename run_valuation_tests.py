#!/usr/bin/env python3
"""
Run tests for the Valuation Agent component of the Benton County Assessor's
Office AI Platform.
"""

import os
import sys
import unittest
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("valuation_tests")

def main():
    """Run the Valuation Agent test suite."""
    print("\n" + "=" * 80)
    print("Benton County Assessor's Office AI Platform - Valuation Agent Tests".center(80))
    print("=" * 80 + "\n")
    
    # Discover and run tests
    print("Discovering tests...\n")
    
    # Create test suite for the Valuation Agent
    test_suite = unittest.TestSuite()
    
    # Add unit tests
    test_loader = unittest.TestLoader()
    unit_tests = test_loader.discover("testing/unit", pattern="test_valuation*.py")
    test_suite.addTests(unit_tests)
    
    # Add integration tests
    integration_tests = test_loader.discover("testing/integration", pattern="test_valuation*.py")
    test_suite.addTests(integration_tests)
    
    # Create test result and run tests
    test_result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    
    # Report results
    print("\nTest Results:")
    print(f"  Run: {test_result.testsRun}")
    print(f"  Errors: {len(test_result.errors)}")
    print(f"  Failures: {len(test_result.failures)}")
    
    # Print errors and failures
    if test_result.errors:
        print("\nErrors:")
        for test, error in test_result.errors:
            print(f"  {test}: {error}")
    
    if test_result.failures:
        print("\nFailures:")
        for test, failure in test_result.failures:
            print(f"  {test}: {failure}")
    
    # Return exit code based on test results
    if test_result.wasSuccessful():
        print("\nAll tests passed successfully!")
        return 0
    else:
        print("\nSome tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())