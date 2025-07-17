from datetime import datetime
import pandas as pd
from sarah.types import BaseMetrics, InventoryData
from sarah.pattern import SarahChenPatternSimulator
import redis

class MarketingSystemState:
    def __init__(self):
        # Define quarterly performance data
        self.quarterly_data = {
            '4th Qtr; 2023': {'ad_spend_change': 0.05, 'revenue_goal_change': 0.0, 'roas_change': -0.15},
            '1st Qtr; 2024': {'ad_spend_change': 0.013, 'revenue_goal_change': -0.023, 'roas_change': -0.12},
            '2nd Qtr; 2024': {'ad_spend_change': 0.036, 'revenue_goal_change': -0.03, 'roas_change': -0.09},
        }

        # Example data
        self.dates = pd.date_range(start='2025-01-01', periods=7, freq='D')
        self.roas_values = [3.5, 3.7, 3.6, 3.8, 3.9, 4.0, 3.8]
        self.ctr_values = [0.01, 0.012, 0.011, 0.013, 0.014, 0.015, 0.013]

        # Define base values for metrics
        self.base_impression = 1000
        self.base_clicks = 10
        self.base_spend = 1000
        self.base_sales = 100
        
        self.budget = 100000
        self.growth_rate = 0.03
        self.current_date = "2025-01-08"

        # Create metrics list and historical data
        self.base_metrics_list = self._create_base_metrics()
        self.historical_data = self._create_historical_data()
        self.inventory_data = self._create_inventory_data()

        # Initialize simulator and outputs
        self.simulator = self._create_simulator()
        self.all_outputs = self._generate_pattern_outputs()

        # Add customer segment and demographic data
        self.customer_segments = ['luxury', 'premium', 'mainstream', 'budget']
        self.age_ranges = ['18-24', '25-34', '35-44', '45-54', '55+']
        self.customer_data = self._create_customer_data()

    def _create_base_metrics(self):
        return [
            BaseMetrics(
                roas=self.roas_values[i] * (1 + self.quarterly_data['4th Qtr; 2023']['roas_change']),
                ctr=self.ctr_values[i] if i < len(self.ctr_values) else 0.01,
                impressions=self.base_impression + i * 100,
                clicks=self.base_clicks + i,
                spend=self.base_spend * (1 + self.quarterly_data['4th Qtr; 2023']['ad_spend_change']),
                sales=self.base_sales * (1 + self.quarterly_data['4th Qtr; 2023']['revenue_goal_change']),
                conversion_rate=0.1 + i * 0.01,
                acos=0.2
            )
            for i in range(len(self.dates))
        ]

    def _create_historical_data(self):
        return {
            self.dates[i]: self.base_metrics_list[i]
            for i in range(len(self.dates))
        }

    def _create_inventory_data(self):
        return {
            "TRAIL-MIX-001": InventoryData(
                current_stock=1500,
                weekly_sales=700,
                lead_time_days=14,
                promo_lift=1.4,
                open_orders=[
                    {
                        "order_id": "PO-001",
                        "quantity": 2000,
                        "expected_date": "2024-12-25",
                        "status": "in_transit"
                    }
                ],
                lead_time_history=[14, 14, 15, 16, 16, 17]
            ),
            "TRAIL-MIX-002": InventoryData(
                current_stock=800,
                weekly_sales=900,
                lead_time_days=14,
                promo_lift=1.0,
                open_orders=[],
                lead_time_history=[14, 14, 14, 14, 14, 14]
            ),
            "CORN-FLAKES-001": InventoryData(
                current_stock=2000,
                weekly_sales=850,
                lead_time_days=10,
                promo_lift=1.2,
                open_orders=[
                    {
                        "order_id": "PO-002",
                        "quantity": 1500,
                        "expected_date": "2024-12-30",
                        "status": "in_transit"
                    }
                ],
                lead_time_history=[10, 11, 10, 10, 9, 10]
            )
        }

    def _create_simulator(self):
        """Create and return the pattern simulator"""
        return SarahChenPatternSimulator(self.historical_data)

    def _generate_pattern_outputs(self):
        """Generate pattern recognition outputs for all historical data"""
        all_outputs = ""
        
        for date, metrics in self.historical_data.items():
            detected_patterns = self.simulator.simulate_real_time_patterns(metrics)
            
            # Use the __str__ method of BaseMetrics
            output = f"\n### Date: {date.strftime('%Y-%m-%d')}\n"
            output += str(metrics)
            
            if detected_patterns:
                for pattern in detected_patterns:
                    output += f"\n**Detected Pattern:** {pattern.pattern_type.value}\n"
                    output += f"- Confidence: {pattern.confidence:.2f}\n"
                    output += f"- Urgency: {pattern.urgency}/5\n"
                    output += f"- Impact Estimate: ${pattern.impact_estimate:.2f}\n"
                    output += f"- Recommended Response Time: {pattern.recommended_response_time} minutes\n"
                    output += f"- Historical Success Rate: {pattern.historical_success_rate:.2f}\n"
                    output += f"- Reason: {pattern.reason}\n"
            else:
                output += "\n**No action taken:** No pattern detected.\n"
            
            all_outputs += output
        
        return all_outputs

    def get_marketing_crew_inputs(self, current_metrics_channels):
        """Get all inputs needed for marketing crew"""
        return {
            "historical_descisions": self.all_outputs,
            "current_metrics_channels": current_metrics_channels,
            "budget": self.budget,
            "growth_rate": self.growth_rate,
            "current_date": self.current_date,
            "inventory_data": self.inventory_data
        }
    def get_system_state(self):
        """Get current system state including marketing metrics and data"""
        try:
            return {
                'quarterly_data': self.quarterly_data,
                'metrics': {
                    'roas_values': self.roas_values,
                    'ctr_values': self.ctr_values,
                    'base_metrics': {
                        'impressions': self.base_impression,
                        'clicks': self.base_clicks,
                        'spend': self.base_spend,
                        'sales': self.base_sales
                    }
                },
                'budget': self.budget,
                'growth_rate': self.growth_rate,
                'current_date': self.current_date,
                'inventory_data': {
                    product_id: {
                        'current_stock': data.current_stock,
                        'weekly_sales': data.weekly_sales,
                        'lead_time_days': data.lead_time_days,
                        'promo_lift': data.promo_lift,
                        'open_orders': data.open_orders,
                        'lead_time_history': data.lead_time_history
                    } for product_id, data in self.inventory_data.items()
                },
                'pattern_outputs': self.all_outputs,
                'historical_data': {
                    date.strftime('%Y-%m-%d'): metrics.__dict__ 
                    for date, metrics in self.historical_data.items()
                },
                'customer_insights': {
                    'segments': [
                        {
                            'segment_name': segment,
                            'demographics': {
                                'age_distribution': {
                                    age: round(1/len(self.age_ranges), 2)
                                    for age in self.age_ranges
                                },
                                'income_brackets': {
                                    'low': 0.2,
                                    'medium': 0.5,
                                    'high': 0.3
                                },
                                'geographic_distribution': {
                                    'urban': 0.45,
                                    'suburban': 0.35,
                                    'rural': 0.20
                                }
                            },
                            'behavior_metrics': {
                                'purchase_frequency': {
                                    'weekly': 0.2,
                                    'monthly': 0.4,
                                    'quarterly': 0.3,
                                    'annually': 0.1
                                },
                                'channel_preference': self.customer_data['age_demographics']['25-34']['channel_preference'],
                                'basket_size': 3.5
                            },
                            'satisfaction_metrics': {
                                'nps': 75,
                                'satisfaction_score': self.customer_data['segment_metrics'][segment]['satisfaction_score'],
                                'repeat_purchase_rate': self.customer_data['segment_metrics'][segment]['repeat_purchase_rate']
                            },
                            'lifetime_value': self.customer_data['segment_metrics'][segment]['lifetime_value']
                        }
                        for segment in self.customer_segments
                    ],
                    'age_demographics': self.customer_data['age_demographics']
                },
                'channel_insights': {
                    'channels': [
                        {
                            'channel_name': channel,
                            'performance_metrics': {
                                'revenue': 500000.00,
                                'growth_rate': 0.15,
                                'market_share': 0.25,
                                'conversion_rate': 0.08,
                                'customer_acquisition_cost': 100.00
                            }
                        }
                        for channel in ['online', 'retail', 'marketplace', 'direct_sales']
                    ]
                }
            }
        except Exception as e:
            print(f"Error getting system state: {e}")
            return {}

    def get_current_metrics_channels(self):
        """Get current metrics for all channels"""
        return {
            "amazon": {
                "roas": 3.8,
                "ctr": 0.012,
                "impressions": 1200,
                "clicks": 14,
                "spend": 1100,
                "sales": 120,
                "conversion_rate": 0.12,
                "acos": 0.18
            },
            "retail_store": {
                "roas": 3.5,
                "ctr": 0.011,
                "impressions": 1150,
                "clicks": 13,
                "spend": 1080,
                "sales": 110,
                "conversion_rate": 0.11,
                "acos": 0.19
            },
            "social_media": {
                "roas": 3.2,
                "ctr": 0.010,
                "impressions": 1100,
                "clicks": 12,
                "spend": 1050,
                "sales": 100,
                "conversion_rate": 0.10,
                "acos": 0.20
            }
        }

    def _create_customer_data(self):
        return {
            "segment_metrics": {
                "luxury": {
                    "segment_share": 0.15,
                    "lifetime_value": 8500.00,
                    "satisfaction_score": 4.6,
                    "repeat_purchase_rate": 0.75
                },
                "premium": {
                    "segment_share": 0.25,
                    "lifetime_value": 5200.00,
                    "satisfaction_score": 4.3,
                    "repeat_purchase_rate": 0.65
                },
                "mainstream": {
                    "segment_share": 0.40,
                    "lifetime_value": 2800.00,
                    "satisfaction_score": 4.0,
                    "repeat_purchase_rate": 0.55
                },
                "budget": {
                    "segment_share": 0.20,
                    "lifetime_value": 1200.00,
                    "satisfaction_score": 3.8,
                    "repeat_purchase_rate": 0.45
                }
            },
            "age_demographics": {
                "18-24": {
                    "population_share": 0.15,
                    "purchase_frequency": "monthly",
                    "channel_preference": {"online": 0.75, "retail": 0.25}
                },
                "25-34": {
                    "population_share": 0.25,
                    "purchase_frequency": "monthly",
                    "channel_preference": {"online": 0.65, "retail": 0.35}
                },
                "35-44": {
                    "population_share": 0.30,
                    "purchase_frequency": "quarterly",
                    "channel_preference": {"online": 0.55, "retail": 0.45}
                },
                "45-54": {
                    "population_share": 0.20,
                    "purchase_frequency": "quarterly",
                    "channel_preference": {"online": 0.45, "retail": 0.55}
                },
                "55+": {
                    "population_share": 0.10,
                    "purchase_frequency": "quarterly",
                    "channel_preference": {"online": 0.35, "retail": 0.65}
                }
            }
        }

