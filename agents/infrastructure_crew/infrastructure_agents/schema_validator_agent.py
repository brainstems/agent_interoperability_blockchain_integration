import logging
from typing import Dict, Any, Optional, Type, Tuple

from pydantic import BaseModel, ValidationError

from .base_agent import InfrastructureBaseAgent
from ..schemas import (
    BaseEvent, CriticalEvent, DataChangeEvent, ServiceStatusChangeEvent,
    ServiceInfo, ServiceRegistrationRequest # Add other relevant schemas if needed
)

logger = logging.getLogger(__name__)

class SchemaValidatorAgent(InfrastructureBaseAgent):
    """Validates event and service data against predefined Pydantic schemas."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.agent_id = config.get("agent_id", "schema_validator_agent") if config else "schema_validator_agent"
        self._schema_map: Dict[str, Type[BaseModel]] = {}
        self._event_type_to_schema: Dict[str, Type[BaseModel]] = {}

    async def initialize(self, **kwargs) -> bool:
        await super().initialize(**kwargs)
        self.logger.info(f"Initializing {self.agent_id}...")
        self._load_known_schemas()
        self.initialized = True
        self.logger.info(f"{self.agent_id} initialized with {len(self._schema_map)} schemas and {len(self._event_type_to_schema)} event type mappings.")
        return True

    def _load_known_schemas(self):
        """Loads all known schemas into a map for quick lookup."""
        # Manually map schema names/IDs to their Pydantic models
        # In a more advanced system, these could be dynamically discovered or registered
        schemas_to_load = {
            "BaseEvent": BaseEvent,
            "CriticalEvent": CriticalEvent,
            "DataChangeEvent": DataChangeEvent,
            "ServiceStatusChangeEvent": ServiceStatusChangeEvent,
            "ServiceInfo": ServiceInfo,
            "ServiceRegistrationRequest": ServiceRegistrationRequest,
            # Payloads can also be registered if direct validation is needed
            "CriticalEventPayload": CriticalEvent._field_defaults['payload'], # Accessing the type hint
            "DataChangeEventPayload": DataChangeEvent._field_defaults['payload'],
            "ServiceStatusChangeEventPayload": ServiceStatusChangeEvent._field_defaults['payload'],
        }

        for name, schema_model in schemas_to_load.items():
            if isinstance(schema_model, type) and issubclass(schema_model, BaseModel):
                self.register_schema(name, schema_model)
            else:
                 # For payload types that are not directly BaseModel subclasses but are type hints
                 # This part is a bit tricky as _field_defaults might not give a direct type for validation
                 # For now, we'll focus on validating the main event models.
                 # A more robust way would be to ensure payload models are also registered if needed.
                 self.logger.debug(f"Schema {name} is a payload type, direct registration might differ.")

        # Map event types to their specific event models for convenience
        self.register_event_type_schema("system.critical_alert", CriticalEvent)
        self.register_event_type_schema("data.changed", DataChangeEvent)
        self.register_event_type_schema("service.status_changed", ServiceStatusChangeEvent)
        # BaseEvent can be a fallback or for generic event types not specifically mapped

    def register_schema(self, schema_id: str, schema_model: Type[BaseModel]):
        """Registers a Pydantic model with a given schema ID."""
        if schema_id in self._schema_map:
            self.logger.warning(f"Schema ID '{schema_id}' already registered. Overwriting.")
        self._schema_map[schema_id] = schema_model
        self.logger.info(f"Registered schema '{schema_id}' for model {schema_model.__name__}.")

    def register_event_type_schema(self, event_type: str, schema_model: Type[BaseEvent]):
        """Maps an event_type string to its corresponding Pydantic event model."""
        if event_type in self._event_type_to_schema:
            self.logger.warning(f"Event type '{event_type}' already mapped. Overwriting.")
        self._event_type_to_schema[event_type] = schema_model
        self.logger.info(f"Mapped event type '{event_type}' to schema {schema_model.__name__}.")

    def get_schema_by_id(self, schema_id: str) -> Optional[Type[BaseModel]]:
        return self._schema_map.get(schema_id)

    def get_schema_by_event_type(self, event_type: str) -> Optional[Type[BaseEvent]]:
        return self._event_type_to_schema.get(event_type)

    def validate_data(self, data: Dict[str, Any], schema_identifier: str, is_event_type: bool = False) -> Tuple[bool, Optional[BaseModel], Optional[str]]:
        """
        Validates data against a schema specified by its ID or event type.

        Args:
            data: The data dictionary to validate.
            schema_identifier: The schema ID or event_type string.
            is_event_type: If True, schema_identifier is treated as an event_type.

        Returns:
            A tuple: (is_valid, validated_model_instance, error_message)
        """
        schema_model: Optional[Type[BaseModel]] = None
        if is_event_type:
            schema_model = self.get_schema_by_event_type(schema_identifier)
            if not schema_model:
                 # Fallback to BaseEvent if specific event type not found, but this might be too permissive
                 # schema_model = self._schema_map.get("BaseEvent") 
                 return False, None, f"No schema mapped for event type '{schema_identifier}'."
        else:
            schema_model = self.get_schema_by_id(schema_identifier)
            if not schema_model:
                return False, None, f"Schema ID '{schema_identifier}' not found."

        try:
            validated_model = schema_model(**data)
            return True, validated_model, None
        except ValidationError as e:
            self.logger.warning(f"Validation failed for schema '{schema_identifier}': {e}")
            return False, None, str(e)
        except Exception as e:
            self.logger.error(f"Unexpected error during validation for schema '{schema_identifier}': {e}", exc_info=True)
            return False, None, f"Unexpected error: {str(e)}"

    async def start(self):
        await super().start()
        self.logger.info(f"{self.agent_id} started.")

    async def stop(self):
        self.logger.info(f"Stopping {self.agent_id}...")
        # No specific resources to release for this agent in its current form
        await super().stop()
        self.logger.info(f"{self.agent_id} stopped.")

# Example Usage (for testing)
async def example_run():
    validator_agent = SchemaValidatorAgent(config={})
    await validator_agent.initialize()

    # Example 1: Validate a known event type
    good_critical_data = {
        "event_type": "system.critical_alert", # This is part of the model, but often comes with the raw data
        "source_service_id": "service_abc",
        "payload": {
            "message": "CPU overload!",
            "severity": 5
        }
    }
    is_valid, model, error = validator_agent.validate_data(good_critical_data, "system.critical_alert", is_event_type=True)
    if is_valid and model:
        validator_agent.logger.info(f"CriticalEvent valid: True, Model: {model.model_dump_json(indent=2)}")
    else:
        validator_agent.logger.error(f"CriticalEvent valid: False, Error: {error}")

    bad_critical_data = {
        "event_type": "system.critical_alert",
        "payload": {
            "message": "CPU overload!",
            "severity": "very_high" # Invalid type for severity
        }
    }
    is_valid, model, error = validator_agent.validate_data(bad_critical_data, "system.critical_alert", is_event_type=True)
    validator_agent.logger.info(f"Bad CriticalEvent valid: {is_valid}, Error: {error}")

    # Example 2: Validate against a schema ID (e.g., ServiceInfo)
    good_service_data = {
        "service_name": "TestService",
        "crew_id": "test_crew",
        "capabilities": ["do_stuff"],
        "endpoints": [{"type": "http_api", "address": "http://localhost/test"}]
    }
    is_valid, model, error = validator_agent.validate_data(good_service_data, "ServiceInfo")
    if is_valid and model:
        validator_agent.logger.info(f"ServiceInfo valid: True, Model: {model.model_dump_json(indent=2)}")
    else:
        validator_agent.logger.error(f"ServiceInfo valid: False, Error: {error}")

    await validator_agent.stop()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    import asyncio
    asyncio.run(example_run())
