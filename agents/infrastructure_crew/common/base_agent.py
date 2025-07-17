"""
Base Agent Implementation

This module provides the base agent class that all infrastructure agents inherit from.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic, Union
from pydantic import BaseModel

# Type variable for the request/response model
T = TypeVar('T')
R = TypeVar('R')

class AgentConfig(BaseModel):
    """Base configuration model for all agents."""
    agent_id: str = "default_agent"
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True
    
    class Config:
        extra = "allow"  # Allow extra fields

class BaseAgent(ABC, Generic[T, R]):
    """
    Base class for all infrastructure agents.
    
    This class provides common functionality and interface that all agents should implement.
    """
    
    # Agent metadata
    name: str = "BaseAgent"
    version: str = "1.0.0"
    description: str = "Base agent implementation"
    
    def __init__(self, agent_id: str, config: Optional[Union[Dict[str, Any], AgentConfig]] = None):
        """
        Initialize the agent with an ID and optional configuration.
        
        Args:
            agent_id: Unique identifier for the agent
            config: Optional configuration for the agent (can be dict or AgentConfig)
        """
        self.agent_id = agent_id
        
        # Handle different config types
        if config is None:
            self.config = AgentConfig(agent_id=agent_id, name=self.name, description=self.description)
        elif isinstance(config, dict):
            self.config = AgentConfig(agent_id=agent_id, **config)
        else:
            self.config = config
        
        self.logger = self._setup_logging()
        self.tools: List[Any] = []  # Placeholder for tools
        self.initialized = False

    def _setup_logging(self) -> logging.Logger:
        # Basic logging setup
        logger_instance = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        # Configure logger (level, handler, formatter) as needed
        # For simplicity, using basic config. Customize as required.
        if not logger_instance.handlers: # Avoid adding multiple handlers if already configured
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger_instance.addHandler(handler)
            logger_instance.setLevel(logging.INFO) # Default level
        return logger_instance

    async def initialize(self) -> None:
        """Initializes the agent and its resources."""
        if not self.initialized:
            self.logger.info(f"Initializing {self.config.name if self.config and self.config.name else self.agent_id}...")
            await self._initialize()
            self.initialized = True
            self.logger.info(f"{self.config.name if self.config and self.config.name else self.agent_id} initialized successfully.")

    @abstractmethod
    async def _initialize(self) -> None:
        """Agent-specific initialization logic."""
        pass

    async def process(self, request: T) -> R:
        """Processes a request using the agent's logic."""
        try:
            self.logger.debug(f"Processing request: {request}")
            if not self.initialized:
                await self.initialize()
            response = await self._process(request)
            self.logger.debug(f"Request processed successfully.")
            return response
        except Exception as e:
            self.logger.error(f"Error processing request: {e}", exc_info=True)
            raise

    @abstractmethod
    async def _process(self, request: T) -> R:
        """Agent-specific processing logic."""
        pass

    async def shutdown(self) -> None:
        """Shuts down the agent and releases resources."""
        if self.initialized:
            self.logger.info(f"Shutting down {self.config.name if self.config and self.config.name else self.agent_id}...")
            await self._shutdown()
            self.initialized = False
            self.logger.info(f"{self.config.name if self.config and self.config.name else self.agent_id} shutdown complete.")

    async def _shutdown(self) -> None:
        """Agent-specific shutdown logic."""
        pass # Default no-op

    def __str__(self) -> str:
        return f"{self.config.name if self.config and self.config.name else self.agent_id} (v{self.version})"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.config.name if self.config and self.config.name else self.agent_id}'>"
