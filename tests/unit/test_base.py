"""
Base test class for infrastructure crew tests.
"""

import asyncio
import logging
import pytest
import pytest_asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from agents.infrastructure_crew.infrastructure.agents.base_agent import BaseAgent
from agents.infrastructure_crew.infrastructure.memory.memory_manager import MemoryManager, MemoryPressureLevel
from agents.infrastructure_crew.infrastructure.memory.team_memory_manager import TeamMemoryManager

logger = logging.getLogger(__name__)

class BaseInfrastructureTest:
    """
    Base class for infrastructure crew tests.
    Provides common fixtures and utility methods.
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
    
    @pytest_asyncio.fixture
    async def memory_manager(self, crew_manager):
        """Fixture that provides a configured MemoryManager instance."""
        from .test_config import TEST_CONFIG
        
        manager = MemoryManager(
            config=TEST_CONFIG["memory"],
            crew_manager=crew_manager
        )
        await manager.initialize()
        yield manager
        await manager.shutdown()
    
    @pytest_asyncio.fixture
    async def team_memory_manager(self):
        """Fixture that provides a configured TeamMemoryManager instance."""
        from .test_config import TEST_CONFIG
        from .mock_redis import MockRedis
        
        # Use mock Redis client
        r = MockRedis()
        
        manager = TeamMemoryManager(TEST_CONFIG["team_memory"])
        await manager.initialize()
        yield manager
        await manager.shutdown()
    
    async def create_test_teams(self, manager: TeamMemoryManager) -> List[str]:
        """
        Create test teams and allocate initial memory.
        
        Args:
            manager: TeamMemoryManager instance
            
        Returns:
            List of team IDs created
        """
        from .test_config import TEST_CONFIG
        
        team_ids = []
        for team_config in TEST_CONFIG["test_teams"]:
            team_id = team_config["id"]
            quota = team_config["initial_quota"]
            success = await manager.allocate_memory(team_id, quota)
            assert success, f"Failed to allocate memory for team {team_id}"
            team_ids.append(team_id)
        
        return team_ids
    
    async def simulate_memory_pressure(self, manager: MemoryManager, 
                                      target_level: MemoryPressureLevel) -> None:
        """
        Simulate memory pressure to reach a specific pressure level.
        
        Args:
            manager: MemoryManager instance
            target_level: Target memory pressure level
        """
        # Get current usage
        usage = manager.get_memory_usage()["percent"] / 100
        
        # Calculate target usage based on thresholds
        thresholds = {
            MemoryPressureLevel.LOW: TEST_CONFIG["memory"]["low_threshold"],
            MemoryPressureLevel.MEDIUM: TEST_CONFIG["memory"]["medium_threshold"],
            MemoryPressureLevel.HIGH: TEST_CONFIG["memory"]["high_threshold"],
            MemoryPressureLevel.CRITICAL: TEST_CONFIG["memory"]["critical_threshold"]
        }
        
        target_usage = thresholds[target_level]
        
        # Simulate memory usage
        while usage < target_usage:
            await manager.allocate_memory(0.01)  # Allocate small chunks
            usage = manager.get_memory_usage()["percent"] / 100
            
        logger.info(f"Simulated memory pressure level: {target_level}")
    
    def verify_metrics(self, metrics: Dict[str, Any], expected: Dict[str, Any]) -> None:
        """
        Verify that metrics match expected values.
        
        Args:
            metrics: Actual metrics dictionary
            expected: Expected metrics dictionary
        """
        for key, value in expected.items():
            assert key in metrics, f"Missing metric: {key}"
            assert metrics[key] == value, f"Metric {key} mismatch: {metrics[key]} != {value}"
    
    async def wait_for_event(self, manager: CrewManager, 
                           event_type: str, timeout: float = 5) -> Dict[str, Any]:
        """
        Wait for a specific event type to be distributed.
        
        Args:
            manager: CrewManager instance
            event_type: Event type to wait for
            timeout: Maximum wait time in seconds
            
        Returns:
            Event data dictionary
        """
        start_time = datetime.now()
        event_data = None
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            events = await manager.get_events()
            for event in events:
                if event["event_type"] == event_type:
                    event_data = event["data"]
                    break
            
            if event_data:
                break
            
            await asyncio.sleep(0.1)
        
        assert event_data, f"Timeout waiting for event: {event_type}"
        return event_data
