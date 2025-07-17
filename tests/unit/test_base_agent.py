"""
Tests for the BaseAgent class.
"""

import pytest
import pytest_asyncio
from typing import Dict, Any

from .test_base import BaseInfrastructureTest
from ..agents.base_agent import BaseAgent

class TestBaseAgent(BaseInfrastructureTest):
    """
    Tests for the BaseAgent class.
    """
    
    @pytest_asyncio.fixture
    async def base_agent(self):
        """Fixture that provides a configured BaseAgent instance."""
        agent = BaseAgent({"test": "config"})
        yield agent
        
    def test_agent_initialization(self, base_agent):
        """
        Test agent initialization.
        """
        assert base_agent.name == "BaseAgent"
        assert base_agent.version == "1.0.0"
        assert base_agent.description == "Base agent implementation"
        assert base_agent.initialized == False
        assert isinstance(base_agent.logger, logging.Logger)
        
    def test_agent_logging(self, base_agent, caplog):
        """
        Test agent logging functionality.
        """
        caplog.set_level(logging.INFO)
        base_agent.logger.info("Test message")
        assert "Test message" in caplog.text
        
    def test_agent_config(self, base_agent):
        """
        Test agent configuration.
        """
        assert base_agent.config == {"test": "config"}
        
    def test_agent_tools(self, base_agent):
        """
        Test agent tools.
        """
        assert isinstance(base_agent.tools, list)
        assert len(base_agent.tools) == 0
        
    def test_agent_metadata(self, base_agent):
        """
        Test agent metadata.
        """
        assert hasattr(base_agent, "name")
        assert hasattr(base_agent, "version")
        assert hasattr(base_agent, "description")
        
    def test_agent_generic_types(self, base_agent):
        """
        Test agent generic type handling.
        """
        assert isinstance(BaseAgent, type)
        assert hasattr(BaseAgent, "__orig_bases__")
        
    def test_agent_abstract_methods(self, base_agent):
        """
        Test that abstract methods are properly defined.
        """
        with pytest.raises(TypeError):
            BaseAgent()  # Should fail since we're not implementing abstract methods
