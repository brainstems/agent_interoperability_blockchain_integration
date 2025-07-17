# federated_learning/marl_trainer.py

import random
import numpy as np
import json
from collections import defaultdict
from typing import Dict, List, Tuple, Any, Optional, Union

# Assuming InventoryMarketingSim and InventoryMarketingSKUData are in marl_environment
from pathlib import Path
from .marl_environment import InventoryMarketingSim, InventoryMarketingSKUData
from agents.infrastructure_crew.infrastructure_agents.registry_manager_agent import RegistryManagerAgent
import asyncio
from datetime import datetime, timezone
import os # Added for path operations


class QLearningAgent:
    def __init__(self,
                 agent_id: str,
                 action_space: List[Any],
                 learning_rate: float = 0.1,
                 discount_factor: float = 0.9,
                 exploration_rate: float = 1.0,
                 exploration_decay_rate: float = 0.995,
                 min_exploration_rate: float = 0.01):
        self.agent_id = agent_id
        self.action_space = action_space
        self.lr = learning_rate
        self.gamma = discount_factor
        self.epsilon = exploration_rate
        self.epsilon_decay = exploration_decay_rate
        self.epsilon_min = min_exploration_rate
        
        # Q-table: defaultdict returning 0 for unvisited state-action pairs
        # Key: state_tuple, Value: Dict[action, q_value]
        self.q_table = defaultdict(lambda: {action: 0.0 for action in self.action_space})

    def choose_action(self, state_tuple: Tuple) -> Any:
        if random.uniform(0, 1) < self.epsilon:
            return random.choice(self.action_space)  # Explore
        else:
            # Exploit: choose the action with the highest Q-value for the current state
            # If all Q-values are the same (e.g., 0 for a new state), pick randomly
            q_values_for_state = self.q_table[state_tuple]
            if not q_values_for_state or len(set(q_values_for_state.values())) == 1:
                 return random.choice(self.action_space)
            return max(q_values_for_state, key=q_values_for_state.get)

    def update_q_table(self, state_tuple: Tuple, action: Any, reward: float, next_state_tuple: Tuple):
        old_value = self.q_table[state_tuple].get(action, 0.0)
        
        # Q-value of the best action in the next state
        next_max_q = 0.0
        if self.q_table[next_state_tuple]: # If next_state has been visited
            next_max_q = max(self.q_table[next_state_tuple].values())
            
        # Q-learning formula
        new_value = old_value + self.lr * (reward + self.gamma * next_max_q - old_value)
        self.q_table[state_tuple][action] = new_value

    def decay_exploration(self):
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def get_policy_as_dict(self) -> Dict:
        # Convert defaultdict to a regular dict for serialization (e.g., JSON)
        # And convert state tuples to strings if necessary for JSON keys
        policy = {}
        for state_tuple, actions_q_values in self.q_table.items():
            policy[str(state_tuple)] = actions_q_values
        return policy

    def load_policy_from_dict(self, policy_dict: Dict):
        self.q_table.clear()
        for state_str, actions_q_values in policy_dict.items():
            # Convert state_str back to tuple (assuming simple tuple of primitives)
            try:
                state_tuple = eval(state_str) # Be cautious with eval on untrusted data
                if isinstance(state_tuple, tuple):
                     self.q_table[state_tuple] = actions_q_values
                else:
                    print(f"Warning: Could not parse state string '{state_str}' back to tuple for agent {self.agent_id}")
            except Exception as e:
                print(f"Error parsing state string '{state_str}' for agent {self.agent_id}: {e}")


class InventoryMarketingMARLTrainer_CTDE:
    def __init__(self,
                 env: InventoryMarketingSim,
                 learning_rate: float = 0.1,
                 discount_factor: float = 0.9,
                 exploration_rate: float = 1.0,
                 exploration_decay_rate: float = 0.995,
                 min_exploration_rate: float = 0.01,
                 registry_manager: Optional[RegistryManagerAgent] = None, # For SharableLearning
                 inventory_bins: Optional[List[Union[int, float]]] = None,
                 sales_bins: Optional[List[Union[int, float]]] = None,
                 orders_bins: Optional[List[Union[int, float]]] = None,
                 promotion_bins: Optional[List[Union[int, float]]] = None,
                ):
        self.registry_manager = registry_manager
        self.env = env
        # self.registry_manager = registry_manager # TODO: Integrate later

        self.inventory_agents: Dict[str, QLearningAgent] = {}
        self.marketing_agents: Dict[str, QLearningAgent] = {}

        for sku_id in self.env.sku_ids:
            inv_agent_id = f"inv_agent_{sku_id}"
            mkt_agent_id = f"mkt_agent_{sku_id}"
            
            self.inventory_agents[sku_id] = QLearningAgent(
                agent_id=inv_agent_id,
                action_space=self.env.action_space_inventory,
                learning_rate=learning_rate,
                discount_factor=discount_factor,
                exploration_rate=exploration_rate,
                exploration_decay_rate=exploration_decay_rate,
                min_exploration_rate=min_exploration_rate
            )
            self.marketing_agents[sku_id] = QLearningAgent(
                agent_id=mkt_agent_id,
                action_space=self.env.action_space_marketing,
                learning_rate=learning_rate,
                discount_factor=discount_factor,
                exploration_rate=exploration_rate,
                exploration_decay_rate=exploration_decay_rate,
                min_exploration_rate=min_exploration_rate
            )
        
        # Define discretization bins (these may need tuning)
        self.inventory_bins = inventory_bins if inventory_bins is not None else [0, 75, 150, 300, 600, 1200]
        self.sales_bins = sales_bins if sales_bins is not None else [0, 20, 40, 60, 80, 120]
        self.orders_bins = orders_bins if orders_bins is not None else [0, 25, 75, 150, 300]
        self.promotion_bins = promotion_bins if promotion_bins is not None else [0, 10, 25, 50, 75, 101] # Max promo 100, so 101 to include it

    def _discretize_value(self, value: float, bins: List[float]) -> int:
        """Converts a continuous value to a discrete bin index."""
        return int(np.digitize(value, bins, right=False)) -1 # np.digitize is 1-indexed

    def _get_state_tuple_for_sku(self, env_observation_sku: Dict, sku_id: str) -> Tuple:
        """Converts environment observation for a SKU into a discrete state tuple."""
        obs_sku = env_observation_sku # This is obs['skus'][sku_id]
        
        inv_level = obs_sku["inventory_level"]
        sales_avg = obs_sku["avg_7_day_sales"]
        outstanding_orders = obs_sku["outstanding_order_quantity"]
        # current_promo is an action by marketing, but part of state for inventory agent
        current_promo = obs_sku["current_promotion_pct"] 

        inv_bin = self._discretize_value(inv_level, self.inventory_bins)
        sales_bin = self._discretize_value(sales_avg, self.sales_bins)
        orders_bin = self._discretize_value(outstanding_orders, self.orders_bins)
        promo_bin = self._discretize_value(current_promo, self.promotion_bins)
        
        # State for Inventory Agent for SKU sku_id:
        # (inv_bin, sales_bin, orders_bin, promo_bin_by_marketing_agent)
        # State for Marketing Agent for SKU sku_id:
        # (inv_bin, sales_bin, orders_bin, its_own_last_promo_action_bin -> promo_bin)
        # For simplicity, we can use the same state tuple structure for both,
        # as the Q-tables are separate.
        return (inv_bin, sales_bin, orders_bin, promo_bin)

    def train(self, num_episodes: int):
        training_run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        print(f"Starting MARL training run ID: {training_run_id} for {num_episodes} episodes...")
        print(f"Starting MARL training for {num_episodes} episodes...")
        episode_rewards = []

        for episode in range(num_episodes):
            current_env_obs = self.env.reset()
            current_sku_observations = current_env_obs["skus"]
            
            done = False
            total_episode_reward = 0
            
            # Store states and actions for updates
            # {sku_id: (state_tuple, action)}
            inventory_s_a_map: Dict[str, Tuple[Tuple, Any]] = {}
            marketing_s_a_map: Dict[str, Tuple[Tuple, Any]] = {}

            while not done:
                inventory_actions_for_env: Dict[str, int] = {}
                marketing_actions_for_env: Dict[str, int] = {}

                # Agents choose actions based on current discretized states
                for sku_id in self.env.sku_ids:
                    sku_obs_data = current_sku_observations[sku_id]
                    state_tuple = self._get_state_tuple_for_sku(sku_obs_data, sku_id)
                    
                    inv_action = self.inventory_agents[sku_id].choose_action(state_tuple)
                    mkt_action = self.marketing_agents[sku_id].choose_action(state_tuple)
                    
                    inventory_actions_for_env[sku_id] = inv_action
                    marketing_actions_for_env[sku_id] = mkt_action
                    
                    inventory_s_a_map[sku_id] = (state_tuple, inv_action)
                    marketing_s_a_map[sku_id] = (state_tuple, mkt_action)

                # Step the environment with chosen actions
                next_env_obs, team_reward, done, info = self.env.step(
                    inventory_actions_for_env, marketing_actions_for_env
                )
                next_sku_observations = next_env_obs["skus"]
                total_episode_reward += team_reward

                # Update Q-tables for all agents (CTDE: all use shared team_reward)
                for sku_id in self.env.sku_ids:
                    prev_inv_state, inv_action = inventory_s_a_map[sku_id]
                    prev_mkt_state, mkt_action = marketing_s_a_map[sku_id]
                    
                    # Get next state tuple for this SKU
                    next_sku_obs_data = next_sku_observations[sku_id]
                    next_state_tuple = self._get_state_tuple_for_sku(next_sku_obs_data, sku_id)
                    
                    self.inventory_agents[sku_id].update_q_table(
                        prev_inv_state, inv_action, team_reward, next_state_tuple
                    )
                    self.marketing_agents[sku_id].update_q_table(
                        prev_mkt_state, mkt_action, team_reward, next_state_tuple
                    )
                
                current_sku_observations = next_sku_observations

            # End of episode
            episode_rewards.append(total_episode_reward)
            for sku_id in self.env.sku_ids:
                self.inventory_agents[sku_id].decay_exploration()
                self.marketing_agents[sku_id].decay_exploration()

            if (episode + 1) % 100 == 0: # Print progress
                avg_reward = np.mean(episode_rewards[-100:])
                print(f"Episode {episode + 1}/{num_episodes} | Avg Reward (last 100): {avg_reward:.2f} | Epsilon Inv: {self.inventory_agents[self.env.sku_ids[0]].epsilon:.3f}")
        
        print("Training complete.")
        self.publish_and_save_policies(training_run_id=training_run_id)
        return episode_rewards

    def publish_and_save_policies(self, training_run_id: str, base_path: str = "./marl_policies_store"):
        if not os.path.exists(base_path):
            os.makedirs(base_path)
        
        trainer_entity_id = "InventoryMarketingMARLTrainer_v1"

        for sku_id in self.env.sku_ids:
            agents_to_publish = {
                "inventory_agent": self.inventory_agents[sku_id],
                "marketing_agent": self.marketing_agents[sku_id]
            }

            for agent_type_key, agent_instance in agents_to_publish.items():
                policy_dict = agent_instance.get_policy_as_dict()
                policy_filename = f"{agent_type_key}_policy_{sku_id}_{training_run_id}.json"
                policy_filepath = os.path.join(base_path, policy_filename)
                policy_file_uri = f"file://{os.path.abspath(policy_filepath)}"

                # Save policy to local file
                with open(policy_filepath, "w") as f:
                    json.dump(policy_dict, f, indent=2)
                print(f"Saved policy for {agent_instance.agent_id} to {policy_filepath}")

                if self.registry_manager:
                    learning_content = {
                        "policy_uri": policy_file_uri,
                        "format": "q_table_json",
                        "agent_id": agent_instance.agent_id,
                        "sku_id": sku_id,
                        "training_run_id": training_run_id
                    }
                    sharable_learning_object = SharableLearning(
                        source_entity_id=trainer_entity_id,
                        learning_type="marl_q_table_policy_uri",
                        content=json.dumps(learning_content), # Content is a JSON string detailing the URI and format
                        task_description=f"{agent_type_key.replace('_', ' ').title()} Q-table policy URI for SKU {sku_id} from training run {training_run_id}. For Inventory-Marketing coordination game.",
                        keywords=["marl", "q_learning", agent_type_key, sku_id, "inventory_marketing_game", training_run_id],
                        version=training_run_id,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        metadata={
                            "hyperparameters": {
                                "learning_rate": agent_instance.lr,
                                "discount_factor": agent_instance.gamma,
                                "initial_epsilon": agent_instance.epsilon, # This would be initial, not current
                            },
                            "discretization_bins": {
                                "inventory_bins": self.inventory_bins,
                                "sales_bins": self.sales_bins,
                                "orders_bins": self.orders_bins
                            }
                        }
                    )
                    try:
                        asyncio.run(self.registry_manager.publish_learning(sharable_learning_object))
                        print(f"Successfully published policy URI for {agent_instance.agent_id} to registry.")
                    except Exception as e:
                        print(f"Error publishing policy URI for {agent_instance.agent_id} to registry: {e}")
                else:
                    print(f"Registry manager not configured. Skipping publishing for {agent_instance.agent_id}.")

    def load_policies(self, base_path: str = "./marl_policies"):
        import os
        for sku_id in self.env.sku_ids:
            try:
                with open(os.path.join(base_path, f"inv_policy_{sku_id}.json"), "r") as f:
                    inv_policy_dict = json.load(f)
                    self.inventory_agents[sku_id].load_policy_from_dict(inv_policy_dict)
                with open(os.path.join(base_path, f"mkt_policy_{sku_id}.json"), "r") as f:
                    mkt_policy_dict = json.load(f)
                    self.marketing_agents[sku_id].load_policy_from_dict(mkt_policy_dict)
            except FileNotFoundError:
                print(f"Warning: Policy file not found for SKU {sku_id} in {base_path}. Using fresh Q-tables.")
            except Exception as e:
                 print(f"Error loading policy for SKU {sku_id}: {e}")
        print(f"Policies loaded from {base_path} (if found).")

    # TODO: publish_policies_to_registry method using SharableLearning


# Example Usage (for testing the trainer directly)
if __name__ == "__main__":
    # Load SKU configurations from CSV
    # Assuming sample_sku_data.csv is in the same directory as marl_environment.py
    # and marl_trainer.py is also in federated_learning directory.
    csv_path = Path(__file__).parent / "sample_sku_data.csv"
    try:
        loaded_sku_configs = InventoryMarketingSim.load_sku_configs_from_csv(str(csv_path))
        print(f"Successfully loaded {len(loaded_sku_configs)} SKU configurations from {csv_path} for trainer.")
    except Exception as e:
        print(f"Error loading SKU configurations for trainer: {e}")
        loaded_sku_configs = [] # Fallback or exit
        import sys
        sys.exit(1)

    # Ensure we have enough SKUs if num_top_skus_to_manage is high, or adjust num_top_skus_to_manage
    num_skus_to_manage_in_sim = min(len(loaded_sku_configs), 5) # Manage up to 5 SKUs from CSV
    if not loaded_sku_configs:
        print("No SKU configurations loaded for trainer, exiting example.")
        import sys
        sys.exit(1)

    sim_env = InventoryMarketingSim(sku_config_list=loaded_sku_configs, num_top_skus_to_manage=num_skus_to_manage_in_sim)
    
    # Initialize trainer
    # The trainer will now use its own updated default bins, including for promotion.
    trainer = InventoryMarketingMARLTrainer_CTDE(
        env=sim_env,
        exploration_decay_rate=0.99, # Faster decay for quick test
        min_exploration_rate=0.1    # Higher min epsilon for quick test
        # registry_manager=registry_manager # Uncomment to test publishing
    )

    print("Starting training...")
    # Reduced episodes for a quick test, can be increased for actual training
    trainer.train(num_episodes=5) 
    print("Training finished.")

    # Save policies
    run_id = f"test_run_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    # Assuming RegistryManagerAgent is not set up for this direct test, 
    # policies will only be saved locally.
    trainer.publish_and_save_policies(training_run_id=run_id)
    print(f"Policies saved locally for run_id: {run_id} in ./marl_policies_store/")

    # Example: Load policies into a new trainer instance (optional)
    # policies_path_to_load = f"./marl_policies_store/{run_id}/{sim_env.sku_ids[0]}/inv_agent_{sim_env.sku_ids[0]}_policy.json"
    # print(f"Example path for one policy: {policies_path_to_load}")
    # new_trainer = InventoryMarketingMARLTrainer_CTDE(env=sim_env)
    # new_trainer.load_policies(base_path=f"./marl_policies_store/{run_id}") # Pass the run_id folder
    # print("Policies loaded into new_trainer.")

    # Example: Test loaded policies (run a few more episodes with exploration off)
    # print("Testing loaded policies...")
    # if new_trainer.env.sku_ids: # Check if SKUs exist
    #     for agent in new_trainer.inventory_agents.values():
    #         agent.epsilon = 0 # Turn off exploration
    #     for agent in new_trainer.marketing_agents.values():
    #         agent.epsilon = 0 # Turn off exploration
    #     new_trainer.train(num_episodes=1) # Run one episode with learned policies
    # print("Test with loaded policies finished.")xploration_rate=0.1,
    #     registry_manager=registry_manager_instance # Pass the instance
    # )

    # rewards_history = trainer.train(num_episodes=500) # Run a small number of episodes for testing
    
    # The publish_and_save_policies is now called at the end of train()
    # trainer.publish_and_save_policies(training_run_id="manual_test_run_001") # Or call manually if needed

    # Basic plot of rewards
    try:
        import matplotlib.pyplot as plt
        plt.plot(rewards_history)
        plt.title("Total Episode Rewards Over Time")
        plt.xlabel("Episode")
        plt.ylabel("Total Reward")
        # Smoothed rewards
        smoothing_window = 50
        if len(rewards_history) >= smoothing_window:
            smoothed_rewards = np.convolve(rewards_history, np.ones(smoothing_window)/smoothing_window, mode='valid')
            plt.plot(np.arange(smoothing_window-1, len(rewards_history)), smoothed_rewards, label=f'Smoothed (window {smoothing_window})')
            plt.legend()
        plt.show()
    except ImportError:
        print("Matplotlib not found. Skipping reward plot.")
