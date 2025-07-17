"""
Tests for the MemoryManager and TeamMemoryManager.
"""

import pytest
import pytest_asyncio
from typing import Dict, Any, List
from datetime import datetime

from tests.unit.test_base import BaseInfrastructureTest
from agents.infrastructure_crew.infrastructure.memory.memory_manager import MemoryManager, MemoryPressureLevel
from agents.infrastructure_crew.infrastructure.memory.team_memory_manager import TeamMemoryManager

class TestMemoryManager(BaseInfrastructureTest):
    """
    Tests for the MemoryManager.
    """
    
    @pytest.mark.asyncio
    async def test_memory_monitoring(self, memory_manager):
        """
        Test memory monitoring functionality.
        """
        # Get initial memory usage
        initial_usage = await memory_manager.get_memory_usage()
        assert initial_usage["total"] > 0
        assert 0 <= initial_usage["percent"] <= 100
        
        # Simulate memory pressure
        await self.simulate_memory_pressure(memory_manager, MemoryPressureLevel.MEDIUM)
        
        # Verify metrics
        metrics = await memory_manager.get_metrics()
        assert metrics["current_usage"] > 0
        assert metrics["peak_usage"] >= metrics["current_usage"]
        
    @pytest.mark.asyncio
    async def test_memory_pressure_handling(self, memory_manager):
        """
        Test memory pressure handling at different levels.
        """
        # Test medium pressure
        await self.simulate_memory_pressure(memory_manager, MemoryPressureLevel.MEDIUM)
        medium_metrics = await memory_manager.get_metrics()
        assert medium_metrics["cleanup_count"] > 0
        
        # Test high pressure
        await self.simulate_memory_pressure(memory_manager, MemoryPressureLevel.HIGH)
        high_metrics = await memory_manager.get_metrics()
        assert high_metrics["cleanup_count"] > medium_metrics["cleanup_count"]
        
        # Test critical pressure
        await self.simulate_memory_pressure(memory_manager, MemoryPressureLevel.CRITICAL)
        critical_metrics = await memory_manager.get_metrics()
        assert critical_metrics["cleanup_count"] > high_metrics["cleanup_count"]
        assert critical_metrics["evictions"] > 0

class TestTeamMemoryManager(BaseInfrastructureTest):
    """
    Tests for the TeamMemoryManager.
    """
    
    @pytest.mark.asyncio
    async def test_team_memory_allocation(self, team_memory_manager):
        """
        Test memory allocation to teams.
        """
        team_ids = await self.create_test_teams(team_memory_manager)
        
        for team_id in team_ids:
            usage = await team_memory_manager.get_team_memory_usage(team_id)
            assert usage["usage"] > 0
            assert usage["quota"] > 0
            
    @pytest.mark.asyncio
    async def test_memory_sharing(self, team_memory_manager):
        """
        Test memory sharing between teams.
        """
        team_ids = await self.create_test_teams(team_memory_manager)
        
        # Get initial usage
        team1_usage = await team_memory_manager.get_team_memory_usage(team_ids[0])
        team2_usage = await team_memory_manager.get_team_memory_usage(team_ids[1])
        
        # Share memory
        amount = 0.05
        success = await team_memory_manager.share_memory(
            team_ids[0], team_ids[1], amount
        )
        assert success
        
        # Verify updated usage
        new_team1_usage = await team_memory_manager.get_team_memory_usage(team_ids[0])
        new_team2_usage = await team_memory_manager.get_team_memory_usage(team_ids[1])
        
        assert new_team1_usage["usage"] < team1_usage["usage"]
        assert new_team2_usage["usage"] > team2_usage["usage"]
        
    @pytest.mark.asyncio
    async def test_memory_conflicts(self, team_memory_manager):
        """
        Test memory conflict detection and resolution.
        """
        team_ids = await self.create_test_teams(team_memory_manager)
        
        # Create conflict by allocating too much memory
        success = await team_memory_manager.allocate_memory(team_ids[0], 0.5)
        assert not success  # Should fail due to exceeding quota
        
        # Verify conflict event
        event_data = await self.wait_for_event(
            team_memory_manager, "team.memory.conflict"
        )
        assert event_data["team_id"] == team_ids[0]
        
    @pytest.mark.asyncio
    async def test_memory_cleanup_events(self, team_memory_manager):
        """
        Test memory cleanup events and metrics.
        """
        team_ids = await self.create_test_teams(team_memory_manager)
        
        # Simulate memory pressure
        await self.simulate_memory_pressure(
            team_memory_manager, MemoryPressureLevel.HIGH
        )
        
        # Verify cleanup event
        event_data = await self.wait_for_event(
            team_memory_manager, "memory.cleanup"
        )
        assert event_data["timestamp"] > 0
        
        # Verify metrics
        metrics = team_memory_manager.get_metrics()
        assert metrics["cleanup_count"] > 0
        assert metrics["evictions"] >= 0
