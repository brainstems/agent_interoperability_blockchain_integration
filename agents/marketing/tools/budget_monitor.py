# budget_monitor.py

from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict
import numpy as np
from enum import Enum

class BudgetAlert(Enum):
    OVERSPEND = "overspend"
    UNDERSPEND = "underspend"
    INEFFICIENT = "inefficient"
    OPPORTUNITY = "opportunity"

@dataclass
class BudgetStatus:
    allocated: float
    spent: float
    remaining: float
    efficiency_score: float  # 0-1 score
    roas: float
    growth_impact: float
    alerts: List[BudgetAlert]

class BudgetMonitor:
    def __init__(self, total_budget: float, monitoring_interval: int = 300):  # 5-minute interval
        self.total_budget = total_budget
        self.monitoring_interval = monitoring_interval
        self.target_growth = 0.03
        
        # Initialize channel allocations
        self.channel_allocations = {
            "amazon_store": 0.20,
            "sponsored_products": 0.45,
            "sponsored_brands": 0.20,
            "sponsored_display": 0.15
        }
        
        # Performance thresholds
        self.thresholds = {
            "roas_min": 2.5,
            "roas_target": 3.5,
            "efficiency_min": 0.7,
            "spend_rate_max": 1.2,  # 20% over target
            "spend_rate_min": 0.8   # 20% under target
        }
        
    def monitor_budget_allocation(self, current_performance: Dict) -> Dict:
        """
        Monitor and analyze budget allocation across channels
        Returns analysis and recommendations
        """
        monitoring_results = {
            "timestamp": datetime.now().isoformat(),
            "channel_status": self._check_channel_status(current_performance),
            "efficiency_analysis": self._analyze_efficiency(current_performance),
            "optimization_recommendations": self._generate_recommendations(current_performance),
            "growth_impact": self._assess_growth_impact(current_performance)
        }
        
        return monitoring_results
        
    def _check_channel_status(self, performance: Dict) -> Dict[str, BudgetStatus]:
        """Check current status of each channel"""
        channel_status = {}
        
        for channel, allocation in self.channel_allocations.items():
            channel_budget = self.total_budget * allocation
            channel_perf = performance.get(channel, {})
            
            # Calculate metrics
            spent = channel_perf.get('spent', 0)
            remaining = channel_budget - spent
            efficiency = self._calculate_efficiency(channel_perf)
            roas = channel_perf.get('roas', 0)
            growth = channel_perf.get('growth_rate', 0)
            
            # Generate alerts
            alerts = []
            if spent/channel_budget > self.thresholds["spend_rate_max"]:
                alerts.append(BudgetAlert.OVERSPEND)
            elif spent/channel_budget < self.thresholds["spend_rate_min"]:
                alerts.append(BudgetAlert.UNDERSPEND)
            if efficiency < self.thresholds["efficiency_min"]:
                alerts.append(BudgetAlert.INEFFICIENT)
            if roas > self.thresholds["roas_target"] and remaining > 0:
                alerts.append(BudgetAlert.OPPORTUNITY)
                
            channel_status[channel] = BudgetStatus(
                allocated=channel_budget,
                spent=spent,
                remaining=remaining,
                efficiency_score=efficiency,
                roas=roas,
                growth_impact=growth,
                alerts=alerts
            )
            
        return channel_status
        
    def _calculate_efficiency(self, channel_perf: Dict) -> float:
        """Calculate efficiency score for a channel"""
        weights = {
            'roas_weight': 0.4,
            'growth_weight': 0.3,
            'conversion_weight': 0.3
        }
        
        roas_score = min(channel_perf.get('roas', 0) / self.thresholds["roas_target"], 1)
        growth_score = min(channel_perf.get('growth_rate', 0) / self.target_growth, 1)
        conversion_score = min(channel_perf.get('conversion_rate', 0) / 0.1, 1)  # 10% baseline
        
        efficiency = (
            roas_score * weights['roas_weight'] +
            growth_score * weights['growth_weight'] +
            conversion_score * weights['conversion_weight']
        )
        
        return round(efficiency, 2)
        
    def _analyze_efficiency(self, performance: Dict) -> Dict:
        """Analyze budget efficiency across channels"""
        channel_status = self._check_channel_status(performance)
        
        efficiency_analysis = {
            "overall_efficiency": np.mean([status.efficiency_score for status in channel_status.values()]),
            "channel_efficiency": {
                channel: {
                    "efficiency_score": status.efficiency_score,
                    "spend_ratio": status.spent / status.allocated,
                    "roas": status.roas
                }
                for channel, status in channel_status.items()
            },
            "optimization_opportunities": []
        }
        
        # Identify optimization opportunities
        for channel, status in channel_status.items():
            if BudgetAlert.OPPORTUNITY in status.alerts:
                efficiency_analysis["optimization_opportunities"].append({
                    "channel": channel,
                    "type": "increase_budget",
                    "amount": min(status.allocated * 0.2, status.remaining),
                    "expected_impact": f"{status.roas:.1f}x ROAS"
                })
            elif BudgetAlert.INEFFICIENT in status.alerts:
                efficiency_analysis["optimization_opportunities"].append({
                    "channel": channel,
                    "type": "reduce_budget",
                    "amount": status.allocated * 0.2,
                    "reason": "Low efficiency score"
                })
                
        return efficiency_analysis
        
    def _generate_recommendations(self, performance: Dict) -> List[Dict]:
        """Generate budget optimization recommendations"""
        efficiency_analysis = self._analyze_efficiency(performance)
        channel_status = self._check_channel_status(performance)
        
        recommendations = []
        
        # Process each channel
        for channel, status in channel_status.items():
            if BudgetAlert.OPPORTUNITY in status.alerts:
                # High performing channel with remaining budget
                recommendations.append({
                    "priority": "HIGH",
                    "channel": channel,
                    "action": "Increase budget allocation",
                    "amount": min(status.allocated * 0.2, status.remaining),
                    "reason": f"High ROAS ({status.roas:.1f}x) and positive growth impact"
                })
            elif BudgetAlert.INEFFICIENT in status.alerts:
                # Underperforming channel
                recommendations.append({
                    "priority": "HIGH",
                    "channel": channel,
                    "action": "Reduce budget allocation",
                    "amount": status.allocated * 0.2,
                    "reason": "Low efficiency score and suboptimal ROAS"
                })
                
        return recommendations
        
    def _assess_growth_impact(self, performance: Dict) -> Dict:
        """Assess impact on growth targets"""
        channel_status = self._check_channel_status(performance)
        
        growth_impact = {
            "overall_growth_rate": np.mean([status.growth_impact for status in channel_status.values()]),
            "gap_to_target": 0,
            "channel_impact": {},
            "recommendations": []
        }
        
        # Calculate gap to target
        growth_impact["gap_to_target"] = self.target_growth - growth_impact["overall_growth_rate"]
        
        # Assess each channel's contribution
        for channel, status in channel_status.items():
            growth_impact["channel_impact"][channel] = {
                "growth_rate": status.growth_impact,
                "contribution_to_gap": (self.target_growth - status.growth_impact) * self.channel_allocations[channel]
            }
            
            # Generate growth-focused recommendations
            if status.growth_impact < self.target_growth and status.roas > self.thresholds["roas_min"]:
                growth_impact["recommendations"].append({
                    "channel": channel,
                    "action": "Increase budget for growth",
                    "amount": status.allocated * 0.15,
                    "expected_impact": f"+{(status.roas * 0.15):.1f}% growth potential"
                })
                
        return growth_impact