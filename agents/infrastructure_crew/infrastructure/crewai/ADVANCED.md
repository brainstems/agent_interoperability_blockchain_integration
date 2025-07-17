# Advanced CrewAI Integration Guide

This guide covers advanced usage patterns and best practices for integrating infrastructure agents with CrewAI.

## Table of Contents

1. [Custom Agent Types](#custom-agent-types)
2. [Advanced Task Patterns](#advanced-task-patterns)
3. [Error Handling and Retries](#error-handling-and-retries)
4. [Tool Integration](#tool-integration)
5. [Performance Optimization](#performance-optimization)
6. [Testing Strategies](#testing-strategies)

## Custom Agent Types

### Creating Specialized Agents

You can create specialized agent classes for different domains:

```python
from infrastructure.agents import BaseAgent
from infrastructure.crewai import CrewAIAgentAdapter

class DataAnalysisAgent(BaseAgent):
    role = "Data Analyst"
    goal = "Analyze data and extract insights"
    backstory = """
    You are a data analyst with expertise in statistical analysis
    and data visualization. You help make data-driven decisions.
    """
    
    def __init__(self, config=None):
        super().__init__(config or {})
        self.tools = [
            # Add data analysis tools here
        ]
    
    async def process(self, data):
        # Custom processing logic
        return {"insights": [...]}

# Usage
agent = DataAnalysisAgent()
crewai_agent = CrewAIAgentAdapter(agent)
```

### Agent Configuration

Agents can be configured using a configuration dictionary:

```python
config = {
    "llm": {
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 2000
    },
    "retry": {
        "max_attempts": 3,
        "delay_seconds": 1
    },
    "custom_param": "value"
}

agent = DataAnalysisAgent(config=config)
```

## Advanced Task Patterns

### Task Dependencies

Create tasks with dependencies using the `context` parameter:

```python
from infrastructure.crewai import InfrastructureTask

# Task 1: Data collection
data_task = InfrastructureTask(
    agent=data_collector,
    description="Collect and preprocess data",
    expected_output="Cleaned and formatted dataset"
)

# Task 2: Analysis (depends on data_task)
analysis_task = InfrastructureTask(
    agent=analyst,
    description="Analyze the collected data",
    expected_output="Analysis results and insights",
    context=[data_task]  # This task depends on data_task
)
```

### Parallel Task Execution

Run tasks in parallel using Crew's process mode:

```python
from crewai import Process

# Create tasks that can run in parallel
task1 = InfrastructureTask(...)
task2 = InfrastructureTask(...)

# Create crew with parallel processing
crew = Crew(
    agents=[agent1, agent2],
    tasks=[task1, task2],
    process=Process.parallel,  # Run tasks in parallel
    verbose=True
)
```

## Error Handling and Retries

### Implementing Retries

You can implement retry logic in your agents:

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

class ReliableAgent(BaseAgent):
    # ... other methods ...
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _call_external_service(self, data):
        # Implementation that might fail
        pass
    
    async def process(self, data):
        try:
            result = await self._call_external_service(data)
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}
```

## Tool Integration

### Creating Custom Tools

Create custom tools that work with both CrewAI and infrastructure agents:

```python
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class DatabaseQueryInput(BaseModel):
    query: str = Field(..., description="SQL query to execute")

class DatabaseQueryTool(BaseTool):
    name: str = "database_query"
    description: str = "Execute a database query"
    args_schema: Type[BaseModel] = DatabaseQueryInput
    
    def _run(self, query: str) -> str:
        # Implementation for synchronous execution
        pass
    
    async def _arun(self, query: str) -> str:
        # Implementation for asynchronous execution
        pass

# Usage
tool = DatabaseQueryTool()
agent.tools = [tool]
```

## Performance Optimization

### Caching

Implement caching for expensive operations:

```python
from functools import lru_cache

class CachingAgent(BaseAgent):
    # ... other methods ...
    
    @lru_cache(maxsize=128)
    def _expensive_operation(self, param):
        # Implementation with caching
        pass
```

### Batch Processing

Process data in batches for better performance:

```python
class BatchProcessingAgent(BaseAgent):
    # ... other methods ...
    
    async def process_batch(self, items, batch_size=10):
        results = []
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_results = await asyncio.gather(
                *(self.process_item(item) for item in batch)
            )
            results.extend(batch_results)
        return results
```

## Testing Strategies

### Unit Testing

Test your agents in isolation:

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_agent_processing():
    agent = MyAgent()
    agent._call_api = AsyncMock(return_value={"result": "test"})
    
    result = await agent.process({"input": "test"})
    
    assert "result" in result
    agent._call_api.assert_awaited_once()
```

### Integration Testing

Test the full workflow:

```python
@pytest.mark.asyncio
async def test_crew_workflow():
    # Setup crew with test agents
    crew = Crew(
        agents=[CrewAIAgentAdapter(TestAgent())],
        tasks=[InfrastructureTask(...)],
        process=Process.sequential
    )
    
    # Run the crew
    result = await crew.kickoff(inputs={...})
    
    # Verify results
    assert "expected_key" in result
```

### Mocking External Services

Use pytest fixtures to mock external services:

```python
import pytest
from unittest.mock import patch

@pytest.fixture
def mock_api():
    with patch('mymodule.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "value"}
        mock_get.return_value = mock_response
        yield mock_get

@pytest.mark.asyncio
async def test_with_mocked_api(mock_api):
    agent = MyAgent()
    result = await agent.process({})
    assert "key" in result
    mock_api.assert_called_once()
```

## Best Practices

1. **Separation of Concerns**: Keep agent logic focused on a single responsibility
2. **Error Handling**: Implement comprehensive error handling and logging
3. **Configuration**: Use configuration files for environment-specific settings
4. **Documentation**: Document agent capabilities and expected inputs/outputs
5. **Testing**: Maintain a good test coverage for both unit and integration tests

## Troubleshooting

### Common Issues

1. **Agent Not Responding**: Check if the agent's `process` method is properly awaited
2. **Task Dependencies**: Ensure all task dependencies are correctly specified
3. **Tool Integration**: Verify tools are properly registered with the agent
4. **Configuration**: Check that all required configuration parameters are provided

### Debugging Tips

1. Enable verbose logging:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. Use the `verbose` flag when creating a Crew:
   ```python
   crew = Crew(..., verbose=True)
   ```

3. Check the task output for errors:
   ```python
   try:
       result = await task.execute()
   except Exception as e:
       print(f"Task failed: {e}")
       raise
   ```
