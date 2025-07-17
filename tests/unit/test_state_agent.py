"""
Tests for the StateAgent class.
"""

import pytest
import pytest_asyncio
from typing import Dict, Any, List
from datetime import datetime

from tests.unit.test_base import BaseInfrastructureTest
from agents.infrastructure_crew.infrastructure.agents.state_agent import StateAgent, StateOperation, StateEvent

class TestStateAgent(BaseInfrastructureTest):
    """
    Tests for the StateAgent class.
    """
    
    @pytest_asyncio.fixture
    async def state_agent(self):
        """Fixture that provides a configured StateAgent instance."""
        config = {
            "storage_backend": "memory",
            "namespace": "test",
            "default_ttl": 3600,
            "lock_timeout": 30,
            "event_retention": 86400,
            "snapshot_interval": 3600
        }
        agent = StateAgent(config)
        await agent._initialize()
        yield agent
        await agent._shutdown()
        
    async def test_state_operations(self, state_agent):
        """
        Test basic state operations.
        """
        # Test set operation
        assert await state_agent.set("test_key", "test_value")
        
        # Test get operation
        value = await state_agent.get("test_key")
        assert value == "test_value"
        
        # Test exists operation
        assert await state_agent.exists("test_key")
        assert not await state_agent.exists("nonexistent_key")
        
        # Test delete operation
        assert await state_agent.delete("test_key")
        assert not await state_agent.exists("test_key")
        
    async def test_state_locking(self, state_agent):
        """
        Test distributed locking functionality.
        """
        key = "test_lock_key"
        
        # Test lock acquisition
        assert await state_agent._acquire_lock(key)
        
        # Test concurrent lock acquisition (should fail)
        assert not await state_agent._acquire_lock(key)
        
        # Test lock release
        assert await state_agent._release_lock(key)
        
        # Test lock re-acquisition
        assert await state_agent._acquire_lock(key)
        
    async def test_state_events(self, state_agent):
        """
        Test state change events.
        """
        key = "event_test_key"
        
        # Set value and verify event
        await state_agent.set(key, "initial_value")
        events = await state_agent.get_state_history(key)
        assert len(events) == 1
        assert events[0].operation == StateOperation.SET
        
        # Update value and verify events
        await state_agent.set(key, "updated_value")
        events = await state_agent.get_state_history(key)
        assert len(events) == 2
        assert events[1].operation == StateOperation.SET
        
        # Delete and verify events
        await state_agent.delete(key)
        events = await state_agent.get_state_history(key)
        assert len(events) == 3
        assert events[2].operation == StateOperation.DELETE
        
    async def test_state_snapshots(self, state_agent):
        """
        Test state snapshots.
        """
        # Set some state
        await state_agent.set("snapshot_key_1", "value_1")
        await state_agent.set("snapshot_key_2", "value_2")
        
        # Create snapshot
        snapshot = await state_agent.get_snapshot()
        assert snapshot is not None
        assert "timestamp" in snapshot
        assert "data" in snapshot
        assert len(snapshot["data"]) == 2
        
        # Verify snapshot contents
        assert snapshot["data"]["snapshot_key_1"] == "value_1"
        assert snapshot["data"]["snapshot_key_2"] == "value_2"
        
    async def test_ttl_handling(self, state_agent):
        """
        Test time-to-live functionality.
        """
        key = "ttl_test_key"
        
        # Set value with TTL
        assert await state_agent.set(key, "expiring_value", ttl=1)
        
        # Value should exist immediately
        assert await state_agent.exists(key)
        
        # Wait for TTL to expire
        await asyncio.sleep(2)
        
        # Value should be gone
        assert not await state_agent.exists(key)
        
    async def test_conflict_resolution(self, state_agent):
        """
        Test conflict resolution strategies.
        """
        key = "conflict_key"
        
        # Test last_write_wins strategy
        await state_agent.set(key, "value_1")
        await state_agent.set(key, "value_2")
        assert await state_agent.get(key) == "value_2"
        
        # Test optimistic lock strategy
        state_agent.config["conflict_strategy"] = "optimistic_lock"
        
        # Simulate concurrent updates
        await state_agent.set(key, "value_3")
        await state_agent.set(key, "value_4")
        assert await state_agent.get(key) == "value_4"
        
    async def test_key_patterns(self, state_agent):
        """
        Test key pattern matching.
        """
        # Set some test keys
        await state_agent.set("pattern_test_1", "value_1")
        await state_agent.set("pattern_test_2", "value_2")
        await state_agent.set("other_key", "value_3")
        
        # Test pattern matching
        keys = await state_agent.keys("pattern_test_*")
        assert len(keys) == 2
        assert "pattern_test_1" in keys
        assert "pattern_test_2" in keys
        
    async def test_error_handling(self, state_agent):
        """
        Test error handling for invalid operations.
        """
        # Test invalid key type
        with pytest.raises(TypeError):
            await state_agent.set(123, "value")  # Invalid key type
            
        # Test invalid operation
        with pytest.raises(ValueError):
            await state_agent._process({"operation": "invalid_op"})
            
        # Test lock timeout
        key = "timeout_key"
        await state_agent._acquire_lock(key)
        assert not await state_agent._acquire_lock(key, timeout=1)
        
        # Test invalid TTL
        with pytest.raises(ValueError):
            await state_agent.set("ttl_key", "value", ttl=-1)
            
    async def test_cleanup(self, state_agent):
        """
        Test cleanup of expired events and snapshots.
        """
        # Create some test data
        await state_agent.set("cleanup_key", "value", ttl=1)
        await state_agent.get_snapshot()
        
        # Wait for cleanup
        await asyncio.sleep(2)
        
        # Verify cleanup
        assert not await state_agent.exists("cleanup_key")
        events = await state_agent.get_state_history("cleanup_key")
        assert len(events) == 0
