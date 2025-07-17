from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import json

@dataclass
class ResponsePatterns:
    coordination_required: bool
    inventory_check_performed: bool
    competitive_analysis_done: bool
    budget_reallocation_needed: bool
    response_priority: str = 'normal'

class PatternType(Enum):
    PERFORMANCE_DECLINE = "performance_decline"
    OPPORTUNITY_SIGNAL = "opportunity_signal"
    COMPETITIVE_PRESSURE = "competitive_pressure"
    SEASONAL_SHIFT = "seasonal_shift"
    INVENTORY_RISK = "inventory_risk"

@dataclass
class PatternSignal:
    pattern_type: PatternType
    confidence: float
    urgency: int  # 1-5 scale
    impact_estimate: float
    recommended_response_time: int  # minutes
    historical_success_rate: float
    reason: str

    
@dataclass
class BaseMetrics:
    impressions: int
    clicks: int
    spend: float
    sales: float
    roas: float
    ctr: float
    conversion_rate: float
    acos: float

    def __str__(self):
        return (
            f"Base Metrics:\n"
            f"- ROAS: {self.roas}\n"
            f"- CTR: {self.ctr}\n"
            f"- Impressions: {self.impressions}\n"
            f"- Clicks: {self.clicks}\n"
            f"- Spend: {self.spend}\n"
            f"- Sales: {self.sales}\n"
            f"- Conversion Rate: {self.conversion_rate}\n"
            f"- ACOS: {self.acos}\n"
        )

@dataclass
class DecisionRecords:
    review_time: datetime
    decision_type: str
    response_time_minutes: int
    action_taken: str = None
    adjustment_amount: float = 0.0

@dataclass
class InventoryData:
    current_stock: int
    weekly_sales: int
    lead_time_days: int
    promo_lift: float
    open_orders: list
    lead_time_history: list

    def __str__(self):
        return json.dumps(asdict(self), indent=4)
  