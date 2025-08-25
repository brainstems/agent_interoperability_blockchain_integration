"""
Reward calculation for reinforcement learning.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np


class RewardType(Enum):
    """Types of rewards in the system."""
    TASK_COMPLETION = "task_completion"
    PERFORMANCE_IMPROVEMENT = "performance_improvement"
    COLLABORATION = "collaboration"
    EFFICIENCY = "efficiency"
    QUALITY = "quality"


@dataclass
class RewardSignal:
    """Represents a reward signal for an agent action."""
    agent_id: str
    reward_type: RewardType
    value: float
    timestamp: float
    metadata: Dict[str, Any]


class RewardCalculator:
    """
    Calculates rewards for agent actions and outcomes.
    
    Supports multiple reward types and custom reward functions
    for different agent behaviors and objectives.
    """
    
    def __init__(
        self,
        base_reward: float = 1.0,
        penalty_multiplier: float = 0.5,
        quality_weight: float = 0.3,
        efficiency_weight: float = 0.3,
        collaboration_weight: float = 0.2,
        completion_weight: float = 0.2
    ):
        """
        Initialize the reward calculator.
        
        Args:
            base_reward: Base reward value for successful actions
            penalty_multiplier: Multiplier for penalties
            quality_weight: Weight for quality metrics
            efficiency_weight: Weight for efficiency metrics
            collaboration_weight: Weight for collaboration metrics
            completion_weight: Weight for task completion
        """
        self.base_reward = base_reward
        self.penalty_multiplier = penalty_multiplier
        self.weights = {
            "quality": quality_weight,
            "efficiency": efficiency_weight,
            "collaboration": collaboration_weight,
            "completion": completion_weight
        }
        self.reward_history: List[RewardSignal] = []
        
    def calculate_task_completion_reward(
        self,
        agent_id: str,
        task_success: bool,
        completion_time: float,
        expected_time: float,
        quality_score: float = 1.0
    ) -> RewardSignal:
        """
        Calculate reward for task completion.
        
        Args:
            agent_id: ID of the agent
            task_success: Whether the task was successful
            completion_time: Actual time taken
            expected_time: Expected completion time
            quality_score: Quality of the output (0-1)
            
        Returns:
            Reward signal
        """
        import time
        
        if not task_success:
            reward_value = -self.base_reward * self.penalty_multiplier
        else:
            # Base reward for completion
            reward_value = self.base_reward * self.weights["completion"]
            
            # Efficiency bonus/penalty
            time_ratio = completion_time / expected_time
            if time_ratio < 1.0:
                # Completed faster than expected
                efficiency_bonus = (1.0 - time_ratio) * self.base_reward * self.weights["efficiency"]
                reward_value += efficiency_bonus
            else:
                # Took longer than expected
                efficiency_penalty = (time_ratio - 1.0) * self.base_reward * self.penalty_multiplier
                reward_value -= efficiency_penalty
            
            # Quality bonus
            quality_bonus = quality_score * self.base_reward * self.weights["quality"]
            reward_value += quality_bonus
        
        signal = RewardSignal(
            agent_id=agent_id,
            reward_type=RewardType.TASK_COMPLETION,
            value=reward_value,
            timestamp=time.time(),
            metadata={
                "task_success": task_success,
                "completion_time": completion_time,
                "expected_time": expected_time,
                "quality_score": quality_score
            }
        )
        
        self.reward_history.append(signal)
        return signal
    
    def calculate_collaboration_reward(
        self,
        agent_id: str,
        collaboration_score: float,
        num_interactions: int,
        successful_interactions: int
    ) -> RewardSignal:
        """
        Calculate reward for collaboration behavior.
        
        Args:
            agent_id: ID of the agent
            collaboration_score: Overall collaboration quality (0-1)
            num_interactions: Total number of interactions
            successful_interactions: Number of successful interactions
            
        Returns:
            Reward signal
        """
        import time
        
        success_rate = successful_interactions / max(num_interactions, 1)
        reward_value = (
            collaboration_score * success_rate * 
            self.base_reward * self.weights["collaboration"]
        )
        
        signal = RewardSignal(
            agent_id=agent_id,
            reward_type=RewardType.COLLABORATION,
            value=reward_value,
            timestamp=time.time(),
            metadata={
                "collaboration_score": collaboration_score,
                "num_interactions": num_interactions,
                "successful_interactions": successful_interactions,
                "success_rate": success_rate
            }
        )
        
        self.reward_history.append(signal)
        return signal
    
    def calculate_performance_improvement_reward(
        self,
        agent_id: str,
        previous_performance: float,
        current_performance: float,
        metric_name: str
    ) -> RewardSignal:
        """
        Calculate reward for performance improvement.
        
        Args:
            agent_id: ID of the agent
            previous_performance: Previous performance metric
            current_performance: Current performance metric
            metric_name: Name of the performance metric
            
        Returns:
            Reward signal
        """
        import time
        
        improvement = current_performance - previous_performance
        improvement_ratio = improvement / max(abs(previous_performance), 0.001)
        
        reward_value = improvement_ratio * self.base_reward
        
        signal = RewardSignal(
            agent_id=agent_id,
            reward_type=RewardType.PERFORMANCE_IMPROVEMENT,
            value=reward_value,
            timestamp=time.time(),
            metadata={
                "previous_performance": previous_performance,
                "current_performance": current_performance,
                "improvement": improvement,
                "improvement_ratio": improvement_ratio,
                "metric_name": metric_name
            }
        )
        
        self.reward_history.append(signal)
        return signal
    
    def get_cumulative_reward(
        self,
        agent_id: str,
        time_window: Optional[float] = None
    ) -> float:
        """
        Get cumulative reward for an agent.
        
        Args:
            agent_id: ID of the agent
            time_window: Optional time window in seconds
            
        Returns:
            Cumulative reward value
        """
        import time
        
        current_time = time.time()
        relevant_signals = [
            signal for signal in self.reward_history
            if signal.agent_id == agent_id and
            (time_window is None or current_time - signal.timestamp <= time_window)
        ]
        
        return sum(signal.value for signal in relevant_signals)
    
    def get_average_reward(
        self,
        agent_id: str,
        reward_type: Optional[RewardType] = None
    ) -> float:
        """
        Get average reward for an agent.
        
        Args:
            agent_id: ID of the agent
            reward_type: Optional filter by reward type
            
        Returns:
            Average reward value
        """
        relevant_signals = [
            signal for signal in self.reward_history
            if signal.agent_id == agent_id and
            (reward_type is None or signal.reward_type == reward_type)
        ]
        
        if not relevant_signals:
            return 0.0
            
        return np.mean([signal.value for signal in relevant_signals])
    
    def get_reward_statistics(self, agent_id: str) -> Dict[str, Any]:
        """
        Get comprehensive reward statistics for an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Dictionary of statistics
        """
        agent_signals = [
            signal for signal in self.reward_history
            if signal.agent_id == agent_id
        ]
        
        if not agent_signals:
            return {
                "total_rewards": 0,
                "cumulative_reward": 0.0,
                "average_reward": 0.0,
                "max_reward": 0.0,
                "min_reward": 0.0,
                "by_type": {}
            }
        
        rewards = [signal.value for signal in agent_signals]
        
        stats = {
            "total_rewards": len(agent_signals),
            "cumulative_reward": sum(rewards),
            "average_reward": np.mean(rewards),
            "max_reward": max(rewards),
            "min_reward": min(rewards),
            "std_reward": np.std(rewards),
            "by_type": {}
        }
        
        # Statistics by reward type
        for reward_type in RewardType:
            type_signals = [s for s in agent_signals if s.reward_type == reward_type]
            if type_signals:
                type_rewards = [s.value for s in type_signals]
                stats["by_type"][reward_type.value] = {
                    "count": len(type_signals),
                    "total": sum(type_rewards),
                    "average": np.mean(type_rewards)
                }
        
        return stats
