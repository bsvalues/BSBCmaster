"""
Experience Replay Buffer Module for Benton County Assessor's Office AI Platform

This module implements the shared replay buffer that stores experiences
from all agents and enables continuous learning and improvement through
collaborative training.
"""

import os
import json
import uuid
import time
import random
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path
import heapq

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import psycopg2
    import psycopg2.extras
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


@dataclass
class Experience:
    """
    Represents a single experience for agent learning.
    
    This class defines the structure for experiences logged by agents,
    including the state before and after an action, the action taken,
    and the result of the action.
    
    Attributes:
        experience_id: Unique identifier for this experience
        agent_id: Identifier of the agent that logged the experience
        timestamp: ISO 8601 datetime when the experience was logged
        state: Representation of the state before the action
        action: Representation of the action taken
        result: Outcome of the action
        next_state: Representation of the state after the action
        reward_signal: Optional numeric reward if using reinforcement learning
        metadata: Additional metadata for the experience, including priority
    """
    agent_id: str
    state: Dict[str, Any]
    action: Dict[str, Any]
    result: Dict[str, Any]
    next_state: Dict[str, Any]
    experience_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')
    reward_signal: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the experience to a dictionary.
        
        Returns:
            Dictionary representation of the experience
        """
        return asdict(self)
    
    def to_json(self) -> str:
        """
        Convert the experience to a JSON string.
        
        Returns:
            JSON string representation of the experience
        """
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Experience':
        """
        Create an experience from a dictionary.
        
        Args:
            data: Dictionary representation of an experience
            
        Returns:
            Experience instance
        """
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Experience':
        """
        Create an experience from a JSON string.
        
        Args:
            json_str: JSON string representation of an experience
            
        Returns:
            Experience instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def get_priority(self) -> float:
        """
        Get the priority of the experience.
        
        Returns:
            Priority value (default: 1.0)
        """
        return self.metadata.get("priority", 1.0)
    
    def set_priority(self, priority: float) -> None:
        """
        Set the priority of the experience.
        
        Args:
            priority: Priority value
        """
        self.metadata["priority"] = float(priority)


class ReplayBuffer:
    """
    Base class for replay buffers.
    
    This abstract class defines the interface for replay buffers,
    which store experiences from agents and provide methods for
    sampling them for training.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the replay buffer.
        
        Args:
            config: Configuration for the replay buffer
        """
        self.config = config
        self.capacity = config.get("capacity", 100000)
        self.alpha = config.get("alpha", 0.6)  # Prioritization factor
        self.beta = config.get("beta", 0.4)  # Importance sampling factor
        self.beta_increment = config.get("beta_increment", 0.001)
        self.logger = logging.getLogger("replay_buffer")
    
    def add(self, experience: Experience) -> bool:
        """
        Add an experience to the buffer.
        
        Args:
            experience: Experience to add
            
        Returns:
            True if successful, False otherwise
        """
        raise NotImplementedError("Subclasses must implement add()")
    
    def sample(self, batch_size: int = 32) -> Tuple[List[Experience], List[int], List[float]]:
        """
        Sample a batch of experiences from the buffer.
        
        Args:
            batch_size: Number of experiences to sample
            
        Returns:
            Tuple containing:
            - List of sampled experiences
            - List of indices of sampled experiences
            - List of importance sampling weights
        """
        raise NotImplementedError("Subclasses must implement sample()")
    
    def update_priorities(self, indices: List[int], priorities: List[float]) -> None:
        """
        Update the priorities of sampled experiences.
        
        Args:
            indices: Indices of experiences to update
            priorities: New priorities for each experience
        """
        raise NotImplementedError("Subclasses must implement update_priorities()")
    
    def __len__(self) -> int:
        """
        Get the current number of experiences in the buffer.
        
        Returns:
            Number of experiences in the buffer
        """
        raise NotImplementedError("Subclasses must implement __len__()")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the buffer.
        
        Returns:
            Dictionary with buffer statistics
        """
        raise NotImplementedError("Subclasses must implement get_stats()")


class InMemoryReplayBuffer(ReplayBuffer):
    """
    In-memory implementation of the replay buffer.
    
    This class stores experiences in memory and provides methods for
    adding, sampling, and updating them.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the in-memory replay buffer.
        
        Args:
            config: Configuration for the replay buffer
        """
        super().__init__(config)
        self.buffer = []
        self.priorities = []
        self.total_added = 0
    
    def add(self, experience: Experience) -> bool:
        """
        Add an experience to the buffer.
        
        Args:
            experience: Experience to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # If buffer is full, remove the oldest experience
            if len(self.buffer) >= self.capacity:
                self.buffer.pop(0)
                self.priorities.pop(0)
            
            # Add the experience to the buffer
            self.buffer.append(experience)
            
            # Use experience priority if available, otherwise max priority
            priority = experience.get_priority()
            if len(self.priorities) > 0:
                max_priority = max(self.priorities)
                if priority < max_priority:
                    priority = max_priority
            
            self.priorities.append(priority)
            self.total_added += 1
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error adding experience to buffer: {e}")
            return False
    
    def sample(self, batch_size: int = 32) -> Tuple[List[Experience], List[int], List[float]]:
        """
        Sample a batch of experiences from the buffer.
        
        Args:
            batch_size: Number of experiences to sample
            
        Returns:
            Tuple containing:
            - List of sampled experiences
            - List of indices of sampled experiences
            - List of importance sampling weights
        """
        # Ensure we have enough experiences
        if len(self.buffer) == 0:
            return [], [], []
        
        batch_size = min(batch_size, len(self.buffer))
        
        # Calculate sampling probabilities based on priorities
        priorities = [p ** self.alpha for p in self.priorities]
        sum_priorities = sum(priorities)
        probabilities = [p / sum_priorities for p in priorities]
        
        # Sample indices based on priorities
        indices = random.choices(
            range(len(self.buffer)),
            weights=probabilities,
            k=batch_size
        )
        
        # Calculate importance sampling weights
        weights = []
        max_weight = 0
        
        for idx in indices:
            # Calculate importance sampling weight
            # w_i = (N * P(i)) ^ -beta
            weight = (len(self.buffer) * probabilities[idx]) ** -self.beta
            weights.append(weight)
            max_weight = max(max_weight, weight)
        
        # Normalize weights
        weights = [w / max_weight for w in weights]
        
        # Get experiences for the sampled indices
        experiences = [self.buffer[idx] for idx in indices]
        
        # Increment beta for future sampling
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
            if 0 <= idx < len(self.priorities):
                # Ensure priority is positive
                priority = max(priority, 1e-6)
                self.priorities[idx] = priority
                
                # Also update the experience metadata
                self.buffer[idx].set_priority(priority)
    
    def __len__(self) -> int:
        """
        Get the current number of experiences in the buffer.
        
        Returns:
            Number of experiences in the buffer
        """
        return len(self.buffer)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the buffer.
        
        Returns:
            Dictionary with buffer statistics
        """
        agent_counts = {}
        total_reward = 0
        min_reward = float('inf')
        max_reward = float('-inf')
        
        for exp in self.buffer:
            # Count experiences per agent
            agent_id = exp.agent_id
            agent_counts[agent_id] = agent_counts.get(agent_id, 0) + 1
            
            # Calculate reward statistics
            if exp.reward_signal is not None:
                reward = exp.reward_signal
                total_reward += reward
                min_reward = min(min_reward, reward)
                max_reward = max(max_reward, reward)
        
        # Calculate average reward
        avg_reward = total_reward / len(self.buffer) if self.buffer else 0
        
        # If no rewards were found, reset min/max
        if min_reward == float('inf'):
            min_reward = 0
        if max_reward == float('-inf'):
            max_reward = 0
        
        return {
            "size": len(self.buffer),
            "capacity": self.capacity,
            "total_added": self.total_added,
            "agent_distribution": agent_counts,
            "avg_reward": avg_reward,
            "min_reward": min_reward,
            "max_reward": max_reward,
            "beta": self.beta
        }


class FileReplayBuffer(ReplayBuffer):
    """
    File-based implementation of the replay buffer.
    
    This class stores experiences in files and provides methods for
    adding, sampling, and updating them.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the file-based replay buffer.
        
        Args:
            config: Configuration for the replay buffer
        """
        super().__init__(config)
        
        self.save_dir = config.get("save_dir", "data/experiences")
        os.makedirs(self.save_dir, exist_ok=True)
        
        # In-memory index of experiences
        self.index = []
        self.priorities = []
        self.total_added = 0
        
        # Load existing experiences
        self._load_existing_experiences()
    
    def _load_existing_experiences(self) -> None:
        """Load existing experiences from files."""
        try:
            # Get all JSON files in the save directory
            json_files = [f for f in os.listdir(self.save_dir) if f.endswith('.json')]
            
            # Sort by timestamp (assuming filename includes timestamp)
            json_files.sort()
            
            # If we have more files than capacity, only load the most recent ones
            if len(json_files) > self.capacity:
                json_files = json_files[-self.capacity:]
            
            # Load each file and add to index
            for filename in json_files:
                try:
                    file_path = os.path.join(self.save_dir, filename)
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    
                    # Add to index
                    self.index.append(file_path)
                    self.priorities.append(data.get("metadata", {}).get("priority", 1.0))
                    self.total_added += 1
                
                except Exception as e:
                    self.logger.error(f"Error loading experience from {filename}: {e}")
            
            self.logger.info(f"Loaded {len(self.index)} experiences from {self.save_dir}")
        
        except Exception as e:
            self.logger.error(f"Error loading existing experiences: {e}")
    
    def add(self, experience: Experience) -> bool:
        """
        Add an experience to the buffer.
        
        Args:
            experience: Experience to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # If buffer is full, remove the oldest experience
            if len(self.index) >= self.capacity:
                oldest_file = self.index.pop(0)
                self.priorities.pop(0)
                
                # Remove the file
                try:
                    os.remove(oldest_file)
                except Exception as e:
                    self.logger.error(f"Error removing oldest experience file {oldest_file}: {e}")
            
            # Generate filename with timestamp and UUID
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{experience.agent_id}_{experience.experience_id}.json"
            file_path = os.path.join(self.save_dir, filename)
            
            # Save experience to file
            with open(file_path, 'w') as f:
                json.dump(experience.to_dict(), f, indent=2)
            
            # Add to index
            self.index.append(file_path)
            self.priorities.append(experience.get_priority())
            self.total_added += 1
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error adding experience to buffer: {e}")
            return False
    
    def sample(self, batch_size: int = 32) -> Tuple[List[Experience], List[int], List[float]]:
        """
        Sample a batch of experiences from the buffer.
        
        Args:
            batch_size: Number of experiences to sample
            
        Returns:
            Tuple containing:
            - List of sampled experiences
            - List of indices of sampled experiences
            - List of importance sampling weights
        """
        # Ensure we have enough experiences
        if len(self.index) == 0:
            return [], [], []
        
        batch_size = min(batch_size, len(self.index))
        
        # Calculate sampling probabilities based on priorities
        priorities = [p ** self.alpha for p in self.priorities]
        sum_priorities = sum(priorities)
        probabilities = [p / sum_priorities for p in priorities]
        
        # Sample indices based on priorities
        indices = random.choices(
            range(len(self.index)),
            weights=probabilities,
            k=batch_size
        )
        
        # Calculate importance sampling weights
        weights = []
        max_weight = 0
        
        for idx in indices:
            # Calculate importance sampling weight
            # w_i = (N * P(i)) ^ -beta
            weight = (len(self.index) * probabilities[idx]) ** -self.beta
            weights.append(weight)
            max_weight = max(max_weight, weight)
        
        # Normalize weights
        weights = [w / max_weight for w in weights]
        
        # Load experiences for the sampled indices
        experiences = []
        for idx in indices:
            try:
                file_path = self.index[idx]
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                experience = Experience.from_dict(data)
                experiences.append(experience)
            
            except Exception as e:
                self.logger.error(f"Error loading experience {file_path}: {e}")
                # If we can't load the experience, return None in its place
                experiences.append(None)
        
        # Increment beta for future sampling
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
            if 0 <= idx < len(self.priorities):
                # Ensure priority is positive
                priority = max(priority, 1e-6)
                self.priorities[idx] = priority
                
                # Also update the experience file
                try:
                    file_path = self.index[idx]
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    
                    # Update priority in metadata
                    if "metadata" not in data:
                        data["metadata"] = {}
                    
                    data["metadata"]["priority"] = priority
                    
                    # Save back to file
                    with open(file_path, 'w') as f:
                        json.dump(data, f, indent=2)
                
                except Exception as e:
                    self.logger.error(f"Error updating priority for {file_path}: {e}")
    
    def __len__(self) -> int:
        """
        Get the current number of experiences in the buffer.
        
        Returns:
            Number of experiences in the buffer
        """
        return len(self.index)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the buffer.
        
        Returns:
            Dictionary with buffer statistics
        """
        # Load a sample of experiences to calculate statistics
        sample_size = min(100, len(self.index))
        sample_indices = random.sample(range(len(self.index)), sample_size) if sample_size > 0 else []
        
        agent_counts = {}
        total_reward = 0
        min_reward = float('inf')
        max_reward = float('-inf')
        reward_count = 0
        
        for idx in sample_indices:
            try:
                file_path = self.index[idx]
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Count experiences per agent
                agent_id = data.get("agent_id", "unknown")
                agent_counts[agent_id] = agent_counts.get(agent_id, 0) + 1
                
                # Calculate reward statistics
                reward = data.get("reward_signal")
                if reward is not None:
                    total_reward += reward
                    min_reward = min(min_reward, reward)
                    max_reward = max(max_reward, reward)
                    reward_count += 1
            
            except Exception as e:
                self.logger.error(f"Error loading experience {file_path} for stats: {e}")
        
        # Calculate average reward
        avg_reward = total_reward / reward_count if reward_count > 0 else 0
        
        # If no rewards were found, reset min/max
        if min_reward == float('inf'):
            min_reward = 0
        if max_reward == float('-inf'):
            max_reward = 0
        
        # Extrapolate agent counts to full buffer
        if sample_size > 0:
            scale_factor = len(self.index) / sample_size
            agent_counts = {
                agent_id: int(count * scale_factor)
                for agent_id, count in agent_counts.items()
            }
        
        return {
            "size": len(self.index),
            "capacity": self.capacity,
            "total_added": self.total_added,
            "agent_distribution": agent_counts,
            "avg_reward": avg_reward,
            "min_reward": min_reward,
            "max_reward": max_reward,
            "beta": self.beta,
            "sample_size": sample_size
        }


class RedisReplayBuffer(ReplayBuffer):
    """
    Redis-based implementation of the replay buffer.
    
    This class stores experiences in Redis and provides methods for
    adding, sampling, and updating them.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Redis-based replay buffer.
        
        Args:
            config: Configuration for the replay buffer
        """
        super().__init__(config)
        
        if not REDIS_AVAILABLE:
            raise ImportError("Redis package is not available. Install it with 'pip install redis'.")
        
        # Get Redis connection settings
        redis_config = config.get("redis", {})
        self.host = redis_config.get("host", "localhost")
        self.port = redis_config.get("port", 6379)
        self.db = redis_config.get("db", 1)
        self.password = redis_config.get("password")
        self.key_prefix = redis_config.get("key_prefix", "replay:")
        
        # Connect to Redis
        self.redis = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            decode_responses=True  # Automatically decode responses to strings
        )
        
        # Redis keys
        self.experiences_key = f"{self.key_prefix}experiences"  # List of experience IDs
        self.priorities_key = f"{self.key_prefix}priorities"  # Sorted set of priorities
        self.info_key = f"{self.key_prefix}info"  # Hash with buffer info
        
        # Initialize buffer info
        if not self.redis.exists(self.info_key):
            self.redis.hset(self.info_key, "total_added", 0)
            self.redis.hset(self.info_key, "beta", self.beta)
        else:
            # Load beta from Redis
            beta_str = self.redis.hget(self.info_key, "beta")
            if beta_str:
                self.beta = float(beta_str)
    
    def add(self, experience: Experience) -> bool:
        """
        Add an experience to the buffer.
        
        Args:
            experience: Experience to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # If buffer is full, remove the oldest experience
            if self.redis.llen(self.experiences_key) >= self.capacity:
                # Get the oldest experience ID
                oldest_id = self.redis.lpop(self.experiences_key)
                if oldest_id:
                    # Remove from priorities and experience data
                    self.redis.zrem(self.priorities_key, oldest_id)
                    self.redis.delete(f"{self.key_prefix}exp:{oldest_id}")
            
            # Add experience to Redis
            exp_id = experience.experience_id
            exp_data = experience.to_json()
            priority = experience.get_priority()
            
            # Store experience data
            self.redis.set(f"{self.key_prefix}exp:{exp_id}", exp_data)
            
            # Add to experiences list
            self.redis.rpush(self.experiences_key, exp_id)
            
            # Add to priorities sorted set
            self.redis.zadd(self.priorities_key, {exp_id: priority})
            
            # Increment total added counter
            self.redis.hincrby(self.info_key, "total_added", 1)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error adding experience to Redis buffer: {e}")
            return False
    
    def sample(self, batch_size: int = 32) -> Tuple[List[Experience], List[int], List[float]]:
        """
        Sample a batch of experiences from the buffer.
        
        Args:
            batch_size: Number of experiences to sample
            
        Returns:
            Tuple containing:
            - List of sampled experiences
            - List of indices of sampled experiences
            - List of importance sampling weights
        """
        # Ensure we have enough experiences
        buffer_size = self.redis.llen(self.experiences_key)
        if buffer_size == 0:
            return [], [], []
        
        batch_size = min(batch_size, buffer_size)
        
        # Get all experience IDs and priorities
        all_exp_with_priorities = self.redis.zrange(
            self.priorities_key, 0, -1, withscores=True
        )
        
        if not all_exp_with_priorities:
            return [], [], []
        
        # Convert to list of (id, priority) tuples
        all_exp_with_priorities = [(exp_id, priority) for exp_id, priority in all_exp_with_priorities]
        
        # Calculate sampling probabilities based on priorities
        priorities = [p ** self.alpha for _, p in all_exp_with_priorities]
        sum_priorities = sum(priorities)
        probabilities = [p / sum_priorities for p in priorities]
        
        # Sample indices based on priorities
        indices = random.choices(
            range(len(all_exp_with_priorities)),
            weights=probabilities,
            k=batch_size
        )
        
        # Calculate importance sampling weights
        weights = []
        max_weight = 0
        
        for idx in indices:
            # Calculate importance sampling weight
            # w_i = (N * P(i)) ^ -beta
            weight = (len(all_exp_with_priorities) * probabilities[idx]) ** -self.beta
            weights.append(weight)
            max_weight = max(max_weight, weight)
        
        # Normalize weights
        weights = [w / max_weight for w in weights]
        
        # Get experiences for the sampled indices
        experiences = []
        for idx in indices:
            try:
                exp_id = all_exp_with_priorities[idx][0]
                exp_data = self.redis.get(f"{self.key_prefix}exp:{exp_id}")
                
                if exp_data:
                    experience = Experience.from_json(exp_data)
                    experiences.append(experience)
                else:
                    # If experience data is missing, return None
                    experiences.append(None)
            
            except Exception as e:
                self.logger.error(f"Error loading experience {exp_id} from Redis: {e}")
                experiences.append(None)
        
        # Increment beta for future sampling
        self.beta = min(1.0, self.beta + self.beta_increment)
        self.redis.hset(self.info_key, "beta", self.beta)
        
        return experiences, indices, weights
    
    def update_priorities(self, indices: List[int], priorities: List[float]) -> None:
        """
        Update the priorities of sampled experiences.
        
        Args:
            indices: Indices of experiences to update
            priorities: New priorities for each experience
        """
        # Get all experience IDs
        all_exp_with_priorities = self.redis.zrange(
            self.priorities_key, 0, -1, withscores=True
        )
        
        if not all_exp_with_priorities:
            return
        
        # Convert to list of (id, priority) tuples
        all_exp_with_priorities = [(exp_id, priority) for exp_id, priority in all_exp_with_priorities]
        
        for idx, priority in zip(indices, priorities):
            if 0 <= idx < len(all_exp_with_priorities):
                # Ensure priority is positive
                priority = max(priority, 1e-6)
                
                # Get experience ID
                exp_id = all_exp_with_priorities[idx][0]
                
                # Update priority in sorted set
                self.redis.zadd(self.priorities_key, {exp_id: priority})
                
                # Update priority in experience data
                try:
                    exp_data = self.redis.get(f"{self.key_prefix}exp:{exp_id}")
                    if exp_data:
                        experience = Experience.from_json(exp_data)
                        experience.set_priority(priority)
                        self.redis.set(f"{self.key_prefix}exp:{exp_id}", experience.to_json())
                
                except Exception as e:
                    self.logger.error(f"Error updating priority for {exp_id} in Redis: {e}")
    
    def __len__(self) -> int:
        """
        Get the current number of experiences in the buffer.
        
        Returns:
            Number of experiences in the buffer
        """
        return self.redis.llen(self.experiences_key)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the buffer.
        
        Returns:
            Dictionary with buffer statistics
        """
        # Get buffer size
        buffer_size = self.redis.llen(self.experiences_key)
        
        # Get total added count
        total_added = int(self.redis.hget(self.info_key, "total_added") or 0)
        
        # Get beta
        beta = float(self.redis.hget(self.info_key, "beta") or self.beta)
        
        # Sample some experiences to calculate statistics
        sample_size = min(100, buffer_size)
        if sample_size == 0:
            return {
                "size": 0,
                "capacity": self.capacity,
                "total_added": total_added,
                "agent_distribution": {},
                "avg_reward": 0,
                "min_reward": 0,
                "max_reward": 0,
                "beta": beta,
                "sample_size": 0
            }
        
        # Get sample of experience IDs
        if sample_size == buffer_size:
            sample_ids = self.redis.lrange(self.experiences_key, 0, -1)
        else:
            # Randomly sample experience IDs
            sample_indices = random.sample(range(buffer_size), sample_size)
            sample_ids = []
            for idx in sample_indices:
                exp_id = self.redis.lindex(self.experiences_key, idx)
                if exp_id:
                    sample_ids.append(exp_id)
        
        agent_counts = {}
        total_reward = 0
        min_reward = float('inf')
        max_reward = float('-inf')
        reward_count = 0
        
        for exp_id in sample_ids:
            try:
                exp_data = self.redis.get(f"{self.key_prefix}exp:{exp_id}")
                if exp_data:
                    experience = Experience.from_json(exp_data)
                    
                    # Count experiences per agent
                    agent_id = experience.agent_id
                    agent_counts[agent_id] = agent_counts.get(agent_id, 0) + 1
                    
                    # Calculate reward statistics
                    if experience.reward_signal is not None:
                        reward = experience.reward_signal
                        total_reward += reward
                        min_reward = min(min_reward, reward)
                        max_reward = max(max_reward, reward)
                        reward_count += 1
            
            except Exception as e:
                self.logger.error(f"Error loading experience {exp_id} from Redis for stats: {e}")
        
        # Calculate average reward
        avg_reward = total_reward / reward_count if reward_count > 0 else 0
        
        # If no rewards were found, reset min/max
        if min_reward == float('inf'):
            min_reward = 0
        if max_reward == float('-inf'):
            max_reward = 0
        
        # Extrapolate agent counts to full buffer
        if sample_size > 0 and sample_size < buffer_size:
            scale_factor = buffer_size / sample_size
            agent_counts = {
                agent_id: int(count * scale_factor)
                for agent_id, count in agent_counts.items()
            }
        
        return {
            "size": buffer_size,
            "capacity": self.capacity,
            "total_added": total_added,
            "agent_distribution": agent_counts,
            "avg_reward": avg_reward,
            "min_reward": min_reward,
            "max_reward": max_reward,
            "beta": beta,
            "sample_size": len(sample_ids)
        }


def create_replay_buffer(config: Dict[str, Any]) -> ReplayBuffer:
    """
    Create a replay buffer based on configuration.
    
    Args:
        config: Configuration for the replay buffer
        
    Returns:
        ReplayBuffer instance
    """
    buffer_type = config.get("type", "memory")
    
    if buffer_type == "redis" and REDIS_AVAILABLE:
        return RedisReplayBuffer(config)
    elif buffer_type == "file":
        return FileReplayBuffer(config)
    else:
        # Default to in-memory buffer
        return InMemoryReplayBuffer(config)