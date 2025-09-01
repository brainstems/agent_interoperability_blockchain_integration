# Reinforcement Learning Integration

## Overview

The RL module provides comprehensive reinforcement learning capabilities for continuous agent improvement through experience and feedback.

## Components

### 1. Reward Calculator

Calculates rewards for agent actions and outcomes across multiple dimensions:

- **Task Completion**: Rewards based on success, timing, and quality
- **Collaboration**: Rewards for effective agent-to-agent interactions
- **Performance Improvement**: Rewards for measurable improvements over time
- **Efficiency**: Rewards for resource-efficient operations
- **Quality**: Rewards for high-quality outputs

#### Usage Example

```python
from infrastructure_crew.rl import RewardCalculator

calculator = RewardCalculator(
    base_reward=1.0,
    quality_weight=0.3,
    efficiency_weight=0.3,
    collaboration_weight=0.2,
    completion_weight=0.2
)

# Calculate task completion reward
reward = calculator.calculate_task_completion_reward(
    agent_id="agent_1",
    task_success=True,
    completion_time=45.0,
    expected_time=60.0,
    quality_score=0.95
)

print(f"Reward value: {reward.value}")
print(f"Reward type: {reward.reward_type}")
```

### 2. Experience Buffer

Stores and manages agent experiences for learning with support for prioritized replay:

```python
from infrastructure_crew.rl import ExperienceBuffer

buffer = ExperienceBuffer(
    max_size=10000,
    prioritized=True,
    alpha=0.6,  # Priority exponent
    beta=0.4    # Importance sampling
)

# Add experience
buffer.add(
    agent_id="agent_1",
    state={"task_queue_length": 5, "cpu_usage": 0.6},
    action={"type": "process_task", "task_id": "task_123"},
    reward=1.5,
    next_state={"task_queue_length": 4, "cpu_usage": 0.7},
    done=False
)

# Sample batch for training
batch = buffer.sample(batch_size=32, agent_id="agent_1")
```

### 3. Policy Optimizer

Optimizes agent policies using policy gradient methods:

```python
from infrastructure_crew.rl import PolicyOptimizer

optimizer = PolicyOptimizer(
    learning_rate=0.001,
    discount_factor=0.99,
    entropy_coefficient=0.01
)

# Update policy based on experiences
update = optimizer.update_policy(
    agent_id="agent_1",
    experiences=batch,
    policy_function=agent.get_action_probabilities,
    value_function=agent.estimate_value
)

print(f"Policy version: {update.policy_version}")
print(f"Performance delta: {update.performance_delta}")
```

## Integration with QA Agents

The RL module integrates with the QA agent architecture to enable continuous improvement:

### Workflow

1. **FC Execution**: Functional Crew executes tasks and emits events
2. **QA Analysis**: QA agent analyzes performance using FCEventSubscriberTool
3. **Reward Calculation**: RewardCalculator computes rewards based on outcomes
4. **Experience Storage**: Experiences stored in ExperienceBuffer
5. **Policy Update**: PolicyOptimizer updates agent policy
6. **Suggestion Generation**: Improved policy generates better suggestions

### Example Integration

```python
from infrastructure_crew.rl import RewardCalculator, ExperienceBuffer, PolicyOptimizer
from infrastructure_crew.agents import TranslationQAAgent

# Initialize RL components
reward_calc = RewardCalculator()
experience_buffer = ExperienceBuffer(max_size=5000)
policy_opt = PolicyOptimizer()

# Initialize QA agent with RL
qa_agent = TranslationQAAgent(
    reward_calculator=reward_calc,
    experience_buffer=experience_buffer,
    policy_optimizer=policy_opt
)

# After FC execution
fc_performance = qa_agent.analyze_fc_performance(crew_run_id="run_123")

# Calculate reward
reward = reward_calc.calculate_performance_improvement_reward(
    agent_id="translation_qa",
    previous_performance=0.75,
    current_performance=0.82,
    metric_name="task_completion_rate"
)

# Store experience
experience_buffer.add(
    agent_id="translation_qa",
    state=fc_performance["state"],
    action=fc_performance["suggestion"],
    reward=reward.value,
    next_state=fc_performance["next_state"],
    done=False
)

# Update policy periodically
if len(experience_buffer) >= 100:
    batch = experience_buffer.sample(batch_size=32)
    update = policy_opt.update_policy(
        agent_id="translation_qa",
        experiences=batch,
        policy_function=qa_agent.get_suggestion_policy
    )
```

## Reward Shaping

### Multi-Objective Rewards

The system supports multi-objective optimization:

```python
# Configure weights for different objectives
calculator = RewardCalculator(
    quality_weight=0.4,      # Prioritize quality
    efficiency_weight=0.3,   # Balance efficiency
    collaboration_weight=0.2, # Encourage teamwork
    completion_weight=0.1    # Basic completion
)
```

### Custom Reward Functions

Extend the RewardCalculator for domain-specific rewards:

```python
class CustomRewardCalculator(RewardCalculator):
    def calculate_translation_quality_reward(
        self,
        agent_id: str,
        accuracy: float,
        fluency: float,
        consistency: float
    ):
        # Custom calculation
        quality_score = (
            0.5 * accuracy +
            0.3 * fluency +
            0.2 * consistency
        )
        
        return self.calculate_task_completion_reward(
            agent_id=agent_id,
            task_success=quality_score > 0.7,
            completion_time=1.0,
            expected_time=1.0,
            quality_score=quality_score
        )
```

## Experience Replay Strategies

### Prioritized Experience Replay

Focus learning on important experiences:

```python
buffer = ExperienceBuffer(
    prioritized=True,
    alpha=0.6,  # Higher = more prioritization
    beta=0.4    # Importance sampling correction
)

# Experiences with higher TD-error get higher priority
buffer.update_priorities(
    indices=[0, 1, 2],
    priorities=[0.8, 0.3, 0.9]
)
```

### Filtered Sampling

Sample specific types of experiences:

```python
# Get high-reward experiences
positive_experiences = buffer.get_experiences_by_reward(
    min_reward=0.5,
    agent_id="agent_1"
)

# Get recent experiences
recent = buffer.get_recent_experiences(n=50, agent_id="agent_1")
```

## Monitoring and Metrics

### Reward Statistics

```python
stats = calculator.get_reward_statistics("agent_1")
print(f"Total rewards: {stats['total_rewards']}")
print(f"Average reward: {stats['average_reward']}")
print(f"By type: {stats['by_type']}")
```

### Learning Progress

```python
learning_stats = optimizer.get_learning_statistics("agent_1")
print(f"Total updates: {learning_stats['total_updates']}")
print(f"Average improvement: {learning_stats['average_performance_delta']}")
print(f"Recent trend: {learning_stats['recent_trend']}")
```

### Buffer Statistics

```python
buffer_stats = buffer.get_statistics("agent_1")
print(f"Total experiences: {buffer_stats['total_experiences']}")
print(f"Average reward: {buffer_stats['average_reward']}")
print(f"Completed episodes: {buffer_stats['completed_episodes']}")
```

## Best Practices

1. **Reward Shaping**: Carefully design reward functions to encourage desired behaviors
2. **Experience Diversity**: Maintain diverse experiences in the buffer
3. **Exploration vs Exploitation**: Balance learning new strategies vs using known good ones
4. **Periodic Updates**: Update policies regularly but not too frequently
5. **Monitor Performance**: Track learning metrics to detect issues early

## Future Enhancements

- Multi-agent RL with shared experiences
- Hierarchical RL for complex task decomposition
- Meta-learning for faster adaptation
- Inverse RL for learning from demonstrations
- Federated RL across distributed agents
