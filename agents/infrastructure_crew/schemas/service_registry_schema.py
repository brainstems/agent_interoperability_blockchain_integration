from pydantic import BaseModel, Field, HttpUrl
from typing import Dict, Optional, List, Any
from enum import Enum
import uuid
from datetime import datetime

class ServiceStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"

class EndpointType(str, Enum):
    REDIS_PUBSUB = "redis_pubsub"
    HTTP_API = "http_api"
    GRPC = "grpc"

class ServiceEndpoint(BaseModel):
    type: EndpointType
    address: str # e.g., Redis channel name, HTTP URL
    metadata: Optional[Dict[str, Any]] = None

class ServiceInfo(BaseModel):
    service_id: str = Field(default_factory=lambda: f"service_{uuid.uuid4()}")
    service_name: str
    crew_id: str
    version: str = "1.0.0"
    description: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list) # e.g., ["translate_sales_to_inventory", "provide_market_analysis"]
    endpoints: List[ServiceEndpoint]
    status: ServiceStatus = ServiceStatus.ACTIVE
    input_schema_id: Optional[str] = None # Reference to a schema for expected input
    output_schema_id: Optional[str] = None # Reference to a schema for output
    registered_at: datetime = Field(default_factory=datetime.utcnow)
    last_heartbeat_at: Optional[datetime] = None
    additional_metadata: Optional[Dict[str, Any]] = None

class ServiceRegistrationRequest(BaseModel):
    service_name: str
    crew_id: str
    version: str = "1.0.0"
    description: Optional[str] = None
    capabilities: List[str]
    endpoints: List[ServiceEndpoint]
    input_schema_id: Optional[str] = None
    output_schema_id: Optional[str] = None
    additional_metadata: Optional[Dict[str, Any]] = None

class ServiceHeartbeat(BaseModel):
    service_id: str
    status: Optional[ServiceStatus] = None # Optional: agent can report a status change during heartbeat
