"""
Tests for the CrewManager class.
"""

import pytest
import pytest_asyncio
from typing import Dict, Any, List
from datetime import datetime

from tests.unit.test_base import BaseInfrastructureTest
from agents.infrastructure.crew_manager import CrewManager, AgentState, AgentHealth, Event, EventPriority
from ..agents.base_agent import BaseAgent

class MockAgent(BaseAgent):
    """Mock agent for testing."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.name = name
        self.state = AgentState.READY
        self.last_heartbeat = time.time()

class TestCrewManager(BaseInfrastructureTest):
    """
    Tests for the CrewManager class.
    """
    
    @pytest_asyncio.fixture
    async def crew_manager(self):
        """Fixture that provides a configured CrewManager instance."""
        from .test_config import TEST_CONFIG
        from .mock_redis import MockStateAgent
        
        manager = CrewManager(TEST_CONFIG["crew_manager"])
        manager.state_agent = MockStateAgent(TEST_CONFIG["crew_manager"])
        await manager.initialize()
        yield manager
        await manager.shutdown()
        
    async def test_agent_management(self, crew_manager):
        """
        Test agent management functionality.
        """
        # Create mock agents
        agent1 = MockAgent("test_agent_1")
        agent2 = MockAgent("test_agent_2")
        
        # Add agents
        await crew_manager.add_agent(agent1)
        await crew_manager.add_agent(agent2)
        
        # Verify agents were added
        assert len(crew_manager.agents) == 2
        assert "test_agent_1" in crew_manager.agents
        assert "test_agent_2" in crew_manager.agents
        
        # Verify agent health
        health = crew_manager.get_agent_health()
        assert len(health) == 2
        assert health["test_agent_1"].state == AgentState.READY
        assert health["test_agent_2"].state == AgentState.READY
        
    async def test_event_distribution(self, crew_manager):
        """
        Test event distribution to agents.
        """
        # Create test event
        test_event = Event(
            event_type="test_event",
            data={"message": "test message"},
            priority=EventPriority.MEDIUM
        )
        
        # Distribute event
        await crew_manager.distribute_event(test_event)
        
        # Verify event was processed
        metrics = crew_manager.get_metrics()
        assert metrics["event_count"] > 0
        assert len(metrics["processing_time"]) > 0
        
    async def test_state_management(self, crew_manager):
        """
        Test state management functionality.
        """
        # Set state
        assert await crew_manager.set_state("test_key", "test_value", ttl=3600)
        
        # Get state
        value = await crew_manager.get_state("test_key")
        assert value == "test_value"
        
        # Verify state in metrics
        metrics = crew_manager.get_metrics()
        assert "redis_connections" in metrics
        assert metrics["redis_connections"] > 0
        
    async def test_memory_management(self, crew_manager):
        """
        Test memory management functionality.
        """
        # Get initial memory metrics
        metrics = crew_manager.get_metrics()
        assert "memory_usage" in metrics
        assert "team_memory_usage" in metrics
        
        # Verify memory metrics are valid
        assert metrics["memory_usage"]["total"] > 0
        assert 0 <= metrics["memory_usage"]["percent"] <= 100
        
    async def test_health_monitoring(self, crew_manager):
        """
        Test agent health monitoring.
        """
        # Create mock agent with error state
        error_agent = MockAgent("error_agent")
        error_agent.state = AgentState.ERROR
        error_agent.last_heartbeat = time.time() - 3600  # Old heartbeat
        
        # Add agent
        await crew_manager.add_agent(error_agent)
        
        # Get health status
        health = crew_manager.get_agent_health()
        assert len(health) == 1
        assert health["error_agent"].state == AgentState.ERROR
        assert health["error_agent"].error is None  # No error message set
        
    async def test_shutdown(self, crew_manager):
        """
        Test crew manager shutdown.
        """
        # Create mock agent
        agent = MockAgent("shutdown_agent")
        await crew_manager.add_agent(agent)
        
        # Shutdown manager
        await crew_manager.shutdown()
        
        # Verify shutdown state
        assert crew_manager._shutdown
        assert len(crew_manager.agents) == 0
        assert len(crew_manager.agent_health) == 0
