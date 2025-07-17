from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from .types import BaseMetrics, DecisionRecords, ResponsePatterns

class SarahChenPerformanceData:
    def __init__(self):
        self.start_date = datetime(2024, 1, 1)
        self.campaign_types = ['sponsored_products', 'sponsored_brands', 'sponsored_display']

    def generate_daily_performance_data(self, days: int = 90) -> pd.DataFrame:
        """Generate synthetic daily performance data reflecting Sarah's management patterns"""
        dates = [self.start_date + timedelta(days=x) for x in range(days)]
        data = []

        for date in dates:
            for campaign_type in self.campaign_types:
                # Base performance metrics
                base_metrics = self._generate_base_metrics(date, campaign_type)
                # Decision records
                decisions = self._generate_decision_records(date, base_metrics)
                # Response patterns
                responses = self._generate_response_patterns(date, base_metrics)

                data.append({
                    'date': date,
                    'campaign_type': campaign_type,
                    **base_metrics,
                    **decisions,
                    **responses
                })

        return pd.DataFrame(data)

    def _generate_base_metrics(self, date: datetime, campaign_type: str) -> BaseMetrics:
        """Generate base performance metrics"""
        # Add seasonality and day-of-week effects
        seasonal_factor = 1 + 0.2 * np.sin(2 * np.pi * date.timetuple().tm_yday / 365)
        dow_factor = 1 + 0.1 * (date.weekday() < 5)  # Higher on weekdays

        # Campaign type specific baseline metrics
        campaign_baselines = {
            'sponsored_products': {'roas': 4.0, 'ctr': 0.012, 'conversion_rate': 0.15},
            'sponsored_brands': {'roas': 3.5, 'ctr': 0.010, 'conversion_rate': 0.12},
            'sponsored_display': {'roas': 3.0, 'ctr': 0.008, 'conversion_rate': 0.10}
        }

        base = campaign_baselines[campaign_type]
        
        return BaseMetrics(
            impressions=int(100000 * seasonal_factor * dow_factor),
            clicks=int(1200 * seasonal_factor * dow_factor),
            spend=float(2500 * seasonal_factor),
            sales=float(base['roas'] * 2500 * seasonal_factor),
            roas=float(base['roas'] * (0.9 + 0.2 * np.random.random())),
            ctr=float(base['ctr'] * (0.9 + 0.2 * np.random.random())),
            conversion_rate=float(base['conversion_rate'] * (0.9 + 0.2 * np.random.random())),
            acos=float(1/base['roas'] * (0.9 + 0.2 * np.random.random()))
        )

    def _generate_decision_records(self, date: datetime, metrics: BaseMetrics) -> DecisionRecords:
        """Generate decision records based on performance metrics"""
        decisions = DecisionRecords(
            review_time=date.replace(hour=9, minute=30),  # Sarah typically reviews at 9:30 AM
            decision_type='routine',
            response_time_minutes=15
        )

        # Adjust for performance thresholds
        if metrics.roas < 3.0:
            decisions.decision_type = 'optimization_required'
            decisions.response_time_minutes = 10  # Faster response to poor performance
            decisions.action_taken = 'budget_reduction'
            decisions.adjustment_amount = -0.2  # 20% reduction
        elif metrics.roas > 4.5:
            decisions.decision_type = 'opportunity_identified'
            decisions.response_time_minutes = 20
            decisions.action_taken = 'budget_increase'
            decisions.adjustment_amount = 0.15  # 15% increase

        return decisions

    def _generate_response_patterns(self, date: datetime, metrics: BaseMetrics) -> ResponsePatterns:
        """Generate response patterns based on different scenarios"""
        patterns = ResponsePatterns(
            coordination_required=False,
            inventory_check_performed=False,
            competitive_analysis_done=False,
            budget_reallocation_needed=False
        )

        # Triggered by performance thresholds
        if metrics.conversion_rate < 0.08:
            patterns.coordination_required = True
            patterns.competitive_analysis_done = True
            patterns.response_priority = 'high'

        # Regular inventory checks on Mondays
        if date.weekday() == 0:
            patterns.inventory_check_performed = True

        # Budget reallocation at start of month
        if date.day == 1:
            patterns.budget_reallocation_needed = True

        return patterns