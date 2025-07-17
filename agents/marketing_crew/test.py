from tools.revenue_performance_generator import RevenuePerformanceGenerator
from tools.campaign_recommendation_engine import CampaignRecommendationEngine
from tools.campaign_performance_tracker import CampaignPerformanceTracker
from tools.budget_monitor import BudgetMonitor
from tools.inventory_tracker import InventoryTracker
from marketing_crew import MarketingCrew
from tools.growth_trajactor import GrowthTrajectoryForecaster
from translation_crew import SalesToInventoryTranslationCrew
from sarah.performance import SarahChenPerformanceData
from sarah.pattern import SarahChenPatternSimulator
from datetime import datetime
import pandas as pd

def main():
  # Example data
  data = {
      'date': pd.date_range(start='2023-01-01', periods=10, freq='D'),
      'roas': [3.5, 3.7, 3.6, 3.8, 3.9, 4.0, 3.8, 3.7, 3.6, 3.5],
      'ctr': [0.01, 0.012, 0.011, 0.013, 0.014, 0.015, 0.013, 0.012, 0.011, 0.01],
      # Add other relevant columns if needed
  }

  # Create DataFrame
  performance_history = pd.DataFrame(data)
  # # Create simulator with historical data
  simulator = SarahChenPatternSimulator(performance_history)

  # # Example current metrics
  # current_metrics = {
  #     'roas': 3.2,
  #     'ctr': 0.008,
  #     'conversion_rate': 0.12,
  #     'spend': 2500,
  #     'impressions': 100000
  # }
  
  # # Simulate pattern recognition
  # detected_patterns = simulator.simulate_real_time_patterns(current_metrics)
  
  # # Print results
  # for pattern in detected_patterns:
  #     print(f"\nDetected Pattern: {pattern.pattern_type.value}")
  #     print(f"Confidence: {pattern.confidence:.2f}")
  #     print(f"Urgency: {pattern.urgency}/5")
  #     print(f"Impact Estimate: ${pattern.impact_estimate:.2f}")
  #     print(f"Recommended Response Time: {pattern.recommended_response_time} minutes")
  #     print(f"Historical Success Rate: {pattern.historical_success_rate:.2f}")

  # Generate example data
  # data_generator = SarahChenPerformanceData()
  # # performance_history = data_generator.generate_daily_performance_data(days=1)
  # base_metrics = data_generator._generate_base_metrics(date=datetime(2024, 1, 1), campaign_type='sponsored_products')

  # print("base_metrics: ", base_metrics)

  # # Print sample data summaries
  # print("\nPerformance Metrics Summary:")
  # print(performance_history.groupby('campaign_type')[
  #     ['roas', 'conversion_rate', 'spend']
  # ].mean())

  # print("\nResponse Pattern Summary:")
  # print(performance_history[
  #     ['decision_type', 'response_time_minutes']
  # ].value_counts().head())

# Example of coordination events
#   coordination_events = pd.DataFrame([
#     {
#         'date': datetime(2024, 1, 15),
#         'event_type': 'inventory_alert',
#         'response_time_minutes': 12,
#         'coordination_with': 'inventory_team',
#         'outcome': 'budget_adjusted',
#         'impact_measured': 'prevented_stockout'
#     },
#     {
#         'date': datetime(2024, 1, 22),
#         'event_type': 'competitive_pressure',
#         'response_time_minutes': 8,
#         'coordination_with': 'marketing_strategy',
#         'outcome': 'increased_bids',
#         'impact_measured': 'maintained_share'
#     }
# ])

# # Example of learning patterns
# learning_events = pd.DataFrame([
#     {
#         'date': datetime(2024, 1, 5),
#         'event_type': 'new_feature_adoption',
#         'feature': 'audience_targeting',
#         'adoption_speed': 'fast',
#         'success_rate': 0.92
#     },
#     {
#         'date': datetime(2024, 1, 12),
#         'event_type': 'strategy_innovation',
#         'feature': 'dayparting',
#         'adoption_speed': 'measured',
#         'success_rate': 0.88
#     }
# ])

# print("\nCoordination Events:")
# print(coordination_events)

# print("\nLearning Patterns:")
# print(learning_events)

  # forecaster = GrowthTrajectoryForecaster(target_growth=0.03)
    
	# # Sample historical data
  # historical_data = {
  #   	"sponsored_products": {
  #       	"daily_growth_rates": [0.025, 0.026, 0.028, 0.027, 0.029, 0.028, 0.030,
  #                            	0.029, 0.031, 0.030, 0.032, 0.031, 0.033, 0.032]
  #   	},
  #   	"sponsored_brands": {
  #       	"daily_growth_rates": [0.020, 0.022, 0.021, 0.023, 0.022, 0.024, 0.023,
  #                            	0.025, 0.024, 0.026, 0.025, 0.027, 0.026, 0.028]
  #   	}
	# }
    
	# # Sample current performance data
  # current_performance = {
  #   	"sponsored_products": {
  #       	"revenue_share": 0.6,
  #       	"current_growth": 0.032
  #   	},
  #   	"sponsored_brands": {
  #       	"revenue_share": 0.4,
  #       	"current_growth": 0.028
  #   	}
	# }
    
	# # Generate forecast
  # forecast_results = forecaster.forecast_growth_trajectory(
  #   	historical_data, current_performance
	# )
  
  # print("\nGROWTH TRAJECTORY FORECAST")
  # print("=========================")
  
  # print("\nChannel Forecasts:")
  # for channel, forecast in forecast_results['channel_forecasts'].items():
  #   	print(f"\n{channel}:")
  #   	print(f"  Current Growth: {forecast.current_growth*100:.1f}%")
  #   	print(f"  Projected Growth: {forecast.projected_growth*100:.1f}%")
  #   	print(f"  Confidence Interval: ({forecast.confidence_interval[0]*100:.1f}%, "
  #         	f"{forecast.confidence_interval[1]*100:.1f}%)")
  #   	print(f"  Risk Level: {forecast.risk_level.value}")
  #   	if forecast.days_to_target:
  #       	print(f"  Days to Target: {forecast.days_to_target}")
  
  # print("\nOverall Projection:")
  # overall = forecast_results['overall_projection']
  # print(f"  Projected Growth: {overall['projected_growth']*100:.1f}%")
  # print(f"  Gap to Target: {overall['target_gap']*100:.1f}%")
  # print(f"  Success Probability: {overall['probability_of_success']*100:.1f}%")
  
  # print("\nRisk Assessment:")
  # risks = forecast_results['risk_assessment']
  # print(f"  Overall Risk Level: {risks['overall_risk_level'].value}")
    
  # print("\nRecommendations:")
  # for rec in forecast_results['recommendations']:
  #   	print(f"\n{rec['channel']}:")
  #   	print(f"  Type: {rec['type']}")
  #   	print(f"  Priority: {rec['priority']}")
  #   	print("  Actions:")
  #   	for action in rec['actions']:
  #       	print(f"  - {action}")







    # crew = MarketingCrew().crew()
    # output = crew.kickoff()
    # print("marketing crew output: ", output.raw)

    # translation_crew = SalesToInventoryTranslationCrew().crew(output.raw)
    # output = translation_crew.kickoff()
    # print("translation crew output: ", output.raw)

    # generator = RevenuePerformanceGenerator(total_budget=100000)
    # performance = generator.generate_initial_performance()
    
    # # Generate and display performance summary
    # print("\nCHANNEL PERFORMANCE SUMMARY")
    # print("===========================")
    # print(generator.generate_performance_summary(performance).to_string(index=False))    # # Generate and display initial recommendations
    # print("\nINITIAL RECOMMENDATIONS")
    # print("======================")
    # recommendations = generator.generate_channel_recommendations(performance)
    # for channel, recs in recommendations.items():
    #     if recs:
    #         print(f"\n{channel.replace('_', ' ').title()}:")
    #         for rec in recs:
    #             print(f"- {rec}")

    # here we generate some initial numbers for search in terms of roas, spend, revenue, growth rate

    # if roas is higher than base increase spend
    # if roas is lower than base decrease spend and check keyword allocation, store display

    # need to keep checking inventory levels and check if we need to order more units


    


    # # Sample performance data
    # performance_data = {
    #     "sponsored_products": {"roas": 4.2, "growth_rate": 0.028},
    #     "sponsored_brands": {"roas": 3.8, "growth_rate": 0.025},
    #     "sponsored_display": {"roas": 3.2, "growth_rate": 0.022}
    # }
    
    # engine = CampaignRecommendationEngine(performance_data)
    # print(engine.generate_recommendation_report())

    # # Initialize and display campaign performance tracker
    # tracker = CampaignPerformanceTracker()
    # print(tracker.format_tables_for_display())

    # Initialize monitor
    # budget_monitor = BudgetMonitor(total_budget=100000)
    
    # # # Sample performance data
    # current_performance = {
    #     "amazon_store": {
    #         "spent": 18000,
    #         "roas": 4.2,
    #         "growth_rate": 0.028,
    #         "conversion_rate": 0.12
    #     },
    #     "sponsored_products": {
    #         "spent": 42000,
    #         "roas": 3.8,
    #         "growth_rate": 0.032,
    #         "conversion_rate": 0.10
    #     },
    #     "sponsored_brands": {
    #         "spent": 17000,
    #         "roas": 3.5,
    #         "growth_rate": 0.025,
    #         "conversion_rate": 0.09
    #     },
    #     "sponsored_display": {
    #         "spent": 13000,
    #         "roas": 3.2,
    #         "growth_rate": 0.022,
    #         "conversion_rate": 0.08
    #     }
    # }
    
    # # # Monitor budget allocation
    # monitoring_results = budget_monitor.monitor_budget_allocation(current_performance)
    
    # # Print results
    # print("\nBUDGET MONITORING RESULTS")
    # print("========================")
    # print(f"\nTimestamp: {monitoring_results['timestamp']}")
    
    # print("\nChannel Status:")
    # for channel, status in monitoring_results['channel_status'].items():
    #     print(f"\n{channel}:")
    #     print(f"  Allocated: ${status.allocated:,.2f}")
    #     print(f"  Spent: ${status.spent:,.2f}")
    #     print(f"  Remaining: ${status.remaining:,.2f}")
    #     print(f"  Efficiency Score: {status.efficiency_score:.2f}")
    #     print(f"  ROAS: {status.roas:.1f}x")
    #     if status.alerts:
    #         print(f"  Alerts: {[alert.value for alert in status.alerts]}")
    
    # print("\nOptimization Recommendations:")
    # for rec in monitoring_results['optimization_recommendations']:
    #     print(f"\n{rec['priority']} Priority - {rec['channel']}:")
    #     print(f"  Action: {rec['action']}")
    #     print(f"  Amount: ${rec['amount']:,.2f}")
    #     print(f"  Reason: {rec['reason']}")


    # print("\nGrowth Impact Assessment:")
    # growth_impact = monitoring_results['growth_impact']
    # print(f"Overall Growth Rate: {growth_impact['overall_growth_rate']*100:.1f}%")
    # print(f"Gap to Target: {growth_impact['gap_to_target']*100:.1f}%")

    # # Initialize tracker
    # tracker = InventoryTracker()
    
    # # Sample inventory data
    # inventory_data = {
    #     "TRAIL-MIX-001": {
    #         "current_stock": 1500,
    #         "weekly_sales": 700,
    #         "lead_time_days": 14,
    #         "promo_lift": 1.4,
    #         "open_orders": [
    #             {
    #                 "order_id": "PO-001",
    #                 "quantity": 2000,
    #                 "expected_date": "2024-12-25",
    #                 "status": "in_transit"
    #             }
    #         ],
    #         "lead_time_history": [14, 14, 15, 16, 16, 17]
    #     },
    #     "TRAIL-MIX-002": {
    #         "current_stock": 800,
    #         "weekly_sales": 900,
    #         "lead_time_days": 14,
    #         "promo_lift": 1.0,
    #         "open_orders": [],
    #         "lead_time_history": [14, 14, 14, 14, 14, 14]
    #     }
    # }
    
    # # Track inventory
    # tracking_results = tracker.track_inventory_levels(inventory_data)
    
    # # Print results
    # print("\nINVENTORY TRACKING RESULTS")
    # print("=========================")
    
    # print("\nSKU Status:")
    # for sku, status in tracking_results['sku_status'].items():
    #     print(f"\n{sku}:")
    #     print(f"  Current Stock: {status.current_stock}")
    #     print(f"  Reorder Point: {status.reorder_point}")
    #     print(f"  Daily Velocity: {status.daily_velocity:.1f}")
    #     print(f"  Stock Coverage: {status.stock_coverage_days:.1f} days")
    #     if status.alerts:
    #         print(f"  Alerts: {[alert.value for alert in status.alerts]}")
    
    # print("\nPromotional Impact:")
    # for sku in tracking_results['promotional_impact']['impacted_skus']:
    #     print(f"\n{sku['sku']}:")
    #     print(f"  Baseline Velocity: {sku['baseline_velocity']:.1f}/day")
    #     print(f"  Promotional Velocity: {sku['promotional_velocity']:.1f}/day")
    #     print(f"  Risk Level: {sku['risk_level']:.2f}")
    
    # print("\nRecommendations:")
    # for rec in tracking_results['recommendations']:
    #     print(f"\n{rec['sku']} - {rec['type'].upper()}:")
    #     print(f"  Action: {rec.get('action', 'Order')} {rec.get('quantity', '')} units")
    #     print(f"  Urgency: {rec['urgency']}")
    #     print(f"  Reason: {rec['reason']}")

if __name__ == "__main__":  
    main()

