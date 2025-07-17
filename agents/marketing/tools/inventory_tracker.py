from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
import pandas as pd

class InventoryAlert(Enum):
    LOW_STOCK = "low_stock"
    STOCKOUT_RISK = "stockout_risk"
    EXCESS_STOCK = "excess_stock"
    REORDER_NEEDED = "reorder_needed"
    PROMO_IMPACT = "promotional_impact"

@dataclass
class SKUStatus:
    sku: str
    current_stock: int
    reorder_point: int
    safety_stock: int
    lead_time_days: int
    daily_velocity: float
    promo_multiplier: float
    stock_coverage_days: float
    alerts: List[InventoryAlert]

class InventoryTracker:
    def __init__(self):
        self.safety_stock_days = 14  # 2 weeks of safety stock
        self.lead_time_buffer = 1.2  # 20% buffer on lead time

    def track_inventory_levels(self, inventory_data: Dict) -> Dict:
        """
        Monitor inventory levels and generate analysis
        Returns comprehensive inventory status and recommendations
        """
        tracking_results = {
            "timestamp": datetime.now().isoformat(),
            "sku_status": self._check_sku_status(inventory_data),
            "promotional_impact": self._analyze_promotional_impact(inventory_data),
            "supply_chain_status": self._check_supply_chain(inventory_data),
            "recommendations": self._generate_recommendations(inventory_data)
        }
        return tracking_results

    def _check_sku_status(self, inventory_data: Dict) -> Dict[str, SKUStatus]:
        """Monitor status of each SKU"""
        sku_status = {}
        for sku, data in inventory_data.items():
            # Calculate key metrics
            daily_velocity = data.get('weekly_sales', 0) / 7
            promo_multiplier = data.get('promo_lift', 1.0)
            adjusted_velocity = daily_velocity * promo_multiplier

            current_stock = data.get('current_stock', 0)
            safety_stock = daily_velocity * self.safety_stock_days
            lead_time = data.get('lead_time_days', 14)
            reorder_point = (adjusted_velocity * lead_time * self.lead_time_buffer) + safety_stock

            # Calculate stock coverage
            stock_coverage = current_stock / adjusted_velocity if adjusted_velocity > 0 else float('inf')

            # Generate alerts
            alerts = []
            if current_stock < safety_stock:
                alerts.append(InventoryAlert.LOW_STOCK)
            if current_stock < reorder_point:
                alerts.append(InventoryAlert.REORDER_NEEDED)
            if stock_coverage < lead_time:
                alerts.append(InventoryAlert.STOCKOUT_RISK)
            if stock_coverage > lead_time * 3:  # More than 3x lead time coverage
                alerts.append(InventoryAlert.EXCESS_STOCK)
            if promo_multiplier > 1.2:  # 20% lift triggers promotional impact alert
                alerts.append(InventoryAlert.PROMO_IMPACT)

            sku_status[sku] = SKUStatus(
                sku=sku,
                current_stock=current_stock,
                reorder_point=int(reorder_point),
                safety_stock=int(safety_stock),
                lead_time_days=lead_time,
                daily_velocity=daily_velocity,
                promo_multiplier=promo_multiplier,
                stock_coverage_days=stock_coverage,
                alerts=alerts
            )
        return sku_status

    def _analyze_promotional_impact(self, inventory_data: Dict) -> Dict:
        """Analyze impact of promotions on inventory"""
        promo_impact = {
            "impacted_skus": [],
            "risk_assessment": [],
            "required_actions": []
        }
        sku_status = self._check_sku_status(inventory_data)
        for sku, status in sku_status.items():
            if status.promo_multiplier > 1:
                impact_analysis = {
                    "sku": sku,
                    "baseline_velocity": status.daily_velocity,
                    "promotional_velocity": status.daily_velocity * status.promo_multiplier,
                    "stock_coverage_baseline": status.current_stock / status.daily_velocity,
                    "stock_coverage_promotional": status.current_stock / (status.daily_velocity * status.promo_multiplier),
                    "risk_level": self._calculate_promo_risk(status)
                }
                promo_impact["impacted_skus"].append(impact_analysis)
                if impact_analysis["risk_level"] > 0.7:  # High risk
                    promo_impact["risk_assessment"].append({
                        "sku": sku,
                        "risk_level": "HIGH",
                        "potential_stockout_date": datetime.now() +
                            timedelta(days=impact_analysis["stock_coverage_promotional"])
                    })
                    promo_impact["required_actions"].append({
                        "sku": sku,
                        "action": "Expedite Reorder",
                        "quantity": int(status.reorder_point - status.current_stock),
                        "urgency": "High"
                    })
        return promo_impact

    def _check_supply_chain(self, inventory_data: Dict) -> Dict:
        """Monitor supply chain status and coordination"""
        supply_chain_status = {
            "open_orders": [],
            "lead_time_updates": [],
            "fulfillment_risks": [],
            "coordination_actions": []
        }
        sku_status = self._check_sku_status(inventory_data)
        for sku, status in sku_status.items():
            # Check open orders
            if 'open_orders' in inventory_data[sku]:
                for order in inventory_data[sku]['open_orders']:
                    supply_chain_status["open_orders"].append({
                        "sku": sku,
                        "order_id": order['order_id'],
                        "quantity": order['quantity'],
                        "expected_date": order['expected_date'],
                        "status": order['status']
                    })
            # Check lead time trends
            if 'lead_time_history' in inventory_data[sku]:
                lead_time_trend = self._analyze_lead_time_trend(
                    inventory_data[sku]['lead_time_history']
                )
                if lead_time_trend['change'] > 0.1:  # 10% increase
                    supply_chain_status["lead_time_updates"].append({
                        "sku": sku,
                        "change": f"+{lead_time_trend['change']*100:.1f}%",
                        "impact": "Increase reorder points"
                    })
            # Assess fulfillment risks
            if InventoryAlert.STOCKOUT_RISK in status.alerts:
                supply_chain_status["fulfillment_risks"].append({
                    "sku": sku,
                    "risk_type": "Stockout Risk",
                    "impact": "Customer satisfaction",
                    "required_action": "Expedite delivery"
                })
        return supply_chain_status

    def _calculate_promo_risk(self, status: SKUStatus) -> float:
        """Calculate risk level for promotional impact"""
        coverage_ratio = status.stock_coverage_days / status.lead_time_days
        velocity_impact = status.promo_multiplier - 1
        risk_score = (1 - coverage_ratio) * 0.6 + velocity_impact * 0.4
        return max(0, min(1, risk_score))

    def _analyze_lead_time_trend(self, history: List) -> Dict:
        """Analyze trends in lead time"""
        if not history:
            return {"change": 0, "trend": "stable"}
        recent_avg = np.mean(history[-3:])
        previous_avg = np.mean(history[:-3])
        change = (recent_avg - previous_avg) / previous_avg
        return {
            "change": change,
            "trend": "increasing" if change > 0 else "decreasing"
        }

    def _generate_recommendations(self, inventory_data: Dict) -> List[Dict]:
        """Generate inventory management recommendations"""
        recommendations = []
        sku_status = self._check_sku_status(inventory_data)
        for sku, status in sku_status.items():
            if InventoryAlert.REORDER_NEEDED in status.alerts:
                recommendations.append({
                    "sku": sku,
                    "type": "reorder",
                    "quantity": status.reorder_point - status.current_stock,
                    "urgency": "high" if InventoryAlert.LOW_STOCK in status.alerts else "medium",
                    "reason": "Below reorder point"
                })
            if InventoryAlert.EXCESS_STOCK in status.alerts:
                recommendations.append({
                    "sku": sku,
                    "type": "reduce_stock",
                    "quantity": status.current_stock - (status.reorder_point * 2),
                    "urgency": "medium",
                    "reason": "Excess inventory holding costs"
                })
            if InventoryAlert.PROMO_IMPACT in status.alerts:
                recommendations.append({
                    "sku": sku,
                    "type": "promo_adjustment",
                    "action": "Increase safety stock",
                    "quantity": int(status.safety_stock * (status.promo_multiplier - 1)),
                    "urgency": "high",
                    "reason": "Promotional impact on velocity"
                })
        return recommendations


  