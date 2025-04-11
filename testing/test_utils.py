"""
Test Utilities Module

This module provides utility functions for test data preparation,
test execution, and test reporting.
"""

import os
import json
import datetime
import logging
import time
from typing import Dict, Any, List, Optional, Callable, Union, Tuple
import uuid
import csv
import random

from .test_config import TestConfig


class TestUtils:
    """
    Utility functions for testing.
    
    This class provides helper methods for preparing test data,
    executing tests, and generating test reports.
    """
    
    def __init__(self, config: TestConfig):
        """
        Initialize test utilities.
        
        Args:
            config: Test configuration
        """
        self.config = config
        self.logger = logging.getLogger("test_utils")
    
    def prepare_test_directory(self, test_name: str) -> str:
        """
        Prepare a directory for test output.
        
        Args:
            test_name: Name of the test
        
        Returns:
            Path to the test output directory
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        test_dir = os.path.join("testing", "results", f"{test_name}_{timestamp}")
        
        os.makedirs(test_dir, exist_ok=True)
        self.logger.info(f"Prepared test directory: {test_dir}")
        
        return test_dir
    
    def load_test_data(self, filename: str, category: Optional[str] = None) -> Any:
        """
        Load test data from a file.
        
        Args:
            filename: Name of the test data file
            category: Optional category subdirectory
        
        Returns:
            Loaded test data
        """
        data_path = self.config.get_test_data_path(category)
        file_path = os.path.join(data_path, filename)
        
        if not os.path.exists(file_path):
            self.logger.warning(f"Test data file not found: {file_path}")
            return None
        
        try:
            if file_path.endswith('.json'):
                with open(file_path, 'r') as f:
                    return json.load(f)
            elif file_path.endswith('.csv'):
                data = []
                with open(file_path, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        data.append(row)
                return data
            else:
                with open(file_path, 'r') as f:
                    return f.read()
        except Exception as e:
            self.logger.error(f"Error loading test data from {file_path}: {e}")
            return None
    
    def save_test_results(self, results: Any, test_name: str, test_dir: Optional[str] = None) -> str:
        """
        Save test results to a file.
        
        Args:
            results: Test results to save
            test_name: Name of the test
            test_dir: Directory to save results (None = create new directory)
            
        Returns:
            Path to the saved results file
        """
        if test_dir is None:
            test_dir = self.prepare_test_directory(test_name)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = os.path.join(test_dir, f"results_{timestamp}.json")
        
        try:
            with open(result_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            self.logger.info(f"Saved test results to {result_file}")
            return result_file
        except Exception as e:
            self.logger.error(f"Error saving test results: {e}")
            return ""
    
    def time_execution(self, func: Callable, *args, **kwargs) -> Tuple[Any, float]:
        """
        Measure execution time of a function.
        
        Args:
            func: Function to time
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Tuple of (function result, execution time in seconds)
        """
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        return result, execution_time
    
    def extract_authentic_property_data(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        Extract a sample of authentic property data for testing.
        
        This method extracts real property data from the database for testing,
        ensuring we're using authentic data as required by policy.
        
        Args:
            count: Number of properties to extract
            
        Returns:
            List of property dictionaries
        """
        from models import Account, Property, Parcel
        from sqlalchemy import desc
        from app_setup import db
        
        properties = []
        
        try:
            # Query recent accounts with associated properties
            accounts = Account.query.order_by(desc(Account.id)).limit(count*2).all()
            
            for account in accounts:
                # Find a property associated with this account
                property_obj = Property.query.filter_by(parcel_id=account.parcel_id).first()
                
                if property_obj:
                    # Create a property dictionary with authentic data
                    property_data = {
                        "account_id": account.id,
                        "parcel_id": account.parcel_id,
                        "address": account.address or "Unknown",
                        "city": account.city or "Unknown",
                        "state": account.state or "WA",
                        "zip_code": account.zip_code or "99352",
                        "property_type": account.property_type or "Residential",
                        "year_built": property_obj.year_built or 2000,
                        "square_footage": property_obj.square_footage or 2000,
                        "assessed_value": account.total_value or 300000,
                        "land_value": account.land_value or 100000,
                        "improvement_value": account.improvement_value or 200000
                    }
                    properties.append(property_data)
                    
                    if len(properties) >= count:
                        break
            
            self.logger.info(f"Extracted {len(properties)} authentic property records for testing")
        except Exception as e:
            self.logger.error(f"Error extracting authentic property data: {e}")
        
        return properties
    
    def generate_test_report(self, test_results: List[Dict[str, Any]], title: str = "Test Report") -> Dict[str, Any]:
        """
        Generate a structured test report.
        
        Args:
            test_results: List of test result dictionaries
            title: Report title
            
        Returns:
            Test report dictionary
        """
        total_tests = len(test_results)
        passed_tests = sum(1 for r in test_results if r.get('status') == 'passed')
        failed_tests = sum(1 for r in test_results if r.get('status') == 'failed')
        skipped_tests = sum(1 for r in test_results if r.get('status') == 'skipped')
        
        if total_tests > 0:
            pass_rate = (passed_tests / total_tests) * 100
        else:
            pass_rate = 0
        
        # Group by category
        categories = {}
        for result in test_results:
            category = result.get('category', 'Unknown')
            if category not in categories:
                categories[category] = {
                    'total': 0,
                    'passed': 0,
                    'failed': 0,
                    'skipped': 0,
                    'results': []
                }
            
            categories[category]['total'] += 1
            categories[category]['results'].append(result)
            
            if result.get('status') == 'passed':
                categories[category]['passed'] += 1
            elif result.get('status') == 'failed':
                categories[category]['failed'] += 1
            elif result.get('status') == 'skipped':
                categories[category]['skipped'] += 1
        
        # Calculate each category's score
        for category, data in categories.items():
            if data['total'] > 0:
                data['pass_rate'] = (data['passed'] / data['total']) * 100
            else:
                data['pass_rate'] = 0
        
        # Calculate weighted score based on category weights
        category_weights = self.config.get_test_categories()
        weighted_score = 0
        total_weight = 0
        
        for category, data in categories.items():
            weight = category_weights.get(category, 1)
            weighted_score += data['pass_rate'] * weight
            total_weight += weight
        
        if total_weight > 0:
            weighted_score /= total_weight
        
        # Generate report
        timestamp = datetime.datetime.now().isoformat()
        report = {
            'title': title,
            'timestamp': timestamp,
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'skipped_tests': skipped_tests,
                'pass_rate': pass_rate,
                'weighted_score': weighted_score
            },
            'categories': categories
        }
        
        return report
    
    def save_test_report(self, report: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        Save a test report to a file.
        
        Args:
            report: Test report dictionary
            filename: Report filename (None = generate filename)
            
        Returns:
            Path to the saved report file
        """
        if filename is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_report_{timestamp}.json"
        
        report_dir = os.path.join("testing", "reports")
        os.makedirs(report_dir, exist_ok=True)
        
        report_path = os.path.join(report_dir, filename)
        
        try:
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            self.logger.info(f"Saved test report to {report_path}")
            return report_path
        except Exception as e:
            self.logger.error(f"Error saving test report: {e}")
            return ""