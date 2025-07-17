"""
Test configuration and fixtures for the crewAI integration tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from infrastructure.agents import BaseAgent

class MockAgent(BaseAgent):
    """Mock agent for testing."""
    role = "Mock Agent"
    goal = "Test agent"
    backstory = "For testing purposes"
    
    async def process(self, data):
        return {"result": f"Processed: {data}"}

@pytest.fixture
def mock_agent():
    """Create a mock agent for testing."""
    agent = MockAgent()
    agent.initialize = AsyncMock()
    agent.process = AsyncMock(return_value={"result": "test"})
    agent.shutdown = AsyncMock()
    return agent

@pytest.fixture
def mock_crewai_agent():
    """Create a mock CrewAI agent."""
    agent = MagicMock()
    agent.role = "Mock CrewAI Agent"
    agent.goal = "Test CrewAI agent"
    agent.backstory = "For testing CrewAI integration"
    agent.tools = []
    return agent

@pytest.fixture
def sample_config():
    """Return a sample configuration for testing."""
    return {
        "decision_agent": {
            "timeout_seconds": 30,
            "max_retries": 3
        },
        "rules_agent": {
            "strict_mode": True,
            "rules_file": "tests/data/rules.yaml"
        }
    }
