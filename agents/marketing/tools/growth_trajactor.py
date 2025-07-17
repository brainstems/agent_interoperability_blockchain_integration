from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from scipy import stats

class GrowthRisk(Enum):
	HIGH = "high"
	MEDIUM = "medium"
	LOW = "low"

@dataclass
class ChannelForecast:
	channel: str
	current_growth: float
	projected_growth: float
	confidence_interval: tuple
	trend_strength: float
	risk_level: GrowthRisk
	days_to_target: Optional[int]

class GrowthTrajectoryForecaster:
	def __init__(self, target_growth: float = 0.03):
		self.target_growth = target_growth
		self.confidence_level = 0.95
		self.minimum_data_points = 14  # 2 weeks minimum

	def forecast_growth_trajectory(self, historical_data: Dict, current_performance: Dict) -> Dict:
		"""
		Analyze growth trends and forecast future performance
		Returns comprehensive growth analysis and projections
		"""
		forecast_results = {
			"timestamp": datetime.now().isoformat(),
			"channel_forecasts": self._generate_channel_forecasts(historical_data, current_performance),
			"overall_projection": self._calculate_overall_projection(historical_data, current_performance),
			"risk_assessment": self._assess_growth_risks(historical_data, current_performance),
			"recommendations": self._generate_recommendations(historical_data, current_performance)
		}

		return forecast_results

	def _generate_channel_forecasts(self, historical_data: Dict, current_performance: Dict) -> Dict[str, ChannelForecast]:
		"""Generate forecasts for each channel"""
		channel_forecasts = {}

		for channel in current_performance.keys():
			# Extract historical growth rates
			growth_rates = historical_data.get(channel, {}).get('daily_growth_rates', [])

			if len(growth_rates) < self.minimum_data_points:
				continue

			# Prepare data for regression
			X = np.arange(len(growth_rates)).reshape(-1, 1)
			y = np.array(growth_rates)

			# Fit linear regression
			model = LinearRegression()
			model.fit(X, y)

			# Calculate trend strength (R-squared)
			trend_strength = model.score(X, y)

			# Project future growth
			future_days = np.array([[len(growth_rates) + 7]])  # Project 7 days ahead
			projected_growth = model.predict(future_days)[0]

			# Calculate confidence interval
			confidence = self._calculate_confidence_interval(y, model.predict(X))

			# Estimate days to target
			days_to_target = self._estimate_days_to_target(
				current_growth=growth_rates[-1],
				target_growth=self.target_growth,
				growth_rate=model.coef_[0]
			)

			# Assess risk level
			risk_level = self._determine_risk_level(
				current_growth=growth_rates[-1],
				projected_growth=projected_growth,
				trend_strength=trend_strength
			)

			channel_forecasts[channel] = ChannelForecast(
				channel=channel,
				current_growth=growth_rates[-1],
				projected_growth=projected_growth,
				confidence_interval=confidence,
				trend_strength=trend_strength,
				risk_level=risk_level,
				days_to_target=days_to_target
			)

		return channel_forecasts

	def _calculate_confidence_interval(self, actual: np.array, predicted: np.array) -> tuple:
		"""Calculate confidence interval for growth projection"""
		mse = np.mean((actual - predicted) ** 2)
		std_err = np.sqrt(mse)

		z_score = stats.norm.ppf(1 - (1 - self.confidence_level) / 2)
		margin = z_score * std_err

		return (predicted[-1] - margin, predicted[-1] + margin)

	def _estimate_days_to_target(self, current_growth: float, target_growth: float, growth_rate: float) -> Optional[int]:
		"""Estimate days until target growth is reached"""
		if growth_rate <= 0 or current_growth >= target_growth:
			return None

		days = (target_growth - current_growth) / growth_rate
		return int(np.ceil(days))

	def _determine_risk_level(self, current_growth: float, projected_growth: float, trend_strength: float) -> GrowthRisk:
		"""Determine risk level based on growth metrics"""
		if trend_strength < 0.5 or projected_growth < self.target_growth * 0.8:
			return GrowthRisk.HIGH
		elif trend_strength < 0.7 or projected_growth < self.target_growth:
			return GrowthRisk.MEDIUM
		else:
			return GrowthRisk.LOW

	def _calculate_overall_projection(self, historical_data: Dict, current_performance: Dict) -> Dict:
		"""Calculate overall growth projection across all channels"""
		channel_forecasts = self._generate_channel_forecasts(historical_data, current_performance)

		weighted_projection = 0
		total_weight = 0

		for channel, forecast in channel_forecasts.items():
			channel_weight = current_performance[channel].get('revenue_share', 1)
			weighted_projection += forecast.projected_growth * channel_weight
			total_weight += channel_weight

		overall_projection = weighted_projection / total_weight if total_weight > 0 else 0

		return {
			"projected_growth": overall_projection,
			"target_gap": self.target_growth - overall_projection,
			"probability_of_success": self._calculate_success_probability(channel_forecasts),
			"required_adjustments": self._calculate_required_adjustments(
				overall_projection, channel_forecasts
			)
		}

	def _calculate_success_probability(self, channel_forecasts: Dict[str, ChannelForecast]) -> float:
		"""Calculate probability of reaching target growth"""
		risk_weights = {
			GrowthRisk.LOW: 0.9,
			GrowthRisk.MEDIUM: 0.6,
			GrowthRisk.HIGH: 0.3
		}

		weighted_probability = sum(
			risk_weights[f.risk_level] * f.trend_strength
			for f in channel_forecasts.values()
		)

		return weighted_probability / len(channel_forecasts) if channel_forecasts else 0

	def _assess_growth_risks(self, historical_data: Dict, current_performance: Dict) -> Dict:
		"""Assess risks to growth targets"""
		channel_forecasts = self._generate_channel_forecasts(historical_data, current_performance)

		risk_assessment = {
			"overall_risk_level": self._calculate_overall_risk(channel_forecasts),
			"channel_risks": {},
			"risk_factors": [],
			"mitigation_strategies": []
		}

		for channel, forecast in channel_forecasts.items():
			risk_assessment["channel_risks"][channel] = {
				"risk_level": forecast.risk_level.value,
				"factors": self._identify_risk_factors(forecast),
				"impact": self._calculate_risk_impact(forecast, current_performance[channel])
			}

			# Aggregate risk factors
			risk_assessment["risk_factors"].extend(
				self._identify_risk_factors(forecast)
			)

			# Generate mitigation strategies
			risk_assessment["mitigation_strategies"].extend(
				self._generate_mitigation_strategies(forecast)
			)

		return risk_assessment

	def _calculate_overall_risk(self, channel_forecasts: Dict[str, ChannelForecast]) -> GrowthRisk:
		"""Calculate overall risk level"""
		risk_scores = {
			GrowthRisk.LOW: 1,
			GrowthRisk.MEDIUM: 2,
			GrowthRisk.HIGH: 3
		}

		avg_risk = np.mean([
			risk_scores[f.risk_level] for f in channel_forecasts.values()
		])

		if avg_risk >= 2.5:
			return GrowthRisk.HIGH
		elif avg_risk >= 1.5:
			return GrowthRisk.MEDIUM
		else:
			return GrowthRisk.LOW

	def _identify_risk_factors(self, forecast: ChannelForecast) -> List[str]:
		"""Identify specific risk factors"""
		risk_factors = []

		if forecast.trend_strength < 0.5:
			risk_factors.append("Weak growth trend")
		if forecast.projected_growth < self.target_growth:
			risk_factors.append("Below target projection")
		if forecast.confidence_interval[1] < self.target_growth:
			risk_factors.append("Low probability of reaching target")

		return risk_factors

	def _calculate_risk_impact(self, forecast: ChannelForecast, performance: Dict) -> str:
		"""Calculate potential impact of risks"""
		revenue_share = performance.get('revenue_share', 0)
		impact_score = revenue_share * (self.target_growth - forecast.projected_growth)

		if impact_score > 0.01:
			return "High Impact"
		elif impact_score > 0.005:
			return "Medium Impact"
		else:
			return "Low Impact"

	def _generate_mitigation_strategies(self, forecast: ChannelForecast) -> List[Dict]:
		"""Generate risk mitigation strategies"""
		strategies = []

		if forecast.risk_level == GrowthRisk.HIGH:
			strategies.append({
				"channel": forecast.channel,
				"strategy": "Immediate intervention required",
				"actions": [
					"Review channel strategy",
					"Increase marketing investment",
					"Optimize targeting"
				],
				"priority": "High"
			})
		elif forecast.risk_level == GrowthRisk.MEDIUM:
			strategies.append({
				"channel": forecast.channel,
				"strategy": "Proactive optimization",
				"actions": [
					"Monitor key metrics",
					"Test new targeting options",
					"Optimize bid strategy"
				],
				"priority": "Medium"
			})

		return strategies

	def _generate_recommendations(self, historical_data: Dict, current_performance: Dict) -> List[Dict]:
		"""Generate growth-focused recommendations"""
		channel_forecasts = self._generate_channel_forecasts(historical_data, current_performance)
		recommendations = []

		for channel, forecast in channel_forecasts.items():
			if forecast.projected_growth < self.target_growth:
				growth_gap = self.target_growth - forecast.projected_growth

				recommendations.append({
					"channel": channel,
					"type": "growth_acceleration",
					"gap": growth_gap,
					"actions": [
						f"Increase investment by {growth_gap * 100:.1f}%",
						"Expand targeting",
						"Test new ad formats"
					],
					"priority": forecast.risk_level.value
				})

		return recommendations

	def _calculate_required_adjustments(self, overall_projection: float, channel_forecasts: Dict[str, ChannelForecast]) -> List[Dict]:
		"""Calculate required adjustments to meet target growth"""
		required_adjustments = []

		for channel, forecast in channel_forecasts.items():
			if forecast.projected_growth < self.target_growth:
				adjustment_needed = self.target_growth - forecast.projected_growth
				required_adjustments.append({
					"channel": channel,
					"adjustment_needed": adjustment_needed,
					"actions": [
						f"Increase growth by {adjustment_needed * 100:.1f}%",
						"Re-evaluate marketing strategies",
						"Consider new growth initiatives"
					]
				})

		return required_adjustments
