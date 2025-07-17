
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from scipy import stats

class CampaignPerformanceTracker:
    def generate_performance_tables(self) -> Dict[str, pd.DataFrame]:
        # Date range for analysis
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # 1. Campaign Performance Overview
        campaign_performance = pd.DataFrame({
            'Campaign Type': ['Sponsored Products', 'Sponsored Brands', 'Sponsored Display', 'Total'],
            'Impressions': [1500000, 750000, 1050000, 3300000],
            'Clicks': [11250, 4875, 5775, 21900],
            'Spend ($)': [45000, 24375, 27562.50, 96937.50],
            'Sales ($)': [180000, 97500, 110250, 387750],
            'ROAS': [4.0, 4.0, 4.0, 4.0],
            'MTD Growth': ['3.2%', '2.8%', '2.5%', '2.8%'],
            'vs Target': ['+0.2%', '-0.2%', '-0.5%', '-0.2%']
        }).set_index('Campaign Type')

        # 2. Daily Trend Analysis
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        daily_trend = pd.DataFrame({
            'Date': dates,
            'Daily Sales': np.random.normal(12500, 1000, len(dates)),
            'Daily ROAS': np.random.normal(4.0, 0.2, len(dates)),
            'Growth vs Prev Day': np.random.normal(0.03/30, 0.005, len(dates)),
        }).set_index('Date')

        # 3. Competitive Analysis
        competitive_analysis = pd.DataFrame({
            'Metric': [
                'Share of Voice',
                'Avg. Position',
                'CTR',
                'Conversion Rate',
                'Avg. Order Value',
                'Market Share'
            ],
            'Our Brand': ['32%', '2.3', '0.75%', '12%', '$35.00', '28%'],
            'Competitor 1': ['28%', '2.5', '0.70%', '11%', '$32.00', '25%'],
            'Competitor 2': ['25%', '2.8', '0.68%', '10%', '$31.00', '22%'],
            'Category Avg': ['25%', '2.7', '0.65%', '10%', '$31.50', '25%']
        }).set_index('Metric')

        # 4. Growth Rate Analysis
        growth_analysis = pd.DataFrame({
            'Channel': [
                'Sponsored Products',
                'Sponsored Brands',
                'Sponsored Display',
                'Total Performance'
            ],
            'Current Growth': ['3.2%', '2.8%', '2.5%', '2.8%'],
            'Target': ['3.0%', '3.0%', '3.0%', '3.0%'],
            'Gap': ['+0.2%', '-0.2%', '-0.5%', '-0.2%'],
            'Projected Month-End': ['3.3%', '2.9%', '2.6%', '2.9%'],
            'Required Daily Growth': ['-', '0.12%', '0.15%', '0.12%']
        }).set_index('Channel')

        # 5. ROAS by Product Category
        category_roas = pd.DataFrame({
            'Category': [
                'Trail Mix',
                'Protein Bars',
                'Dried Fruits',
                'Nuts',
                'Seeds'
            ],
            'ROAS': [4.5, 3.8, 3.5, 4.2, 3.9],
            'Growth Rate': ['3.5%', '3.1%', '2.8%', '3.0%', '2.9%'],
            'Market Position': ['1st', '2nd', '3rd', '1st', '2nd'],
            'vs Competition': ['+15%', '+8%', '+5%', '+12%', '+7%']
        }).set_index('Category')

        return {
            'campaign_performance': campaign_performance,
            'daily_trend': daily_trend,
            'competitive_analysis': competitive_analysis,
            'growth_analysis': growth_analysis,
            'category_roas': category_roas
        }

    def format_tables_for_display(self) -> str:
        tables = self.generate_performance_tables()
        
        output = """
CAMPAIGN PERFORMANCE DASHBOARD
Date Range: Last 30 Days
Last Updated: {current_time}

1. OVERALL CAMPAIGN PERFORMANCE
{campaign_performance}

2. DAILY TREND ANALYSIS (Last 5 Days)
{daily_trend}

3. COMPETITIVE ANALYSIS
{competitive_analysis}

4. GROWTH RATE ANALYSIS
{growth_analysis}

5. ROAS BY PRODUCT CATEGORY
{category_roas}
""".format(
            current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            campaign_performance=tables['campaign_performance'].to_string(),
            daily_trend=tables['daily_trend'].tail().to_string(),
            competitive_analysis=tables['competitive_analysis'].to_string(),
            growth_analysis=tables['growth_analysis'].to_string(),
            category_roas=tables['category_roas'].to_string()
        )
        
        return output