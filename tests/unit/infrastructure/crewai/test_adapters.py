"""
Tests for the crewAI adapters.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from infrastructure.crewai.adapters import CrewAIAgentAdapter, InfrastructureTask

class TestCrewAIAgentAdapter:
    """Tests for the CrewAIAgentAdapter class."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_agent):
        """Test that the adapter initializes correctly."""
        adapter = CrewAIAgentAdapter(mock_agent)
        
        assert adapter.role == "Mock Agent"
        assert adapter.goal == "Test agent"
        assert adapter.backstory == "For testing purposes"
    
    @pytest.mark.asyncio
    async def test_execute_task_calls_agent_process(self, mock_agent):
        """Test that execute_task calls the agent's process method."""
        adapter = CrewAIAgentAdapter(mock_agent)
        test_input = {"test": "data"}
        
        result = await adapter.execute_task(test_input)
        
        mock_agent.process.assert_awaited_once_with(test_input)
        assert result == {"result": "test"}
    
    @pytest.mark.asyncio
    async def test_execute_task_handles_errors(self, mock_agent):
        """Test that execute_task handles errors from the agent."""
        mock_agent.process.side_effect = Exception("Test error")
        adapter = CrewAIAgentAdapter(mock_agent)
        
        with pytest.raises(Exception, match="Test error"):
            await adapter.execute_task({"test": "data"})


class TestInfrastructureTask:
    """Tests for the InfrastructureTask class."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_agent):
        """Test that the task initializes correctly."""
        task = InfrastructureTask(
            agent=mock_agent,
            description="Test task",
            expected_output="Test output"
        )
        
        assert task.agent.role == "Mock Agent"
        assert task.description == "Test task"
        assert task.expected_output == "Test output"
    
    @pytest.mark.asyncio
    async def test_from_crewai_task(self, mock_agent):
        """Test creating an InfrastructureTask from a CrewAITask."""
        crewai_task = MagicMock()
        crewai_task.description = "CrewAI Task"
        crewai_task.expected_output = "Expected output"
        crewai_task.tools = ["tool1", "tool2"]
        crewai_task.async_execution = True
        crewai_task.context = ["context1", "context2"]
        crewai_task.output_file = "output.txt"
        crewai_task.output_pydantic = None
        crewai_task.callback = lambda x: x
        crewai_task.human_input = False
        
        task = InfrastructureTask.from_crewai_task(crewai_task, mock_agent)
        
        assert task.description == "CrewAI Task"
        assert task.expected_output == "Expected output"
        assert task.tools == ["tool1", "tool2"]
        assert task.async_execution is True
        assert task.context == ["context1", "context2"]
        assert task.output_file == "output.txt"
        assert task.output_pydantic is None
        assert task.callback is not None
        assert task.human_input is False
