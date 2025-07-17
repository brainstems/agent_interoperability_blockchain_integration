import asyncio
import json
import logging
from typing import Optional, Dict, Any

from redis.asyncio import Redis as AsyncRedis
from pydantic import ValidationError

from agents.infrastructure_crew.common.base_agent import BaseAgent, AgentConfig
# Adjust import path for event_schemas, assuming it's accessible from the new location
# This might need to be agents.infrastructure_crew.schemas.event_schemas
# For now, let's try the original path and see if Python's path resolution handles it, 
# or if we need to make it more absolute (e.g. from ..infrastructure_crew...)
# Given the current structure, a direct import from infrastructure_crew should work if 'agents' is in PYTHONPATH
from agents.infrastructure_crew.schemas.event_schemas import (
    SystemHealthBroadcastEvent,
    ResourceAlertEvent,
    ServicePerformanceWarningEvent,
    ResourceAlertType
)

logger = logging.getLogger(__name__)

class ExampleAdaptiveAgentConfig(AgentConfig):
    health_broadcast_channel: str = "system:health:broadcast"
    resource_alert_channel: str = "system:resource:alerts"
    service_warning_channel: str = "system:service:warnings"
    performance_threshold_cpu: float = 75.0

class ExampleAdaptiveAgent(BaseAgent):
    def __init__(self, 
                 agent_id: str, 
                 redis_pool: AsyncRedis,
                 config: Optional[ExampleAdaptiveAgentConfig] = None):
        super().__init__(agent_id, config or ExampleAdaptiveAgentConfig())
        self.redis_pool = redis_pool
        self.config: ExampleAdaptiveAgentConfig = self.config
        self._subscriber_task: Optional[asyncio.Task] = None
        self.initialized = False
        self.current_operational_intensity = 1.0
        self.current_strategy = "normal"

    async def initialize(self):
        if not self.redis_pool:
            logger.error(f"[{self.agent_id}] Redis pool not provided. Cannot initialize.")
            return
        logger.info(f"[{self.agent_id}] ExampleAdaptiveAgent initializing with config: {self.config.dict()}")
        self.initialized = True
        logger.info(f"[{self.agent_id}] ExampleAdaptiveAgent initialized.")

    async def start(self):
        if not self.initialized:
            logger.warning(f"[{self.agent_id}] Agent not initialized. Call initialize() first.")
            await self.initialize()
            if not self.initialized:
                 logger.error(f"[{self.agent_id}] Initialization failed. Cannot start subscriber task.")
                 return

        if self._subscriber_task is None or self._subscriber_task.done():
            self._subscriber_task = asyncio.create_task(self._redis_subscriber_loop())
            logger.info(f"[{self.agent_id}] Redis subscriber task started.")
        else:
            logger.info(f"[{self.agent_id}] Redis subscriber task already running.")

    async def _redis_subscriber_loop(self):
        pubsub = self.redis_pool.pubsub()
        channels_to_subscribe = {
            self.config.health_broadcast_channel: self._handle_health_message,
            self.config.resource_alert_channel: self._handle_resource_alert_message,
            self.config.service_warning_channel: self._handle_service_warning_message
        }
        await pubsub.subscribe(*channels_to_subscribe.keys())
        logger.info(f"[{self.agent_id}] Subscribed to Redis channels: {list(channels_to_subscribe.keys())}")

        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "message":
                    channel = message['channel'].decode('utf-8')
                    data = message['data'].decode('utf-8')
                    logger.debug(f"[{self.agent_id}] Received message on {channel}")
                    handler = channels_to_subscribe.get(channel)
                    if handler:
                        await handler(data)
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            logger.info(f"[{self.agent_id}] Redis subscriber loop cancelled.")
        except aioredis.RedisError as e:
            logger.error(f"[{self.agent_id}] Redis error in subscriber loop: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"[{self.agent_id}] Unexpected error in subscriber loop: {e}", exc_info=True)
        finally:
            logger.info(f"[{self.agent_id}] Unsubscribing from Redis channels.")
            await pubsub.unsubscribe(*channels_to_subscribe.keys())
            await pubsub.close()

    async def _handle_health_message(self, data: str):
        try:
            event = SystemHealthBroadcastEvent.parse_raw(data)
            logger.info(f"[{self.agent_id}] Received System Health: CPU {event.payload.cpu_utilization_percentage}%")
            if event.payload.cpu_utilization_percentage and \
               event.payload.cpu_utilization_percentage > self.config.performance_threshold_cpu:
                if self.current_operational_intensity > 0.5:
                    logger.warning(f"[{self.agent_id}] High CPU. Throttling.")
                    await self._throttle_operations(0.5)
            elif self.current_operational_intensity < 1.0:
                logger.info(f"[{self.agent_id}] CPU normal. Restoring operations.")
                await self._throttle_operations(1.0)
        except (ValidationError, json.JSONDecodeError) as e:
            logger.error(f"[{self.agent_id}] Error parsing SystemHealthBroadcastEvent: {e}")

    async def _handle_resource_alert_message(self, data: str):
        try:
            event = ResourceAlertEvent.parse_raw(data)
            logger.warning(f"[{self.agent_id}] Resource Alert: {event.payload.alert_type.value} - {event.payload.message}")
            if event.payload.alert_type == ResourceAlertType.REDIS_UNAVAILABLE:
                if self.current_strategy != "fallback_mode_no_redis":
                    await self._switch_strategy("fallback_mode_no_redis")
            elif self.current_strategy == "fallback_mode_no_redis" and event.payload.alert_type != ResourceAlertType.REDIS_UNAVAILABLE:
                 logger.info(f"[{self.agent_id}] Reverting to normal strategy.")
                 await self._switch_strategy("normal")
        except (ValidationError, json.JSONDecodeError) as e:
            logger.error(f"[{self.agent_id}] Error parsing ResourceAlertEvent: {e}")

    async def _handle_service_warning_message(self, data: str):
        try:
            event = ServicePerformanceWarningEvent.parse_raw(data)
            logger.warning(f"[{self.agent_id}] Service Warning for {event.payload.service_id}: {event.payload.metric_name} is {event.payload.current_value}")
        except (ValidationError, json.JSONDecodeError) as e:
            logger.error(f"[{self.agent_id}] Error parsing ServicePerformanceWarningEvent: {e}")

    async def _throttle_operations(self, intensity: float):
        self.current_operational_intensity = max(0.1, min(1.0, intensity))
        logger.info(f"[{self.agent_id}] Operational intensity: {self.current_operational_intensity * 100}%")

    async def _switch_strategy(self, new_strategy: str):
        if self.current_strategy != new_strategy:
            self.current_strategy = new_strategy
            logger.info(f"[{self.agent_id}] Strategy: {self.current_strategy}")
            if new_strategy == "fallback_mode_no_redis":
                logger.warning(f"[{self.agent_id}] Fallback: Redis unavailable.")
            elif new_strategy == "normal":
                logger.info(f"[{self.agent_id}] Normal strategy restored.")
        else:
            logger.debug(f"[{self.agent_id}] Already in strategy: {new_strategy}")

    async def stop(self):
        if self._subscriber_task:
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                logger.info(f"[{self.agent_id}] Subscriber task cancelled.")
            self._subscriber_task = None
        self.initialized = False
        logger.info(f"[{self.agent_id}] ExampleAdaptiveAgent stopped.")

    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "initialized": self.initialized,
            "subscriber_task_running": self._subscriber_task is not None and not self._subscriber_task.done(),
            "config": self.config.dict(),
            "current_operational_intensity": self.current_operational_intensity,
            "current_strategy": self.current_strategy
        }
