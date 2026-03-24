"""
Report Engine - Logic for assembling Excel reports from DuckDB data.
"""
import io
import logging
import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from data_engine.data_loader import get_data_loader
from data_engine.query_store import (
    ORGANIZATION_BY_PLATFORM_QUERY,
    USER_BY_PLATFORM_QUERY,
    ECOSYSTEM_ADOPTION_RATE_QUERY,
    MULTIPLATFORM_ORGANIZATION_QUERY
)

logger = logging.getLogger(__name__)

# Report Catalog - Dictionary of available reports
REPORT_CATALOG = {
    "kpi_summary": {
        "title": "Platform KPI Summary",
        "description": "High-level metrics including active orgs, users, and ecosystem adoption rates.",
        "icon": "analytics",
        "sheets": ["KPIs", "Adoption Rates"]
    },
    "user_acquisition": {
        "title": "User Acquisition & Trends",
        "description": "Daily tracking of active sessions, broken down by user type (signed-in vs anonymous).",
        "icon": "trending_up",
        "sheets": ["Daily Trends"]
    },
    "geo_traffic": {
        "title": "Geographic & Traffic Analysis",
        "description": "Breakdown of user distribution by country and traffic source channels.",
        "icon": "public",
        "sheets": ["Geographic", "Traffic Sources"]
    },
    "module_usage": {
        "title": "Module Usage Report",
        "description": "Analysis of the most frequently used product modules per platform.",
        "icon": "view_module",
        "sheets": ["Module Usage"]
    },
    "org_engagement": {
        "title": "Organization Engagement",
        "description": "Detailed engagement metrics per organization (requires proper authorization).",
        "icon": "business",
        "sheets": ["Org Engagement"]
    }
}

class ReportEngine:
    def __init__(self):
        self.loader = get_data_loader()

    def generate_excel_report(self, report_key, platform, file_path=None):
        """
        Generate an Excel report for a specific key and platform.
        """
        if report_key not in REPORT_CATALOG:
            raise ValueError(f"Report key '{report_key}' not found in catalog.")
            
        report_info = REPORT_CATALOG[report_key]
        wb = Workbook()
        # Remove default sheet
        wb.remove(wb.active)
        
        try:
            if report_key == "kpi_summary":
                self._build_kpi_summary(wb, platform)
            elif report_key == "user_acquisition":
                self._build_user_acquisition(wb, platform)
            elif report_key == "geo_traffic":
                self._build_geo_traffic(wb, platform)
            elif report_key == "module_usage":
                self._build_module_usage(wb, platform)
            elif report_key == "org_engagement":
                self._build_org_engagement(wb, platform)
            else:
                raise NotImplementedError(f"Report logic for '{report_key}' not implemented.")

            # Save
            if file_path:
                wb.save(file_path)
                return file_path
            
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)
            return output.getvalue()
        except Exception as e:
            logger.error(f"Error generating Excel for {report_key}: {e}")
            raise

    def _add_df_to_sheet(self, wb, df, sheet_title):
        """Helper to add a DataFrame to a new sheet in the workbook."""
        ws = wb.create_sheet(title=sheet_title)
        for r in dataframe_to_rows(df, index=False, header=True):
            ws.append(r)
        
        # Simple column width adjustment
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            ws.column_dimensions[column_letter].width = min(adjusted_width, 50)

    def _build_kpi_summary(self, wb, platform):
        # Query for Orgs
        org_query = ORGANIZATION_BY_PLATFORM_QUERY
        if platform != "All":
            org_query = f"SELECT * FROM ({org_query}) WHERE platform = '{platform}'"
        df_orgs = self.loader.execute_query(org_query)
        self._add_df_to_sheet(wb, df_orgs, "KPIs")
        
        # Adoption Rates
        df_adoption = self.loader.execute_query(ECOSYSTEM_ADOPTION_RATE_QUERY)
        self._add_df_to_sheet(wb, df_adoption, "Adoption Rates")

    def _build_user_acquisition(self, wb, platform):
        query = """
        SELECT 
            CAST(event_date AS DATE) as date,
            COUNT(DISTINCT CASE WHEN user_id IS NOT NULL THEN session_id END) as signed_in_sessions,
            COUNT(DISTINCT CASE WHEN user_id IS NULL THEN session_id END) as anonymous_sessions
        FROM sessions
        """
        if platform != "All":
            query += f" WHERE platform = '{platform}'"
        query += " GROUP BY date ORDER BY date DESC"
        
        df = self.loader.execute_query(query)
        self._add_df_to_sheet(wb, df, "Daily Trends")

    def _build_geo_traffic(self, wb, platform):
        # Geo
        geo_query = "SELECT country, COUNT(DISTINCT user_id) as users FROM all_users"
        if platform != "All":
            geo_query += f" WHERE platform = '{platform}'"
        geo_query += " GROUP BY country ORDER BY users DESC"
        df_geo = self.loader.execute_query(geo_query)
        self._add_df_to_sheet(wb, df_geo, "Geographic")
        
        # Traffic
        traffic_query = "SELECT source, medium, COUNT(*) as sessions FROM sessions"
        if platform != "All":
            traffic_query += f" WHERE platform = '{platform}'"
        traffic_query += " GROUP BY source, medium ORDER BY sessions DESC"
        df_traffic = self.loader.execute_query(traffic_query)
        self._add_df_to_sheet(wb, df_traffic, "Traffic Sources")

    def _build_module_usage(self, wb, platform):
        query = "SELECT page_path, platform, COUNT(*) as pageviews FROM sessions"
        if platform != "All":
            query += f" WHERE platform = '{platform}'"
        query += " GROUP BY page_path, platform ORDER BY pageviews DESC LIMIT 50"
        
        df = self.loader.execute_query(query)
        self._add_df_to_sheet(wb, df, "Module Usage")

    def _build_org_engagement(self, wb, platform):
        query = "SELECT email_domain as organization, count(*) as session_count FROM all_organizations"
        if platform != "All":
            query += f" WHERE platform = '{platform}'"
        query += " GROUP BY organization ORDER BY session_count DESC"
        
        df = self.loader.execute_query(query)
        self._add_df_to_sheet(wb, df, "Org Engagement")

_engine_instance = None
def get_report_engine():
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ReportEngine()
    return _engine_instance
