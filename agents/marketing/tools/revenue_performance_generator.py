from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from scipy import stats

@dataclass
class ChannelPerformance:
    channel: str
    spend: float
    roas: float
    revenue: float
    growth_rate: float
    market_share: float

class RevenuePerformanceGenerator:
    def __init__(self, total_budget: float = 100000, target_growth: float = 0.03):
        self.total_budget = total_budget
        self.target_growth = target_growth  # Use input target growth
        
        # Initial budget allocation percentages
        self.budget_allocation = {
            "sponsored_products": 0.50, # 50% of budget
            "sponsored_brands": 0.25,   # 25% of budget
            "sponsored_display": 0.25   # 25% of budget
        }
        
        # Base ROAS by channel
        self.base_roas = {
            "sponsored_products": 3.8, # Main advertising channel
            "sponsored_brands": 3.5,   # Brand building
            "sponsored_display": 3.2   # Awareness and remarketing
        }
        
        # Market share by channel (percentage of category revenue)
        self.market_share = {
            "sponsored_products": 0.40, # Adjusted to 40% of total share
            "sponsored_brands": 0.35,   # Adjusted to 35% of total share
            "sponsored_display": 0.25   # Adjusted to 25% of total share
        }

    def generate_initial_performance(self) -> Dict[str, ChannelPerformance]:
        """Generates initial performance metrics for each channel"""
        performance = {}
        
        for channel in self.budget_allocation.keys():
            # Calculate channel spend
            spend = self.total_budget * self.budget_allocation[channel]
            
            # Add some random variation to ROAS (-5% to +5%)
            roas_variation = np.random.uniform(0.95, 1.05)
            roas = self.base_roas[channel] * roas_variation
            
            # Calculate revenue
            revenue = spend * roas
            
            # Generate initial growth rate (slightly different for each channel)
            growth_variation = np.random.uniform(0.90, 1.10)
            growth_rate = self.target_growth * growth_variation
            
            # Add some variation to market share (-2% to +2%)
            share_variation = np.random.uniform(0.98, 1.02)
            market_share = self.market_share[channel] * share_variation
            
            performance[channel] = ChannelPerformance(
                channel=channel,
                spend=round(spend, 2),
                roas=round(roas, 2),
                revenue=round(revenue, 2),
                growth_rate=round(growth_rate, 4),
                market_share=round(market_share, 4)
            )
            
        return performance

    def generate_performance_summary(self, performance: Dict[str, ChannelPerformance]) -> pd.DataFrame:
        """Creates a formatted performance summary table based on the provided performance data"""
        
        data = []
        for channel, metrics in performance.items():
            data.append({
                'Channel': channel.replace('_', ' ').title(),
                'Spend ($)': f"{metrics.spend:,.2f}",
                'ROAS': f"{metrics.roas:.2f}x",
                'Revenue ($)': f"{metrics.revenue:,.2f}",
                'Growth Rate': f"{metrics.growth_rate*100:.1f}%",
                'Market Share': f"{metrics.market_share*100:.1f}%",
                'vs Target': f"{((metrics.growth_rate-self.target_growth)/self.target_growth)*100:+.1f}%"
            })
            
        df = pd.DataFrame(data)
        
        # Add totals row
        totals = {
            'Channel': 'TOTAL',
            'Spend ($)': f"{sum(p.spend for p in performance.values()):,.2f}",
            'ROAS': f"{np.mean([p.roas for p in performance.values()]):.2f}x",
            'Revenue ($)': f"{sum(p.revenue for p in performance.values()):,.2f}",
            'Growth Rate': f"{np.mean([p.growth_rate for p in performance.values()])*100:.1f}%",
            'Market Share': f"{sum(p.market_share for p in performance.values())*100:.1f}%",
            'vs Target': f"{(np.mean([p.growth_rate for p in performance.values()])-self.target_growth)/self.target_growth*100:+.1f}%"
        }
        df = pd.concat([df, pd.DataFrame([totals])], ignore_index=True)
        
        return df

    def generate_channel_recommendations(self, performance: Dict[str, ChannelPerformance]) -> Dict[str, List[str]]:
        """Generates recommendations based on provided performance data"""
        
        recommendations = {}
        
        for channel, metrics in performance.items():
            channel_recs = []
            
            # Check growth rate vs target
            if metrics.growth_rate < self.target_growth:
                if metrics.roas > np.mean([p.roas for p in performance.values()]):
                    channel_recs.append(f"Increase budget allocation to drive growth (High ROAS of {metrics.roas:.2f}x)")
                else:
                    channel_recs.append("Optimize targeting and creative to improve performance")
                    
            # Check ROAS performance
            if metrics.roas < self.base_roas[channel]:
                channel_recs.append("Review bidding strategy and keyword performance")
                
            # Check market share
            # if metrics.market_share < self.market_share[channel]:
            #     channel_recs.append("Expand reach to regain market share")
                
            recommendations[channel] = channel_recs
            
        return recommendations