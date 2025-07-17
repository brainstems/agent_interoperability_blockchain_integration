from typing import List, Dict, Optional, Union, Any
from pydantic.v1 import BaseModel as PydanticV1BaseModel, Field as PydanticV1Field
from enum import Enum
import json
import yaml
import re
from pathlib import Path
import numpy as np
from typing import Tuple # For type hinting evaluate_global_parameters

# --- Placeholder External Tool Definitions ---
class BaseExternalTool:
    def run(self, query_details: Dict[str, str]) -> Optional[str]:
        """Runs the query and returns the result as a string, or None if an error occurs."""
        raise NotImplementedError("Subclasses must implement this method.")

class BlockchainTool(BaseExternalTool):
    def run(self, query_details: Dict[str, str]) -> Optional[str]:
        print(f"  [BlockchainTool] Querying with details: {query_details}")
        if query_details.get("contract") == "0xContractA" and query_details.get("property") == "owner":
            return "UserX_from_tool"
        elif query_details.get("transaction_id") == "0xTX123" and query_details.get("log_index") == "0":
            return "EVENT_TRANSFER_SUCCESS"  # For matches_regex: "EVENT_.*_SUCCESS"
        elif query_details.get("contract") == "0xDataStore" and query_details.get("field") == "optional_user_data":
            return ""  # For is_empty
        elif query_details.get("contract") == "0xContractB" and query_details.get("method") == "balance":
            return "1500ETH_from_tool"
        elif query_details.get("contract") == "0xContractC" and query_details.get("property") == "isActive":
            return "true_from_tool"
        # Add more mock responses as needed
        return None

class DatabaseTool(BaseExternalTool):
    def run(self, query_details: Dict[str, str]) -> Optional[str]:
        print(f"  [DatabaseTool] Querying with details: {query_details}")
        if query_details.get("table") == "user_table" and query_details.get("id") == "123" and query_details.get("column") == "status":
            return "active_from_tool"
        elif query_details.get("table") == "system_config" and query_details.get("key") == "error_threshold" and query_details.get("column") == "value":
            return "3"  # For less_than_or_equals: "5"
        elif query_details.get("table") == "app_settings" and query_details.get("setting") == "maintenance_mode" and query_details.get("column") == "is_active":
            return "false"  # For is_false
        elif query_details.get("table") == "user_table" and query_details.get("id") == "123":
            return "active_from_tool"
        elif query_details.get("table") == "order_table" and query_details.get("id") == "789":
            return "300.00_from_tool"
        # Add more mock responses as needed
        return None

class APITool(BaseExternalTool):
    def run(self, query_details: Dict[str, str]) -> Optional[str]:
        endpoint = query_details.get("endpoint")
        # Corrected print statement to show all query_details for better debugging
        print(f"  [APITool] Querying endpoint '{endpoint}' with details: {query_details}")
        if endpoint == "order_value_check" and query_details.get("id") == "789":
            return "250.75"
        elif endpoint == "inventory_check" and query_details.get("item_id") == "XYZ":
            return "15"  # For greater_than_or_equals: "10"
        elif endpoint == "feature_flags" and query_details.get("flag_name") == "new_dashboard":
            return "true"  # For is_true
        elif endpoint == "user_feedback" and query_details.get("feedback_id") == "FDBK001":
            return "User left a comment."  # For is_not_empty
        # Add more mock responses as needed
        return None
# --- End Placeholder External Tool Definitions ---


# Attempt to import PerformanceAnalysisReport and related models
# This path assumes the script is run from the root of agent_blockchain-integration-main
try:
    from agents.infrastructure_crew.tools.fc_performance_analyzer_tool import (
        PerformanceAnalysisReport,
        TaskPerformance,
        PerformanceMetrics
    )
except ImportError:
    # Fallback for potential execution context issues, though direct execution of this file
    # might require PYTHONPATH adjustments if this fallback is hit.
    # This is primarily for type hinting and development convenience.
    print("Warning: Could not import PerformanceAnalysisReport models directly. Using placeholders.")
    class PerformanceMetrics(PydanticV1BaseModel):
        crew_run_duration_seconds: Optional[float]
        error_count: int
        total_events_processed: int = 0
        total_agents_involved: int = 0
        total_tool_calls: int = 0
        total_tasks_identified: int = 0

    class TaskPerformance(PydanticV1BaseModel):
        task_description: str
        status: str
        duration_seconds: Optional[float]
        errors_associated: List[str] = []
        events_in_task: List[Dict] = []
        agents_involved: List[str] = []
        tools_used: List[str] = []

    class PerformanceAnalysisReport(PydanticV1BaseModel):
        original_task_description: str
        metrics: PerformanceMetrics
        task_breakdown: List[TaskPerformance]
        agent_performance_summary: List[Dict] = []
        tool_usage_summary: List[Dict] = []
        identified_errors: List[Dict] = []
        efficiency_observations: List[Dict] = []
        potential_bottlenecks: List[Dict] = []
        recommendations: List[Dict] = []

# --- Reward Milestone Definitions ---
class BaseRewardMilestone(PydanticV1BaseModel):
    milestone_id: str
    description: str
    reward_amount: float = PydanticV1Field(..., gt=0) # Reward amount must be positive

class TaskCompletionMilestone(BaseRewardMilestone):
    milestone_type: str = "TaskCompletion"
    task_name: str
    expected_status: str = "Completed"
    max_errors_associated: int = 0

class CrewPerformanceMilestone(BaseRewardMilestone):
    milestone_type: str = "CrewPerformance"
    max_crew_duration_seconds: Optional[float] = None
    max_total_errors: Optional[int] = None
    min_tasks_completed: Optional[int] = None # e.g., at least N tasks must be completed

class ExternalStateMilestone(BaseRewardMilestone):
    milestone_type: str = "ExternalState"
    target_system: str # e.g., "Blockchain", "Database", "API"
    query_details: Dict[str, str] # e.g., {"contract": "0x123", "method": "getBalance", "params": "userA"}
    expected_value: str # The expected result from the query
    comparison_operator: str = "equals" # e.g., "equals", "contains", "greater_than", "less_than"

# Union type for milestones
AnyRewardMilestone = Union[TaskCompletionMilestone, CrewPerformanceMilestone, ExternalStateMilestone]

# --- QA Agent Definition ---
class QAAgent:
    def __init__(self, config_file_path: str, external_tools: Dict[str, BaseExternalTool], crew_id: str = "default_crew"):
        self.crew_id = crew_id
        self.milestones = self._load_milestones_from_config(config_file_path)
        self.external_tools = external_tools
        # Initialize federated learning parameters - a list containing one NumPy array for simplicity
        # These represent the 'model weights' for this agent.
        self.federated_parameters: List[np.ndarray] = [np.array([0.5, 0.5, 0.5], dtype=np.float32)]
        # Define hypothetical ideal parameters for evaluation purposes
        self.ideal_federated_parameters: List[np.ndarray] = [np.array([1.0, 0.0, 0.75], dtype=np.float32)]
        print(f"QAAgent initialized for crew '{self.crew_id}' with {len(self.milestones)} milestones, {len(self.external_tools)} external tools, and initial FL params: {self.federated_parameters}.")

    def _load_milestones_from_config(self, config_file_path: str) -> List[AnyRewardMilestone]:
        loaded_milestones: List[AnyRewardMilestone] = []
        try:
            config_path = Path(config_file_path)
            if not config_path.is_file():
                print(f"Error: Milestones config file not found at {config_file_path}")
                return loaded_milestones

            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data or 'milestones' not in config_data:
                print(f"Error: 'milestones' key not found or empty in {config_file_path}")
                return loaded_milestones

            for m_data in config_data['milestones']:
                milestone_type = m_data.pop('milestone_type', None)
                if milestone_type == "TaskCompletion":
                    loaded_milestones.append(TaskCompletionMilestone(**m_data))
                elif milestone_type == "CrewPerformance":
                    loaded_milestones.append(CrewPerformanceMilestone(**m_data))
                elif milestone_type == "ExternalState":
                    loaded_milestones.append(ExternalStateMilestone(**m_data))
                else:
                    print(f"Warning: Unknown milestone_type '{milestone_type}' in config. Skipping.")
            
            print(f"Successfully loaded {len(loaded_milestones)} milestones from {config_file_path}")

        except yaml.YAMLError as e:
            print(f"Error parsing YAML from {config_file_path}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while loading milestones: {e}")
        
        return loaded_milestones

    def _parse_report(self, report_json_string: str) -> Optional[PerformanceAnalysisReport]:
        """Parses the JSON report string into a PerformanceAnalysisReport object."""
        try:
            report_data = json.loads(report_json_string)
            # Assuming PerformanceAnalysisReport is correctly imported or defined
            if 'PerformanceAnalysisReport' not in globals() or not hasattr(globals()['PerformanceAnalysisReport'], 'parse_obj'):
                 print("Error: PerformanceAnalysisReport model is not correctly defined or imported.")
                 return None
            return PerformanceAnalysisReport(**report_data)
        except json.JSONDecodeError as e:
            print(f"Error decoding report JSON: {e}")
            return None
        except Exception as e: # Catch Pydantic validation errors or other issues
            print(f"Error parsing report into Pydantic model: {e}")
            return None

    def _query_external_state(self, target_system: str, query_details: Dict[str, str]) -> Optional[str]:
        """Queries an external system using the appropriate tool."""
        print(f"  [QA Agent] Attempting to query '{target_system}' with details: {query_details}")
        tool = self.external_tools.get(target_system)
        if tool:
            try:
                result = tool.run(query_details=query_details)
                if result is not None:
                    print(f"    [QA Agent] Tool '{target_system}' returned: '{result}'")
                    return str(result) # Ensure string return for consistent comparison
                else:
                    print(f"    [QA Agent] Tool '{target_system}' returned None.")
                    return None
            except Exception as e:
                print(f"    [QA Agent] Error calling tool '{target_system}': {e}")
                return None
        else:
            print(f"    [QA Agent] No tool configured for target system '{target_system}'.")
            return None

    def _mock_grant_reward(self, reward_amount: float, reason: str, agent_ids: Optional[List[str]] = None):
        """Simulates calling Crew.ai's reward function."""
        print(f"\n--- REWARD GRANTED ---")
        if agent_ids and len(agent_ids) > 0:
            print(f"  Agents: {', '.join(agent_ids)}")
        else:
            print(f"  Crew: {self.crew_id}")
        print(f"  Amount: ${reward_amount:.2f}")
        print(f"  Reason: {reason}")
        print(f"----------------------")

    # --- Federated Learning Placeholder Methods ---
    def get_federated_parameters(self, config=None) -> List[np.ndarray]:
        # self.federated_parameters is now always List[np.ndarray]
        print(f"  [QA Agent FL] get_federated_parameters called. Returning: {self._params_to_repr(self.federated_parameters)}")
        return self.federated_parameters

    def set_federated_parameters(self, parameters: List[np.ndarray]) -> None:
        """Updates the agent's local 'learnings' with parameters from the server."""
        print(f"  [QA Agent FL] set_federated_parameters called. Old: {self._params_to_repr(self.federated_parameters)}, New: {self._params_to_repr(parameters)}")
        self.federated_parameters = parameters

    def perform_local_update_and_get_parameters(self, config: Dict) -> List[np.ndarray]:
        """Simulates local learning and returns updated parameters.
        In a real scenario, this would involve processing reports, updating RL models, etc.
        """
        print(f"  [QA Agent FL] perform_local_update_and_get_parameters called with config: {config}")
        print(f"  [QA Agent FL] Parameters before local update: {self._params_to_repr(self.federated_parameters)}")
        
        updated_parameters_list = []
        for params_array in self.federated_parameters:
            # Ensure the random update has the same dtype as the parameters array
            update = np.random.uniform(-0.05, 0.05, params_array.shape).astype(params_array.dtype)
            updated_array = params_array + update
            updated_array = np.clip(updated_array, 0, 1)  # Ensure params stay in [0,1]
            updated_parameters_list.append(updated_array)
        
        self.federated_parameters = updated_parameters_list
        print(f"  [QA Agent FL] Parameters after local update: {self._params_to_repr(self.federated_parameters)}")
        return self.federated_parameters

    def evaluate_global_parameters(self, server_parameters: List[np.ndarray]) -> Tuple[float, float]:
        """
        Evaluate the global parameters received from the server against a set of ideal parameters.
        Loss is calculated as Mean Squared Error (MSE) against these ideal parameters.
        Accuracy is derived from the RMSE (1 - sqrt(MSE)), clipped between 0 and 1.

        Args:
            server_parameters: The global model parameters from the server.

        Returns:
            A tuple (loss, accuracy).
        """
        print(f"  [QA Agent FL] evaluate_global_parameters called with server parameters: {self._params_to_repr(server_parameters)}")
        
        if not self.ideal_federated_parameters or not server_parameters or len(self.ideal_federated_parameters) != len(server_parameters):
            print("  [QA Agent FL WARNING] Parameter mismatch (ideal vs server) or empty parameters in evaluate_global_parameters.")
            return 1.0, 0.0 # High loss, zero accuracy

        mse_values = []
        for ideal_param_array, server_param_array in zip(self.ideal_federated_parameters, server_parameters):
            if ideal_param_array.shape != server_param_array.shape:
                print("  [QA Agent FL WARNING] Shape mismatch between ideal and server parameters in evaluate_global_parameters.")
                # Attempt to reshape or pad might be an option, but for now, return high loss
                return 1.0, 0.0 # High loss, zero accuracy
            squared_diff = (ideal_param_array - server_param_array) ** 2
            mse_values.append(np.mean(squared_diff))
        
        if not mse_values:
            overall_mse = 1.0 # Default to high loss if no valid comparisons
            print("  [QA Agent FL WARNING] No comparable elements found for loss calculation in evaluate_global_parameters.")
        else:
            overall_mse = np.mean(mse_values) # Average MSE if multiple parameter arrays
        
        # Accuracy derived from RMSE: 1 - sqrt(MSE), clipped to [0, 1]
        # This means RMSE of 0 = 1.0 accuracy, RMSE of 1.0 (or >1) = 0.0 accuracy.
        accuracy = np.clip(1.0 - np.sqrt(overall_mse), 0.0, 1.0)
        
        print(f"  [QA Agent FL] Evaluation - MSE Loss (vs ideal): {overall_mse}, Accuracy: {accuracy}")
        return float(overall_mse), float(accuracy)

    def _params_to_repr(self, params: Any) -> Any: # More general input type for robustness
        if isinstance(params, list):
            if not params: # Empty list
                return []
            if all(isinstance(p, np.ndarray) for p in params):
                return [arr.tolist() for arr in params]
            else:
                # It's a list, but not all elements are np.ndarray
                print(f"  [QA Agent FL WARNING] _params_to_repr received a list, but not all elements are np.ndarray.")
                repr_list = []
                for i, elem in enumerate(params):
                    elem_type = type(elem)
                    elem_val_str = str(elem.tolist() if isinstance(elem, np.ndarray) else elem)
                    print(f"    Elem {i} - Type: {elem_type}, Value: {elem_val_str[:100]}{'...' if len(elem_val_str) > 100 else ''}")
                    # For logging purposes, returning string representations might be clearer if types are mixed
                    repr_list.append(f"(Type: {elem_type.__name__}) {elem_val_str[:50]}") 
                return repr_list # Return a list of detailed string representations
        elif isinstance(params, np.ndarray):
            # This case should ideally not be hit if params are always List[np.ndarray] in FL context
            print("  [QA Agent FL WARNING] _params_to_repr received a single np.ndarray, expected List[np.ndarray] in FL context. Wrapping it in a list for representation.")
            return [params.tolist()] # Wrap in list for consistent representation
        else:
            # Neither a list nor a direct np.ndarray
            val_str = str(params)
            print(f"  [QA Agent FL WARNING] _params_to_repr received unexpected type: {type(params)}. Value: {val_str[:100]}{'...' if len(val_str) > 100 else ''}")
            return val_str

    def evaluate_and_reward(self, report_json_string: str):
        report = self._parse_report(report_json_string)
        if not report:
            print("QA Agent: Could not process report. No rewards will be evaluated.")
            return

        print(f"\nQA Agent: Evaluating {len(self.milestones)} milestones against the report for crew '{self.crew_id}'...")
        granted_rewards_count = 0

        for milestone in self.milestones:
            reward_granted = False
            reason_for_grant = ""
            evaluation_details = [] # To provide more feedback

            if isinstance(milestone, TaskCompletionMilestone):
                task_found = False
                for task_perf in report.task_breakdown:
                    if task_perf.task_description == milestone.task_name:
                        task_found = True
                        evaluation_details.append(f"Task '{task_perf.task_description}': Status '{task_perf.status}' (Expected: '{milestone.expected_status}'), Errors {len(task_perf.errors_associated)} (Max: {milestone.max_errors_associated})")
                        if task_perf.status == milestone.expected_status and len(task_perf.errors_associated) <= milestone.max_errors_associated:
                            reward_granted = True
                            reason_for_grant = f"Milestone '{milestone.milestone_id}': Task '{milestone.task_name}' completed successfully as per criteria."
                            # Agent-specific reward for TaskCompletion
                            if reward_granted:
                                contributing_agents = task_perf.agents_involved
                                self._mock_grant_reward(milestone.reward_amount, reason_for_grant, agent_ids=contributing_agents if contributing_agents else None)
                                granted_rewards_count += 1
                                continue # Move to next milestone
                        break 
                if not task_found:
                    evaluation_details.append(f"Task '{milestone.task_name}' not found in report.")
            
            elif isinstance(milestone, CrewPerformanceMilestone):
                conditions_met_flags = []
                if milestone.max_crew_duration_seconds is not None:
                    met = report.metrics.crew_run_duration_seconds is not None and report.metrics.crew_run_duration_seconds <= milestone.max_crew_duration_seconds
                    conditions_met_flags.append(met)
                    evaluation_details.append(f"Crew duration {report.metrics.crew_run_duration_seconds:.2f}s {'<=' if met else '>'} {milestone.max_crew_duration_seconds:.2f}s ({'MET' if met else 'NOT MET'})")
                
                if milestone.max_total_errors is not None:
                    met = report.metrics.error_count <= milestone.max_total_errors
                    conditions_met_flags.append(met)
                    evaluation_details.append(f"Total errors {report.metrics.error_count} {'<=' if met else '>'} {milestone.max_total_errors} ({'MET' if met else 'NOT MET'})")

                if milestone.min_tasks_completed is not None:
                    completed_tasks = sum(1 for task_item in report.task_breakdown if task_item.status == 'Completed')
                    met = completed_tasks >= milestone.min_tasks_completed
                    conditions_met_flags.append(met)
                    evaluation_details.append(f"Tasks completed {completed_tasks} {'>=' if met else '<'} {milestone.min_tasks_completed} ({'MET' if met else 'NOT MET'})")
                
                if conditions_met_flags and all(conditions_met_flags):
                    reward_granted = True
                    reason_for_grant = f"Milestone '{milestone.milestone_id}': Crew performance criteria met."
                    # Agent-specific reward for CrewPerformance
                    if reward_granted:
                        agent_roles_in_summary = []
                        if report.agent_performance_summary:
                            for item in report.agent_performance_summary: # agent_performance_summary is List[Dict]
                                agent_role = item.get('agent_role')
                                if agent_role: # Ensure agent_role is not None or empty
                                    agent_roles_in_summary.append(agent_role)
                        self._mock_grant_reward(milestone.reward_amount, reason_for_grant, agent_ids=agent_roles_in_summary if agent_roles_in_summary else None)
                        granted_rewards_count += 1
                        continue # Move to next milestone

            elif isinstance(milestone, ExternalStateMilestone):
                actual_value_str = self._query_external_state(milestone.target_system, milestone.query_details)
                evaluation_details.append(f"External State '{milestone.target_system} - {milestone.query_details}': Expected '{milestone.expected_value}', Got '{actual_value_str}', Op: '{milestone.comparison_operator}'")

                if actual_value_str is not None:
                    expected_value_str = str(milestone.expected_value)
                    met_condition = False
                    try:
                        if milestone.comparison_operator == "equals":
                            met_condition = (actual_value_str == expected_value_str)
                        elif milestone.comparison_operator == "contains":
                            met_condition = (expected_value_str in actual_value_str)
                        elif milestone.comparison_operator in [
                            "greater_than", "less_than", 
                            "greater_than_or_equals", "less_than_or_equals"
                        ]:
                            actual_numeric = float(actual_value_str)
                            expected_numeric = float(expected_value_str)
                            if milestone.comparison_operator == "greater_than":
                                met_condition = (actual_numeric > expected_numeric)
                            elif milestone.comparison_operator == "less_than":
                                met_condition = (actual_numeric < expected_numeric)
                            elif milestone.comparison_operator == "greater_than_or_equals":
                                met_condition = (actual_numeric >= expected_numeric)
                            elif milestone.comparison_operator == "less_than_or_equals":
                                met_condition = (actual_numeric <= expected_numeric)
                        elif milestone.comparison_operator == "matches_regex":
                            try:
                                met_condition = bool(re.search(expected_value_str, actual_value_str))
                            except re.error as regex_err:
                                evaluation_details.append(f"Regex error for pattern '{expected_value_str}': {regex_err}")
                                met_condition = False 
                        elif milestone.comparison_operator == "is_true":
                            met_condition = actual_value_str.lower() in ["true", "1", "yes"]
                        elif milestone.comparison_operator == "is_false":
                            met_condition = actual_value_str.lower() in ["false", "0", "no"]
                        elif milestone.comparison_operator == "is_empty":
                            met_condition = (not actual_value_str) 
                        elif milestone.comparison_operator == "is_not_empty":
                            met_condition = bool(actual_value_str)
                        else:
                            evaluation_details.append(f"Unsupported comparison operator: '{milestone.comparison_operator}'")
                            met_condition = False # Ensure met_condition is defined
                            
                    except ValueError: 
                        evaluation_details.append(f"Numeric conversion error for operator '{milestone.comparison_operator}': Values '{actual_value_str}' or '{expected_value_str}' may not be valid numbers.")
                        met_condition = False 
                    except Exception as e: 
                        evaluation_details.append(f"Unexpected error during comparison for operator '{milestone.comparison_operator}': {e}")
                        met_condition = False 

                    if met_condition:
                        reward_granted = True 
                        reason_for_grant = f"Milestone '{milestone.milestone_id}': External state condition met for operator '{milestone.comparison_operator}'."
                        self._mock_grant_reward(milestone.reward_amount, reason_for_grant)
                        granted_rewards_count += 1
                        continue # Move to next milestone

            # If reward was not granted for this milestone, print evaluation details
            if not reward_granted and evaluation_details:
                print(f"  Milestone '{milestone.milestone_id}' ({milestone.description}): Conditions NOT met. Details: {evaluation_details}")
            elif not reward_granted:
                print(f"  Milestone '{milestone.milestone_id}' ({milestone.description}): Conditions NOT met or not applicable.")

        print(f"QA Agent: Evaluation complete. {granted_rewards_count} reward(s) granted.")

# --- Example Usage ---
if __name__ == '__main__':
    # Define path to the milestones configuration file
    CONFIG_FILE_PATH = Path(__file__).parent.parent / "config" / "milestones_config.yaml"

    # --- Sample Report Data (as before) ---
    sample_report_json_str = """
    {
        "original_task_description": "Analyze blockchain transaction data and deploy a new smart contract based on findings.",
        "metrics": {
            "total_events_processed": 150,
            "crew_run_duration_seconds": 115.5,
            "error_count": 0,
            "total_agents_involved": 3,
            "total_tool_calls": 10,
            "total_tasks_identified": 2
        },
        "task_breakdown": [
            {
                "task_description": "Perform Data Analysis",
                "status": "Completed",
                "duration_seconds": 60.5,
                "errors_associated": [],
                "contributing_agents": ["DataAnalyzerAgent", "ResearcherAgent"],
                "events_in_task": [],
                "agents_involved": ["AnalyzerAgent"],
                "tools_used": ["DataQueryTool", "AnalysisTool"]
            },
            {
                "task_description": "Deploy Smart Contract",
                "status": "Completed",
                "duration_seconds": 30.0,
                "errors_associated": [],
                "contributing_agents": ["SmartContractAgent"],
                "events_in_task": [],
                "agents_involved": ["DeployerAgent"],
                "tools_used": ["CompilerTool", "DeploymentTool"]
            }
        ],
        "agent_performance_summary": [
            {
                "agent_role": "AnalyzerAgent",
                "total_executions": 1,
                "total_duration_seconds": 60.5,
                "avg_duration_seconds": 60.5,
                "errors_encountered": 0
            },
            {
                "agent_role": "DeployerAgent",
                "total_executions": 1,
                "total_duration_seconds": 30.0,
                "avg_duration_seconds": 30.0,
                "errors_encountered": 0
            }
        ],
        "tool_usage_summary": [],
        "identified_errors": [],
        "efficiency_observations": [],
        "potential_bottlenecks": [],
        "recommendations": []
    }
    """

    print("--- Starting QA Agent Test (Scenario 1: Success) ---")
    # Ensure the config directory exists, though write_to_file should handle it for the file itself
    CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # For demonstration, if the config file doesn't exist, we could write the default milestones to it.
    # However, in a real scenario, this file would be managed externally.
    # We are assuming the previous write_to_file call successfully created milestones_config.yaml

    # Instantiate tools
    blockchain_tool = BlockchainTool()
    database_tool = DatabaseTool()
    api_tool = APITool()

    external_tools_suite = {
        "Blockchain": blockchain_tool,
        "Database": database_tool,
        "API": api_tool  # Assuming one of your milestones uses 'API' as target_system
    }

    qa_agent = QAAgent(config_file_path=str(CONFIG_FILE_PATH), external_tools=external_tools_suite, crew_id="test_crew_001")
    
    # Check if milestones were loaded, otherwise, the agent won't do much
    if not qa_agent.milestones:
        print("No milestones loaded. Exiting test.")
    else:
        # Modify mock states for specific scenarios if needed, or rely on defaults
        # Example: qa_agent.mock_external_states["Blockchain"]["contract_0xContractC_property_isActive"] = "false" # for a failing test
        qa_agent.evaluate_and_reward(report_json_string=sample_report_json_str)

    print("\n--- Test with a report that fails some milestones (Scenario 2: Partial Failure) ---")
    failing_report_json_str = """
    {
        "original_task_description": "Analyze blockchain transaction data and deploy a new smart contract based on findings.",
        "metrics": {
            "total_events_processed": 160,
            "crew_run_duration_seconds": 180.0, 
            "error_count": 1,
            "total_agents_involved": 3,
            "total_tool_calls": 12,
            "total_tasks_identified": 3
        },
        "task_breakdown": [
            {
                "task_description": "Perform Data Analysis",
                "status": "Completed",
                "duration_seconds": 70.0,
                "errors_associated": ["Timeout during data fetch"],
                "contributing_agents": ["DataAnalyzerAgent"],
                "events_in_task": [],
                "agents_involved": ["AnalyzerAgent"],
                "tools_used": ["DataQueryTool", "AnalysisTool"]
            },
            {
                "task_description": "Deploy Smart Contract",
                "status": "Failed",
                "duration_seconds": 25.0,
                "errors_associated": ["Insufficient gas"],
                "contributing_agents": ["SmartContractAgent"],
                "events_in_task": [],
                "agents_involved": ["DeployerAgent"],
                "tools_used": ["CompilerTool", "DeploymentTool"]
            },
            {
                "task_description": "Process Raw Data",
                "status": "Completed",
                "duration_seconds": 20.0,
                "errors_associated": ["One warning during processing"],
                "contributing_agents": ["DataProcessorAgent"],
                "events_in_task": [],
                "agents_involved": ["ProcessorAgent"],
                "tools_used": ["CleaningTool"]
            }
        ],
        "agent_performance_summary": [
            {
                "agent_role": "AnalyzerAgent",
                "total_executions": 1,
                "total_duration_seconds": 70.0,
                "avg_duration_seconds": 70.0,
                "errors_encountered": 1
            },
            {
                "agent_role": "DeployerAgent",
                "total_executions": 1,
                "total_duration_seconds": 25.0,
                "avg_duration_seconds": 25.0,
                "errors_encountered": 1
            },
            {
                "agent_role": "ProcessorAgent",
                "total_executions": 1,
                "total_duration_seconds": 85.0,
                "avg_duration_seconds": 85.0,
                "errors_encountered": 1
            }
        ],
        "tool_usage_summary": [],
        "identified_errors": [{"error_message": "Compilation error: XYZ"}],
        "efficiency_observations": [],
        "potential_bottlenecks": [],
        "recommendations": []
    }
    """
    qa_agent.evaluate_and_reward(report_json_string=failing_report_json_str)
    print("\n--- QA Agent Test Complete ---")

