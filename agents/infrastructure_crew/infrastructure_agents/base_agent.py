# /Users/erichillerbrand/agent_blockchain-integration-main/agents/infrastructure_crew/agents/base_agent.py
"""
Base Agent Implementation for Infrastructure Crew

This module provides the base agent class that all infrastructure agents inherit from.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic, Union
from pydantic import BaseModel
from redis.asyncio import Redis as AsyncRedis # Example import for shared service
from ...common.base_agent import BaseAgent as CommonBaseAgent, AgentConfig as CommonAgentConfig, T, R
# Import from the common base agent




logger = logging.getLogger(__name__)

# --- Renamed existing classes for temporary preservation ---
class OldInfrastructureAgentConfig(BaseModel):
    """Base configuration model for all agents."""
    agent_id: str = "default_agent"
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True
    
    class Config:
        extra = "allow"  # Allow extra fields

T_Old = TypeVar('T_Old') # Renaming typevars for old class
R_Old = TypeVar('R_Old')

class OldInfrastructureBaseAgent(ABC, Generic[T_Old, R_Old]):
    """
    (Old) Base class for all infrastructure agents.
    This class provides common functionality and interface that all agents should implement.
    """
    name: str = "BaseAgent"
    version: str = "1.0.0"
    description: str = "Base agent implementation"
    
    def __init__(self, agent_id: str, config: Optional[Union[Dict[str, Any], OldInfrastructureAgentConfig]] = None):
        self.agent_id = agent_id
        if config is None:
            self.config = OldInfrastructureAgentConfig(agent_id=agent_id, name=self.name, description=self.description)
        elif isinstance(config, dict):
            self.config = OldInfrastructureAgentConfig(agent_id=agent_id, **config)
        else:
            self.config = config
        self.logger = self._setup_logging()
        self.tools: List[Any] = []
        self.initialized = False
    
    def _setup_logging(self) -> logging.Logger:
        logger_instance = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        logger_instance.setLevel(logging.INFO)
        if not logger_instance.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger_instance.addHandler(handler)
        return logger_instance
    
    async def initialize(self) -> None:
        if not self.initialized:
            self.logger.info(f"Initializing {self.config.name}...") # Adjusted to use config.name
            await self._initialize()
            self.initialized = True
            self.logger.info(f"{self.config.name} initialized successfully") # Adjusted
    
    @abstractmethod
    async def _initialize(self) -> None:
        pass
    
    async def process(self, request: T_Old) -> R_Old:
        try:
            self.logger.debug(f"Processing request: {request}")
            if not self.initialized:
                await self.initialize()
            response = await self._process(request)
            self.logger.debug(f"Request processed successfully")
            return response
        except Exception as e:
            self.logger.error(f"Error processing request: {e}", exc_info=True)
            raise
    
    @abstractmethod
    async def _process(self, request: T_Old) -> R_Old:
        pass
    
    async def shutdown(self) -> None:
        if self.initialized:
            self.logger.info(f"Shutting down {self.config.name}...") # Adjusted
            await self._shutdown()
            self.initialized = False
            self.logger.info(f"{self.config.name} shutdown complete") # Adjusted
    
    async def _shutdown(self) -> None:
        pass
    
    def __str__(self) -> str:
        return f"{self.config.name} (v{self.version})" # Adjusted
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.config.name}'>" # Adjusted

# --- New InfrastructureAgentConfig and InfrastructureBaseAgent ---

class InfrastructureAgentConfig(CommonAgentConfig):
    """
    Configuration specific to infrastructure agents.
    Inherits common configurations and adds infrastructure-specific ones.
    """
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    # Add other common infrastructure config fields here, e.g.:
    # event_bus_topic_prefix: str = "infra.events"

    class Config(CommonAgentConfig.Config): # Ensure Pydantic V2 Config behavior
        pass


class InfrastructureBaseAgent(CommonBaseAgent[T, R], Generic[T, R]): # Inherits from common.base_agent.BaseAgent
    """
    Base class for all agents within the Infrastructure Crew.
    Provides common functionalities and configurations tailored for infrastructure tasks.
    """
    config: InfrastructureAgentConfig # Type hint for the specific config

    def __init__(self, agent_id: str, config: Optional[Union[Dict[str, Any], InfrastructureAgentConfig]] = None, **kwargs):
        """
        Initialize the infrastructure agent.

        Args:
            agent_id: Unique identifier for the agent.
            config: Configuration for the agent. Can be a dict or InfrastructureAgentConfig.
            **kwargs: Additional keyword arguments, potentially for shared services like Redis.
        """
        if isinstance(config, dict):
            # Ensure agent_id from arg takes precedence if also in dict
            config_data = {**config, "agent_id": agent_id}
            parsed_config = InfrastructureAgentConfig(**config_data)
        elif isinstance(config, InfrastructureAgentConfig):
            parsed_config = config
            parsed_config.agent_id = agent_id # Ensure agent_id is set
        else: # Handles None or other types, defaults to InfrastructureAgentConfig
            parsed_config = InfrastructureAgentConfig(agent_id=agent_id)

        # Ensure name and description from class are used if not in config
        if not parsed_config.name: # Use class attribute if name not in config
            parsed_config.name = getattr(self.__class__, 'name', agent_id)
        if not parsed_config.description: # Use class attribute if description not in config
            parsed_config.description = getattr(self.__class__, 'description', 'Infrastructure Agent')
        
        # Call the __init__ of CommonBaseAgent
        super().__init__(agent_id=agent_id, config=parsed_config)

        self.redis_client: Optional[AsyncRedis] = kwargs.get("redis_client")
        logger.info(f"Initialized {self.config.name} (ID: {self.agent_id}) with config: {self.config.model_dump_json(indent=2)}")

    async def setup_shared_resources(self):
        """
        Sets up shared resources like Redis connection.
        This method can be called after initialization.
        """
        if not self.redis_client: # Check if already provided via kwargs
            try:
                self.redis_client = AsyncRedis(host=self.config.redis_host,
                                               port=self.config.redis_port,
                                               db=self.config.redis_db,
                                               decode_responses=True)
                await self.redis_client.ping()
                logger.info(f"{self.config.name}: Successfully connected to Redis at {self.config.redis_host}:{self.config.redis_port}")
            except Exception as e:
                logger.error(f"{self.config.name}: Failed to connect to Redis - {e}")
                self.redis_client = None

    async def teardown_shared_resources(self):
        """
        Tears down shared resources.
        """
        if self.redis_client:
            try:
                await self.redis_client.close()
                logger.info(f"{self.config.name}: Successfully closed Redis connection.")
            except Exception as e:
                logger.error(f"{self.config.name}: Error closing Redis connection - {e}")

    @abstractmethod
    async def perform_infrastructure_task(self, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Abstract method for performing a generic infrastructure-related task.
        Specific infrastructure agents should implement this.
        """
        pass

    async def initialize_agent(self) -> None: 
        """Initializes shared resources and agent-specific logic."""
        await self.setup_shared_resources()
        await self._initialize_agent_specific() 
        logger.info(f"{self.config.name} fully initialized.")

    @abstractmethod
    async def _initialize_agent_specific(self) -> None:
        """Agent-specific initialization logic beyond shared resources."""
        pass

    async def process_agent_request(self, request: Any) -> Any: 
        """Processes a request using agent-specific logic."""
        return await self._process_agent_specific(request) 

    @abstractmethod
    async def _process_agent_specific(self, request: Any) -> Any:
        """Agent-specific request processing logic."""
        pass

    async def shutdown_agent(self) -> None: 
        """Shuts down agent-specific logic and shared resources."""
        await self._shutdown_agent_specific() 
        await self.teardown_shared_resources()
        logger.info(f"{self.config.name} fully shut down.")

    @abstractmethod
    async def _shutdown_agent_specific(self) -> None:
        """Agent-specific shutdown logic before shared resources are torn down."""
        pass

