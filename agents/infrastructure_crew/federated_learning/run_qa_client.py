# Flower QA Agent Client Runner
import flwr as fl
import numpy as np
import argparse
from pathlib import Path
import sys
from typing import List, Dict, Tuple, Any

# --- Path Setup --- 
# Add the project root to sys.path to allow imports from other directories like 'agents'
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Attempt to import QAAgent and its tools
# This structure assumes qa_agent.py is in PROJECT_ROOT/agents/infrastructure_crew/qa_sub_crew/agents/
from agents.infrastructure_crew.qa_sub_crew.agents.qa_agent import QAAgent, BlockchainTool, DatabaseTool, APITool

# Define a Flower client that wraps the QAAgent
class QAAgentFlowerClient(fl.client.NumPyClient):
    def _log_params(self, params_name: str, params: Any, context: str):
        log_prefix = f"  [{context}] {params_name}"
        print(f"{log_prefix} - Type: {type(params)}")
        if isinstance(params, list):
            print(f"{log_prefix} - Is List, Len: {len(params)}")
            for i, p_elem in enumerate(params):
                elem_type = type(p_elem)
                elem_val_str = str(p_elem.tolist() if isinstance(p_elem, np.ndarray) else p_elem)
                print(f"{log_prefix}   Elem {i} - Type: {elem_type}, Value: {elem_val_str[:100]}{'...' if len(elem_val_str) > 100 else ''}")
        elif isinstance(params, np.ndarray):
            print(f"{log_prefix} - Is NumPy Array, Shape: {params.shape}, Dtype: {params.dtype}")
            val_str = str(params.tolist())
            print(f"{log_prefix}   Value: {val_str[:100]}{'...' if len(val_str) > 100 else ''}")
        else:
            val_str = str(params)
            print(f"{log_prefix} - Value: {val_str[:100]}{'...' if len(val_str) > 100 else ''}")

    def __init__(self, qa_agent_instance):
        self.qa_agent = qa_agent_instance
        # Parameters are now managed by the qa_agent instance itself.
        print(f"Client {self.qa_agent.crew_id}: Initialized. Will use QAAgent's federated parameters.")

    def get_parameters(self, config):
        print(f"Client {self.qa_agent.crew_id}: get_parameters called by server.")
        return self.qa_agent.get_federated_parameters()

    def fit(self, parameters: List[np.ndarray], config: Dict) -> Tuple[List[np.ndarray], int, Dict]:
        print(f"Client {self.qa_agent.crew_id}: fit called by server.")
        self._log_params("parameters_received", parameters, "QAFC.fit")

        self.qa_agent.set_federated_parameters(parameters)
        print(f"Client {self.qa_agent.crew_id}: Updated local QAAgent parameters.")

        # Perform local update using QAAgent's logic
        updated_parameters = self.qa_agent.perform_local_update_and_get_parameters(config)
        self._log_params("updated_parameters_to_return", updated_parameters, "QAFC.fit")
        
        # Return updated parameters, number of examples (dummy 1), and empty metrics dict
        return updated_parameters, 1, {}

    def evaluate(self, parameters, config):
        print(f"Client {self.qa_agent.crew_id}: evaluate called by server.")
        # QAAgent evaluates the global model (parameters) on its local data/criteria.
        loss, accuracy = self.qa_agent.evaluate_global_parameters(parameters)
        print(f"Client {self.qa_agent.crew_id}: QAAgent evaluated global parameters. Loss: {loss}, Accuracy: {accuracy}")
        
        # Return loss, number of examples, and an accuracy metric from QAAgent's evaluation.
        return loss, 1, {"accuracy": accuracy}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flower QA Agent Client")
    parser.add_argument("--server_address", type=str, default="127.0.0.1:8081", help="Server address and port")
    parser.add_argument(
        "--crew_id",
        type=str,
        default="qa_client_001",
        help=f"Unique ID for this QA agent/crew (default: qa_client_001)"
    )
    parser.add_argument(
        "--config_path",
        type=str,
        default=str(PROJECT_ROOT / "agents" / "infrastructure_crew" / "qa_sub_crew" / "config" / "milestones_config.yaml"),
        help="Path to the QAAgent's milestone configuration file."
    )
    args = parser.parse_args()

    print(f"--- Starting QA Agent Flower Client {args.crew_id} ---")
    print(f"Attempting to connect to server at {args.server_address}")
    print(f"Using Milestone Config Path: {args.config_path}")

    # Instantiate placeholder external tools (as in qa_agent.py's __main__)
    external_tools_suite = {
        "Blockchain": BlockchainTool(),
        "Database": DatabaseTool(),
        "API": APITool()
    }

    # Instantiate your QAAgent
    # The QAAgent class itself doesn't need FL-specific methods for this initial setup,
    # as the QAAgentFlowerClient acts as a wrapper.
    # Later, we might add methods like `get_federated_parameters` to QAAgent directly.
    qa_instance = QAAgent(config_file_path=args.config_path, external_tools=external_tools_suite, crew_id=args.crew_id)

    # Start Flower client using the new recommended way
    fl.client.start_client(
        server_address=args.server_address,
        client=QAAgentFlowerClient(qa_instance).to_client() # Use .to_client()
    )
    print(f"--- QA Agent Flower Client {args.crew_id} finished. ---")
