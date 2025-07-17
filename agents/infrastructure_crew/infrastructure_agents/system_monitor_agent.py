import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional

from redis.asyncio import Redis as AsyncRedis

from ...common.base_agent import BaseAgent, AgentConfig
from ..schemas.event_schemas import (
    BaseEvent,
    SystemOverallHealthPayload,
    SystemHealthBroadcastEvent,
    ResourceAlertPayload,
    ResourceAlertEvent,
    ResourceAlertType,
    ServicePerformanceWarningPayload,
    ServicePerformanceWarningEvent,
    EventPriority
)

logger = logging.getLogger(__name__)

class SystemMonitorAgentConfig(AgentConfig):
    monitoring_interval_seconds: int = 60
    health_broadcast_channel: str = "system:health:broadcast"
    resource_alert_channel: str = "system:resource:alerts"
    service_warning_channel: str = "system:service:warnings"
    # Thresholds for alerts/warnings (examples, can be expanded)
    cpu_threshold_percent: Optional[float] = 85.0
    memory_threshold_percent: Optional[float] = 85.0 # Assuming memory_usage_mb is a % of total
    error_rate_threshold_percent: Optional[float] = 5.0
    avg_processing_time_threshold_ms: Optional[float] = 1000.0

class SystemMonitorAgent(BaseAgent):
    def __init__(self, 
                 agent_id: str, 
                 crew_manager_metrics_getter: callable, # Function to get CrewManager's metrics dict
                 redis_pool: AsyncRedis,
                 config: Optional[SystemMonitorAgentConfig] = None):
        super().__init__(agent_id, config or SystemMonitorAgentConfig())
        self.crew_manager_metrics_getter = crew_manager_metrics_getter
        self.redis_pool = redis_pool
        self.config: SystemMonitorAgentConfig = self.config # Type hint for convenience
        self._monitor_task: Optional[asyncio.Task] = None
        self.initialized = False

    async def initialize(self):
        if not self.redis_pool:
            logger.error(f"[{self.agent_id}] Redis pool not provided. Cannot initialize.")
            return
        logger.info(f"[{self.agent_id}] SystemMonitorAgent initializing with config: {self.config.dict()}")
        self.initialized = True
        logger.info(f"[{self.agent_id}] SystemMonitorAgent initialized.")

    async def start(self):
        if not self.initialized:
            logger.warning(f"[{self.agent_id}] Agent not initialized. Call initialize() first.")
            await self.initialize()
            if not self.initialized: # Check again after trying to initialize
                 logger.error(f"[{self.agent_id}] Initialization failed. Cannot start monitoring task.")
                 return

        if self._monitor_task is None or self._monitor_task.done():
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            logger.info(f"[{self.agent_id}] System monitoring task started.")
        else:
            logger.info(f"[{self.agent_id}] System monitoring task already running.")

    async def _monitor_loop(self):
        while True:
            try:
                await self._collect_and_broadcast_health()
            except asyncio.CancelledError:
                logger.info(f"[{self.agent_id}] Monitoring loop cancelled.")
                break
            except Exception as e:
                logger.error(f"[{self.agent_id}] Error in monitoring loop: {e}", exc_info=True)
            await asyncio.sleep(self.config.monitoring_interval_seconds)

    async def _collect_and_broadcast_health(self):
        logger.debug(f"[{self.agent_id}] Collecting system health metrics.")
        crew_metrics = self.crew_manager_metrics_getter()
        if not crew_metrics:
            logger.warning(f"[{self.agent_id}] Could not retrieve metrics from CrewManager.")
            return

        # 1. SystemOverallHealthPayload
        # Assuming crew_metrics has the necessary fields or defaults
        overall_status = "healthy" # Basic default, logic can be added to determine this
        error_rate = (crew_metrics.get("error_count", 0) / crew_metrics.get("event_count", 1)) * 100 if crew_metrics.get("event_count", 0) > 0 else 0
        avg_processing_time_list = crew_metrics.get("processing_time", [])
        avg_processing_time = sum(avg_processing_time_list) / len(avg_processing_time_list) * 1000 if avg_processing_time_list else 0

        # Placeholder for actual CPU/Memory - these often need OS-level access or dedicated libraries
        # For now, using what might be in crew_metrics or placeholders
        memory_usage_mb = crew_metrics.get("memory_usage", {}).get("total_mb", 0.0) 
        # cpu_utilization_percentage = psutil.cpu_percent() # Example if psutil was used

        health_payload = SystemOverallHealthPayload(
            overall_status=overall_status,
            active_services=crew_metrics.get("services_registered_total", 0),
            total_events_processed=crew_metrics.get("event_count", 0),
            error_rate_percentage=error_rate,
            avg_processing_time_ms=avg_processing_time,
            redis_connection_status="connected" if crew_metrics.get("redis_connections", 0) > 0 else "disconnected",
            memory_usage_mb=memory_usage_mb,
            # cpu_utilization_percentage=cpu_utilization_percentage, # If available
            detailed_metrics=crew_metrics 
        )
        health_event = SystemHealthBroadcastEvent(payload=health_payload)
        await self._publish_event(self.config.health_broadcast_channel, health_event)

        # 2. ResourceAlertEvent (Example for high error rate)
        if self.config.error_rate_threshold_percent is not None and error_rate > self.config.error_rate_threshold_percent:
            alert_payload = ResourceAlertPayload(
                alert_type=ResourceAlertType.SERVICE_DEGRADATION, # Placeholder, needs a better type
                message=f"System error rate {error_rate:.2f}% exceeds threshold of {self.config.error_rate_threshold_percent}%.",
                current_value=error_rate,
                threshold_value=self.config.error_rate_threshold_percent,
                severity=4
            )
            alert_event = ResourceAlertEvent(payload=alert_payload, priority=EventPriority.HIGH)
            await self._publish_event(self.config.resource_alert_channel, alert_event)
        
        # Add more checks for other ResourceAlerts (CPU, Memory if available) and ServicePerformanceWarnings

    async def _publish_event(self, channel: str, event_data: BaseEvent):
        try:
            message = event_data.json() # Pydantic models have .json() method
            await self.redis_pool.publish(channel, message)
            logger.debug(f"[{self.agent_id}] Published event to {channel}: {event_data.event_type}")
        except Exception as e:
            logger.error(f"[{self.agent_id}] Failed to publish event to {channel}: {e}", exc_info=True)

    async def stop(self):
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                logger.info(f"[{self.agent_id}] Monitoring task successfully cancelled.")
            except Exception as e:
                 logger.error(f"[{self.agent_id}] Error during monitoring task cancellation: {e}", exc_info=True)
            self._monitor_task = None
        self.initialized = False
        logger.info(f"[{self.agent_id}] SystemMonitorAgent stopped.")

    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "initialized": self.initialized,
            "monitoring_task_running": self._monitor_task is not None and not self._monitor_task.done(),
            "config": self.config.dict()
        }
