"""
Adapters for integrating infrastructure agents with CrewAI.

This module provides adapters to make our infrastructure agents work
seamlessly with the CrewAI framework.
"""

from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from pydantic import BaseModel
from crewai import Agent as CrewAIAgent
from crewai.tools import BaseTool

from infrastructure.agents import BaseAgent

T = TypeVar('T', bound=BaseModel)

class CrewAIAgentAdapter(CrewAIAgent):
    """
    Adapter to make our BaseAgent compatible with crewAI.
    
    This class wraps our infrastructure agents to provide the interface
    expected by the CrewAI framework.
    """
    
    def __init__(self, agent: BaseAgent, **kwargs):
        """
        Initialize the adapter with an infrastructure agent.
        
        Args:
            agent: The infrastructure agent to adapt
            **kwargs: Additional arguments to pass to the CrewAIAgent constructor
        """
        # Get agent metadata
        name = getattr(agent, 'name', agent.__class__.__name__)
        goal = getattr(agent, 'goal', '')
        backstory = getattr(agent, 'backstory', '')
        tools = getattr(agent, 'tools', [])
        
        # Initialize the CrewAI agent
        super().__init__(
            name=name,
            goal=goal,
            backstory=backstory,
            tools=tools,
            **kwargs
        )
        
        # Store a reference to the underlying agent
        self._agent = agent
    
    async def execute_task(
        self, 
        task_input: Union[str, Dict[str, Any]], 
        tools: Optional[List[BaseTool]] = None,
        context: Optional[List[Any]] = None
    ) -> str:
        """
        Execute a task with the given input and tools.
        
        Args:
            task_input: The input for the task (can be a string or dict)
            tools: List of tools available for the task
            context: Additional context for the task
            
        Returns:
            The result of the task execution as a string
        """
        # Prepare the input for our agent
        if isinstance(task_input, str):
            input_data = {"input": task_input}
        else:
            input_data = task_input
            
        if context:
            input_data["context"] = context
            
        if tools:
            input_data["tools"] = tools
        
        # Execute the agent's process method
        try:
            result = await self._agent.process(input_data)
            
            # Convert the result to a string if it isn't already
            if not isinstance(result, str):
                if isinstance(result, (dict, list)):
                    import json
                    result = json.dumps(result, indent=2)
                else:
                    result = str(result)
                    
            return result
            
        except Exception as e:
            error_msg = f"Error executing task: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return error_msg


class InfrastructureTask:
    """
    A CrewAI task that works with our infrastructure agents.
    
    This class extends CrewAITask to work with our infrastructure agents
    through the CrewAIAgentAdapter.
    """
    
    def __init__(self, agent: BaseAgent, **kwargs):
        """
        Initialize the task with an infrastructure agent.
        
        Args:
            agent: The infrastructure agent to use for this task
            **kwargs: Additional arguments to pass to the CrewAITask constructor
        """
        # Create an adapter for the agent
        adapted_agent = CrewAIAgentAdapter(agent)
        
        # Initialize the CrewAI task
        self.agent = adapted_agent
        self.description = kwargs.get("description")
        self.expected_output = kwargs.get("expected_output")
        self.tools = kwargs.get("tools")
        self.async_execution = kwargs.get("async_execution")
        self.context = kwargs.get("context")
        self.output_file = kwargs.get("output_file")
        self.output_pydantic = kwargs.get("output_pydantic")
        self.callback = kwargs.get("callback")
        self.human_input = kwargs.get("human_input")
    
    @classmethod
    def from_crewai_task(cls, task: 'InfrastructureTask', agent: BaseAgent) -> 'InfrastructureTask':
        """
        Create an InfrastructureTask from an existing CrewAITask.
        
        Args:
            task: The CrewAITask to convert
            agent: The infrastructure agent to use
            
        Returns:
            A new InfrastructureTask instance
        """
        return cls(
            agent=agent,
            description=task.description,
            expected_output=task.expected_output,
            tools=task.tools,
            async_execution=task.async_execution,
            context=task.context,
            output_file=task.output_file,
            output_pydantic=task.output_pydantic,
            callback=task.callback,
            human_input=task.human_input
        )
