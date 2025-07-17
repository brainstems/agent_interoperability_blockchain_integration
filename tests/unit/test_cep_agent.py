"""
Tests for the CEPAgent class.
"""

import pytest
import pytest_asyncio
from typing import Dict, Any, List
from datetime import datetime

from tests.unit.test_base import BaseInfrastructureTest
from agents.infrastructure_crew.infrastructure.agents.cep_agent import CEPAgent, PatternType, PatternCondition, EventPattern
from ..crew_manager import Event, EventPriority

class TestCEPAgent(BaseInfrastructureTest):
    """
    Tests for the CEPAgent class.
    """
    
    @pytest_asyncio.fixture
    async def cep_agent(self):
        """Fixture that provides a configured CEPAgent instance."""
        agent = CEPAgent({"window_size": 100})
        yield agent
        
    def test_agent_initialization(self, cep_agent):
        """
        Test CEPAgent initialization.
        """
        assert cep_agent.name == "CEPAgent"
        assert cep_agent.description == "Complex Event Processing Agent"
        assert cep_agent.config["window_size"] == 100
        assert len(cep_agent.patterns) == 0
        assert isinstance(cep_agent.event_buffer, list)
        
    def test_pattern_creation(self, cep_agent):
        """
        Test pattern creation and management.
        """
        # Create a pattern condition
        condition = PatternCondition(
            field="status",
            operator="==",
            value="error",
            pattern_type=PatternType.AND
        )
        
        # Create an event pattern
        pattern = EventPattern(
            name="error_pattern",
            conditions=[condition],
            pattern_type=PatternType.AND,
            time_window=3600
        )
        
        # Add pattern to agent
        assert cep_agent.add_pattern(pattern)
        assert len(cep_agent.patterns) == 1
        assert "error_pattern" in cep_agent.patterns
        
    def test_event_processing(self, cep_agent):
        """
        Test event processing and pattern matching.
        """
        # Create test events
        event1 = Event(
            event_type="system_event",
            data={"status": "error", "component": "api"},
            priority=EventPriority.HIGH
        )
        
        event2 = Event(
            event_type="system_event",
            data={"status": "warning", "component": "db"},
            priority=EventPriority.MEDIUM
        )
        
        # Process events
        result1 = cep_agent._process(event1)
        result2 = cep_agent._process(event2)
        
        # Verify results
        assert len(cep_agent.event_buffer) == 2
        assert isinstance(result1, dict)
        assert isinstance(result2, dict)
        
    def test_pattern_matching(self, cep_agent):
        """
        Test pattern matching with different conditions.
        """
        # Create patterns with different conditions
        pattern1 = EventPattern(
            name="sequence_pattern",
            conditions=[
                PatternCondition("status", "==", "error"),
                PatternCondition("component", "==", "api")
            ],
            pattern_type=PatternType.SEQUENCE,
            time_window=3600
        )
        
        pattern2 = EventPattern(
            name="and_pattern",
            conditions=[
                PatternCondition("status", "==", "error"),
                PatternCondition("priority", ">=", EventPriority.MEDIUM.value)
            ],
            pattern_type=PatternType.AND
        )
        
        # Add patterns
        cep_agent.add_pattern(pattern1)
        cep_agent.add_pattern(pattern2)
        
        # Create test event
        test_event = Event(
            event_type="system_event",
            data={"status": "error", "component": "api", "priority": EventPriority.HIGH.value},
            priority=EventPriority.HIGH
        )
        
        # Process event
        result = cep_agent._process(test_event)
        
        # Verify matches
        assert len(result.get("matches", [])) == 2
        assert "sequence_pattern" in [m["pattern_name"] for m in result["matches"]]
        assert "and_pattern" in [m["pattern_name"] for m in result["matches"]]
        
    def test_event_buffer_management(self, cep_agent):
        """
        Test event buffer management with window size.
        """
        # Fill buffer to capacity
        for i in range(100):
            event = Event(
                event_type="test_event",
                data={"index": i},
                priority=EventPriority.LOW
            )
            cep_agent._process(event)
        
        # Verify buffer size
        assert len(cep_agent.event_buffer) == 100
        
        # Add one more event
        new_event = Event(
            event_type="test_event",
            data={"index": 100},
            priority=EventPriority.LOW
        )
        cep_agent._process(new_event)
        
        # Verify buffer size and oldest event removed
        assert len(cep_agent.event_buffer) == 100
        assert cep_agent.event_buffer[0].data["index"] == 1
