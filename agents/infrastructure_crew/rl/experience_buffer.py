"""
Experience buffer for reinforcement learning.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque
import random
import numpy as np


@dataclass
class Experience:
    """Represents a single experience tuple (state, action, reward, next_state)."""
    agent_id: str
    state: Dict[str, Any]
    action: Dict[str, Any]
    reward: float
    next_state: Dict[str, Any]
    done: bool
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None


class ExperienceBuffer:
    """
    Stores and manages agent experiences for learning.
    
    Implements a replay buffer with prioritization and sampling strategies
    for efficient reinforcement learning.
    """
    
    def __init__(
        self,
        max_size: int = 10000,
        prioritized: bool = False,
        alpha: float = 0.6,
        beta: float = 0.4
    ):
        """
        Initialize the experience buffer.
        
        Args:
            max_size: Maximum number of experiences to store
            prioritized: Whether to use prioritized experience replay
            alpha: Priority exponent (0 = uniform, 1 = full prioritization)
            beta: Importance sampling exponent
        """
        self.max_size = max_size
        self.prioritized = prioritized
        self.alpha = alpha
        self.beta = beta
        
        self.buffer: deque = deque(maxlen=max_size)
        self.priorities: deque = deque(maxlen=max_size)
        self.position = 0
        
    def add(
        self,
        agent_id: str,
        state: Dict[str, Any],
        action: Dict[str, Any],
        reward: float,
        next_state: Dict[str, Any],
        done: bool,
        priority: Optional[float] = None
    ) -> None:
        """
        Add an experience to the buffer.
        
        Args:
            agent_id: ID of the agent
            state: State before action
            action: Action taken
            reward: Reward received
            next_state: State after action
            done: Whether episode is done
            priority: Optional priority value
        """
        import time
        
        experience = Experience(
            agent_id=agent_id,
            state=state,
            action=action,
            reward=reward,
            next_state=next_state,
            done=done,
            timestamp=time.time()
        )
        
        self.buffer.append(experience)
        
        if self.prioritized:
            max_priority = max(self.priorities) if self.priorities else 1.0
            self.priorities.append(priority if priority is not None else max_priority)
    
    def sample(
        self,
        batch_size: int,
        agent_id: Optional[str] = None
    ) -> List[Experience]:
        """
        Sample a batch of experiences.
        
        Args:
            batch_size: Number of experiences to sample
            agent_id: Optional filter by agent ID
            
        Returns:
            List of sampled experiences
        """
        # Filter by agent if specified
        if agent_id:
            available = [exp for exp in self.buffer if exp.agent_id == agent_id]
        else:
            available = list(self.buffer)
        
        if len(available) < batch_size:
            return available
        
        if self.prioritized:
            return self._prioritized_sample(available, batch_size)
        else:
            return random.sample(available, batch_size)
    
    def _prioritized_sample(
        self,
        experiences: List[Experience],
        batch_size: int
    ) -> List[Experience]:
        """Sample experiences based on priorities."""
        indices = list(range(len(experiences)))
        priorities = [self.priorities[i] for i in indices]
        
        # Calculate sampling probabilities
        priorities = np.array(priorities) ** self.alpha
        probabilities = priorities / priorities.sum()
        
        # Sample indices
        sampled_indices = np.random.choice(
            indices,
            size=min(batch_size, len(indices)),
            replace=False,
            p=probabilities
        )
        
        return [experiences[i] for i in sampled_indices]
    
    def update_priorities(
        self,
        indices: List[int],
        priorities: List[float]
    ) -> None:
        """
        Update priorities for specific experiences.
        
        Args:
            indices: Indices of experiences to update
            priorities: New priority values
        """
        if not self.prioritized:
            return
            
        for idx, priority in zip(indices, priorities):
            if idx < len(self.priorities):
                self.priorities[idx] = priority
    
    def get_recent_experiences(
        self,
        n: int,
        agent_id: Optional[str] = None
    ) -> List[Experience]:
        """
        Get the n most recent experiences.
        
        Args:
            n: Number of experiences to retrieve
            agent_id: Optional filter by agent ID
            
        Returns:
            List of recent experiences
        """
        if agent_id:
            filtered = [exp for exp in self.buffer if exp.agent_id == agent_id]
            return list(filtered)[-n:]
        else:
            return list(self.buffer)[-n:]
    
    def get_experiences_by_reward(
        self,
        min_reward: Optional[float] = None,
        max_reward: Optional[float] = None,
        agent_id: Optional[str] = None
    ) -> List[Experience]:
        """
        Get experiences filtered by reward range.
        
        Args:
            min_reward: Minimum reward threshold
            max_reward: Maximum reward threshold
            agent_id: Optional filter by agent ID
            
        Returns:
            List of filtered experiences
        """
        filtered = list(self.buffer)
        
        if agent_id:
            filtered = [exp for exp in filtered if exp.agent_id == agent_id]
        
        if min_reward is not None:
            filtered = [exp for exp in filtered if exp.reward >= min_reward]
        
        if max_reward is not None:
            filtered = [exp for exp in filtered if exp.reward <= max_reward]
        
        return filtered
    
    def clear(self, agent_id: Optional[str] = None) -> None:
        """
        Clear the buffer or experiences for a specific agent.
        
        Args:
            agent_id: Optional agent ID to clear experiences for
        """
        if agent_id:
            self.buffer = deque(
                [exp for exp in self.buffer if exp.agent_id != agent_id],
                maxlen=self.max_size
            )
            if self.prioritized:
                # Rebuild priorities
                self.priorities = deque(
                    [self.priorities[i] for i, exp in enumerate(self.buffer)],
                    maxlen=self.max_size
                )
        else:
            self.buffer.clear()
            if self.prioritized:
                self.priorities.clear()
    
    def __len__(self) -> int:
        """Return the number of experiences in the buffer."""
        return len(self.buffer)
    
    def get_statistics(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about the experiences in the buffer.
        
        Args:
            agent_id: Optional filter by agent ID
            
        Returns:
            Dictionary of statistics
        """
        experiences = list(self.buffer)
        if agent_id:
            experiences = [exp for exp in experiences if exp.agent_id == agent_id]
        
        if not experiences:
            return {
                "total_experiences": 0,
                "unique_agents": 0,
                "average_reward": 0.0,
                "max_reward": 0.0,
                "min_reward": 0.0
            }
        
        rewards = [exp.reward for exp in experiences]
        agents = set(exp.agent_id for exp in experiences)
        
        return {
            "total_experiences": len(experiences),
            "unique_agents": len(agents),
            "average_reward": np.mean(rewards),
            "max_reward": max(rewards),
            "min_reward": min(rewards),
            "std_reward": np.std(rewards),
            "completed_episodes": sum(1 for exp in experiences if exp.done)
        }
