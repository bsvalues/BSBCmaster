"""
Performance Tracking Module for Agent Coordination

This module provides functionality for tracking agent performance metrics
and identifying when agents need assistance or optimization.
"""

import time
from typing import Dict, Any, List, Optional, Callable
import json
import os
from datetime import datetime
import statistics
from collections import deque


class PerformanceTracker:
    """
    Tracks and analyzes performance metrics for agents.
    
    This class monitors various performance indicators for agents,
    identifies trends, and provides alerts when agents need assistance.
    """
    
    def __init__(self, performance_threshold: float = 0.7,
                 window_size: int = 100, save_dir: Optional[str] = None):
        """
        Initialize the performance tracker.
        
        Args:
            performance_threshold: Threshold below which an agent needs assistance
            window_size: Number of metrics to keep for each agent
            save_dir: Directory to save performance data (None = no saving)
        """
        self.performance_threshold = performance_threshold
        self.window_size = window_size
        self.save_dir = save_dir
        
        # Create save directory if it doesn't exist
        if self.save_dir is not None:
            os.makedirs(self.save_dir, exist_ok=True)
        
        # Metrics for each agent
        # {agent_id: {metric_name: deque of values}}
        self.metrics = {}
        
        # Last time each agent was evaluated
        self.last_evaluation = {}
        
        # Current performance score for each agent
        self.performance_scores = {}
    
    def record_metric(self, agent_id: str, metric_name: str, value: float) -> None:
        """
        Record a performance metric for an agent.
        
        Args:
            agent_id: Identifier of the agent
            metric_name: Name of the metric
            value: Value of the metric
        """
        # Initialize agent metrics if needed
        if agent_id not in self.metrics:
            self.metrics[agent_id] = {}
        
        # Initialize metric deque if needed
        if metric_name not in self.metrics[agent_id]:
            self.metrics[agent_id][metric_name] = deque(maxlen=self.window_size)
        
        # Add the metric value
        self.metrics[agent_id][metric_name].append(value)
        
        # Save metric to disk if save_dir is specified
        if self.save_dir is not None:
            self._save_metric(agent_id, metric_name, value)
    
    def evaluate_agent(self, agent_id: str, metric_weights: Optional[Dict[str, float]] = None) -> float:
        """
        Evaluate the overall performance of an agent.
        
        Args:
            agent_id: Identifier of the agent to evaluate
            metric_weights: Dictionary mapping metric names to their weights
                            (None = equal weights for all metrics)
        
        Returns:
            Performance score between 0.0 and 1.0
        """
        if agent_id not in self.metrics:
            # No metrics recorded for this agent
            return 1.0
        
        # Use default weights if not provided
        if metric_weights is None:
            metric_weights = {name: 1.0 for name in self.metrics[agent_id].keys()}
        
        total_weight = sum(weight for name, weight in metric_weights.items() 
                          if name in self.metrics[agent_id])
        
        if total_weight == 0:
            # No valid metrics with weights
            return 1.0
        
        # Calculate weighted average of normalized metric values
        score = 0.0
        for name, weight in metric_weights.items():
            if name in self.metrics[agent_id] and len(self.metrics[agent_id][name]) > 0:
                # Get the average value of this metric
                avg_value = statistics.mean(self.metrics[agent_id][name])
                
                # Normalize to [0, 1] based on the metric type
                # This should be customized based on the specific metrics
                if name == 'success_rate':
                    # Higher is better (already in [0, 1])
                    normalized = avg_value
                elif name == 'error_rate':
                    # Lower is better
                    normalized = 1.0 - min(1.0, avg_value)
                elif name == 'response_time':
                    # Lower is better, assuming reasonable range (0-5s)
                    normalized = 1.0 - min(1.0, avg_value / 5.0)
                else:
                    # Default: assume higher is better and already normalized
                    normalized = avg_value
                
                score += normalized * (weight / total_weight)
        
        # Store the performance score
        self.performance_scores[agent_id] = score
        self.last_evaluation[agent_id] = time.time()
        
        return score
    
    def needs_assistance(self, agent_id: str, metric_weights: Optional[Dict[str, float]] = None) -> bool:
        """
        Determine if an agent needs assistance based on its performance.
        
        Args:
            agent_id: Identifier of the agent to check
            metric_weights: Dictionary mapping metric names to their weights
                            (None = equal weights for all metrics)
        
        Returns:
            True if the agent needs assistance, False otherwise
        """
        score = self.evaluate_agent(agent_id, metric_weights)
        return score < self.performance_threshold
    
    def get_agent_stats(self, agent_id: str) -> Dict[str, Any]:
        """
        Get statistics for an agent's performance metrics.
        
        Args:
            agent_id: Identifier of the agent
            
        Returns:
            Dictionary with statistics for each metric
        """
        if agent_id not in self.metrics:
            return {}
        
        stats = {}
        for metric_name, values in self.metrics[agent_id].items():
            if not values:
                stats[metric_name] = {"count": 0}
                continue
            
            stats[metric_name] = {
                "count": len(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "min": min(values),
                "max": max(values)
            }
            
            # Calculate standard deviation if we have enough values
            if len(values) > 1:
                stats[metric_name]["std_dev"] = statistics.stdev(values)
            
            # Add trend (positive = improving, negative = worsening)
            if len(values) > 1:
                first_half = list(values)[:len(values)//2]
                second_half = list(values)[len(values)//2:]
                
                first_mean = statistics.mean(first_half) if first_half else 0
                second_mean = statistics.mean(second_half) if second_half else 0
                
                # Determine if higher or lower is better for this metric
                if metric_name in ['success_rate', 'accuracy']:
                    # Higher is better
                    trend = second_mean - first_mean
                else:
                    # Lower is better (e.g., error_rate, response_time)
                    trend = first_mean - second_mean
                
                stats[metric_name]["trend"] = trend
        
        # Add overall performance score if available
        if agent_id in self.performance_scores:
            stats["overall_score"] = self.performance_scores[agent_id]
        
        return stats
    
    def _save_metric(self, agent_id: str, metric_name: str, value: float) -> None:
        """
        Save a metric value to disk.
        
        Args:
            agent_id: Identifier of the agent
            metric_name: Name of the metric
            value: Value of the metric
        """
        timestamp = time.time()
        date_str = datetime.fromtimestamp(timestamp).strftime('%Y%m%d')
        
        # Create agent directory if it doesn't exist
        agent_dir = os.path.join(self.save_dir, agent_id)
        os.makedirs(agent_dir, exist_ok=True)
        
        # Create metrics file for this day
        metrics_file = os.path.join(agent_dir, f"{date_str}_metrics.jsonl")
        
        # Append the metric to the file
        with open(metrics_file, 'a') as f:
            metric_data = {
                "timestamp": timestamp,
                "metric": metric_name,
                "value": value
            }
            f.write(json.dumps(metric_data) + '\n')
    
    def load_metrics_from_disk(self, agent_id: Optional[str] = None) -> int:
        """
        Load metrics from disk.
        
        Args:
            agent_id: Identifier of the agent to load metrics for
                     (None = all agents)
        
        Returns:
            Number of metrics loaded
        """
        if self.save_dir is None:
            return 0
        
        count_loaded = 0
        
        # Get all agent directories or just the specified one
        if agent_id is not None:
            agent_dirs = [os.path.join(self.save_dir, agent_id)]
        else:
            agent_dirs = [os.path.join(self.save_dir, d) for d in os.listdir(self.save_dir) 
                         if os.path.isdir(os.path.join(self.save_dir, d))]
        
        for agent_dir in agent_dirs:
            if not os.path.exists(agent_dir):
                continue
            
            # Get all metrics files
            metrics_files = [f for f in os.listdir(agent_dir) if f.endswith('_metrics.jsonl')]
            
            for metrics_file in metrics_files:
                file_path = os.path.join(agent_dir, metrics_file)
                
                with open(file_path, 'r') as f:
                    for line in f:
                        try:
                            metric_data = json.loads(line.strip())
                            current_agent_id = os.path.basename(agent_dir)
                            
                            self.record_metric(
                                current_agent_id,
                                metric_data["metric"],
                                metric_data["value"]
                            )
                            count_loaded += 1
                        except Exception as e:
                            print(f"Error loading metric from {file_path}: {e}")
        
        return count_loaded
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive performance report for all agents.
        
        Returns:
            Dictionary with performance data for all agents
        """
        report = {
            "timestamp": time.time(),
            "agents": {},
            "system": {
                "total_agents": len(self.metrics),
                "agents_below_threshold": 0,
                "average_performance": 0.0
            }
        }
        
        total_score = 0.0
        
        # Evaluate all agents to ensure scores are up to date
        for agent_id in self.metrics:
            score = self.evaluate_agent(agent_id)
            report["agents"][agent_id] = {
                "stats": self.get_agent_stats(agent_id),
                "score": score,
                "needs_assistance": score < self.performance_threshold
            }
            
            if score < self.performance_threshold:
                report["system"]["agents_below_threshold"] += 1
            
            total_score += score
        
        # Calculate average performance
        if self.metrics:
            report["system"]["average_performance"] = total_score / len(self.metrics)
        
        return report