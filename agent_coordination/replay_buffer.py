"""
Replay Buffer Module for Agent Coordination

This module implements the shared replay buffer that stores experiences
from all agents and enables continuous learning and improvement through
collaborative training.
"""

import random
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
import heapq
import time
import json
import os
from datetime import datetime
from collections import deque


@dataclass
class Experience:
    """
    Represents a single experience (state, action, reward, next_state) tuple.
    
    Attributes:
        agent_id: Identifier of the agent that generated this experience
        state: The state before the action was taken
        action: The action that was taken
        reward: The reward that was received
        next_state: The state after the action was taken
        done: Whether this experience ended an episode
        timestamp: When this experience was generated
        priority: The priority of this experience (for prioritized replay)
        metadata: Additional information about this experience
    """
    agent_id: str
    state: Dict[str, Any]
    action: Dict[str, Any]
    reward: float
    next_state: Dict[str, Any]
    done: bool
    timestamp: float = None
    priority: float = 1.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = time.time()
        
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the experience to a dictionary."""
        return {
            "agent_id": self.agent_id,
            "state": self.state,
            "action": self.action,
            "reward": self.reward,
            "next_state": self.next_state,
            "done": self.done,
            "timestamp": self.timestamp,
            "priority": self.priority,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Experience':
        """Create an experience from a dictionary."""
        return cls(**data)


class ReplayBuffer:
    """
    A prioritized replay buffer for storing agent experiences.
    
    This buffer stores experiences from all agents and allows sampling
    based on priority, enabling more impactful experiences to be
    revisited more frequently during training.
    """
    
    def __init__(self, capacity: int = 10000, alpha: float = 0.6, 
                 beta: float = 0.4, beta_increment: float = 0.001,
                 save_dir: Optional[str] = None):
        """
        Initialize the replay buffer.
        
        Args:
            capacity: Maximum number of experiences to store
            alpha: How much prioritization to use (0 = uniform, 1 = full prioritization)
            beta: Importance sampling weight (0 = no correction, 1 = full correction)
            beta_increment: How much to increase beta over time
            save_dir: Directory to save experiences to disk (None = no saving)
        """
        self.capacity = capacity
        self.alpha = alpha
        self.beta = beta
        self.beta_increment = beta_increment
        self.save_dir = save_dir
        
        # Create save directory if it doesn't exist
        if self.save_dir is not None:
            os.makedirs(self.save_dir, exist_ok=True)
        
        # Buffer for storing experiences
        self.buffer = deque(maxlen=capacity)
        
        # Priority for each experience
        self.priorities = deque(maxlen=capacity)
        
        # Total number of experiences added
        self.total_added = 0
    
    def add(self, experience: Experience) -> None:
        """
        Add an experience to the buffer.
        
        Args:
            experience: The experience to add
        """
        # Use max priority for new experiences to ensure they're sampled at least once
        max_priority = max(self.priorities, default=1.0)
        
        self.buffer.append(experience)
        self.priorities.append(max_priority)
        
        self.total_added += 1
        
        # Save experience to disk if save_dir is specified
        if self.save_dir is not None:
            self._save_experience(experience)
    
    def sample(self, batch_size: int = 32) -> Tuple[List[Experience], List[int], List[float]]:
        """
        Sample a batch of experiences based on their priorities.
        
        Args:
            batch_size: Number of experiences to sample
            
        Returns:
            Tuple containing:
            - List of sampled experiences
            - List of indices of sampled experiences
            - List of importance sampling weights
        """
        # Ensure we have enough experiences
        batch_size = min(batch_size, len(self.buffer))
        if batch_size == 0:
            return [], [], []
        
        # Convert priorities to probabilities
        priorities = [p ** self.alpha for p in self.priorities]
        total_priority = sum(priorities)
        probabilities = [p / total_priority for p in priorities]
        
        # Sample indices based on probabilities
        indices = random.choices(range(len(self.buffer)), weights=probabilities, k=batch_size)
        
        # Calculate importance sampling weights
        weights = [(len(self.buffer) * probabilities[i]) ** -self.beta for i in indices]
        max_weight = max(weights)
        weights = [w / max_weight for w in weights]  # Normalize
        
        # Get the corresponding experiences
        experiences = [self.buffer[i] for i in indices]
        
        # Increment beta for future samples
        self.beta = min(1.0, self.beta + self.beta_increment)
        
        return experiences, indices, weights
    
    def update_priorities(self, indices: List[int], priorities: List[float]) -> None:
        """
        Update the priorities of sampled experiences.
        
        Args:
            indices: Indices of experiences to update
            priorities: New priorities for each experience
        """
        for idx, priority in zip(indices, priorities):
            self.priorities[idx] = max(priority, 1e-6)  # Ensure priority is positive
    
    def _save_experience(self, experience: Experience) -> None:
        """
        Save an experience to disk.
        
        Args:
            experience: The experience to save
        """
        date_str = datetime.fromtimestamp(experience.timestamp).strftime('%Y%m%d')
        filename = f"{date_str}_{experience.agent_id}_{int(experience.timestamp * 1000)}.json"
        filepath = os.path.join(self.save_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(experience.to_dict(), f)
    
    def load_from_disk(self, max_to_load: Optional[int] = None) -> int:
        """
        Load experiences from disk into the buffer.
        
        Args:
            max_to_load: Maximum number of experiences to load (None = all)
            
        Returns:
            Number of experiences loaded
        """
        if self.save_dir is None:
            return 0
        
        # Get all JSON files in the save directory
        experience_files = [f for f in os.listdir(self.save_dir) if f.endswith('.json')]
        
        # Limit number of files to load if specified
        if max_to_load is not None:
            experience_files = experience_files[:max_to_load]
        
        count_loaded = 0
        for filename in experience_files:
            filepath = os.path.join(self.save_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    experience_dict = json.load(f)
                
                experience = Experience.from_dict(experience_dict)
                
                # Use the standard add method to add the experience
                self.add(experience)
                count_loaded += 1
            except Exception as e:
                print(f"Error loading experience from {filepath}: {e}")
        
        return count_loaded
    
    def clear(self) -> None:
        """Clear all experiences from the buffer."""
        self.buffer.clear()
        self.priorities.clear()
    
    def __len__(self) -> int:
        """Get the current number of experiences in the buffer."""
        return len(self.buffer)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the buffer."""
        agent_counts = {}
        reward_sum = 0
        reward_min = float('inf')
        reward_max = float('-inf')
        
        for exp in self.buffer:
            agent_counts[exp.agent_id] = agent_counts.get(exp.agent_id, 0) + 1
            reward_sum += exp.reward
            reward_min = min(reward_min, exp.reward)
            reward_max = max(reward_max, exp.reward)
        
        avg_reward = reward_sum / len(self.buffer) if self.buffer else 0
        
        return {
            "size": len(self.buffer),
            "capacity": self.capacity,
            "total_added": self.total_added,
            "agent_distribution": agent_counts,
            "avg_reward": avg_reward,
            "min_reward": reward_min if self.buffer else None,
            "max_reward": reward_max if self.buffer else None,
            "beta": self.beta
        }