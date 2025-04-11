#!/usr/bin/env python3
"""
Test Runner and Report Generator for Benton County Assessor's Office AI Platform

This script runs the comprehensive test suite and generates an HTML report
of the test results. It provides a single entry point for the entire testing
process.
"""

import os
import sys
import argparse
import logging
import subprocess
import datetime
import json
from typing import Dict, Any, List, Optional


def setup_logging(log_dir: str = 'logs/testing'):
    """Set up logging for the test runner."""
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"test_run_and_report_{timestamp}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger("test_runner_and_report")


def run_tests(test_type: Optional[str] = None, config_path: Optional[str] = None) -> int:
    """
    Run the tests.
    
    Args:
        test_type: Type of tests to run ('unit', 'integration', 'performance', 'all')
        config_path: Path to test configuration file
        
    Returns:
        Return code from the test runner script
    """
    logger = logging.getLogger("test_runner_and_report")
    
    logger.info(f"Running {test_type or 'all'} tests")
    
    # Build command
    cmd = [sys.executable, "run_tests.py"]
    
    if test_type and test_type != 'all':
        cmd.extend(["--type", test_type])
    
    if config_path:
        cmd.extend(["--config", config_path])
    
    # Run tests
    try:
        result = subprocess.run(cmd, check=False)
        logger.info(f"Test runner exited with code {result.returncode}")
        return result.returncode
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        return 1


def generate_report(results_dir: str = 'testing/results', 
                    output_path: str = 'testing/reports/test_report.html') -> int:
    """
    Generate a report from test results.
    
    Args:
        results_dir: Directory containing test results
        output_path: Path to save the HTML report
        
    Returns:
        Return code from the report generator script
    """
    logger = logging.getLogger("test_runner_and_report")
    
    logger.info("Generating test report")
    
    # Build command
    cmd = [
        sys.executable,
        "generate_test_report.py",
        "--results-dir", results_dir,
        "--output", output_path
    ]
    
    # Run report generator
    try:
        result = subprocess.run(cmd, check=False)
        logger.info(f"Report generator exited with code {result.returncode}")
        
        if result.returncode == 0:
            logger.info(f"HTML report generated at {output_path}")
        
        return result.returncode
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return 1


def main():
    """Main entry point for the test runner and report generator."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Run tests and generate HTML report for the AI platform"
    )
    parser.add_argument(
        "--type",
        choices=["unit", "integration", "performance", "all"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--config",
        help="Path to test configuration file",
        default="testing/test_config.json"
    )
    parser.add_argument(
        "--results-dir",
        default="testing/results",
        help="Directory containing test results"
    )
    parser.add_argument(
        "--report-output",
        default="testing/reports/test_report.html",
        help="Path to save the HTML report"
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests and only generate report"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging()
    
    logger.info("Starting test run and report generation")
    
    # Create result directory if it doesn't exist
    os.makedirs(args.results_dir, exist_ok=True)
    
    # Create report directory if it doesn't exist
    os.makedirs(os.path.dirname(args.report_output), exist_ok=True)
    
    # Run tests
    test_success = True
    if not args.skip_tests:
        test_return_code = run_tests(args.type, args.config)
        test_success = (test_return_code == 0)
    
    # Generate report
    report_return_code = generate_report(args.results_dir, args.report_output)
    report_success = (report_return_code == 0)
    
    # Output final status
    if test_success and report_success:
        logger.info("Test run and report generation completed successfully")
        sys.exit(0)
    elif not test_success:
        logger.error("Test run failed. See test runner output for details.")
        sys.exit(1)
    else:
        logger.error("Report generation failed. See report generator output for details.")
        sys.exit(2)


if __name__ == "__main__":
    main()