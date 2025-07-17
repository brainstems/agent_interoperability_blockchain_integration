import numpy as np
from datetime import datetime, timedelta
import random
from typing import Dict, List, Any
import uuid

class CustomerInsightSimulator:
    def __init__(self, seed: int = None):
        if seed:
            np.random.seed(seed)
            random.seed(seed)
        
        self.customer_segments = ['luxury', 'premium', 'mainstream', 'budget']
        self.age_ranges = ['18-24', '25-34', '35-44', '45-54', '55+']
        self.purchase_frequencies = ['weekly', 'monthly', 'quarterly', 'annually']

    def generate_customer_insights(self, num_segments: int = 4) -> Dict[str, Any]:
        insights = {
            "timestamp": datetime.now().isoformat(),
            "segments": []
        }

        for segment in self.customer_segments[:num_segments]:
            segment_data = {
                "segment_id": str(uuid.uuid4()),
                "segment_name": segment,
                "demographics": self._generate_demographics(),
                "behavior_metrics": self._generate_behavior_metrics(),
                "satisfaction_metrics": self._generate_satisfaction_metrics(),
                "lifetime_value": round(random.uniform(100, 10000), 2)
            }
            insights["segments"].append(segment_data)

        return insights

    def _generate_demographics(self) -> Dict[str, Any]:
        return {
            "age_distribution": {
                age: round(random.uniform(0.05, 0.35), 2)
                for age in self.age_ranges
            },
            "income_brackets": {
                "low": round(random.uniform(0.1, 0.3), 2),
                "medium": round(random.uniform(0.3, 0.5), 2),
                "high": round(random.uniform(0.1, 0.3), 2)
            },
            "geographic_distribution": {
                "urban": round(random.uniform(0.3, 0.6), 2),
                "suburban": round(random.uniform(0.2, 0.4), 2),
                "rural": round(random.uniform(0.1, 0.3), 2)
            }
        }

    def _generate_behavior_metrics(self) -> Dict[str, Any]:
        return {
            "purchase_frequency": {
                freq: round(random.uniform(0.1, 0.4), 2)
                for freq in self.purchase_frequencies
            },
            "channel_preference": {
                "online": round(random.uniform(0.3, 0.7), 2),
                "retail": round(random.uniform(0.3, 0.7), 2)
            },
            "basket_size": round(random.uniform(1, 5), 1)
        }

    def _generate_satisfaction_metrics(self) -> Dict[str, Any]:
        return {
            "nps": random.randint(30, 90),
            "satisfaction_score": round(random.uniform(3.5, 4.8), 1),
            "repeat_purchase_rate": round(random.uniform(0.4, 0.8), 2)
        }

class ChannelInsightSimulator:
    def __init__(self, seed: int = None):
        if seed:
            np.random.seed(seed)
            random.seed(seed)
        
        self.channels = ['online', 'retail', 'marketplace', 'direct_sales']
        self.products = ['electronics', 'apparel', 'home_goods', 'accessories']

    def generate_channel_insights(self) -> Dict[str, Any]:
        insights = {
            "timestamp": datetime.now().isoformat(),
            "channels": []
        }

        for channel in self.channels:
            channel_data = {
                "channel_id": str(uuid.uuid4()),
                "channel_name": channel,
                "performance_metrics": self._generate_performance_metrics(),
                "product_performance": self._generate_product_performance(),
                "operational_metrics": self._generate_operational_metrics(),
                "customer_engagement": self._generate_engagement_metrics()
            }
            insights["channels"].append(channel_data)

        return insights

    def _generate_performance_metrics(self) -> Dict[str, Any]:
        return {
            "revenue": round(random.uniform(100000, 1000000), 2),
            "growth_rate": round(random.uniform(-0.05, 0.25), 3),
            "market_share": round(random.uniform(0.05, 0.30), 2),
            "conversion_rate": round(random.uniform(0.02, 0.15), 3),
            "customer_acquisition_cost": round(random.uniform(20, 200), 2)
        }

    def _generate_product_performance(self) -> Dict[str, Any]:
        return {
            product: {
                "revenue_share": round(random.uniform(0.1, 0.4), 2),
                "margin": round(random.uniform(0.2, 0.6), 2),
                "turnover_rate": round(random.uniform(4, 12), 1)
            }
            for product in self.products
        }

    def _generate_operational_metrics(self) -> Dict[str, Any]:
        return {
            "fulfillment_rate": round(random.uniform(0.85, 0.99), 2),
            "average_processing_time": round(random.uniform(1, 5), 1),
            "return_rate": round(random.uniform(0.02, 0.15), 3),
            "inventory_accuracy": round(random.uniform(0.90, 0.99), 2)
        }

    def _generate_engagement_metrics(self) -> Dict[str, Any]:
        return {
            "active_customers": random.randint(1000, 10000),
            "customer_satisfaction": round(random.uniform(3.5, 4.8), 1),
            "repeat_purchase_rate": round(random.uniform(0.3, 0.7), 2)
        }

class LocationInsightSimulator:
    def __init__(self, seed: int = None):
        if seed:
            np.random.seed(seed)
            random.seed(seed)
        
        self.regions = ['north', 'south', 'east', 'west']
        self.store_types = ['flagship', 'mall', 'street', 'outlet']

    def generate_location_insights(self) -> Dict[str, Any]:
        insights = {
            "timestamp": datetime.now().isoformat(),
            "regions": []
        }

        for region in self.regions:
            region_data = {
                "region_id": str(uuid.uuid4()),
                "region_name": region,
                "market_metrics": self._generate_market_metrics(),
                "store_performance": self._generate_store_performance(),
                "logistics_metrics": self._generate_logistics_metrics(),
                "customer_demographics": self._generate_regional_demographics()
            }
            insights["regions"].append(region_data)

        return insights

    def _generate_market_metrics(self) -> Dict[str, Any]:
        return {
            "market_size": round(random.uniform(1000000, 10000000), 2),
            "market_growth": round(random.uniform(-0.05, 0.15), 3),
            "competitor_density": round(random.uniform(0.2, 0.8), 2),
            "market_penetration": round(random.uniform(0.1, 0.5), 2)
        }

    def _generate_store_performance(self) -> Dict[str, Any]:
        return {
            store_type: {
                "revenue": round(random.uniform(100000, 1000000), 2),
                "traffic": random.randint(1000, 10000),
                "conversion_rate": round(random.uniform(0.02, 0.15), 3),
                "average_transaction": round(random.uniform(50, 500), 2)
            }
            for store_type in self.store_types
        }

    def _generate_logistics_metrics(self) -> Dict[str, Any]:
        return {
            "warehouse_utilization": round(random.uniform(0.6, 0.9), 2),
            "delivery_time": round(random.uniform(1, 5), 1),
            "stockout_rate": round(random.uniform(0.01, 0.1), 3),
            "transportation_cost": round(random.uniform(1000, 10000), 2)
        }

    def _generate_regional_demographics(self) -> Dict[str, Any]:
        return {
            "population_density": round(random.uniform(100, 1000), 1),
            "income_level": round(random.uniform(30000, 100000), 2),
            "age_distribution": {
                "young": round(random.uniform(0.2, 0.4), 2),
                "middle": round(random.uniform(0.3, 0.5), 2),
                "senior": round(random.uniform(0.1, 0.3), 2)
            }
        }

# Example usage
def generate_all_insights():
    customer_sim = CustomerInsightSimulator(seed=42)
    channel_sim = ChannelInsightSimulator(seed=42)
    location_sim = LocationInsightSimulator(seed=42)

    insights = {
        "customer_insights": customer_sim.generate_customer_insights(),
        "channel_insights": channel_sim.generate_channel_insights(),
        "location_insights": location_sim.generate_location_insights()
    }

    return insights

# Generate and print example insights
if __name__ == "__main__":
    insights = generate_all_insights()
    print("Generated insights:", insights)