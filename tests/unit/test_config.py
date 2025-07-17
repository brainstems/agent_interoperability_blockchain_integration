"""
Test configuration for the infrastructure crew.
"""

import os
from typing import Dict, Any

# Test configuration
TEST_CONFIG = {
    "redis": {
        "url": "redis://localhost:6379/0",
        "max_connections": 10,
        "timeout": 5
    },
    "crew_manager": {
        "redis_url": "redis://localhost:6379/0",
        "redis_max_connections": 10,
        "redis_timeout": 5
    },
    "memory": {
        "low_threshold": 0.7,
        "medium_threshold": 0.8,
        "high_threshold": 0.9,
        "critical_threshold": 0.95,
        "monitor_interval": 1,
        "cleanup_interval": 2,
        "redis_url": "redis://localhost:6379/0"
    },
    "team_memory": {
        "default_quota": 0.1,
        "high_priority_quota": 0.2,
        "low_priority_quota": 0.05,
        "sharing_policy": "round_robin",
        "monitor_interval": 1
    },
    "test_teams": [
        {
            "id": "test_team_1",
            "priority": "high",
            "initial_quota": 0.15
        },
        {
            "id": "test_team_2",
            "priority": "default",
            "initial_quota": 0.1
        },
        {
            "id": "test_team_3",
            "priority": "low",
            "initial_quota": 0.05
        }
    ]
}

# Test environment variables
os.environ["TEST_REDIS_URL"] = TEST_CONFIG["redis"]["url"]
os.environ["TEST_MEMORY_LOW_THRESHOLD"] = str(TEST_CONFIG["memory"]["low_threshold"])
