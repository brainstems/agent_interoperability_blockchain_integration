
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from scipy import stats

class RecommendationType(Enum):
    BUDGET = "budget"
    TARGETING = "targeting"
    CREATIVE = "creative"
    GROWTH = "growth"

@dataclass
class CampaignRecommendation:
    type: RecommendationType
    priority: int  # 1 (highest) to 3 (lowest)
    impact: float  # Estimated impact percentage
    effort: int    # 1 (easy) to 3 (complex)
    description: str
    action_items: List[str]
    estimated_roi: float

class CampaignRecommendationEngine:
    def __init__(self, performance_data: Dict):
        self.performance_data = performance_data
        self.growth_target = 0.03  # 3% target

    def generate_campaign_recommendations(self) -> Dict[str, List[CampaignRecommendation]]:
        recommendations = {
            "sponsored_products": self._analyze_sponsored_products(),
            "sponsored_brands": self._analyze_sponsored_brands(),
            "sponsored_display": self._analyze_sponsored_display(),
            "cross_channel": self._analyze_cross_channel()
        }

        # Sort recommendations by priority and impact
        for channel in recommendations:
            recommendations[channel].sort(key=lambda x: (x.priority, -x.impact))

        return recommendations

    def _analyze_sponsored_products(self) -> List[CampaignRecommendation]:
        recommendations = []

        # Budget Optimization
        if self.performance_data["sponsored_products"]["roas"] > 4.0:
            recommendations.append(
                CampaignRecommendation(
                    type=RecommendationType.BUDGET,
                    priority=1,
                    impact=0.15,
                    effort=1,
                    description="Increase budget allocation for high-performing Sponsored Products campaigns",
                    action_items=[
                        "Increase daily budget by 25% for campaigns with ROAS > 4",
                        "Reallocate budget from campaigns with ROAS < 2",
                        "Implement dayparting for peak shopping hours"
                    ],
                    estimated_roi=4.5
                )
            )

        # Targeting Improvements
        recommendations.append(
            CampaignRecommendation(
                type=RecommendationType.TARGETING,
                priority=2,
                impact=0.08,
                effort=2,
                description="Optimize keyword targeting based on search term performance",
                action_items=[
                    "Add top-performing search terms as exact match keywords",
                    "Negative match low-converting search terms",
                    "Expand to related category targets"
                ],
                estimated_roi=3.2
            )
        )

        return recommendations

    def _analyze_sponsored_brands(self) -> List[CampaignRecommendation]:
        recommendations = []

        # Creative Optimization
        recommendations.append(
            CampaignRecommendation(
                type=RecommendationType.CREATIVE,
                priority=1,
                impact=0.12,
                effort=2,
                description="Enhance Sponsored Brands creative assets",
                action_items=[
                    "Update hero images with lifestyle photography",
                    "Test new headline variations",
                    "Implement seasonal creative updates"
                ],
                estimated_roi=3.8
            )
        )

        # Growth Opportunities
        recommendations.append(
            CampaignRecommendation(
                type=RecommendationType.GROWTH,
                priority=2,
                impact=0.10,
                effort=2,
                description="Expand Sponsored Brands video coverage",
                action_items=[
                    "Create video assets for top 10 products",
                    "Test different video lengths",
                    "Implement A/B testing for video content"
                ],
                estimated_roi=3.5
            )
        )

        return recommendations

    def _analyze_sponsored_display(self) -> List[CampaignRecommendation]:
        recommendations = []

        # Targeting Improvements
        recommendations.append(
            CampaignRecommendation(
                type=RecommendationType.TARGETING,
                priority=1,
                impact=0.09,
                effort=2,
                description="Refine audience targeting for Sponsored Display",
                action_items=[
                    "Implement view-based remarketing",
                    "Create product-specific audience segments",
                    "Expand to similar product targets"
                ],
                estimated_roi=3.0
            )
        )

        return recommendations

    def _analyze_cross_channel(self) -> List[CampaignRecommendation]:
        recommendations = []

        # Budget Optimization
        recommendations.append(
            CampaignRecommendation(
                type=RecommendationType.BUDGET,
                priority=1,
                impact=0.20,
                effort=3,
                description="Optimize cross-channel budget allocation",
                action_items=[
                    "Shift 15% budget to highest ROAS channels",
                    "Implement cross-channel attribution model",
                    "Create daypart-specific budget allocation"
                ],
                estimated_roi=4.2
            )
        )

        return recommendations

    def generate_recommendation_report(self) -> str:
        recommendations = self.generate_campaign_recommendations()

        report = """
CAMPAIGN RECOMMENDATIONS REPORT
Generated: {datetime}

1. PRIORITY RECOMMENDATIONS
{priority_recs}

2. BUDGET OPTIMIZATION
{budget_recs}

3. TARGETING IMPROVEMENTS
{targeting_recs}

4. CREATIVE OPTIMIZATIONS
{creative_recs}

5. GROWTH OPPORTUNITIES
{growth_recs}
"""

        def format_recommendation(rec: CampaignRecommendation) -> str:
            return f"""
Priority: {rec.priority}
Impact: {rec.impact*100}%
Effort: {'●' * rec.effort}
Description: {rec.description}
Actions:
{chr(10).join('- ' + item for item in rec.action_items)}
Estimated ROI: {rec.estimated_roi}x
"""

        # Format recommendations by type
        priority_recs = []
        budget_recs = []
        targeting_recs = []
        creative_recs = []
        growth_recs = []

        for channel, recs in recommendations.items():
            for rec in recs:
                if rec.priority == 1:
                    priority_recs.append(f"[{channel}] {format_recommendation(rec)}")
                if rec.type == RecommendationType.BUDGET:
                    budget_recs.append(f"[{channel}] {format_recommendation(rec)}")
                elif rec.type == RecommendationType.TARGETING:
                    targeting_recs.append(f"[{channel}] {format_recommendation(rec)}")
                elif rec.type == RecommendationType.CREATIVE:
                    creative_recs.append(f"[{channel}] {format_recommendation(rec)}")
                elif rec.type == RecommendationType.GROWTH:
                    growth_recs.append(f"[{channel}] {format_recommendation(rec)}")

        return report.format(
            datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            priority_recs="\n".join(priority_recs),
            budget_recs="\n".join(budget_recs),
            targeting_recs="\n".join(targeting_recs),
            creative_recs="\n".join(creative_recs),
            growth_recs="\n".join(growth_recs)
        )