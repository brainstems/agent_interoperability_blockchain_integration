"""
CrewAI Task Definitions

This module provides task definitions that integrate infrastructure agents
with the CrewAI framework.
"""

from typing import Any, Dict, List, Optional, Type, Union
from pydantic import BaseModel, Field

from crewai import Task as CrewAITask
from crewai.utilities import I18N

class InfrastructureTask(CrewAITask):
    """
    A CrewAI task that works with infrastructure agents.
    
    This class extends the base CrewAI Task to provide additional functionality
    for working with infrastructure agents.
    """
    
    def __init__(
        self,
        agent: Any = None,
        description: str = "",
        expected_output: str = "",
        tools: Optional[List[Any]] = None,
        async_execution: bool = False,
        context: Optional[Union[List[Any], Any]] = None,
        output_file: str = "",
        output_pydantic: Optional[Type[BaseModel]] = None,
        output_json: Optional[Dict[str, Any]] = None,
        callback: Optional[callable] = None,
        human_input: bool = False,
        **kwargs
    ):
        """
        Initialize the InfrastructureTask.
        
        Args:
            agent: The agent that will execute this task
            description: Description of the task
            expected_output: Expected output format
            tools: List of tools the agent can use
            async_execution: Whether to execute asynchronously
            context: Context for the task
            output_file: File to save the output to
            output_pydantic: Pydantic model for output validation
            output_json: JSON schema for output validation
            callback: Callback function to call after task completion
            human_input: Whether to prompt for human input
            **kwargs: Additional keyword arguments
        """
        super().__init__(
            agent=agent,
            description=description,
            expected_output=expected_output,
            tools=tools or [],
            async_execution=async_execution,
            context=context or [],
            output_file=output_file,
            output_pydantic=output_pydantic,
            output_json=output_json,
            callback=callback,
            human_input=human_input,
            **kwargs
        )
    
    @classmethod
    def from_crewai_task(
        cls,
        crewai_task: CrewAITask,
        agent: Optional[Any] = None,
        **kwargs
    ) -> 'InfrastructureTask':
        """
        Create an InfrastructureTask from a CrewAITask.
        
        Args:
            crewai_task: The CrewAITask to convert
            agent: Optional agent to use (overrides the task's agent)
            **kwargs: Additional keyword arguments to override task attributes
            
        Returns:
            A new InfrastructureTask instance
        """
        task_agent = agent or crewai_task.agent
        
        return cls(
            agent=task_agent,
            description=kwargs.get('description', crewai_task.description),
            expected_output=kwargs.get('expected_output', crewai_task.expected_output),
            tools=kwargs.get('tools', crewai_task.tools),
            async_execution=kwargs.get('async_execution', crewai_task.async_execution),
            context=kwargs.get('context', crewai_task.context),
            output_file=kwargs.get('output_file', crewai_task.output_file),
            output_pydantic=kwargs.get('output_pydantic', crewai_task.output_pydantic),
            output_json=kwargs.get('output_json', crewai_task.output_json),
            callback=kwargs.get('callback', crewai_task.callback),
            human_input=kwargs.get('human_input', crewai_task.human_input),
            **{k: v for k, v in kwargs.items() 
               if k not in ['description', 'expected_output', 'tools', 'async_execution', 
                          'context', 'output_file', 'output_pydantic', 'output_json', 
                          'callback', 'human_input']}
        )
    
    async def execute(self, task_input: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        """
        Execute the task with the given input.
        
        Args:
            task_input: Input data for the task
            **kwargs: Additional keyword arguments
            
        Returns:
            The result of the task execution
        """
        # Merge task input with additional kwargs
        task_input = task_input or {}
        if kwargs:
            task_input.update(kwargs)
        
        # Execute the task using the parent class implementation
        result = await super().execute(task_input=task_input)
        
        # Additional processing can be added here
        return result
    
    def add_context(self, context: Any) -> None:
        """
        Add context to the task.
        
        Args:
            context: Context to add to the task
        """
        if not isinstance(context, list):
            context = [context]
            
        if not hasattr(self, '_context'):
            self._context = []
            
        self._context.extend(context)
    
    def __repr__(self) -> str:
        """Return a string representation of the task."""
        return f"<InfrastructureTask: {self.description[:50]}...>"
