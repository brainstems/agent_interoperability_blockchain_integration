# Flower Server
import flwr as fl
import asyncio # For running async publish_learning
import os # Already imported but ensure it's available for abspath
from datetime import datetime, timezone # For SharableLearning timestamps

from agents.infrastructure_crew.infrastructure_agents.registry_manager_agent import RegistryManagerAgent
from agents.infrastructure_crew.schemas.learning_schemas import SharableLearning
import numpy as np
from typing import List, Tuple, Dict, Optional, Union
import os
from flwr.common import Metrics, Parameters, FitRes, Scalar
from flwr.server.client_proxy import ClientProxy

# Define a custom metrics aggregation function for evaluation
def aggregate_weighted_average(metrics: List[Tuple[int, Metrics]]) -> Metrics:
    """Compute weighted average."""
    if not metrics:
        print("  [Server Log] aggregate_weighted_average received no metrics.")
        return {}
    accuracies = [num_examples * m["accuracy"] for num_examples, m in metrics if "accuracy" in m]
    examples = [num_examples for num_examples, m in metrics if "accuracy" in m]
    if not examples or sum(examples) == 0:
        print("  [Server Log] aggregate_weighted_average: No examples or sum of examples is zero for accuracy.")
        return {}
    aggregated_accuracy = sum(accuracies) / sum(examples)
    print(f"  [Server Log] Aggregated accuracy from clients: {aggregated_accuracy}")
    return {"accuracy": aggregated_accuracy}

# Define initial model parameters
# Attempt to load parameters from file, otherwise use default
model_path = "final_federated_model.npz"
if os.path.exists(model_path):
    print(f"Loading model parameters from {model_path}")
    loaded_npz = np.load(model_path)
    # np.savez stores arrays as arr_0, arr_1, ...
    # We need to reconstruct the list of ndarrays in the correct order
    initial_model_weights = [loaded_npz[key] for key in sorted(loaded_npz.files)]
    initial_parameters = fl.common.ndarrays_to_parameters(initial_model_weights)
    print(f"Successfully loaded initial parameters: {initial_model_weights}")
else:
    print(f"No saved model found at {model_path}. Using default initial parameters.")
    # In a real application, you would load your model's initial weights here.
    # For this example, we're just creating a simple NumPy array.
    # Flower expects parameters as a list of NumPy arrays.
    initial_model_weights: List[np.ndarray] = [np.array([0.1, 0.1, 0.1], dtype=np.float32)]
    initial_parameters = fl.common.ndarrays_to_parameters(initial_model_weights)
    print(f"Server starting with default initial parameters: {initial_model_weights}")

# Custom strategy to save model parameters after aggregation
class FedAvgWithSaving(fl.server.strategy.FedAvg):
    def __init__(self, 
                 model_save_path="final_federated_model.npz", 
                 registry_manager: Optional[RegistryManagerAgent] = None,
                 fl_server_id: str = "default_fl_server",
                 model_name_tag: str = "federated_model",
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_save_path = model_save_path
        self.registry_manager = registry_manager
        self.fl_server_id = fl_server_id
        self.model_name_tag = model_name_tag
        print(f"Custom FedAvgWithSaving strategy initialized. Will save models to: {self.model_save_path}")
        if self.registry_manager:
            print(f"  RegistryManagerAgent configured. FL Server ID: {self.fl_server_id}, Model Tag: {self.model_name_tag}")
        else:
            print("  RegistryManagerAgent not configured. Model updates will not be published as learnings.")

    def aggregate_fit(
        self,
        server_round: int,
        results: List[Tuple[ClientProxy, FitRes]],
        failures: List[Union[Tuple[ClientProxy, FitRes], BaseException]],
    ) -> Tuple[Optional[Parameters], Dict[str, Scalar]]:
        """Aggregate fit results using weighted average and save the new global model."""
        # Call the superclass method to perform the actual aggregation
        aggregated_parameters, aggregated_metrics = super().aggregate_fit(
            server_round, results, failures
        )

        if aggregated_parameters is not None:
            # Convert `Parameters` to `List[np.ndarray]`
            aggregated_ndarrays: List[np.ndarray] = fl.common.parameters_to_ndarrays(
                aggregated_parameters
            )
            print(f"  [Custom Strategy] Saving aggregated model parameters for round {server_round} to {self.model_save_path}...")
            np.savez(self.model_save_path, *aggregated_ndarrays)
            print(f"  [Custom Strategy] Aggregated model parameters saved successfully for round {server_round}.")

            if self.registry_manager and aggregated_parameters is not None:
                print(f"  [Custom Strategy] Attempting to publish learning for round {server_round}...")
                try:
                    absolute_model_path = os.path.abspath(self.model_save_path)
                    fit_metrics_summary = {k: v for k, v in aggregated_metrics.items() if isinstance(v, (int, float))}

                    learning_content = {
                        "model_name": f"{self.model_name_tag}_global",
                        "model_version": f"round_{server_round}",
                        "parameters_reference": f"file://{absolute_model_path}",
                        "aggregation_details": {
                            "clients_participated_fit": len(results),
                            "server_round": server_round
                        },
                        "fit_metrics": fit_metrics_summary
                    }

                    learning_object = SharableLearning(
                        source_entity_id=self.fl_server_id,
                        learning_type="federated_model_update",
                        content=learning_content,
                        task_description=f"Global model update from federated learning for '{self.model_name_tag}' after server round {server_round}.",
                        keywords=["federated_learning", self.model_name_tag, "global_model", f"round_{server_round}"]
                    )
                    
                    asyncio.run(self.registry_manager.publish_learning(learning_object))
                    print(f"  [Custom Strategy] Learning published successfully for round {server_round}, ID: {learning_object.learning_id}")

                except Exception as e:
                    print(f"  [Custom Strategy] Error publishing learning for round {server_round}: {e}")
        else:
            print(f"  [Custom Strategy] Aggregation failed for round {server_round}. Model not saved.")

        return aggregated_parameters, aggregated_metrics

# Configuration for RegistryManagerAgent and FL Server specifics
REDIS_URL = "redis://localhost:6379/0" 
FL_SERVER_ID_CONFIG = "fl_server_main_qa" 
MODEL_TAG_CONFIG = "QAModel"             

registry_manager_instance = None
try:
    registry_config = {"redis_url": REDIS_URL, "agent_id": f"registry_for_{FL_SERVER_ID_CONFIG}"}
    registry_manager_instance = RegistryManagerAgent(config=registry_config)
    print(f"RegistryManagerAgent initialized for FL server {FL_SERVER_ID_CONFIG}.")
except Exception as e:
    print(f"Failed to initialize RegistryManagerAgent: {e}. Learnings will not be published.")

# Define strategy
strategy = FedAvgWithSaving(
    fraction_fit=1.0,  # Sample 100% of available clients for training
    min_fit_clients=2,  # Require 2 clients for training rounds
    min_available_clients=2, # Wait for at least 2 clients to be available before starting
    fraction_evaluate=1.0, # Sample 100% of available clients for evaluation
    min_evaluate_clients=2, # Require 2 clients for evaluation rounds
    evaluate_metrics_aggregation_fn=aggregate_weighted_average, # Aggregate client evaluation metrics
    initial_parameters=initial_parameters, # Set initial model parameters
    registry_manager=registry_manager_instance,
    fl_server_id=FL_SERVER_ID_CONFIG,
    model_name_tag=MODEL_TAG_CONFIG,
    model_save_path=model_path
)

# Start Flower server
if __name__ == "__main__":
    print("Starting Flower server with federated evaluation enabled...")
    fl.server.start_server(
        server_address="127.0.0.1:8081",
        config=fl.server.ServerConfig(num_rounds=3),
        strategy=strategy
    )
    print("Flower server finished.")

    # Save the final model parameters
    # The `strategy` object holds the latest aggregated parameters after training concludes.
    # However, `start_server` itself doesn't directly return them in a straightforward way for all strategy types.
    # A common approach is to access them from the strategy if it stores them, or use a custom strategy to save them.
    # For FedAvg, the parameters are accessible via strategy.global_model if it's been set/updated.
    # Let's assume the strategy object might not directly expose final parameters easily after start_server finishes.
    # A more robust way for this example is to modify the strategy to save parameters, or to use a callback if available.
    # For simplicity, if we want to save parameters *during* rounds, we'd need a custom strategy or use on_fit_config_fn carefully.

    # Given our current setup, the `initial_parameters` are what the server starts with,
    # and they get updated round by round. The `strategy` object itself would be the place
    # to inspect for the *final* parameters if the API provided a clean post-run hook or return.

    # Let's adjust to a more direct way: If `start_server` could return results, that would be ideal.
    # Since it doesn't directly return the final parameters, we'll rely on the fact that
    # the `strategy` object is updated. We'll save the parameters that are part of the strategy
    # after the server stops. This is a bit of a conceptual workaround for FedAvg not having a direct post-training save hook.

    # A better way: `start_server` can return a History object which might contain metrics, but not raw parameters.
    # The strategy object itself is the most reliable place to get the parameters.
    # We need to ensure the parameters are accessible *after* start_server has run and updated the strategy.
    
    # The FedAvg strategy doesn't have a public attribute like `strategy.global_parameters` that's guaranteed.
    # The most reliable way is to customize the strategy's `aggregate_fit` or `aggregate_evaluate`
    # to also store/save the parameters. 

    # Let's try a simpler approach for now: save the parameters that were used to *initialize* the last round, 
    # which are effectively the result of the previous round's aggregation.
    # This is not perfect. For true final parameters, a custom strategy is best.

    # Simpler approach for now: We will save the `initial_parameters` that were defined. 
    # This is NOT the trained model, but shows the saving mechanism.
    # To save the *trained* model, we'd need to hook into the strategy's aggregation steps.

    # Let's refine: The `FedAvg` strategy does not inherently store the final global model in an easily accessible public attribute
    # *after* `start_server()` has completed. The parameters are handled internally during the calls.
    # To save the final parameters, we would typically:
    # 1. Create a custom strategy that saves parameters in its `aggregate_fit` method.
    # 2. Or, if the server could return the final parameters from `start_server`, use that.

    # For this exercise, let's assume we want to save the parameters that the server *would have* if it were to run one more round.
    # The `initial_parameters` variable in our script holds the parameters for the *first* round.
    # To get the *final* ones, we need to access them from within the strategy's lifecycle.

    # Let's make a slight modification to `aggregate_weighted_average` to also save parameters passed to it during evaluation,
    # as these are the global parameters for that round.
    # This is a bit of a hack for FedAvg, a proper solution is a custom strategy.

    # The most straightforward way with minimal changes to FedAvg is to recognize that
    # the `initial_parameters` argument to `FedAvg` sets the *starting point*. 
    # The strategy then internally manages the global model. 
    # To get the *final* model, we'd typically need a custom strategy or a callback.

    # Given the limitations, we will demonstrate saving the `initial_parameters` to a file
    # and then show how to load them. This demonstrates the mechanics, though not saving a *trained* model from FedAvg directly.

    final_model_path = "final_federated_model.npz"
    # The `strategy.initial_parameters` are `Parameters` objects. We need to convert them back to ndarrays.
    # However, `strategy.initial_parameters` refers to the *very first* initial parameters.
