#!/usr/bin/env python3
"""
Test Runner for Benton County Assessor's Office AI Platform

This script runs the comprehensive test suite for the AI platform,
including unit tests, integration tests, and performance tests.
"""

import os
import sys
import unittest
import logging
import argparse
import json
import datetime
from typing import Dict, Any, List, Optional

# Ensure testing directory is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from testing.test_config import TestConfig
from testing.test_utils import TestUtils


def setup_logging(log_dir: str = 'logs/testing'):
    """Set up logging for the test runner."""
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"test_run_{timestamp}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger("test_runner")


def discover_tests(test_type: Optional[str] = None) -> unittest.TestSuite:
    """
    Discover tests to run.
    
    Args:
        test_type: Type of tests to run ('unit', 'integration', 'performance', None=all)
    
    Returns:
        TestSuite containing the discovered tests
    """
    logger = logging.getLogger("test_runner")
    
    if test_type:
        logger.info(f"Discovering {test_type} tests")
        test_dir = os.path.join('testing', test_type)
    else:
        logger.info("Discovering all tests")
        test_dir = 'testing'
    
    loader = unittest.TestLoader()
    suite = loader.discover(test_dir, pattern="test_*.py")
    
    return suite


def run_tests(suite: unittest.TestSuite) -> unittest.TestResult:
    """
    Run the test suite.
    
    Args:
        suite: TestSuite to run
    
    Returns:
        TestResult with test outcomes
    """
    logger = logging.getLogger("test_runner")
    
    logger.info("Running tests")
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    logger.info(f"Tests completed: {result.testsRun} run")
    logger.info(f"  Successful: {result.testsRun - len(result.failures) - len(result.errors)}")
    logger.info(f"  Failures: {len(result.failures)}")
    logger.info(f"  Errors: {len(result.errors)}")
    
    return result


def generate_test_report(result: unittest.TestResult, test_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate a test report from TestResult.
    
    Args:
        result: TestResult to report on
        test_type: Type of tests that were run
    
    Returns:
        Dictionary with test report data
    """
    # Initialize test configuration
    config = TestConfig()
    
    # Initialize test utilities
    utils = TestUtils(config)
    
    test_count = result.testsRun
    success_count = test_count - len(result.failures) - len(result.errors)
    failure_count = len(result.failures)
    error_count = len(result.errors)
    
    if test_count > 0:
        success_rate = (success_count / test_count) * 100
    else:
        success_rate = 0
    
    # Generate report
    timestamp = datetime.datetime.now().isoformat()
    report = {
        'title': f"{test_type.title() if test_type else 'All'} Tests Report",
        'timestamp': timestamp,
        'summary': {
            'total_tests': test_count,
            'successful_tests': success_count,
            'failed_tests': failure_count,
            'error_tests': error_count,
            'success_rate': success_rate
        },
        'failures': [
            {
                'test': str(test),
                'message': err
            }
            for test, err in result.failures
        ],
        'errors': [
            {
                'test': str(test),
                'message': err
            }
            for test, err in result.errors
        ]
    }
    
    # Save report
    utils.save_test_report(report)
    
    return report


def main():
    """Main entry point for the test runner."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run tests for the AI platform")
    parser.add_argument(
        "--type",
        choices=["unit", "integration", "performance", "all"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--config",
        help="Path to test configuration file"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging()
    
    logger.info("Starting test runner")
    
    # Load test configuration
    config = TestConfig(args.config)
    
    # Determine test type
    test_type = args.type if args.type != "all" else None
    
    # Discover tests
    suite = discover_tests(test_type)
    
    try:
        # Run tests
        result = run_tests(suite)
        
        # Generate report
        report = generate_test_report(result, test_type)
        
        # Output final result
        if result.wasSuccessful():
            logger.info("All tests passed!")
            sys.exit(0)
        else:
            logger.error("Some tests failed. See test report for details.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()