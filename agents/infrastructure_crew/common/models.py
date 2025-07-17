from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class AgentRegistration(BaseModel):
    agent_id: str
    crew_id: str
    capabilities: List[str]
    # Add other relevant details

class ServiceRegistrationRequest(BaseModel):
    service_id: str
    service_name: str
    crew_id: str
    capabilities: List[str]
    endpoints: Dict[str, str] # e.g., {"http_post": "/api/service_a"}
    # Add other relevant details like version, description, etc.

class ServiceHeartbeat(BaseModel):
    service_id: str
    timestamp: float
    status: str # e.g., "HEALTHY", "DEGRADED", "UNAVAILABLE"
    # Add other metrics like load, response_time, etc.

class EndpointType(BaseModel):
    # Define endpoint types if needed, e.g., for different communication protocols
    pass

class ServiceStatus(BaseModel):
    # Define service statuses if needed
    pass

class ServiceEndpoint(BaseModel):
    # Define service endpoint details if needed
    pass

class LLMClientConfig(BaseModel):
    """Configuration for an LLM client."""
    client_type: str = "openai" # e.g., "openai", "anthropic", "ollama", "custom_http"
    model_name: Optional[str] = "gpt-4-turbo-preview"
    api_base_url: Optional[str] = None # For self-hosted or alternative endpoints
    api_key_env_var: Optional[str] = "OPENAI_API_KEY"
    max_tokens: Optional[int] = 4096
    temperature: Optional[float] = 0.7
    # Add other common LLM parameters as needed

    class Config:
        extra = 'allow' # Allow other parameters for specific client types
