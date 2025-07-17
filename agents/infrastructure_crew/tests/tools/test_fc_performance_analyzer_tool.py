import unittest
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

from agents.infrastructure_crew.tools.fc_performance_analyzer_tool import (
    FCPerformanceAnalyzerTool,
    FCPerformanceAnalyzerToolInput,
    EventType,
    PerformanceAnalysisReport,
    PerformanceMetrics,
    TaskPerformance,
    AgentPerformance,
    ToolPerformance
)

class TestFCPerformanceAnalyzerTool(unittest.TestCase):
    def setUp(self):
        self.tool = FCPerformanceAnalyzerTool()
        # Basic thresholds for testing
        self.default_thresholds = {
            'task_duration_threshold_sec': 60.0,
            'agent_error_rate_threshold_pct': 20.0,
            'agent_avg_duration_threshold_sec': 30.0,
            'agent_total_runtime_share_threshold_pct': 70.0,
            'tool_error_rate_threshold_pct': 15.0,
            'tool_avg_duration_threshold_sec': 20.0,
        }

    def test_initialization(self):
        """Test that the tool initializes correctly."""
        self.assertIsNotNone(self.tool)
        self.assertEqual(self.tool.name, "functional_crew_performance_analyzer")


    def test_parse_simple_valid_events(self):
        """Test parsing a simple valid event string and check basic metrics."""
        crew_start_time = datetime(2023, 1, 1, 10, 0, 0)
        crew_end_time = datetime(2023, 1, 1, 10, 0, 10) # 10 seconds duration

        events_list = [
            {
                "event_type": EventType.CREW_EXECUTION_STARTED.value,
                "timestamp": crew_start_time.isoformat(),
                "crew_id": "test_crew_001"
            },
            {
                "event_type": EventType.CREW_EXECUTION_FINISHED.value,
                "timestamp": crew_end_time.isoformat(),
                "crew_id": "test_crew_001",
                "final_result": "Task completed successfully."
            }
        ]
        events_string = json.dumps(events_list)
        original_task_description = "Test simple crew execution."

        report_str = self.tool._run(
            events_string=events_string,
            original_task_description=original_task_description,
            **self.default_thresholds
        )
        
        self.assertIsInstance(report_str, str)
        report_dict = json.loads(report_str)

        self.assertIn("metrics", report_dict)
        metrics = report_dict["metrics"]
        self.assertEqual(metrics["total_events_processed"], 2)
        self.assertAlmostEqual(metrics["crew_run_duration_seconds"], 10.0, places=2)
        self.assertEqual(metrics["total_tasks_identified"], 0) # No explicit task events
        self.assertEqual(metrics["total_agents_involved"], 0)
        self.assertEqual(metrics["total_tool_calls"], 0)
        self.assertEqual(report_dict["original_task_description"], original_task_description)

if __name__ == '__main__':
    unittest.main()
