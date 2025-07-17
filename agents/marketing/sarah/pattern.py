from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sarah.types import BaseMetrics
from sarah.types import ResponsePatterns, PatternType, PatternSignal

class SarahChenPatternSimulator:
    def __init__(self, historical_data: Dict[datetime, BaseMetrics]):
        self.historical_data = historical_data
        self.response_patterns = self._analyze_historical_responses()
        self.current_state = {}
        
    def simulate_real_time_patterns(self, current_metrics: BaseMetrics) -> List[PatternSignal]:
        """Simulates real-time pattern recognition based on current metrics"""
        
        # Update current state
        self.current_state = {
            'roas': current_metrics.roas,
            'spend': current_metrics.spend,
            'ctr': current_metrics.ctr,
            'impressions': current_metrics.impressions
        }
        
        # Analyze patterns using rolling windows
        patterns = []
        
        # Check for performance patterns
        if perf_pattern := self._check_performance_pattern():
            patterns.append(perf_pattern)
            
        # Check for opportunity patterns
        if opp_pattern := self._check_opportunity_pattern():
            patterns.append(opp_pattern)
            
        # Check for competitive patterns
        if comp_pattern := self._check_competitive_pattern():
            patterns.append(comp_pattern)
            
        return self._prioritize_patterns(patterns)

    def _analyze_historical_responses(self) -> Dict:
        """Analyzes historical response patterns from Sarah's data"""
        response_analysis = {
            PatternType.PERFORMANCE_DECLINE: {
                'avg_response_time': 10,  # minutes
                'success_rate': 0.92,
                'typical_actions': ['budget_adjustment', 'bid_optimization']
            },
            PatternType.OPPORTUNITY_SIGNAL: {
                'avg_response_time': 20,
                'success_rate': 0.88,
                'typical_actions': ['budget_increase', 'targeting_expansion']
            },
            PatternType.COMPETITIVE_PRESSURE: {
                'avg_response_time': 15,
                'success_rate': 0.85,
                'typical_actions': ['bid_adjustment', 'strategy_review']
            }
        }
        return response_analysis

    def _check_performance_pattern(self) -> Optional[PatternSignal]:
        """Checks for performance-related patterns"""
        
        # Calculate rolling averages
        current_roas = self.current_state.get('roas', 0)
        historical_avg = np.mean([metric.roas for metric in self.historical_data.values()])
        
        if current_roas < historical_avg * 0.9:  # 10% below average
            confidence = self._calculate_confidence(
                current_roas, 
                historical_avg,
                np.std([metric.roas for metric in self.historical_data.values()])
            )
            
            reason = "Current ROAS is significantly below historical average, indicating a performance decline."
            
            return PatternSignal(
                pattern_type=PatternType.PERFORMANCE_DECLINE,
                confidence=confidence,
                urgency=4 if current_roas < historical_avg * 0.8 else 3,
                impact_estimate=(historical_avg - current_roas) * self.current_state.get('spend', 0),
                recommended_response_time=10 if confidence > 0.8 else 15,
                historical_success_rate=self.response_patterns[PatternType.PERFORMANCE_DECLINE]['success_rate'],
                reason=reason
            )
        
        return None

    def _check_opportunity_pattern(self) -> Optional[PatternSignal]:
        """Checks for opportunity patterns"""
        
        current_roas = self.current_state.get('roas', 0)
        historical_avg = np.mean([metric.roas for metric in self.historical_data.values()])
        
        if current_roas > historical_avg * 1.1:  # 10% above average
            confidence = self._calculate_confidence(
                current_roas,
                historical_avg,
                np.std([metric.roas for metric in self.historical_data.values()])
            )
            
            reason = "Current ROAS is significantly above historical average, indicating an opportunity signal."
            
            return PatternSignal(
                pattern_type=PatternType.OPPORTUNITY_SIGNAL,
                confidence=confidence,
                urgency=3,
                impact_estimate=(current_roas - historical_avg) * self.current_state.get('spend', 0),
                recommended_response_time=20,
                historical_success_rate=self.response_patterns[PatternType.OPPORTUNITY_SIGNAL]['success_rate'],
                reason=reason
            )
            
        return None

    def _check_competitive_pattern(self) -> Optional[PatternSignal]:
        """Checks for competitive pressure patterns"""
        
        current_ctr = self.current_state.get('ctr', 0)
        historical_avg_ctr = np.mean([metric.ctr for metric in self.historical_data.values()])
        
        if current_ctr < historical_avg_ctr * 0.85:  # 15% below average
            confidence = self._calculate_confidence(
                current_ctr,
                historical_avg_ctr,
                np.std([metric.ctr for metric in self.historical_data.values()])
            )
            
            reason = "Current CTR is significantly below historical average, indicating competitive pressure."
            
            return PatternSignal(
                pattern_type=PatternType.COMPETITIVE_PRESSURE,
                confidence=confidence,
                urgency=4,
                impact_estimate=(historical_avg_ctr - current_ctr) * self.current_state.get('impressions', 0),
                recommended_response_time=15,
                historical_success_rate=self.response_patterns[PatternType.COMPETITIVE_PRESSURE]['success_rate'],
                reason=reason
            )
            
        return None

    def _calculate_confidence(self, current: float, historical_avg: float, historical_std: float) -> float:
        """Calculates confidence score for pattern detection"""
        z_score = abs(current - historical_avg) / historical_std
        confidence = 1 - (1 / (1 + z_score))
        return min(max(confidence, 0), 1)

    def _prioritize_patterns(self, patterns: List[PatternSignal]) -> List[PatternSignal]:
        """Prioritizes detected patterns based on urgency and impact"""
        if not patterns:
            return []
            
        return sorted(
            patterns,
            key=lambda x: (x.urgency, x.impact_estimate * x.confidence),
            reverse=True
        )