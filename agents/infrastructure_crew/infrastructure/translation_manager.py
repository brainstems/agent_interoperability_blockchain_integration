"""
Translation Manager Implementation

This module provides the TranslationManager class which manages protocol translation
and data transformation between different systems.
"""

import json
import inspect
from typing import Dict, Any, Type, TypeVar, Generic, Callable, Optional
from dataclasses import dataclass
from enum import Enum

from .agents.base_agent import BaseAgent

T = TypeVar('T')

class Protocol(Enum):
    """Enumeration of supported protocols."""
    REST = "rest"
    GRPC = "grpc"
    MQTT = "mqtt"
    AMQP = "amqp"
    WEBSOCKET = "websocket"

class TranslationError(Exception):
    """Exception raised for translation errors."""
    pass

class ProtocolAdapter:
    """Base class for protocol adapters."""
    
    def __init__(self, protocol: Protocol):
        self.protocol = protocol
        
    def translate_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Translate a request to the target protocol."""
        raise NotImplementedError
        
    def translate_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Translate a response from the target protocol."""
        raise NotImplementedError
        
    def validate_schema(self, data: Dict[str, Any]) -> bool:
        """Validate data against the protocol's schema."""
        raise NotImplementedError

class RESTAdapter(ProtocolAdapter):
    """Adapter for REST protocol."""
    
    def translate_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Translate request to REST format."""
        return {
            "method": request.get("method", "GET"),
            "url": request["url"],
            "headers": request.get("headers", {}),
            "body": request.get("body", {})
        }
        
    def translate_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Translate response from REST format."""
        return {
            "status_code": response["status_code"],
            "headers": response["headers"],
            "body": response["body"]
        }
        
    def validate_schema(self, data: Dict[str, Any]) -> bool:
        """Validate REST request/response schema."""
        required_fields = {
            "request": ["url"],
            "response": ["status_code", "headers", "body"]
        }
        
        for field in required_fields["request"]:
            if field not in data:
                return False
        return True

class GRPCAdapter(ProtocolAdapter):
    """Adapter for gRPC protocol."""
    
    def translate_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Translate request to gRPC format."""
        return {
            "service": request["service"],
            "method": request["method"],
            "request": request["request"]
        }
        
    def translate_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Translate response from gRPC format."""
        return {
            "response": response["response"],
            "status_code": response.get("status_code", 0)
        }
        
    def validate_schema(self, data: Dict[str, Any]) -> bool:
        """Validate gRPC request/response schema."""
        required_fields = {
            "request": ["service", "method", "request"],
            "response": ["response", "status_code"]
        }
        
        for field in required_fields["request"]:
            if field not in data:
                return False
        return True

class TranslationManager:
    """
    Manages protocol translation and data transformation.
    
    The TranslationManager provides services for converting data between different
    protocols and ensuring proper schema validation and transformation.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the TranslationManager.
        
        Args:
            config: Configuration dictionary for the manager
        """
        self.config = config
        self.protocol_adapters: Dict[Protocol, ProtocolAdapter] = {}
        self.schema_registry: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
        
        # Register default adapters
        self.register_protocol_adapter(Protocol.REST, RESTAdapter)
        self.register_protocol_adapter(Protocol.GRPC, GRPCAdapter)
    
    def register_protocol_adapter(self, protocol: Protocol, adapter_class: Type[ProtocolAdapter]):
        """
        Register a protocol adapter.
        
        Args:
            protocol: The protocol to register
            adapter_class: The adapter class to use
        """
        if protocol in self.protocol_adapters:
            raise ValueError(f"Adapter for protocol {protocol} already registered")
            
        self.protocol_adapters[protocol] = adapter_class(protocol)
        self.logger.info(f"Registered adapter for protocol {protocol}")
    
    def register_schema(self, schema_name: str, schema: Dict[str, Any]):
        """
        Register a data schema.
        
        Args:
            schema_name: The name of the schema
            schema: The schema definition
        """
        self.schema_registry[schema_name] = schema
        self.logger.info(f"Registered schema: {schema_name}")
    
    def validate_schema(self, data: Dict[str, Any], schema_name: str) -> bool:
        """
        Validate data against a registered schema.
        
        Args:
            data: The data to validate
            schema_name: The name of the schema to use
            
        Returns:
            True if the data is valid, False otherwise
        """
        schema = self.schema_registry.get(schema_name)
        if not schema:
            raise ValueError(f"Schema {schema_name} not found")
            
        # Basic schema validation
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in data:
                return False
                
        return True
    
    async def translate_request(self, 
                              request: Dict[str, Any],
                              target_protocol: Protocol,
                              source_protocol: Optional[Protocol] = None) -> Dict[str, Any]:
        """
        Translate a request to the target protocol.
        
        Args:
            request: The request to translate
            target_protocol: The protocol to translate to
            source_protocol: The protocol to translate from (optional)
            
        Returns:
            The translated request
            
        Raises:
            TranslationError: If translation fails
        """
        try:
            # Get the target adapter
            target_adapter = self.protocol_adapters.get(target_protocol)
            if not target_adapter:
                raise TranslationError(f"No adapter registered for protocol {target_protocol}")
                
            # Translate the request
            translated = target_adapter.translate_request(request)
            
            # Validate the result
            if not target_adapter.validate_schema(translated):
                raise TranslationError("Translated request does not match protocol schema")
                
            return translated
            
        except Exception as e:
            self.logger.error(f"Error translating request: {e}", exc_info=True)
            raise TranslationError(f"Failed to translate request: {str(e)}")
    
    async def translate_response(self, 
                               response: Dict[str, Any],
                               target_protocol: Protocol,
                               source_protocol: Optional[Protocol] = None) -> Dict[str, Any]:
        """
        Translate a response from the target protocol.
        
        Args:
            response: The response to translate
            target_protocol: The protocol to translate to
            source_protocol: The protocol to translate from (optional)
            
        Returns:
            The translated response
            
        Raises:
            TranslationError: If translation fails
        """
        try:
            # Get the target adapter
            target_adapter = self.protocol_adapters.get(target_protocol)
            if not target_adapter:
                raise TranslationError(f"No adapter registered for protocol {target_protocol}")
                
            # Translate the response
            translated = target_adapter.translate_response(response)
            
            # Validate the result
            if not target_adapter.validate_schema(translated):
                raise TranslationError("Translated response does not match protocol schema")
                
            return translated
            
        except Exception as e:
            self.logger.error(f"Error translating response: {e}", exc_info=True)
            raise TranslationError(f"Failed to translate response: {str(e)}")
    
    async def transform_data(self, 
                           data: Dict[str, Any],
                           schema_name: str,
                           target_schema: Optional[str] = None) -> Dict[str, Any]:
        """
        Transform data between schemas.
        
        Args:
            data: The data to transform
            schema_name: The source schema name
            target_schema: The target schema name (optional)
            
        Returns:
            The transformed data
            
        Raises:
            TranslationError: If transformation fails
        """
        try:
            # Validate input schema
            if not self.validate_schema(data, schema_name):
                raise TranslationError(f"Data does not match schema {schema_name}")
                
            # Get source schema
            source_schema = self.schema_registry.get(schema_name)
            if not source_schema:
                raise TranslationError(f"Schema {schema_name} not found")
                
            # If no target schema specified, return validated data
            if not target_schema:
                return data
                
            # Get target schema
            target_schema = self.schema_registry.get(target_schema)
            if not target_schema:
                raise TranslationError(f"Target schema {target_schema} not found")
                
            # Perform schema transformation
            transformed = {}
            for field, mapping in target_schema["fields"].items():
                source_field = mapping.get("source_field", field)
                if source_field in data:
                    transformed[field] = data[source_field]
                    
            # Validate transformed data
            if not self.validate_schema(transformed, target_schema):
                raise TranslationError("Transformed data does not match target schema")
                
            return transformed
            
        except Exception as e:
            self.logger.error(f"Error transforming data: {e}", exc_info=True)
            raise TranslationError(f"Failed to transform data: {str(e)}")
