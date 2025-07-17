# federated_learning/marl_environment.py

from typing import Dict, List, Tuple, Any, Optional
from pydantic import BaseModel, Field
import numpy as np
import random
import csv
from pathlib import Path

class InventoryMarketingSKUData(BaseModel):
    sku_id: str
    initial_inventory: int
    # initial_average_daily_sales: float # Replaced by base_demand_mean for initialization consistency
    initial_outstanding_orders: int
    # current_promotion_percentage: float = 0.0 # This will be an action, not static data

    # Core SKU economic and operational parameters
    unit_cost: float = Field(default=10.0, gt=0) # Cost to acquire/produce one unit
    price_per_unit: float = Field(default=20.0, gt=0) # Selling price per unit
    holding_cost_rate: float = Field(default=0.01, ge=0) # Cost to hold inventory, as a % of unit_cost per period
    shortage_cost_per_unit: float = Field(default=5.0, ge=0) # Penalty for unmet demand
    reorder_cost: float = Field(default=50.0, ge=0) # Fixed cost per reorder placed

    # Demand characteristics
    base_demand_mean: float = Field(default=50.0, gt=0) # Average base demand per period
    demand_std_dev_factor: float = Field(default=0.2, ge=0) # Std dev of demand as factor of mean
    max_promotion_lift_factor: float = Field(default=1.5, ge=1.0) # Max demand multiplier at full promotion (e.g., 1.5 = 50% lift)

    # Inventory and Reordering
    lead_time_periods: int = Field(default=2, ge=0) # Number of periods for reorder to arrive
    max_inventory_capacity: int = Field(default=1000, ge=0)
    
    # Simulation state - managed per SKU, initialized from above where applicable
    # These are not part of the input config but are set during simulation reset/init
    current_inventory: int = 0
    current_average_daily_sales: float = 0.0 # This will be dynamically calculated
    current_outstanding_orders: int = 0
    current_promotion_percentage: float = 0.0 # This will be set by marketing agent action in the sim state


class InventoryMarketingSim:
    def __init__(self, sku_config_list: List[InventoryMarketingSKUData], num_top_skus_to_manage: int = 10):
        if not sku_config_list or len(sku_config_list) < num_top_skus_to_manage:
            raise ValueError(f"Must provide at least {num_top_skus_to_manage} SKU configurations.")

        self.sku_configs: Dict[str, InventoryMarketingSKUData] = {
            sku.sku_id: sku for sku in sku_config_list[:num_top_skus_to_manage]
        }
        self.sku_ids: List[str] = list(self.sku_configs.keys())
        self.num_skus = len(self.sku_ids)

        # Dynamic state per SKU, re-initialized on reset
        self.current_inventory: Dict[str, int] = {}
        self.current_promotion_pct: Dict[str, int] = {} # {0, 10, 20, 30}
        self.avg_7_day_sales: Dict[str, float] = {}
        self.daily_sales_history: Dict[str, List[int]] = {sku_id: [] for sku_id in self.sku_ids}

        # Orders in transit
        # List of tuples: (quantity_ordered, arrival_day_timestep)
        self.outstanding_orders: Dict[str, List[Tuple[int, int]]] = {sku_id: [] for sku_id in self.sku_ids}
        
        self.current_timestep = 0
        self.action_space_inventory = [0, 50, 100, 200] # Possible reorder quantities
        self.action_space_marketing = [0, 10, 20, 30]   # Possible promotion percentages

        self.reset()

    def _initialize_sku_state(self):
        for sku_id, config in self.sku_configs.items():
            config = self.sku_configs[sku_id] # config is the InventoryMarketingSKUData instance
            
            # Initialize dynamic simulation states based on config
            self.current_inventory[sku_id] = config.initial_inventory
            self.current_promotion_pct[sku_id] = 0.0 # Start with no promotion
            self.avg_7_day_sales[sku_id] = config.base_demand_mean # Initialize with base demand mean
            self.daily_sales_history[sku_id] = [int(config.base_demand_mean)] * 7 # Seed history
            # outstanding_orders for this SKU is already initialized to [] in __init__
            # config.current_inventory, config.current_average_daily_sales etc. are not used here
            # as they were intended for dynamic state within the config object itself, which we simplify.
            self.outstanding_orders[sku_id] = []
        self.current_timestep = 0

    def reset(self) -> Dict[str, Any]:
        """Resets the environment to an initial state and returns the initial observation."""
        self._initialize_sku_state()
        return self._get_observation()

    def _get_observation(self) -> Dict[str, Any]:
        """Constructs the observation dictionary for the MARL agents."""
        obs = {}
        for sku_id in self.sku_ids:
            obs[sku_id] = {
                "inventory_level": self.current_inventory[sku_id],
                "current_promotion_pct": self.current_promotion_pct[sku_id],
                "avg_7_day_sales": self.avg_7_day_sales[sku_id],
                "outstanding_order_quantity": sum(order[0] for order in self.outstanding_orders[sku_id])
            }
        return {"skus": obs, "timestep": self.current_timestep}

    def step(self, 
             inventory_actions: Dict[str, int], # {sku_id: reorder_qty from self.action_space_inventory}
             marketing_actions: Dict[str, int]  # {sku_id: promo_pct from self.action_space_marketing}
            ) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        """
        Processes one timestep of the simulation.
        Args:
            inventory_actions: Actions from the Inventory Agent.
            marketing_actions: Actions from the Marketing Agent.
        Returns:
            observation (Dict): The next state observation.
            reward (float): The team reward for the timestep.
            done (bool): Whether the episode has ended.
            info (Dict): Additional info (e.g., individual cost/profit components).
        """
        if not (set(inventory_actions.keys()) == set(self.sku_ids) and set(marketing_actions.keys()) == set(self.sku_ids)):
             raise ValueError("Actions must be provided for all managed SKUs.")

        total_profit_for_step = 0.0
        total_holding_cost_for_step = 0.0
        total_stockout_penalty_for_step = 0.0
        
        detailed_info = {
            "sku_details": {},
            "total_profit": 0,
            "total_holding_cost": 0,
            "total_stockout_penalty": 0,
            "total_units_sold": 0,
            "total_units_stocked_out": 0,
            "total_units_reordered":0,
        }

        # 1. Process arriving orders (before demand calculation for the day)
        for sku_id in self.sku_ids:
            arrived_today = []
            remaining_orders = []
            for qty, arrival_day in self.outstanding_orders[sku_id]:
                if arrival_day == self.current_timestep:
                    arrived_today.append(qty)
                else:
                    remaining_orders.append((qty, arrival_day))
            
            total_arrived = sum(arrived_today)
            self.current_inventory[sku_id] = min(
                self.current_inventory[sku_id] + total_arrived,
                self.sku_configs[sku_id].max_inventory_capacity 
            )
            self.outstanding_orders[sku_id] = remaining_orders
            detailed_info["sku_details"].setdefault(sku_id, {})["units_arrived"] = total_arrived


        # 2. Apply marketing actions & Calculate demand
        # 3. Fulfill demand & Calculate profit/stockouts
        # 4. Apply inventory actions (place new orders)
        # 5. Calculate holding costs
        
        for sku_id in self.sku_ids:
            sku_info = detailed_info["sku_details"].setdefault(sku_id, {})
            config = self.sku_configs[sku_id]

            # Apply marketing action
            promo_action_value = marketing_actions.get(sku_id, 0)
            if promo_action_value not in self.action_space_marketing:
                raise ValueError(f"Invalid promotion value {promo_action_value} for SKU {sku_id}")
            self.current_promotion_pct[sku_id] = promo_action_value # This is the direct % like 10, 20

            # Calculate demand
            # Normalize promotion intensity (0 to 1) based on action space
            max_promo_in_action_space = max(self.action_space_marketing) if self.action_space_marketing else 1 # Avoid div by zero
            normalized_promo_intensity = self.current_promotion_pct[sku_id] / max_promo_in_action_space if max_promo_in_action_space > 0 else 0
            
            # Calculate effective lift factor based on normalized intensity and max_promotion_lift_factor
            # If max_promotion_lift_factor = 1.5, it means 50% lift at full promo.
            # Lift is (max_promotion_lift_factor - 1). Apply normalized intensity to this lift.
            effective_lift_factor = 1 + (normalized_promo_intensity * (config.max_promotion_lift_factor - 1))
            
            demand_with_promo = config.base_demand_mean * effective_lift_factor
            
            # Add stochasticity using demand_std_dev_factor
            demand_std_dev = config.base_demand_mean * config.demand_std_dev_factor # Std dev on base demand
            simulated_demand = max(0, int(np.random.normal(loc=demand_with_promo, scale=demand_std_dev)))
            sku_info["simulated_demand"] = simulated_demand
            
            # Fulfill demand
            units_sold = min(self.current_inventory[sku_id], simulated_demand)
            stockout_units = max(0, simulated_demand - self.current_inventory[sku_id])
            
            self.current_inventory[sku_id] -= units_sold
            sku_info["units_sold"] = units_sold
            sku_info["stockout_units"] = stockout_units
            detailed_info["total_units_sold"] += units_sold
            detailed_info["total_units_stocked_out"] += stockout_units

            # Update sales history and average
            self.daily_sales_history[sku_id].pop(0)
            self.daily_sales_history[sku_id].append(units_sold)
            self.avg_7_day_sales[sku_id] = np.mean(self.daily_sales_history[sku_id])

            # Calculate profit for this SKU
            profit = (config.price_per_unit - config.unit_cost) * units_sold
            total_profit_for_step += profit
            sku_info["profit"] = profit
            
            # Calculate stockout penalty for this SKU
            stockout_penalty = config.shortage_cost_per_unit * stockout_units
            total_stockout_penalty_for_step += stockout_penalty
            sku_info["stockout_penalty"] = stockout_penalty

            # Apply inventory action (place new order)
            reorder_qty = inventory_actions.get(sku_id, 0)
            sku_reorder_cost_this_step = 0
            if reorder_qty not in self.action_space_inventory:
                raise ValueError(f"Invalid reorder quantity {reorder_qty} for SKU {sku_id}")
            if reorder_qty > 0:
                current_plus_on_order = self.current_inventory[sku_id] + sum(o[0] for o in self.outstanding_orders[sku_id])
                if current_plus_on_order + reorder_qty <= config.max_inventory_capacity:
                    arrival_day = self.current_timestep + config.lead_time_periods # Use standardized name
                    self.outstanding_orders[sku_id].append((reorder_qty, arrival_day))
                    sku_info["reordered_qty"] = reorder_qty
                    detailed_info["total_units_reordered"] += reorder_qty
                    sku_reorder_cost_this_step = config.reorder_cost # Add reorder cost
                else:
                    sku_info["reordered_qty"] = 0
                    sku_info["reorder_attempt_failed_capacity"] = True
            sku_info["reorder_cost"] = sku_reorder_cost_this_step

            # Calculate holding cost for this SKU (on end-of-day inventory)
            # Holding cost = rate * unit_cost * inventory_level
            holding_cost = config.holding_cost_rate * config.unit_cost * self.current_inventory[sku_id]
            total_holding_cost_for_step += holding_cost
            sku_info["holding_cost"] = holding_cost
            sku_info["end_of_day_inventory"] = self.current_inventory[sku_id]

        # Calculate team reward
        total_reorder_costs_for_step = sum(detailed_info["sku_details"][s_id].get("reorder_cost", 0) for s_id in self.sku_ids)
        team_reward = total_profit_for_step - total_holding_cost_for_step - total_stockout_penalty_for_step - total_reorder_costs_for_step
        
        detailed_info["total_profit"] = total_profit_for_step
        detailed_info["total_holding_cost"] = total_holding_cost_for_step
        detailed_info["total_stockout_penalty"] = total_stockout_penalty_for_step
        detailed_info["total_reorder_costs"] = total_reorder_costs_for_step
        detailed_info["team_reward"] = team_reward

        self.current_timestep += 1
        
        # Define 'done' condition (e.g., after a fixed number of timesteps)
        done = self.current_timestep >= 200 # Example: episode ends after 200 days

        return self._get_observation(), team_reward, done, detailed_info

    @property
    def sku_ids_set(self): # Helper for checking action keys
        return set(self.sku_ids)

    @classmethod
    def load_sku_configs_from_csv(cls, csv_file_path: str) -> List[InventoryMarketingSKUData]:
        """Loads SKU configurations from a CSV file."""
        sku_configs = []
        file_path = Path(csv_file_path)
        if not file_path.is_file():
            raise FileNotFoundError(f"CSV file not found: {csv_file_path}")

        field_types = {
            'initial_inventory': int,
            'initial_outstanding_orders': int,
            'unit_cost': float,
            'price_per_unit': float,
            'holding_cost_rate': float,
            'shortage_cost_per_unit': float,
            'reorder_cost': float,
            'base_demand_mean': float,
            'demand_std_dev_factor': float,
            'max_promotion_lift_factor': float,
            'lead_time_periods': int,
            'max_inventory_capacity': int
        }

        with open(file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row_num, row in enumerate(reader, start=2): # start=2 for 1-based header + 1 for data row
                try:
                    # Convert row values to their correct types
                    typed_row = {}
                    for key, value_str in row.items():
                        if key in field_types:
                            typed_row[key] = field_types[key](value_str)
                        else:
                            typed_row[key] = value_str # sku_id is a string
                    
                    sku_configs.append(InventoryMarketingSKUData(**typed_row))
                except ValueError as e:
                    raise ValueError(f"Error parsing row {row_num} in {csv_file_path}: {e}. Row: {row}")
                except Exception as e:
                    raise RuntimeError(f"Unexpected error processing row {row_num} in {csv_file_path}: {e}. Row: {row}")
        return sku_configs

# Example Usage (for testing the environment directly)
if __name__ == "__main__":
    # Load SKU configurations from CSV
    csv_path = Path(__file__).parent / "sample_sku_data.csv"
    try:
        loaded_sku_configs = InventoryMarketingSim.load_sku_configs_from_csv(str(csv_path))
        print(f"Successfully loaded {len(loaded_sku_configs)} SKU configurations from {csv_path}")
    except Exception as e:
        print(f"Error loading SKU configurations: {e}")
        loaded_sku_configs = [] # Fallback or exit
        # For testing, let's exit if loading fails
        import sys
        sys.exit(1)

    # Ensure we have enough SKUs if num_top_skus_to_manage is high, or adjust num_top_skus_to_manage
    num_skus_to_manage_in_sim = min(len(loaded_sku_configs), 5) # Manage up to 5 SKUs from CSV or all if fewer
    if not loaded_sku_configs:
        print("No SKU configurations loaded, exiting example.")
        import sys
        sys.exit(1)

    env = InventoryMarketingSim(sku_config_list=loaded_sku_configs, num_top_skus_to_manage=num_skus_to_manage_in_sim)
    obs = env.reset()
    print("Initial Observation:", obs)

    total_reward_for_episode = 0
    for day in range(205): # Simulate for a bit longer than episode length
        # Dummy actions: inventory agent orders a bit, marketing agent randomly promotes
        inv_actions = {}
        mkt_actions = {}
        for sku_id_key in env.sku_ids:
            inv_actions[sku_id_key] = random.choice(env.action_space_inventory) if random.random() < 0.3 else 0 # Order sometimes
            mkt_actions[sku_id_key] = random.choice(env.action_space_marketing) if random.random() < 0.5 else 0 # Promote sometimes
        
        next_obs, reward, done, info = env.step(inv_actions, mkt_actions)
        total_reward_for_episode += reward
        
        print(f"\n--- Day {env.current_timestep} ---")
        print(f"Actions Inv: {inv_actions}")
        print(f"Actions Mkt: {mkt_actions}")
        # Print the first SKU's observation for brevity
        if env.sku_ids: # Check if there are any SKUs being managed
            first_sku_id = env.sku_ids[0]
            print(f"Observation ({first_sku_id}): {next_obs['skus'][first_sku_id]}")
        else:
            print("Observation: No SKUs being managed.")
        print(f"Reward: {reward:.2f}")
        print(f"Done: {done}")
        # print(f"Info: {info['sku_details']['SKU_001']}")

        if done:
            print(f"\nEpisode finished after {env.current_timestep} timesteps.")
            print(f"Total reward for episode: {total_reward_for_episode:.2f}")
            break
        obs = next_obs
