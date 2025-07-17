from pydantic.v1 import BaseModel as PydanticV1BaseModel, Field as PydanticV1Field
from typing import Optional, List, Dict, Any
import json

# Adjust the import path if your project structure is different
from agents.infrastructure_crew.tools.fc_performance_analyzer_tool import PerformanceAnalysisReport, TaskPerformance, AgentPerformance, ToolPerformance

class RedTeamChallenge(PydanticV1BaseModel):
    """Defines the structure for a challenge formulated by the Red Team Agent."""
    challenge_type: str = PydanticV1Field(description="Type of challenge (e.g., TaskDuration, TaskError, EfficiencyObservation, PotentialBottleneck).")
    target_id: Optional[str] = PydanticV1Field(None, description="Identifier of the target (e.g., task_id, agent_role, tool_name, or general observation type).")
    description: str = PydanticV1Field(description="Detailed description of the challenge or observation.")
    suggested_scrutiny_focus: str = PydanticV1Field(description="Specific areas, questions, or metrics to focus on during scrutiny.")
    severity: str = PydanticV1Field("Medium", description="Severity of the challenge (e.g., Low, Medium, High).")
    # Future potential fields:
    # - expected_crew_response_format: str
    # - evidence_required_for_closure: str

class RedTeamAgent:
    """Agent responsible for analyzing Functional Crew performance reports and formulating challenges."""
    def __init__(self, 
                 high_task_duration_threshold_sec: float = 120.0, 
                 medium_task_duration_threshold_sec: float = 60.0,
                 agent_error_rate_threshold_pct: float = 10.0,
                 agent_avg_action_duration_threshold_sec: float = 30.0,
                 tool_error_rate_threshold_pct: float = 15.0,
                 tool_avg_duration_threshold_sec: float = 45.0):
        """
        Initializes the Red Team Agent.
        Args:
            high_task_duration_threshold_sec: Threshold for flagging tasks with high duration.
            medium_task_duration_threshold_sec: Threshold for flagging tasks with medium duration.
            agent_error_rate_threshold_pct: Threshold for flagging agents with high error rates.
            agent_avg_action_duration_threshold_sec: Threshold for flagging agents with high average action durations.
            tool_error_rate_threshold_pct: Threshold for flagging tools with high error rates.
            tool_avg_duration_threshold_sec: Threshold for flagging tools with high average durations.
        """
        self.high_task_duration_threshold_sec = high_task_duration_threshold_sec
        self.medium_task_duration_threshold_sec = medium_task_duration_threshold_sec
        self.agent_error_rate_threshold_pct = agent_error_rate_threshold_pct
        self.agent_avg_action_duration_threshold_sec = agent_avg_action_duration_threshold_sec
        self.tool_error_rate_threshold_pct = tool_error_rate_threshold_pct
        self.tool_avg_duration_threshold_sec = tool_avg_duration_threshold_sec

    def _parse_report(self, report_json_string: str) -> PerformanceAnalysisReport:
        """Parses the JSON report string into a PerformanceAnalysisReport object."""
        try:
            report_dict = json.loads(report_json_string)
            # Pydantic V1 models can be created from dictionaries. 
            # Datetime fields in PerformanceAnalysisReport are handled by Pydantic's parsing.
            return PerformanceAnalysisReport(**report_dict)
        except json.JSONDecodeError as e:
            # Handle JSON parsing errors, perhaps by raising a custom exception or returning None
            print(f"Error decoding performance report JSON: {e}")
            raise ValueError(f"Invalid JSON format for performance report: {e}")
        except Exception as e:
            # Handle other Pydantic validation errors or unexpected issues
            print(f"Error creating PerformanceAnalysisReport from dict: {e}")
            raise ValueError(f"Error instantiating performance report: {e}")

    def formulate_challenges(self, report: PerformanceAnalysisReport) -> List[RedTeamChallenge]:
        """Analyzes the performance report and formulates challenges for the crew."""
        challenges: List[RedTeamChallenge] = []

        # 1. Challenge long-running tasks
        for task in report.task_breakdown:
            if task.duration_seconds is not None:
                severity = None
                if task.duration_seconds > self.high_task_duration_threshold_sec:
                    severity = "High"
                elif task.duration_seconds > self.medium_task_duration_threshold_sec:
                    severity = "Medium"
                
                if severity:
                    challenges.append(
                        RedTeamChallenge(
                            challenge_type="TaskDuration",
                            target_id=task.task_id or task.task_description,
                            description=f"Task '{task.task_id or task.task_description}' took {task.duration_seconds:.2f}s.",
                            suggested_scrutiny_focus="Investigate reasons for extended duration: task complexity, agent loops, inefficient tool usage, external dependencies, or resource contention. Compare with expected duration.",
                            severity=severity
                        )
                    )

        # 2. Challenge tasks with errors
        for task in report.task_breakdown:
            if task.errors_associated:
                challenges.append(
                    RedTeamChallenge(
                        challenge_type="TaskError",
                        target_id=task.task_id or task.task_description,
                        description=f"Task '{task.task_id or task.task_description}' reported {len(task.errors_associated)} associated errors.",
                        suggested_scrutiny_focus=f"Review error details: {'; '.join(task.errors_associated)}. Identify root causes, impact on task outcome, and preventative measures.",
                        severity="High"
                    )
                )
        
        # 3. Challenge based on identified errors in the general report
        for error_event in report.identified_errors:
            challenges.append(
                RedTeamChallenge(
                    challenge_type="GeneralError",
                    target_id=error_event.get('event_type', 'Unknown Event'),
                    description=f"An error was reported: {error_event.get('message', 'No message')}. Context: {error_event}",
                    suggested_scrutiny_focus="Investigate the cause and impact of this error. Was it handled gracefully? Did it affect the outcome?",
                    severity="High"
                )
            )

        # 4. Challenge based on overall efficiency observations
        for observation in report.efficiency_observations:
            challenges.append(
                RedTeamChallenge(
                    challenge_type="EfficiencyObservation",
                    target_id="OverallProcess",
                    description=f"Efficiency Observation: {observation}",
                    suggested_scrutiny_focus="Validate this observation. If confirmed, explore potential process improvements, tool optimizations, or agent behavior adjustments.",
                    severity="Medium"
                )
            )
            
        # 5. Challenge based on identified potential bottlenecks
        for bottleneck in report.potential_bottlenecks:
            challenges.append(
                RedTeamChallenge(
                    challenge_type="PotentialBottleneck",
                    target_id="OverallProcess", # Or more specific if bottleneck info allows
                    description=f"Identified Potential Bottleneck: {bottleneck}",
                    suggested_scrutiny_focus="Investigate this potential bottleneck. Confirm its existence and impact. Identify mitigation strategies or alternative approaches.",
                    severity="High"
                )
            )
        
        # 6. Challenge based on agent performance
        for agent_perf in report.agent_performance_summary:
            if agent_perf.error_rate_percentage is not None and agent_perf.error_rate_percentage > self.agent_error_rate_threshold_pct:
                challenges.append(
                    RedTeamChallenge(
                        challenge_type="AgentPerformanceIssue",
                        target_id=agent_perf.agent_role,
                        description=f"Agent '{agent_perf.agent_role}' has a high error rate of {agent_perf.error_rate_percentage:.2f}% (Threshold: >{self.agent_error_rate_threshold_pct:.2f}%).",
                        suggested_scrutiny_focus=f"Investigate the reasons for {agent_perf.agent_role}'s high error rate. Review associated errors, task complexity, tool interactions, or potential misunderstandings of instructions.",
                        severity="High"
                    )
                )
            
            if agent_perf.avg_duration_seconds is not None and agent_perf.avg_duration_seconds > self.agent_avg_action_duration_threshold_sec:
                challenges.append(
                    RedTeamChallenge(
                        challenge_type="AgentPerformanceIssue",
                        target_id=agent_perf.agent_role,
                        description=f"Agent '{agent_perf.agent_role}' has a high average action duration of {agent_perf.avg_duration_seconds:.2f}s (Threshold: >{self.agent_avg_action_duration_threshold_sec:.2f}s).",
                        suggested_scrutiny_focus=f"Analyze why {agent_perf.agent_role}'s actions are taking longer than expected. Consider tool execution times, decision-making latency, or waiting for external resources.",
                        severity="Medium"
                    )
                )

        # 7. Challenge based on tool performance
        for tool_perf in report.tool_usage_summary:
            if tool_perf.error_rate_percentage is not None and tool_perf.error_rate_percentage > self.tool_error_rate_threshold_pct:
                challenges.append(
                    RedTeamChallenge(
                        challenge_type="ToolPerformanceIssue",
                        target_id=tool_perf.tool_name,
                        description=f"Tool '{tool_perf.tool_name}' has a high error rate of {tool_perf.error_rate_percentage:.2f}% (Threshold: >{self.tool_error_rate_threshold_pct:.2f}%). Called by: {', '.join(tool_perf.callers) if tool_perf.callers else 'N/A'}.",
                        suggested_scrutiny_focus=f"Investigate why '{tool_perf.tool_name}' is failing frequently. Check its internal logic, input data, dependencies, or integration points with calling agents.",
                        severity="High"
                    )
                )
            
            if tool_perf.avg_duration_seconds is not None and tool_perf.avg_duration_seconds > self.tool_avg_duration_threshold_sec:
                challenges.append(
                    RedTeamChallenge(
                        challenge_type="ToolPerformanceIssue",
                        target_id=tool_perf.tool_name,
                        description=f"Tool '{tool_perf.tool_name}' has a high average execution duration of {tool_perf.avg_duration_seconds:.2f}s (Threshold: >{self.tool_avg_duration_threshold_sec:.2f}s). Called by: {', '.join(tool_perf.callers) if tool_perf.callers else 'N/A'}.",
                        suggested_scrutiny_focus=f"Analyze the reasons for '{tool_perf.tool_name}'s slow performance. Profile its execution, check for inefficient algorithms, resource limitations, or issues with external services it might depend on.",
                        severity="Medium"
                    )
                )

        return challenges

    def run(self, performance_report_json: str) -> List[Dict[str, Any]]:
        """
        Main entry point for the Red Team Agent.
        Consumes a performance report JSON string, analyzes it, and generates challenges.

        Args:
            performance_report_json: A JSON string representing the PerformanceAnalysisReport.

        Returns:
            A list of dictionaries, where each dictionary is a challenge.
        """
        report_object = self._parse_report(performance_report_json)
        if not report_object:
            return [] # Or raise an error, or return a challenge indicating parsing failure
        
        challenges_pydantic = self.formulate_challenges(report_object)
        
        # Convert Pydantic models to dictionaries for output
        return [challenge.dict() for challenge in challenges_pydantic]

# Example Usage (for testing purposes):
if __name__ == '__main__':
    # This example assumes you have a sample JSON output from FCPerformanceAnalyzerTool
    # For a real test, you'd load this from a file or a direct call to the other tool.
    sample_report_json = """
    {
        "original_task_description": "Test task for performance analysis",
        "analysis_timestamp": "2024-05-25T00:00:00Z",
        "metrics": {
            "total_events_processed": 10,
            "crew_run_duration_seconds": 150.5,
            "total_tasks_identified": 2,
            "total_agents_involved": 3,
            "total_tool_calls": 5,
            "error_count": 1
        },
        "task_breakdown": [
            {
                "task_description": "Sub-task 1: Data Collection",
                "task_id": "task_001",
                "status": "Completed",
                "duration_seconds": 70.0,
                "errors_associated": []
            },
            {
                "task_description": "Sub-task 2: Data Processing",
                "task_id": "task_002",
                "status": "Error",
                "duration_seconds": 180.0,
                "errors_associated": ["Processing failed due to timeout"]
            }
        ],
        "agent_performance_summary": [
            {
                "agent_role": "PlannerAgent",
                "total_runtime_seconds": 30.0,
                "action_count": 3,
                "avg_duration_seconds": 10.0,
                "error_count": 0,
                "error_rate_percentage": 0.0,
                "tools_used": ["PlanningTool"]
            },
            {
                "agent_role": "ExecutorAgent",
                "total_runtime_seconds": 100.0,
                "action_count": 5,
                "avg_duration_seconds": 20.0,
                "error_count": 2,
                "error_rate_percentage": 40.0, 
                "tools_used": ["ExecutionToolA", "ExecutionToolB"]
            },
            {
                "agent_role": "ProcessorAgent",
                "total_runtime_seconds": 120.5,
                "action_count": 2,
                "avg_duration_seconds": 60.25,
                "error_count": 1,
                "error_rate_percentage": 50.0,
                "tools_used": ["DataProcessorTool"]
            }
        ],
        "tool_usage_summary": [
            {
                "tool_name": "PlanningTool",
                "total_calls": 3,
                "total_duration_seconds": 15.0,
                "avg_duration_seconds": 5.0,
                "callers": ["PlannerAgent"],
                "errors_in_tool_usage": 0,
                "error_rate_percentage": 0.0
            },
            {
                "tool_name": "ExecutionToolA",
                "total_calls": 2,
                "total_duration_seconds": 10.0,
                "avg_duration_seconds": 5.0,
                "callers": ["ExecutorAgent"],
                "errors_in_tool_usage": 1,
                "error_rate_percentage": 50.0
            },
            {
                "tool_name": "ExecutionToolB",
                "total_calls": 3,
                "total_duration_seconds": 90.0,
                "avg_duration_seconds": 30.0,
                "callers": ["ExecutorAgent"],
                "errors_in_tool_usage": 0,
                "error_rate_percentage": 0.0
            },
            {
                "tool_name": "DataProcessorTool",
                "total_calls": 2,
                "total_duration_seconds": 110.0, 
                "avg_duration_seconds": 55.0,
                "callers": ["ProcessorAgent"],
                "errors_in_tool_usage": 1,
                "error_rate_percentage": 50.0
            }
        ],
        "identified_errors": [
            {"event_type": "ToolUsageFinishedEvent", "agent": "ProcessorAgent", "tool_name": "DataProcessorTool", "error_message": "Timeout during processing", "timestamp": "2024-05-25T00:02:00Z"}
        ],
        "potential_bottlenecks": ["DataProcessorTool performance under load"],
        "efficiency_observations": ["Crew took longer than expected for data processing stage."],
        "recommendations": []
    }
    """
    
    # Example with custom thresholds for agent performance
    red_team_agent = RedTeamAgent(
        high_task_duration_threshold_sec=150, 
        medium_task_duration_threshold_sec=75,
        agent_error_rate_threshold_pct=25.0, 
        agent_avg_action_duration_threshold_sec=45.0, 
        tool_error_rate_threshold_pct=20.0, # To catch ExecutionToolA and DataProcessorTool
        tool_avg_duration_threshold_sec=50.0  # To catch DataProcessorTool
    )
    challenges_output = red_team_agent.run(sample_report_json)
    
    print("Generated Challenges:")
    for i, challenge_dict in enumerate(challenges_output):
        print(f"--- Challenge {i+1} ---")
        for key, value in challenge_dict.items():
            print(f"  {key}: {value}")
        print()
