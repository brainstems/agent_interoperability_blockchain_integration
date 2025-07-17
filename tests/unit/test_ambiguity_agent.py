"""
Tests for the AmbiguityAgent class.
"""

import pytest
import pytest_asyncio
from typing import Dict, Any, List

from tests.unit.test_base import BaseInfrastructureTest
from agents.infrastructure_crew.infrastructure.agents.ambiguity_agent import AmbiguityAgent

class TestAmbiguityAgent(BaseInfrastructureTest):
    """
    Tests for the AmbiguityAgent class.
    """
    
    @pytest_asyncio.fixture
    async def ambiguity_agent(self):
        """Fixture that provides a configured AmbiguityAgent instance."""
        config = {
            "detection_threshold": 0.7,
            "max_suggestions": 3,
            "enabled_detectors": ["missing_fields", "vague_terms", "contradictions"],
            "resolvers": {
                "default": "suggest_options"
            }
        }
        agent = AmbiguityAgent(config)
        await agent._initialize()
        yield agent
        
    def test_agent_initialization(self, ambiguity_agent):
        """
        Test AmbiguityAgent initialization.
        """
        assert ambiguity_agent.name == "AmbiguityAgent"
        assert ambiguity_agent.description == "Detects and resolves ambiguities in input data"
        assert ambiguity_agent.config["detection_threshold"] == 0.7
        assert len(ambiguity_agent.config["enabled_detectors"]) == 3
        
    async def test_ambiguity_detection(self, ambiguity_agent):
        """
        Test ambiguity detection with different inputs.
        """
        # Test with missing fields
        request_missing = {"partial": {"value": 100}}
        response_missing = await ambiguity_agent.process(request_missing)
        assert "ambiguities" in response_missing
        assert len(response_missing["ambiguities"]) > 0
        assert "missing_fields" in response_missing["ambiguities"]
        
        # Test with vague terms
        request_vague = {"description": "big amount of money"}
        response_vague = await ambiguity_agent.process(request_vague)
        assert "ambiguities" in response_vague
        assert len(response_vague["ambiguities"]) > 0
        assert "vague_terms" in response_vague["ambiguities"]
        
        # Test with contradictions
        request_contradiction = {"status": "active", "closed": True}
        response_contradiction = await ambiguity_agent.process(request_contradiction)
        assert "ambiguities" in response_contradiction
        assert len(response_contradiction["ambiguities"]) > 0
        assert "contradictions" in response_contradiction["ambiguities"]
        
    async def test_ambiguity_resolution(self, ambiguity_agent):
        """
        Test ambiguity resolution strategies.
        """
        # Test suggestion resolution
        request_suggestion = {"description": "big amount"}
        response_suggestion = await ambiguity_agent.process(request_suggestion)
        assert "suggestions" in response_suggestion
        assert len(response_suggestion["suggestions"]) <= 3
        
        # Test clarification resolution
        request_clarification = {"status": "active", "closed": True}
        response_clarification = await ambiguity_agent.process(request_clarification)
        assert "clarification" in response_clarification
        assert "questions" in response_clarification["clarification"]
        
    async def test_threshold_handling(self, ambiguity_agent):
        """
        Test detection threshold behavior.
        """
        # Test below threshold
        request_below = {"value": 100.1}
        response_below = await ambiguity_agent.process(request_below)
        assert "ambiguities" not in response_below
        
        # Test above threshold
        request_above = {"value": 99.9}
        response_above = await ambiguity_agent.process(request_above)
        assert "ambiguities" in response_above
        
    async def test_detector_configuration(self, ambiguity_agent):
        """
        Test detector configuration.
        """
        # Test with custom detectors
        custom_config = {
            "enabled_detectors": ["custom_detector"],
            "custom_detector": {
                "threshold": 0.5,
                "keywords": ["test", "sample"]
            }
        }
        ambiguity_agent.config.update(custom_config)
        
        # Test custom detector
        request_custom = {"description": "test case"}
        response_custom = await ambiguity_agent.process(request_custom)
        assert "ambiguities" in response_custom
        assert "custom_detector" in response_custom["ambiguities"]
        
    async def test_error_handling(self, ambiguity_agent):
        """
        Test error handling with invalid inputs.
        """
        # Test with invalid input
        request_invalid = {"invalid": [1, 2, 3]}
        response_invalid = await ambiguity_agent.process(request_invalid)
        assert "error" in response_invalid
        assert "Invalid input format" in response_invalid["error"]
        
        # Test with invalid detector
        invalid_config = {
            "enabled_detectors": ["nonexistent_detector"]
        }
        ambiguity_agent.config.update(invalid_config)
        response_error = await ambiguity_agent.process({"test": "data"})
        assert "error" in response_error
        assert "Unknown detector" in response_error["error"]
