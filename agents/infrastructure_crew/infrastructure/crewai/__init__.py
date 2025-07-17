"""
CrewAI Integration for Infrastructure Agents

This module provides adapters, tasks, and utilities to make infrastructure agents
compatible with the CrewAI framework.
"""

# Import adapters and tasks
from .adapters import CrewAIAgentAdapter
from .tasks import InfrastructureTask

# Import tools
from .tools import create_csv_search_tool, CSVSearchTool

# Re-export commonly used types and classes
from typing import Dict, Any, List, Optional, Type, Union, TypeVar
from pydantic import BaseModel, Field

__all__ = [
    # Adapters
    'CrewAIAgentAdapter',
    
    # Tasks
    'InfrastructureTask',
    
    # Tools
    'create_csv_search_tool',
    'CSVSearchTool',
    
    # Common types
    'Dict', 'Any', 'List', 'Optional', 'Type', 'Union', 'TypeVar',
    'BaseModel', 'Field'
]
