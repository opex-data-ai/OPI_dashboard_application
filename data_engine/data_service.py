"""
Data service - API layer for frontend to fetch data
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any

from data_engine.data_loader import get_data_loader


class DataService:
    """
    Service layer that provides clean API for frontend to fetch data
    """
    
    def __init__(self):
        self.loader = get_data_loader()
    
    def get_kpi_metrics(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Get KPI metrics data
        
        Args:
            start_date: Start date (YYYY-MM-DD) or None for default
            end_date: End date (YYYY-MM-DD) or None for default
            
        Returns:
            pd.DataFrame: KPI metrics
        """
        # Default to last 30 days if not specified
        if not start_date or not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        return self.loader.get_data_for_metric('kpi_metrics', start_date, end_date, 'kpi_metrics.sql')

    def get_country_summary(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Get country summary data
        """
        if not start_date or not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        return self.loader.get_data_for_metric('country_summary', start_date, end_date, 'country_summary.sql')

    def get_user_trend(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Get user trend data
        """
        if not start_date or not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        return self.loader.get_data_for_metric('kpi_metrics', start_date, end_date, 'user_trend.sql')
    
    def get_task_progress(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Get task progress data
        """
        if not start_date or not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        return self.loader.get_data_for_metric('task_progress', start_date, end_date, 'task_progress.sql')
    
    def format_for_chart(self, df: pd.DataFrame, metric_col: str = 'metric') -> Dict[str, Any]:
        """
        Format DataFrame for frontend chart consumption
        
        Args:
            df: DataFrame with metrics
            metric_col: Column name containing metric names
            
        Returns:
            dict: Formatted data for charts
        """
        if df is None or df.empty:
            return {'labels': [], 'datasets': []}
        
        # Convert to dictionary format
        result = df.set_index(metric_col).to_dict('index')
        
        return result
    
    def get_summary_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate summary statistics from DataFrame
        
        Args:
            df: Source DataFrame
            
        Returns: 
            dict: Summary statistics
        """
        if df is None or df.empty:
            return {}
        
        # Calculate basic stats
        summary = {
            'total_records': len(df),
            'columns': list(df.columns),
            'sample_data': df.head(5).to_dict('records')
        }
        
        # Add numeric column stats
        numeric_cols = df.select_dtypes(include=['number']).columns
        for col in numeric_cols:
            summary[f'{col}_sum'] = float(df[col].sum())
            summary[f'{col}_avg'] = float(df[col].mean())
        
        return summary
    
    def reload_all_data(self):
        """Force reload all data from Drive"""
        return self.loader.load_all_data(force_reload=True)


# Singleton instance
_data_service_instance = None

def get_data_service():
    """Get or create DataService singleton"""
    global _data_service_instance
    if _data_service_instance is None:
        _data_service_instance = DataService()
    return _data_service_instance