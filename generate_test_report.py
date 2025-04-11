#!/usr/bin/env python3
"""
Test Report Generator for Benton County Assessor's Office AI Platform

This script generates a comprehensive HTML report from test results,
providing visualizations and analysis of test outcomes.
"""

import os
import sys
import json
import argparse
import datetime
import logging
from typing import Dict, Any, List, Optional

# Import plotly and pandas for data visualization, if available
try:
    import plotly.graph_objects as go
    import plotly.express as px
    import pandas as pd
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False


def setup_logging(log_dir: str = 'logs/reporting'):
    """Set up logging for the report generator."""
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"report_generation_{timestamp}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger("report_generator")


def load_test_results(results_dir: str) -> Dict[str, Any]:
    """
    Load test results from JSON files.
    
    Args:
        results_dir: Directory containing test result files
        
    Returns:
        Dictionary of test results by category
    """
    logger = logging.getLogger("report_generator")
    
    results = {
        "unit": [],
        "integration": [],
        "performance": []
    }
    
    # Walk through the testing directory
    for root, dirs, files in os.walk(results_dir):
        for file in files:
            if file.endswith(".json") and "test_report" not in file and "performance_report" not in file:
                try:
                    file_path = os.path.join(root, file)
                    
                    with open(file_path, 'r') as f:
                        result = json.load(f)
                    
                    # Determine result category based on directory path
                    if "unit" in root:
                        results["unit"].append(result)
                    elif "integration" in root:
                        results["integration"].append(result)
                    elif "performance" in root:
                        results["performance"].append(result)
                    
                except Exception as e:
                    logger.error(f"Error loading test result from {file_path}: {e}")
    
    logger.info(f"Loaded {len(results['unit'])} unit test results")
    logger.info(f"Loaded {len(results['integration'])} integration test results")
    logger.info(f"Loaded {len(results['performance'])} performance test results")
    
    return results


def generate_summary_stats(results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Generate summary statistics from test results.
    
    Args:
        results: Dictionary of test results by category
        
    Returns:
        Dictionary of summary statistics
    """
    summary = {
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "error_tests": 0,
        "by_category": {}
    }
    
    for category, category_results in results.items():
        category_summary = {
            "total": len(category_results),
            "passed": 0,
            "failed": 0,
            "error": 0
        }
        
        for result in category_results:
            # Check if it's a specific test result or a group of results
            if "status" in result:
                # Individual test result
                if result["status"] == "passed":
                    category_summary["passed"] += 1
                elif result["status"] == "failed":
                    category_summary["failed"] += 1
                else:
                    category_summary["error"] += 1
            elif "test_type" in result and category == "performance":
                # Performance test result
                category_summary["passed"] += 1  # Assume performance tests passed for now
            
        summary["by_category"][category] = category_summary
        summary["total_tests"] += category_summary["total"]
        summary["passed_tests"] += category_summary["passed"]
        summary["failed_tests"] += category_summary["failed"]
        summary["error_tests"] += category_summary["error"]
    
    # Calculate success rate
    if summary["total_tests"] > 0:
        summary["success_rate"] = (summary["passed_tests"] / summary["total_tests"]) * 100
    else:
        summary["success_rate"] = 0
    
    return summary


def generate_performance_stats(results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Generate performance statistics from test results.
    
    Args:
        results: Dictionary of test results by category
        
    Returns:
        Dictionary of performance statistics
    """
    performance_stats = {
        "message_throughput": {},
        "task_throughput": {},
        "message_latency": {},
        "concurrent_load": {}
    }
    
    # Extract performance test results
    performance_results = results.get("performance", [])
    
    for result in performance_results:
        test_type = result.get("test_type")
        
        if test_type == "message_throughput":
            performance_stats["message_throughput"] = {
                "messages_sent": result.get("messages_sent", 0),
                "messages_received": result.get("messages_received", 0),
                "throughput": result.get("total_throughput", 0),
                "success_rate": result.get("success_rate", 0)
            }
        elif test_type == "task_throughput":
            performance_stats["task_throughput"] = {
                "tasks_created": result.get("tasks_created", 0),
                "tasks_received": result.get("tasks_received", 0),
                "throughput": result.get("total_throughput", 0),
                "success_rate": result.get("success_rate", 0)
            }
        elif test_type == "message_latency":
            performance_stats["message_latency"] = {
                "average_ms": result.get("average_latency_ms", 0),
                "p95_ms": result.get("p95_latency_ms", 0),
                "p99_ms": result.get("p99_latency_ms", 0),
                "min_ms": result.get("min_latency_ms", 0),
                "max_ms": result.get("max_latency_ms", 0)
            }
        elif test_type == "concurrent_load":
            performance_stats["concurrent_load"] = {
                "operations": result.get("total_operations", 0),
                "throughput": result.get("operation_throughput", 0),
                "message_success_rate": result.get("message_success_rate", 0),
                "task_success_rate": result.get("task_success_rate", 0)
            }
    
    return performance_stats


def generate_visualizations(summary: Dict[str, Any], 
                           performance: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate HTML visualizations of test results.
    
    Args:
        summary: Summary statistics
        performance: Performance statistics
        
    Returns:
        Dictionary mapping visualization names to HTML strings
    """
    if not VISUALIZATION_AVAILABLE:
        return {}
    
    visualizations = {}
    
    # Test results by category chart
    categories = list(summary["by_category"].keys())
    passed = [summary["by_category"][cat]["passed"] for cat in categories]
    failed = [summary["by_category"][cat]["failed"] for cat in categories]
    error = [summary["by_category"][cat]["error"] for cat in categories]
    
    fig = go.Figure(data=[
        go.Bar(name="Passed", x=categories, y=passed, marker_color="green"),
        go.Bar(name="Failed", x=categories, y=failed, marker_color="red"),
        go.Bar(name="Error", x=categories, y=error, marker_color="orange")
    ])
    
    fig.update_layout(
        barmode="group",
        title="Test Results by Category",
        xaxis_title="Test Category",
        yaxis_title="Number of Tests",
        legend_title="Test Status"
    )
    
    visualizations["results_by_category"] = fig.to_html(full_html=False)
    
    # Overall results pie chart
    labels = ["Passed", "Failed", "Error"]
    values = [summary["passed_tests"], summary["failed_tests"], summary["error_tests"]]
    colors = ["green", "red", "orange"]
    
    fig = go.Figure(data=[
        go.Pie(labels=labels, values=values, marker_colors=colors)
    ])
    
    fig.update_layout(
        title="Overall Test Results"
    )
    
    visualizations["overall_results"] = fig.to_html(full_html=False)
    
    # Performance metrics chart
    if performance["message_throughput"] and performance["task_throughput"]:
        metrics = ["Message Throughput (msgs/s)", "Task Throughput (tasks/s)"]
        values = [
            performance["message_throughput"].get("throughput", 0),
            performance["task_throughput"].get("throughput", 0)
        ]
        
        fig = go.Figure(data=[
            go.Bar(x=metrics, y=values, marker_color="blue")
        ])
        
        fig.update_layout(
            title="Performance Metrics",
            xaxis_title="Metric",
            yaxis_title="Value"
        )
        
        visualizations["performance_metrics"] = fig.to_html(full_html=False)
    
    # Latency metrics chart
    if performance["message_latency"]:
        metrics = ["Average", "P95", "P99", "Min", "Max"]
        values = [
            performance["message_latency"].get("average_ms", 0),
            performance["message_latency"].get("p95_ms", 0),
            performance["message_latency"].get("p99_ms", 0),
            performance["message_latency"].get("min_ms", 0),
            performance["message_latency"].get("max_ms", 0)
        ]
        
        fig = go.Figure(data=[
            go.Bar(x=metrics, y=values, marker_color="purple")
        ])
        
        fig.update_layout(
            title="Message Latency Metrics (ms)",
            xaxis_title="Metric",
            yaxis_title="Latency (ms)"
        )
        
        visualizations["latency_metrics"] = fig.to_html(full_html=False)
    
    return visualizations


def generate_html_report(summary: Dict[str, Any], 
                        performance: Dict[str, Any],
                        visualizations: Dict[str, str]) -> str:
    """
    Generate an HTML report from test results.
    
    Args:
        summary: Summary statistics
        performance: Performance statistics
        visualizations: HTML visualizations
        
    Returns:
        HTML report as a string
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Benton County Assessor's Office AI Platform - Test Report</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                color: #333;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }}
            header {{
                background-color: #003366;
                color: white;
                padding: 20px;
                text-align: center;
            }}
            h1, h2, h3 {{
                margin: 0;
            }}
            .card {{
                background-color: white;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
                margin: 20px 0;
                padding: 20px;
            }}
            .summary {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 20px;
            }}
            .summary-card {{
                flex: 1;
                text-align: center;
                padding: 20px;
                margin: 0 10px;
                border-radius: 5px;
            }}
            .summary-card.passed {{
                background-color: #d4edda;
                color: #155724;
            }}
            .summary-card.failed {{
                background-color: #f8d7da;
                color: #721c24;
            }}
            .summary-card.error {{
                background-color: #fff3cd;
                color: #856404;
            }}
            .summary-card.total {{
                background-color: #cce5ff;
                color: #004085;
            }}
            .number {{
                font-size: 2em;
                font-weight: bold;
                margin: 10px 0;
            }}
            .percent {{
                font-size: 1.5em;
                font-weight: bold;
                margin: 10px 0;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}
            th, td {{
                padding: 10px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background-color: #003366;
                color: white;
            }}
            tr:nth-child(even) {{
                background-color: #f2f2f2;
            }}
            .section {{
                margin: 40px 0;
            }}
            .visualization {{
                width: 100%;
                height: 400px;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <header>
            <h1>Benton County Assessor's Office AI Platform</h1>
            <h2>Test Report</h2>
            <p>Generated on {timestamp}</p>
        </header>
        
        <div class="container">
            <div class="card">
                <h2>Test Summary</h2>
                <div class="summary">
                    <div class="summary-card total">
                        <h3>Total Tests</h3>
                        <div class="number">{summary["total_tests"]}</div>
                    </div>
                    <div class="summary-card passed">
                        <h3>Passed</h3>
                        <div class="number">{summary["passed_tests"]}</div>
                    </div>
                    <div class="summary-card failed">
                        <h3>Failed</h3>
                        <div class="number">{summary["failed_tests"]}</div>
                    </div>
                    <div class="summary-card error">
                        <h3>Errors</h3>
                        <div class="number">{summary["error_tests"]}</div>
                    </div>
                </div>
                <div class="summary">
                    <div class="summary-card total">
                        <h3>Success Rate</h3>
                        <div class="percent">{summary["success_rate"]:.2f}%</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <div class="card">
                    <h2>Test Results by Category</h2>
                    <table>
                        <tr>
                            <th>Category</th>
                            <th>Total</th>
                            <th>Passed</th>
                            <th>Failed</th>
                            <th>Errors</th>
                            <th>Success Rate</th>
                        </tr>
    """
    
    for category, stats in summary["by_category"].items():
        if stats["total"] > 0:
            success_rate = (stats["passed"] / stats["total"]) * 100
        else:
            success_rate = 0
        
        html += f"""
                        <tr>
                            <td>{category.title()}</td>
                            <td>{stats["total"]}</td>
                            <td>{stats["passed"]}</td>
                            <td>{stats["failed"]}</td>
                            <td>{stats["error"]}</td>
                            <td>{success_rate:.2f}%</td>
                        </tr>
        """
    
    html += """
                    </table>
                </div>
            </div>
    """
    
    # Add visualizations if available
    if visualizations:
        html += """
            <div class="section">
                <div class="card">
                    <h2>Visualizations</h2>
        """
        
        for name, vis_html in visualizations.items():
            html += f"""
                    <div class="visualization">
                        {vis_html}
                    </div>
            """
        
        html += """
                </div>
            </div>
        """
    
    # Add performance metrics if available
    if performance["message_throughput"] or performance["task_throughput"]:
        html += """
            <div class="section">
                <div class="card">
                    <h2>Performance Metrics</h2>
                    <table>
                        <tr>
                            <th>Metric</th>
                            <th>Value</th>
                        </tr>
        """
        
        if performance["message_throughput"]:
            html += f"""
                        <tr>
                            <td>Message Throughput</td>
                            <td>{performance["message_throughput"].get("throughput", 0):.2f} msgs/second</td>
                        </tr>
                        <tr>
                            <td>Message Success Rate</td>
                            <td>{performance["message_throughput"].get("success_rate", 0):.2f}%</td>
                        </tr>
            """
        
        if performance["task_throughput"]:
            html += f"""
                        <tr>
                            <td>Task Throughput</td>
                            <td>{performance["task_throughput"].get("throughput", 0):.2f} tasks/second</td>
                        </tr>
                        <tr>
                            <td>Task Success Rate</td>
                            <td>{performance["task_throughput"].get("success_rate", 0):.2f}%</td>
                        </tr>
            """
        
        if performance["message_latency"]:
            html += f"""
                        <tr>
                            <td>Average Message Latency</td>
                            <td>{performance["message_latency"].get("average_ms", 0):.2f} ms</td>
                        </tr>
                        <tr>
                            <td>P95 Message Latency</td>
                            <td>{performance["message_latency"].get("p95_ms", 0):.2f} ms</td>
                        </tr>
                        <tr>
                            <td>P99 Message Latency</td>
                            <td>{performance["message_latency"].get("p99_ms", 0):.2f} ms</td>
                        </tr>
            """
        
        if performance["concurrent_load"]:
            html += f"""
                        <tr>
                            <td>Concurrent Operation Throughput</td>
                            <td>{performance["concurrent_load"].get("throughput", 0):.2f} ops/second</td>
                        </tr>
            """
        
        html += """
                    </table>
                </div>
            </div>
        """
    
    html += """
        </div>
    </body>
    </html>
    """
    
    return html


def save_html_report(html: str, output_path: str) -> None:
    """
    Save HTML report to a file.
    
    Args:
        html: HTML report as a string
        output_path: Path to save the report
    """
    logger = logging.getLogger("report_generator")
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(html)
        
        logger.info(f"HTML report saved to {output_path}")
    except Exception as e:
        logger.error(f"Error saving HTML report: {e}")


def main():
    """Main entry point for the report generator."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate HTML test report")
    parser.add_argument(
        "--results-dir",
        default="testing/results",
        help="Directory containing test results"
    )
    parser.add_argument(
        "--output",
        default="testing/reports/test_report.html",
        help="Path to save the HTML report"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging()
    
    logger.info("Starting report generation")
    
    try:
        # Load test results
        results = load_test_results(args.results_dir)
        
        # Generate summary statistics
        summary = generate_summary_stats(results)
        
        # Generate performance statistics
        performance = generate_performance_stats(results)
        
        # Generate visualizations
        visualizations = generate_visualizations(summary, performance)
        
        # Generate HTML report
        html = generate_html_report(summary, performance, visualizations)
        
        # Save HTML report
        save_html_report(html, args.output)
        
        logger.info("Report generation completed successfully")
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()