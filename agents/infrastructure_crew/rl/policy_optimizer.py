"""
Policy optimization for agent learning.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
import numpy as np


@dataclass
class PolicyUpdate:
    """Represents a policy update."""
    agent_id: str
    policy_version: int
    parameters: Dict[str, Any]
    performance_delta: float
    timestamp: float


class PolicyOptimizer:
    """
    Optimizes agent policies using reinforcement learning.
    
    Implements policy gradient methods and other optimization
    strategies for continuous agent improvement.
    """
    
    def __init__(
        self,
        learning_rate: float = 0.001,
        discount_factor: float = 0.99,
        entropy_coefficient: float = 0.01,
        value_coefficient: float = 0.5,
        max_gradient_norm: float = 0.5
    ):
        """
        Initialize the policy optimizer.
        
        Args:
            learning_rate: Learning rate for updates
            discount_factor: Discount factor for future rewards
            entropy_coefficient: Coefficient for entropy regularization
            value_coefficient: Coefficient for value function loss
            max_gradient_norm: Maximum gradient norm for clipping
        """
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.entropy_coefficient = entropy_coefficient
        self.value_coefficient = value_coefficient
        self.max_gradient_norm = max_gradient_norm
        
        self.policy_versions: Dict[str, int] = {}
        self.policy_parameters: Dict[str, Dict[str, Any]] = {}
        self.update_history: List[PolicyUpdate] = []
        
    def compute_returns(
        self,
        rewards: List[float],
        dones: List[bool],
        values: Optional[List[float]] = None
    ) -> List[float]:
        """
        Compute discounted returns.
        
        Args:
            rewards: List of rewards
            dones: List of done flags
            values: Optional list of value estimates
            
        Returns:
            List of discounted returns
        """
        returns = []
        R = 0
        
        for reward, done in zip(reversed(rewards), reversed(dones)):
            if done:
                R = 0
            R = reward + self.discount_factor * R
            returns.insert(0, R)
        
        return returns
    
    def compute_advantages(
        self,
        rewards: List[float],
        values: List[float],
        dones: List[bool],
        next_value: float = 0.0
    ) -> List[float]:
        """
        Compute advantage estimates using GAE (Generalized Advantage Estimation).
        
        Args:
            rewards: List of rewards
            values: List of value estimates
            dones: List of done flags
            next_value: Value estimate for next state
            
        Returns:
            List of advantage estimates
        """
        advantages = []
        gae = 0
        
        values = values + [next_value]
        
        for t in reversed(range(len(rewards))):
            if dones[t]:
                delta = rewards[t] - values[t]
                gae = delta
            else:
                delta = rewards[t] + self.discount_factor * values[t + 1] - values[t]
                gae = delta + self.discount_factor * 0.95 * gae  # lambda = 0.95
            
            advantages.insert(0, gae)
        
        return advantages
    
    def update_policy(
        self,
        agent_id: str,
        experiences: List[Dict[str, Any]],
        policy_function: Callable,
        value_function: Optional[Callable] = None
    ) -> PolicyUpdate:
        """
        Update agent policy based on experiences.
        
        Args:
            agent_id: ID of the agent
            experiences: List of experience dictionaries
            policy_function: Function to evaluate policy
            value_function: Optional function to evaluate values
            
        Returns:
            Policy update information
        """
        import time
        
        # Extract components from experiences
        rewards = [exp["reward"] for exp in experiences]
        dones = [exp["done"] for exp in experiences]
        
        # Compute returns
        returns = self.compute_returns(rewards, dones)
        
        # Compute advantages if value function is provided
        if value_function:
            values = [value_function(exp["state"]) for exp in experiences]
            advantages = self.compute_advantages(rewards, values, dones)
        else:
            # Use returns as advantages
            advantages = returns
        
        # Normalize advantages
        advantages = np.array(advantages)
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        # Compute policy gradient
        policy_loss = self._compute_policy_loss(
            experiences,
            advantages,
            policy_function
        )
        
        # Update policy parameters
        current_version = self.policy_versions.get(agent_id, 0)
        new_version = current_version + 1
        
        # Store update
        update = PolicyUpdate(
            agent_id=agent_id,
            policy_version=new_version,
            parameters={"loss": policy_loss, "advantages": advantages.tolist()},
            performance_delta=float(np.mean(rewards)),
            timestamp=time.time()
        )
        
        self.policy_versions[agent_id] = new_version
        self.update_history.append(update)
        
        return update
    
    def _compute_policy_loss(
        self,
        experiences: List[Dict[str, Any]],
        advantages: np.ndarray,
        policy_function: Callable
    ) -> float:
        """Compute policy loss."""
        # Simplified policy loss computation
        # In practice, this would involve actual gradient computation
        log_probs = []
        
        for exp in experiences:
            # Get action probabilities from policy
            action_probs = policy_function(exp["state"])
            # Compute log probability of taken action
            log_prob = np.log(action_probs.get(exp["action"]["type"], 0.5))
            log_probs.append(log_prob)
        
        log_probs = np.array(log_probs)
        
        # Policy gradient loss
        policy_loss = -(log_probs * advantages).mean()
        
        # Add entropy bonus for exploration
        entropy = -np.sum(log_probs * np.exp(log_probs))
        policy_loss -= self.entropy_coefficient * entropy
        
        return float(policy_loss)
    
    def get_policy_version(self, agent_id: str) -> int:
        """Get current policy version for an agent."""
        return self.policy_versions.get(agent_id, 0)
    
    def get_update_history(
        self,
        agent_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[PolicyUpdate]:
        """
        Get policy update history.
        
        Args:
            agent_id: Optional filter by agent ID
            limit: Optional limit on number of updates
            
        Returns:
            List of policy updates
        """
        updates = self.update_history
        
        if agent_id:
            updates = [u for u in updates if u.agent_id == agent_id]
        
        if limit:
            updates = updates[-limit:]
        
        return updates
    
    def get_learning_statistics(self, agent_id: str) -> Dict[str, Any]:
        """
        Get learning statistics for an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Dictionary of statistics
        """
        updates = [u for u in self.update_history if u.agent_id == agent_id]
        
        if not updates:
            return {
                "total_updates": 0,
                "current_version": 0,
                "average_performance_delta": 0.0,
                "total_improvement": 0.0
            }
        
        performance_deltas = [u.performance_delta for u in updates]
        
        return {
            "total_updates": len(updates),
            "current_version": self.policy_versions.get(agent_id, 0),
            "average_performance_delta": np.mean(performance_deltas),
            "total_improvement": sum(performance_deltas),
            "best_performance": max(performance_deltas),
            "worst_performance": min(performance_deltas),
            "recent_trend": np.mean(performance_deltas[-5:]) if len(performance_deltas) >= 5 else 0.0
        }
    
    def reset_policy(self, agent_id: str) -> None:
        """
        Reset policy for an agent.
        
        Args:
            agent_id: ID of the agent
        """
        if agent_id in self.policy_versions:
            del self.policy_versions[agent_id]
        if agent_id in self.policy_parameters:
            del self.policy_parameters[agent_id]
