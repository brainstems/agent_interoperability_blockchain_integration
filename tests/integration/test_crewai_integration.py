"""
Integration tests for crewAI integration.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from infrastructure.agents import BaseAgent
from infrastructure.crewai import CrewAIAgentAdapter, InfrastructureTask
from crewai import Crew, Process

class TestCrewAIIntegration:
    """Integration tests for crewAI integration."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test a complete workflow with crewAI and infrastructure agents."""
        # Create a mock agent
        class TestAgent(BaseAgent):
            role = "Test Agent"
            goal = "Test the integration"
            backstory = "For testing purposes"
            
            async def process(self, data):
                return {"result": f"Processed: {data}"}
        
        # Create our infrastructure agent
        agent = TestAgent()
        agent.process = AsyncMock(return_value={"result": "test result"})
        
        # Create a crewAI task using our agent
        task = InfrastructureTask(
            agent=agent,
            description="Test task",
            expected_output="Test output"
        )
        
        # Create a crew with our task
        crew = Crew(
            agents=[CrewAIAgentAdapter(agent)],
            tasks=[task],
            process=Process.sequential,
            verbose=True
        )
        
        # Run the crew
        result = await crew.kickoff(inputs={"test": "data"})
        
        # Verify the results
        assert "test result" in str(result)
        agent.process.assert_awaited_once_with({"test": "data"})
    
    @pytest.mark.asyncio
    async def test_multiple_agents_workflow(self):
        """Test a workflow with multiple agents."""
        # Create mock agents
        class AgentA(BaseAgent):
            role = "Agent A"
            goal = "First agent"
            async def process(self, data):
                return {"result": f"A: {data}"}
        
        class AgentB(BaseAgent):
            role = "Agent B"
            goal = "Second agent"
            async def process(self, data):
                return {"result": f"B: {data}"}
        
        # Create our infrastructure agents
        agent_a = AgentA()
        agent_b = AgentB()
        
        # Mock the process methods
        agent_a.process = AsyncMock(side_effect=agent_a.process)
        agent_b.process = AsyncMock(side_effect=agent_b.process)
        
        # Create tasks
        task1 = InfrastructureTask(
            agent=agent_a,
            description="First task",
            expected_output="Output from first task"
        )
        
        task2 = InfrastructureTask(
            agent=agent_b,
            description="Second task",
            expected_output="Output from second task"
        )
        
        # Create and run the crew
        crew = Crew(
            agents=[
                CrewAIAgentAdapter(agent_a),
                CrewAIAgentAdapter(agent_b)
            ],
            tasks=[task1, task2],
            process=Process.sequential
        )
        
        result = await crew.kickoff(inputs={"test": "data"})
        
        # Verify the results
        assert "B: A: {'test': 'data'}" in str(result)
        agent_a.process.assert_awaited_once()
        agent_b.process.assert_awaited_once()
