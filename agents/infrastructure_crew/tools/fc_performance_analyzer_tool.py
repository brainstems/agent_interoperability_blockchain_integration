from langchain_core.tools import BaseTool
from pydantic.v1 import BaseModel as PydanticV1BaseModel, Field as PydanticV1Field
from typing import Type, List, Dict, Any, Optional, Tuple, Union
from enum import Enum
from datetime import datetime, timedelta
import json
import statistics # For potential future use with more advanced stats
from collections import defaultdict, Counter # For easier aggregation

class EventType(str, Enum):
    AGENT_EXECUTION_STARTED = "AgentExecutionStartedEvent"
    AGENT_EXECUTION_FINISHED = "AgentExecutionFinishedEvent"
    TOOL_USAGE_STARTED = "ToolUsageStartedEvent"
    TOOL_USAGE_FINISHED = "ToolUsageFinishedEvent"
    TASK_STARTED = "TaskStartedEvent"  # Assuming such events might exist or be added
    TASK_FINISHED = "TaskFinishedEvent" # Assuming such events might exist or be added
    CREW_EXECUTION_STARTED = "CrewExecutionStartedEvent" # Hypothetical, for overall timing
    CREW_EXECUTION_FINISHED = "CrewExecutionFinishedEvent" # Hypothetical
    ERROR_EVENT = "ErrorEvent" # For explicit error logging
    UNKNOWN = "UnknownEventType"

class PerformanceMetrics(PydanticV1BaseModel):
    total_events_processed: int = 0
    crew_run_duration_seconds: Optional[float] = None
    total_tasks_identified: int = 0
    total_agents_involved: int = 0
    total_tool_calls: int = 0
    avg_task_duration_seconds: Optional[float] = None
    avg_agent_execution_duration_seconds: Optional[float] = None
    avg_tool_call_duration_seconds: Optional[float] = None
    # success_rate: Optional[float] = None # Requires clear definition of success
    error_count: int = 0

class TaskPerformance(PydanticV1BaseModel):
    task_description: str # Could be from original input or inferred
    task_id: Optional[str] = None # If tasks have explicit IDs in events
    status: str = "Unknown"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    contributing_agents: List[str] = []
    tool_calls_count: int = 0
    sub_tasks_count: int = 0 # If hierarchical tasks are identifiable
    errors_associated: List[str] = []

class AgentPerformance(PydanticV1BaseModel):
    agent_role: str
    total_executions: int = 0
    total_duration_seconds: float = 0.0
    avg_duration_seconds: Optional[float] = None
    tool_calls_made: Dict[str, int] = PydanticV1Field(default_factory=dict) # Tool name to count
    tasks_contributed_to: int = 0
    errors_encountered: int = 0
    error_rate_percentage: Optional[float] = None

class ToolPerformance(PydanticV1BaseModel):
    tool_name: str
    total_calls: int = 0
    total_duration_seconds: float = 0.0
    avg_duration_seconds: Optional[float] = None
    callers: List[str] = PydanticV1Field(default_factory=list) # Agents that called this tool
    errors_in_tool_usage: int = 0
    error_rate_percentage: Optional[float] = None

class PerformanceAnalysisReport(PydanticV1BaseModel):
    original_task_description: str
    analysis_timestamp: datetime = PydanticV1Field(default_factory=datetime.utcnow)
    metrics: PerformanceMetrics
    task_breakdown: List[TaskPerformance] = []
    agent_performance_summary: List[AgentPerformance] = []
    tool_usage_summary: List[ToolPerformance] = []
    identified_errors: List[Dict[str, Any]] = [] # List of error event details
    potential_bottlenecks: List[str] = []
    efficiency_observations: List[str] = []
    recommendations: List[str] = []

    def to_markdown(self) -> str:
        md_parts = [f"# Performance Analysis Report for Task: '{self.original_task_description}'"]
        md_parts.append(f"_Analysis performed at: {self.analysis_timestamp.isoformat()}_\n")

        # Overall Metrics
        md_parts.append("## Overall Metrics")
        m = self.metrics
        md_parts.append(f"- Events Processed: {m.total_events_processed}")
        if m.crew_run_duration_seconds is not None:
            md_parts.append(f"- Crew Run Duration: {m.crew_run_duration_seconds:.2f}s")
        md_parts.append(f"- Tasks Identified: {m.total_tasks_identified}")
        md_parts.append(f"- Agents Involved: {m.total_agents_involved}")
        md_parts.append(f"- Tool Calls: {m.total_tool_calls}")
        if m.avg_task_duration_seconds is not None:
            md_parts.append(f"- Avg. Task Duration: {m.avg_task_duration_seconds:.2f}s")
        if m.avg_agent_execution_duration_seconds is not None:
            md_parts.append(f"- Avg. Agent Execution: {m.avg_agent_execution_duration_seconds:.2f}s")
        if m.avg_tool_call_duration_seconds is not None:
            md_parts.append(f"- Avg. Tool Call: {m.avg_tool_call_duration_seconds:.2f}s")
        md_parts.append(f"- Errors Logged: {m.error_count}")
        md_parts.append("\n")

        # Task Breakdown
        if self.task_breakdown:
            md_parts.append("## Task Breakdown")
            for task in self.task_breakdown:
                md_parts.append(f"### Task: {task.task_description[:100]}")
                md_parts.append(f"  - Status: {task.status}")
                if task.duration_seconds is not None: md_parts.append(f"  - Duration: {task.duration_seconds:.2f}s")
                md_parts.append(f"  - Contributing Agents: {', '.join(task.contributing_agents) if task.contributing_agents else 'N/A'}")
                md_parts.append(f"  - Tool Calls: {task.tool_calls_count}")
                if task.errors_associated: md_parts.append(f"  - Errors: {len(task.errors_associated)}")
            md_parts.append("\n")
        
        # Agent Performance
        if self.agent_performance_summary:
            md_parts.append("## Agent Performance")
            for agent in sorted(self.agent_performance_summary, key=lambda x: x.agent_role):
                md_parts.append(f"### Agent: {agent.agent_role}")
                md_parts.append(f"  - Executions: {agent.total_executions}")
                if agent.avg_duration_seconds is not None: md_parts.append(f"  - Avg. Duration: {agent.avg_duration_seconds:.2f}s (Total: {agent.total_duration_seconds:.2f}s)")
                md_parts.append(f"  - Tool Calls: {sum(agent.tool_calls_made.values())}")
                if agent.tool_calls_made: md_parts.append(f"    - Breakdown: {json.dumps(agent.tool_calls_made)}")
                md_parts.append(f"  - Tasks Contributed: {agent.tasks_contributed_to}")
                md_parts.append(f"  - Errors Encountered: {agent.errors_encountered}")
            md_parts.append("\n")

        # Tool Usage
        if self.tool_usage_summary:
            md_parts.append("## Tool Usage Summary")
            for tool in sorted(self.tool_usage_summary, key=lambda x: x.total_calls, reverse=True):
                md_parts.append(f"### Tool: {tool.tool_name}")
                md_parts.append(f"  - Total Calls: {tool.total_calls}")
                if tool.avg_duration_seconds is not None: md_parts.append(f"  - Avg. Duration: {tool.avg_duration_seconds:.2f}s (Total: {tool.total_duration_seconds:.2f}s)")
                md_parts.append(f"  - Called By: {', '.join(sorted(list(set(tool.callers)))) if tool.callers else 'N/A'}")
                md_parts.append(f"  - Errors in Usage: {tool.errors_in_tool_usage}")
            md_parts.append("\n")

        # Errors, Bottlenecks, Observations, Recommendations
        for section_title, items_list in [
            ("Identified Errors", self.identified_errors),
            ("Potential Bottlenecks", self.potential_bottlenecks),
            ("Efficiency Observations", self.efficiency_observations),
            ("Recommendations", self.recommendations)
        ]:
            if items_list:
                md_parts.append(f"## {section_title}")
                for item in items_list:
                    if isinstance(item, dict):
                        md_parts.append(f"- {json.dumps(item)}") # For error dicts
                    else:
                        md_parts.append(f"- {item}")
                md_parts.append("\n")
        
        return "\n".join(md_parts)

class FCPerformanceAnalyzerToolInput(PydanticV1BaseModel):
    events_string: str = PydanticV1Field(
        description="A string representation of a list of event dictionaries, typically from FCEventSubscriberTool."
    )
    original_task_description: str = PydanticV1Field(
        description="The original task description given to the crew for context."
    )
    detailed_analysis: bool = PydanticV1Field(
        default=True,
        description="Whether to perform a detailed analysis including timing metrics and potential issues. Currently, this flag is noted but full differential logic might be implemented progressively."
    )
    task_duration_threshold_sec: float = PydanticV1Field(
        default=60.0,
        description="Threshold in seconds for flagging long-running tasks."
    )
    agent_error_rate_threshold_pct: float = PydanticV1Field(
        default=20.0,
        description="Threshold in percent for flagging agents with high error rates."
    )
    agent_avg_duration_threshold_sec: float = PydanticV1Field(
        default=30.0,
        description="Threshold in seconds for flagging agents with high average execution time."
    )
    agent_total_runtime_share_threshold_pct: float = PydanticV1Field(
        default=70.0,
        description="Threshold in percent for flagging agents consuming a significant share of total runtime."
    )
    tool_error_rate_threshold_pct: float = PydanticV1Field(
        default=15.0,
        description="Threshold in percent for flagging tools with high error rates."
    )
    tool_avg_duration_threshold_sec: float = PydanticV1Field(
        default=20.0,
        description="Threshold in seconds for flagging tools with high average call duration."
    )

class FCPerformanceAnalyzerTool(BaseTool):
    name: str = "functional_crew_performance_analyzer"
    description: str = (
        "Analyzes execution events from a Functional Crew to identify performance characteristics, "
        "bottlenecks, and potential improvements. Input should be events from FCEventSubscriberTool "
        "and the original task description. Returns a detailed performance report as a JSON string."
    )
    args_schema: Type[PydanticV1BaseModel] = FCPerformanceAnalyzerToolInput

    class Config:
        underscore_attrs_are_private = True
        arbitrary_types_allowed = True # Often useful with BaseTool

    def __init__(self, **data: Any):
        super().__init__(**data)
        # Internal state for processing, initialized as instance attributes using object.__setattr__
        object.__setattr__(self, '_parsed_events', [])
        object.__setattr__(self, '_event_timeline', [])
        object.__setattr__(self, '_overall_start_time', None)
        object.__setattr__(self, '_overall_end_time', None)
        
        # Using defaultdict for easier aggregation, also initialized as instance attributes
        object.__setattr__(self, '_tasks_data', defaultdict(lambda: {
            'executions': [], 
            'description': None, 
            'task_id': None, 
            'tool_calls': 0,
            'errors': [], 
            'agent_ids_involved': set()
        }))
        object.__setattr__(self, '_agents_data', defaultdict(lambda: {'executions': [], 'tool_calls_made': Counter(), 'errors': 0}))
        object.__setattr__(self, '_tools_data', defaultdict(lambda: {'calls': [], 'callers': set(), 'errors': 0}))
        object.__setattr__(self, '_errors_logged', [])

    def _reset_state(self):
        """Resets internal state before processing a new set of events."""
        object.__setattr__(self, '_parsed_events', [])
        object.__setattr__(self, '_event_timeline', [])
        object.__setattr__(self, '_overall_start_time', None)
        object.__setattr__(self, '_overall_end_time', None)
        
        # Using defaultdict for easier aggregation
        object.__setattr__(self, '_tasks_data', defaultdict(lambda: {
            'executions': [], 
            'description': None, 
            'task_id': None, 
            'tool_calls': 0,
            'errors': [], 
            'agent_ids_involved': set()
        }))
        object.__setattr__(self, '_agents_data', defaultdict(lambda: {'executions': [], 'tool_calls_made': Counter(), 'errors': 0}))
        object.__setattr__(self, '_tools_data', defaultdict(lambda: {'calls': [], 'callers': set(), 'errors': 0}))
        object.__setattr__(self, '_errors_logged', [])

    def _parse_timestamp(self, ts_str: Optional[str]) -> Optional[datetime]:
        if not ts_str or not isinstance(ts_str, str):
            return None
        try:
            # Handle potential 'Z' for UTC
            if ts_str.endswith('Z'):
                ts_str = ts_str[:-1] + '+00:00'
            
            # Try ISO format, allowing for missing microseconds or timezone
            if 'T' in ts_str:
                if '.' in ts_str and '+' in ts_str.split('.')[1]: # Full with microseconds and tz
                     return datetime.fromisoformat(ts_str)
                elif '.' in ts_str: # Microseconds, no tz
                    return datetime.strptime(ts_str.split('.')[0], "%Y-%m-%dT%H:%M:%S") + timedelta(microseconds=int(ts_str.split('.')[1].rstrip('Z')))
                elif '+' in ts_str: # No microseconds, with tz
                    return datetime.fromisoformat(ts_str)
                else: # No microseconds, no tz
                    return datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S")

            # Fallback for other common formats if necessary (less likely with CrewAI events)
            for fmt in ("%Y-%m-%d %H:%M:%S.%f%z", "%Y-%m-%d %H:%M:%S%z", 
                          "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(ts_str, fmt)
                except ValueError:
                    continue
            print(f"Warning: Could not parse timestamp '{ts_str}' with known formats.")
        except Exception as e:
            print(f"Error parsing timestamp '{ts_str}': {e}")
        return None

    def _calculate_duration(self, start_ts: Optional[datetime], end_ts: Optional[datetime]) -> Optional[float]:
        if start_ts and end_ts and end_ts >= start_ts:
            return (end_ts - start_ts).total_seconds()
        return None

    def _parse_events_string(self, events_string: str) -> List[Dict[str, Any]]:
        """Parses the input string (JSON or custom block format) into a list of event dictionaries."""
        processed_events = []
        content_to_parse = events_string.strip()

        # Remove potential header from FCEventSubscriberTool
        header_prefix = "Collected events for crew run"
        if content_to_parse.startswith(header_prefix):
            first_event_marker = "Event Type:"
            first_event_start_index = content_to_parse.find(first_event_marker)
            if first_event_start_index != -1:
                content_to_parse = content_to_parse[first_event_start_index:]
            else:
                # Header present but no actual event content found
                content_to_parse = ""
        
        if not content_to_parse:
            return []

        # Attempt to parse as a JSON list of dictionaries first
        try:
            data = json.loads(content_to_parse)
            if isinstance(data, list) and all(isinstance(item, dict) for item in data):
                # Ensure essential fields like 'event_type' and 'timestamp' are present
                for event_dict in data:
                    if 'event_type' in event_dict and 'timestamp' in event_dict:
                        processed_events.append(event_dict)
                    else:
                        print(f"Warning: Skipping JSON event due to missing 'event_type' or 'timestamp': {event_dict}")
                return processed_events
        except json.JSONDecodeError:
            # Not a direct JSON list, proceed with custom block parsing
            pass
        except TypeError: # Handle cases where json.loads gets non-string input if not caught earlier
            print(f"Warning: events_string was not a string for JSON parsing: {type(events_string)}")
            return []

        # Custom parser for the "Event Type: ..., Timestamp: ...\n  key: value\n---" format
        # This format is based on the previous implementation of FCEventSubscriberTool's output
        event_blocks = content_to_parse.split("\n---\n")
        for block in event_blocks:
            block = block.strip()
            if not block:
                continue
            
            current_event_dict = {}
            lines = block.split('\n')
            first_line = lines[0].strip()

            if first_line.startswith("Event Type:"):
                # Parse Event Type and Timestamp from the first line
                parts = first_line.split(", Timestamp:")
                current_event_dict['event_type'] = parts[0].replace("Event Type:", "").strip()
                if len(parts) > 1:
                    current_event_dict['timestamp'] = parts[1].strip()
                else:
                    current_event_dict['timestamp'] = None # Or handle as an error
                
                # Parse key-value pairs from subsequent lines
                for line in lines[1:]:
                    line = line.strip()
                    if ':' in line:
                        key, value = line.split(':', 1)
                        current_event_dict[key.strip()] = value.strip()
                
                if current_event_dict.get('event_type') and current_event_dict.get('timestamp'):
                    processed_events.append(current_event_dict)
                else:
                    print(f"Warning: Skipping block event due to missing 'event_type' or 'timestamp': {current_event_dict}")
            else:
                print(f"Warning: Skipping malformed event block (missing 'Event Type:' in first line): {block[:100]}...")
        
        return processed_events

    def _run(self, events_string: str, original_task_description: str, detailed_analysis: bool = True, **kwargs: Any) -> str:
        self._reset_state() # Ensure clean state for each run

        if not isinstance(events_string, str) or not events_string.strip():
            report = PerformanceAnalysisReport(
                original_task_description=original_task_description,
                metrics=PerformanceMetrics(error_count=1),
                potential_bottlenecks=["Input 'events_string' was empty or not a string."]
            )
            return report.json(indent=2)

        if not original_task_description or not isinstance(original_task_description, str):
             # Still proceed with event analysis if possible, but note the missing task description
            self._errors_logged.append({"error_type": "InputValidation", "message": "'original_task_description' was empty or not a string."})
            original_task_description = "Unknown - Original task description not provided or invalid"

        try:
            object.__setattr__(self, '_parsed_events', self._parse_events_string(events_string))
        except Exception as e:
            report = PerformanceAnalysisReport(
                original_task_description=original_task_description,
                metrics=PerformanceMetrics(error_count=1),
                identified_errors=[{"error_type": "ParsingException", "message": f"Fatal error parsing events string: {e}"}]
            )
            return report.json(indent=2)

        if not self._parsed_events:
            report = PerformanceAnalysisReport(
                original_task_description=original_task_description,
                metrics=PerformanceMetrics(total_events_processed=0, error_count=1),
                potential_bottlenecks=["No valid events could be parsed from the 'events_string'. Input might be malformed or empty after header removal."],
                efficiency_observations=[f"Problematic input (first 500 chars): {events_string[:500]}"]
            )
            return report.json(indent=2)

        # Populate and sort the event timeline
        for event_data in self._parsed_events:
            parsed_ts = self._parse_timestamp(event_data.get('timestamp'))
            current_timeline = self._event_timeline
            current_errors = self._errors_logged
            if parsed_ts:
                current_timeline.append({**event_data, 'parsed_timestamp': parsed_ts})
            else:
                # Event kept but marked, or dropped if timestamp is critical and unparsable
                current_errors.append({
                    "error_type": "TimestampParsingError", 
                    "message": f"Could not parse timestamp for event: {event_data.get('event_type')}",
                    "original_timestamp": event_data.get('timestamp')
                })
                # Optionally, add to timeline with None timestamp if partial analysis is desired
                # current_timeline.append({**event_data, 'parsed_timestamp': None})
            object.__setattr__(self, '_event_timeline', current_timeline)
            object.__setattr__(self, '_errors_logged', current_errors)
        
        # Sort by parsed_timestamp, events with unparsable timestamps might be at the end or handled based on policy
        current_timeline = self._event_timeline
        current_timeline.sort(key=lambda e: e['parsed_timestamp'] if e['parsed_timestamp'] else datetime.min)
        object.__setattr__(self, '_event_timeline', current_timeline)

        if self._event_timeline:
            object.__setattr__(self, '_overall_start_time', self._event_timeline[0]['parsed_timestamp'])
            object.__setattr__(self, '_overall_end_time', self._event_timeline[-1]['parsed_timestamp'])
        
        self._process_event_timeline()
        
        # --- Placeholder for further analysis steps ---
        # _compile_performance_report() which will call sub-methods like:
        #   _calculate_aggregate_metrics()
        #   _analyze_task_performance()
        #   _analyze_agent_performance()
        #   _analyze_tool_performance()
        #   _identify_patterns_and_issues()
        #   _generate_recommendations()
        # --- End Placeholder ---

        # Correctly get threshold values from kwargs if provided, else use defaults
        default_thresholds_map = {
            "task_duration_threshold_sec": FCPerformanceAnalyzerToolInput.__fields__['task_duration_threshold_sec'].default,
            "agent_error_rate_threshold_pct": FCPerformanceAnalyzerToolInput.__fields__['agent_error_rate_threshold_pct'].default,
            "agent_avg_duration_threshold_sec": FCPerformanceAnalyzerToolInput.__fields__['agent_avg_duration_threshold_sec'].default,
            "agent_total_runtime_share_threshold_pct": FCPerformanceAnalyzerToolInput.__fields__['agent_total_runtime_share_threshold_pct'].default,
            "tool_error_rate_threshold_pct": FCPerformanceAnalyzerToolInput.__fields__['tool_error_rate_threshold_pct'].default,
            "tool_avg_duration_threshold_sec": FCPerformanceAnalyzerToolInput.__fields__['tool_avg_duration_threshold_sec'].default,
        }

        final_thresholds = {
            key: kwargs.get(key, default_value) 
            for key, default_value in default_thresholds_map.items()
        }

        final_report_obj = self._compile_performance_report(original_task_description, final_thresholds)
        return final_report_obj.json(indent=2)

    def _analyze_agent_performance(self) -> List[AgentPerformance]:
        agent_summary_list = []
        for agent_role, data in self._agents_data.items():
            total_duration = 0.0
            valid_executions_count = 0
            for execution_pair in data.get('executions', []):
                if len(execution_pair) == 2 and execution_pair[0] and execution_pair[1]:
                    start_event, end_event = execution_pair
                    duration = self._calculate_duration(start_event.get('parsed_timestamp'), end_event.get('parsed_timestamp'))
                    if duration is not None:
                        total_duration += duration
                        valid_executions_count +=1
            
            total_timed_executions = valid_executions_count
            avg_duration = total_duration / total_timed_executions if total_timed_executions > 0 else None
            
            # total_executions should ideally count all agent start events, not just timed ones.
            # This might need refinement in _process_event_timeline to store total_execution_start_events.
            # For now, using timed executions or a placeholder if available from data dict.
            num_executions = data.get('total_execution_start_events', total_timed_executions)

            agent_perf = AgentPerformance(
                agent_role=agent_role,
                total_executions=num_executions, 
                total_duration_seconds=round(total_duration, 3),
                avg_duration_seconds=round(avg_duration, 3) if avg_duration is not None else None,
                tool_calls_made=dict(data.get('tool_calls_made', Counter())),
                tasks_contributed_to=len(data.get('tasks_contributed_to', set())),
                errors_encountered=data.get('errors_encountered', 0) 
            )
            agent_summary_list.append(agent_perf)
        return agent_summary_list

    def _analyze_tool_performance(self) -> List[ToolPerformance]:
        tool_summary_list = []
        for tool_name, data in self._tools_data.items():
            total_duration = 0.0
            valid_calls_count = 0
            for call_pair in data.get('calls', []):
                if len(call_pair) == 2 and call_pair[0] and call_pair[1]:
                    start_event, end_event = call_pair
                    duration = self._calculate_duration(start_event.get('parsed_timestamp'), end_event.get('parsed_timestamp'))
                    if duration is not None:
                        total_duration += duration
                        valid_calls_count += 1
            
            total_timed_calls = valid_calls_count
            avg_duration = total_duration / total_timed_calls if total_timed_calls > 0 else None
            
            # Similar to agents, total_calls should ideally count all tool start events.
            # For now, using timed calls or a placeholder.
            num_calls = data.get('total_call_start_events', total_timed_calls)
            errors_in_usage = data.get('errors_in_usage', 0)
            error_rate_percentage = (errors_in_usage / num_calls * 100) if num_calls > 0 else 0.0

            tool_perf = ToolPerformance(
                tool_name=tool_name,
                total_calls=num_calls, 
                total_duration_seconds=round(total_duration, 3),
                avg_duration_seconds=round(avg_duration, 3) if avg_duration is not None else None,
                callers=list(data.get('callers', set())),
                errors_in_tool_usage=errors_in_usage,
                error_rate_percentage=round(error_rate_percentage, 2)
            )
            tool_summary_list.append(tool_perf)
        return tool_summary_list

    def _analyze_task_performance(self) -> List[TaskPerformance]:
        task_summary_list = []
        for task_id_or_desc, data in self._tasks_data.items():
            start_time, end_time, duration_seconds = None, None, None
            status = "Unknown"
            
            if data.get('executions'): # Matched start/end pairs
                valid_execution_found = False
                for exec_pair in data['executions']:
                    if len(exec_pair) == 2 and exec_pair[0] and exec_pair[1]:
                        start_event, end_event = exec_pair
                        start_time = start_event.get('parsed_timestamp')
                        end_time = end_event.get('parsed_timestamp')
                        duration_seconds = self._calculate_duration(start_time, end_time)
                        status = "Completed" if duration_seconds is not None else "ErrorInTiming"
                        valid_execution_found = True
                        break 
                if not valid_execution_found and data.get('start_events'): # Has start but no valid end from 'executions'
                    status = "Incomplete"
                    if data['start_events']: start_time = data['start_events'][0].get('parsed_timestamp')
            elif data.get('start_events'): # No 'executions' but has 'start_events'
                status = "Incomplete"
                if data['start_events']: start_time = data['start_events'][0].get('parsed_timestamp')
            
            if data.get('errors_associated'):
                if status == "Completed": status = "CompletedWithErrors"
                elif status == "Incomplete": status = "IncompleteWithErrors"
                elif status == "ErrorInTiming": status = "ErrorInTimingWithErrors"
                elif status == "Unknown": status = "FailedOrError" 
            
            if status == "Unknown" and (data.get('agent_ids_involved') or data.get('tool_calls_count')):
                 status = "PartiallyTracked"

            task_perf = TaskPerformance(
                task_description=data.get('description', str(task_id_or_desc)),
                task_id=data.get('task_id', str(task_id_or_desc) if "task-" in str(task_id_or_desc) else None),
                status=status,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=round(duration_seconds, 3) if duration_seconds is not None else None,
                contributing_agents=list(data.get('agent_ids_involved', set())),
                tool_calls_count=data.get('tool_calls_count', 0),
                errors_associated=[str(e.get('message', e) if isinstance(e, dict) else e) for e in data.get('errors_associated', [])]
            )
            task_summary_list.append(task_perf)
        return task_summary_list




    def _compile_performance_report(self, original_task_description: str, analysis_thresholds: Dict[str, float]) -> PerformanceAnalysisReport:
        """Compiles all analyzed data into the final PerformanceAnalysisReport."""
        
        crew_run_duration = self._calculate_duration(self._overall_start_time, self._overall_end_time)
        agent_performance_summary = self._analyze_agent_performance()
        tool_usage_summary = self._analyze_tool_performance()
        task_breakdown = self._analyze_task_performance()

        total_errors_from_agents = sum(perf.errors_encountered for perf in agent_performance_summary)
        total_errors_from_tools = sum(perf.errors_in_tool_usage for perf in tool_usage_summary)
        total_error_count = len(self._errors_logged) + total_errors_from_agents + total_errors_from_tools

        metrics = PerformanceMetrics(
            total_events_processed=len(self._event_timeline),
            crew_run_duration_seconds=round(crew_run_duration, 3) if crew_run_duration is not None else None,
            error_count=total_error_count,
            total_agents_involved=len(agent_performance_summary),
            total_tool_calls=sum(perf.total_calls for perf in tool_usage_summary),
            total_tasks_identified=len(task_breakdown)
        )

        report = PerformanceAnalysisReport(
            original_task_description=original_task_description,
            metrics=metrics,
            agent_performance_summary=agent_performance_summary,
            tool_usage_summary=tool_usage_summary,
            task_breakdown=task_breakdown,
            identified_errors=list(self._errors_logged) 
        )

        self._identify_bottlenecks_and_issues(report, analysis_thresholds)
        self._generate_recommendations(report)
        
        return report

    def _identify_bottlenecks_and_issues(self, report: PerformanceAnalysisReport, analysis_thresholds: Dict[str, float]) -> None:
        """Analyzes the report to identify bottlenecks and issues based on configurable thresholds."""
        # Task-level analysis
        for task in report.task_breakdown:
            if task.duration_seconds and task.duration_seconds > analysis_thresholds['task_duration_threshold_sec']:
                report.potential_bottlenecks.append(f"Task '{task.task_description}' took {task.duration_seconds:.2f}s, exceeding threshold of {analysis_thresholds['task_duration_threshold_sec']:.2f}s.")
            if task.status not in ["Completed", "CompletedWithErrors"]:
                report.efficiency_observations.append(f"Task '{task.task_description}' has status: {task.status}. Errors: {', '.join(task.errors_associated) if task.errors_associated else 'None'}")

        # Agent-level analysis
        total_crew_runtime = report.metrics.crew_run_duration_seconds or 0
        for agent_perf in report.agent_performance_summary:
            if agent_perf.total_executions > 0:
                error_rate = (agent_perf.errors_encountered / agent_perf.total_executions) * 100 if agent_perf.total_executions > 0 else 0
                if error_rate > analysis_thresholds['agent_error_rate_threshold_pct']:
                    report.efficiency_observations.append(f"Agent '{agent_perf.agent_role}' has a high error rate: {error_rate:.2f}% (Threshold: {analysis_thresholds['agent_error_rate_threshold_pct']:.2f}%). Errors: {agent_perf.errors_encountered}, Executions: {agent_perf.total_executions}.")
            if agent_perf.avg_duration_seconds and agent_perf.avg_duration_seconds > analysis_thresholds['agent_avg_duration_threshold_sec']:
                report.potential_bottlenecks.append(f"Agent '{agent_perf.agent_role}' has a high average execution time: {agent_perf.avg_duration_seconds:.2f}s (Threshold: {analysis_thresholds['agent_avg_duration_threshold_sec']:.2f}s).")
            if total_crew_runtime > 0 and agent_perf.total_duration_seconds:
                runtime_share = (agent_perf.total_duration_seconds / total_crew_runtime) * 100
                if runtime_share > analysis_thresholds['agent_total_runtime_share_threshold_pct']:
                    report.potential_bottlenecks.append(f"Agent '{agent_perf.agent_role}' consumed a significant portion of total runtime: {runtime_share:.2f}% (Threshold: {analysis_thresholds['agent_total_runtime_share_threshold_pct']:.2f}%).")

        # Tool-level analysis
        for tool_perf in report.tool_usage_summary:
            if tool_perf.total_calls > 0:
                error_rate = (tool_perf.errors_in_tool_usage / tool_perf.total_calls) * 100 if tool_perf.total_calls > 0 else 0
                if error_rate > analysis_thresholds['tool_error_rate_threshold_pct']:
                    report.efficiency_observations.append(f"Tool '{tool_perf.tool_name}' has a high error rate in usage: {error_rate:.2f}% (Threshold: {analysis_thresholds['tool_error_rate_threshold_pct']:.2f}%). Errors: {tool_perf.errors_in_tool_usage}, Calls: {tool_perf.total_calls}.")
            if tool_perf.avg_duration_seconds and tool_perf.avg_duration_seconds > analysis_thresholds['tool_avg_duration_threshold_sec']:
                report.potential_bottlenecks.append(f"Tool '{tool_perf.tool_name}' has a high average call duration: {tool_perf.avg_duration_seconds:.2f}s (Threshold: {analysis_thresholds['tool_avg_duration_threshold_sec']:.2f}s).")

        # General observations from _errors_logged (parsing, timing, unmatched events)
        for err_log in self._errors_logged:
            report.efficiency_observations.append(f"Processing Error: Type '{err_log.get('error_type', 'Unknown')}', Message: '{err_log.get('message', 'N/A')}'")
            if 'Unmatched' in err_log.get('error_type', ''):
                report.potential_bottlenecks.append(f"Data Integrity Issue: {err_log.get('error_type')} for {err_log.get('agent_role') or err_log.get('tool_name') or err_log.get('task_key')}. Check event logging.")

        if not report.potential_bottlenecks:
            report.potential_bottlenecks.append("No obvious performance bottlenecks identified based on current thresholds.")
        if not report.efficiency_observations:
            report.efficiency_observations.append("No specific efficiency observations noted based on current analysis.")

    def _generate_recommendations(self, report: PerformanceAnalysisReport) -> None:
        """Generates recommendations based on the identified issues and observations."""
        # Task-related recommendations
        if any("took" in bottleneck for bottleneck in report.potential_bottlenecks if "Task" in bottleneck):
            report.recommendations.append("Investigate long-running tasks to identify optimization opportunities.")
        if any("Task" in obs and ("Failed" in obs or "Error" in obs or "Incomplete" in obs) for obs in report.efficiency_observations):
            report.recommendations.append("Review failed or incomplete tasks to understand root causes and improve task robustness.")

        # Agent-related recommendations
        if any("Agent" in obs and "high error rate" in obs for obs in report.efficiency_observations):
            report.recommendations.append("Address agents with high error rates by reviewing their logic, error handling, or input validation.")
        if any("Agent" in bottleneck and ("high average execution time" in bottleneck or "consumed a significant portion" in bottleneck) for bottleneck in report.potential_bottlenecks):
            report.recommendations.append("Analyze agents with high execution times or those consuming large parts of total runtime for potential optimizations.")

        # Tool-related recommendations
        if any("Tool" in obs and "high error rate" in obs for obs in report.efficiency_observations):
            report.recommendations.append("Investigate tools with high error rates; check their configurations, dependencies, or internal logic.")
        if any("Tool" in bottleneck and "high average call duration" in bottleneck for bottleneck in report.potential_bottlenecks):
            report.recommendations.append("Optimize tools with high average call durations or explore alternative tools if performance is critical.")
        
        # General recommendations
        if any("Data Integrity Issue" in bottleneck for bottleneck in report.potential_bottlenecks):
            report.recommendations.append("Improve event logging consistency to ensure all operations have corresponding start and end events for accurate tracking.")

        if not report.recommendations:
            report.recommendations.append("Overall performance appears nominal based on current analysis. Consider adjusting analysis thresholds for more granular insights or if specific concerns exist.")

    def _process_event_timeline(self):
        """Iterates over the sorted event timeline to populate aggregated data stores."""
        if not self._event_timeline:
            return

        # Temporary stacks to match start/end events
        agent_execution_starts: Dict[str, Dict] = {}
        tool_usage_starts: Dict[Tuple[str, str], Dict] = {} # (agent_role, tool_name) -> start_event
        task_starts: Dict[str, Dict] = {} # task_key (id or description) -> start_event

        for event in self._event_timeline:
            event_type_str = event.get('event_type', EventType.UNKNOWN.value)
            parsed_ts = event.get('parsed_timestamp')
            agent_role = event.get('agent_role')
            tool_name = event.get('tool_name')
            task_description_from_event = event.get('task_description') 
            task_id_from_event = event.get('task_id')
            # Determine a primary key for tasks
            current_task_key = task_id_from_event or task_description_from_event

            try:
                event_type = EventType(event_type_str)
            except ValueError:
                event_type = EventType.UNKNOWN
                self._errors_logged.append({
                    "error_type": "UnknownEventTypeEncountered",
                    "message": f"Event with unknown type: {event_type_str}",
                    "event_details": event
                })

            # Agent Executions
            if event_type == EventType.AGENT_EXECUTION_STARTED and agent_role:
                agent_execution_starts[agent_role] = event
            elif event_type == EventType.AGENT_EXECUTION_FINISHED and agent_role:
                if agent_role in agent_execution_starts:
                    start_event = agent_execution_starts.pop(agent_role)
                    self._agents_data[agent_role]['executions'].append((start_event, event))
                    if task_description: # Associate agent with this task
                        self._agents_data[agent_role]['tasks_contributed_to'].add(task_description)
                else:
                    self._errors_logged.append({"error_type": "OrphanedAgentEndEvent", "agent_role": agent_role, "event": event})
                    self._agents_data[agent_role]['errors_encountered'] += 1
            
            # Tool Usage (assuming tool calls are nested within agent executions)
            if event_type == EventType.TOOL_USAGE_STARTED and agent_role and tool_name:
                tool_usage_starts[(agent_role, tool_name)] = event
            elif event_type == EventType.TOOL_USAGE_FINISHED and agent_role and tool_name:
                start_key = (agent_role, tool_name)
                if start_key in tool_usage_starts:
                    start_event = tool_usage_starts.pop(start_key)
                    self._tools_data[tool_name]['calls'].append((start_event, event))
                    self._tools_data[tool_name]['callers'].add(agent_role)
                    self._agents_data[agent_role]['tool_calls_made'][tool_name] += 1
                    # If tool usage has an error indicator (e.g., in output or a flag)
                    if "error" in str(event.get('output', '')).lower() or event.get('status') == 'error': # Heuristic
                        self._tools_data[tool_name]['errors_in_usage'] += 1
                        self._agents_data[agent_role]['errors_encountered'] += 1 # Also count as agent error
                else:
                    self._errors_logged.append({"error_type": "OrphanedToolEndEvent", "agent_role": agent_role, "tool_name": tool_name, "event": event})
                    self._tools_data[tool_name]['errors_in_usage'] += 1
            
            # Generic Error Events (if any are explicitly logged with this type)
            if event_type == EventType.ERROR_EVENT:
                self._errors_logged.append(event) # Store the whole error event
                if agent_role: self._agents_data[agent_role]['errors_encountered'] += 1
                if tool_name: self._tools_data[tool_name]['errors_in_usage'] += 1

            # Task Executions
            if event_type == EventType.TASK_STARTED and current_task_key:
                task_starts[current_task_key] = event
                self._tasks_data[current_task_key]['description'] = task_description_from_event or current_task_key
                if task_id_from_event: self._tasks_data[current_task_key]['task_id'] = task_id_from_event
            elif event_type == EventType.TASK_FINISHED and current_task_key:
                if current_task_key in task_starts:
                    start_event = task_starts.pop(current_task_key)
                    self._tasks_data[current_task_key]['executions'].append((start_event, event))
                else:
                    self._errors_logged.append({"error_type": "OrphanedTaskEndEvent", "task_key": current_task_key, "event": event})
                    if current_task_key: self._tasks_data[current_task_key]['errors'].append(f"Orphaned task end event: {event.get('timestamp')}")

            # Associate agents and tool calls with tasks if task context is available
            if current_task_key:
                if agent_role and (event_type == EventType.AGENT_EXECUTION_STARTED or event_type == EventType.AGENT_EXECUTION_FINISHED):
                     self._tasks_data[current_task_key]['agent_ids_involved'].add(agent_role)
                     # Ensure description/id are set if an agent acts on a task not explicitly started/ended
                     if not self._tasks_data[current_task_key]['description']:
                         self._tasks_data[current_task_key]['description'] = task_description_from_event or current_task_key
                     if task_id_from_event and not self._tasks_data[current_task_key]['task_id']:
                         self._tasks_data[current_task_key]['task_id'] = task_id_from_event
                if event_type == EventType.TOOL_USAGE_FINISHED:
                    self._tasks_data[current_task_key]['tool_calls'] += 1
            
            # Generic Error Events - associate with task if possible
            if event_type == EventType.ERROR_EVENT:
                error_message = event.get('message', 'Unknown error')
                self._errors_logged.append(event) # Store the whole error event
                if agent_role: self._agents_data[agent_role]['errors_encountered'] += 1
                if tool_name: self._tools_data[tool_name]['errors_in_usage'] += 1
                if current_task_key:
                    self._tasks_data[current_task_key]['errors'].append(error_message)
                    # Ensure description/id are set if an error occurs for a task not explicitly started/ended
                    if not self._tasks_data[current_task_key]['description']:
                        self._tasks_data[current_task_key]['description'] = task_description_from_event or current_task_key
                    if task_id_from_event and not self._tasks_data[current_task_key]['task_id']:
                        self._tasks_data[current_task_key]['task_id'] = task_id_from_event

        # Log unmatched start events as errors/warnings
        for agent_role, start_event in agent_execution_starts.items():
            self._errors_logged.append({"error_type": "UnmatchedAgentStartEvent", "agent_role": agent_role, "event": start_event})
            self._agents_data[agent_role]['errors_encountered'] += 1
        for (agent_role, tool_name), start_event in tool_usage_starts.items():
            self._errors_logged.append({"error_type": "UnmatchedToolStartEvent", "agent_role": agent_role, "tool_name": tool_name, "event": start_event})
            self._tools_data[tool_name]['errors_in_usage'] += 1
            if agent_role: self._agents_data[agent_role]['errors_encountered'] +=1
        
        for task_key, start_event in task_starts.items():
            self._errors_logged.append({"error_type": "UnmatchedTaskStartEvent", "task_key": task_key, "event": start_event})
            self._tasks_data[task_key]['errors'].append(f"Task started at {start_event.get('timestamp')} but never finished.")
