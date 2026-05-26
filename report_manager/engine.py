"""
Report Engine - Logic for assembling premium Excel reports from DuckDB using high-fidelity queries.
"""
import io
import logging
import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from data_engine.data_loader import get_data_loader
import report_manager.report_query as rq

logger = logging.getLogger(__name__)

# Premium Report Catalog
REPORT_CATALOG = {
    "exec_health": {
        "title": "Executive Platform Health Summary",
        "description": "Premium health indicators including cross-platform snapshot, organisation risk levels, growth trends, and audit metrics.",
        "icon": "insights",
        "sheets": ["Platform Snapshot", "Org Health", "User Growth Trend", "Audit Performance"]
    },
    "sales_churn": {
        "title": "Sales Opportunity & Churn Risk",
        "description": "Actionable customer success metrics detailing churning risk scores, expansion upsell signals, and platform usage leaderboards.",
        "icon": "trending_up",
        "sheets": ["Churn Risk", "Expansion Signals", "Org Leaderboard"]
    },
    "product_adoption": {
        "title": "Product Feature Adoption & Module Usage",
        "description": "Granular user experience insights detailing page/module activity levels, audit compliance funnel metrics, and user roles.",
        "icon": "view_module",
        "sheets": ["Module Usage", "Audit Funnel Depth", "Feature Signals", "User Roles"]
    },
    "user_engagement": {
        "title": "User Engagement & Retention",
        "description": "Deep-dive engagement audit summarizing traffic source quality, geographic distribution, daily trendlines, and power-user stickiness.",
        "icon": "public",
        "sheets": ["Engagement KPIs", "Daily Trend", "User Segments", "Traffic Quality", "Geographic Dist"]
    },
    "aml_operations": {
        "title": "RegPort Compliance Operations",
        "description": "Specialized audit of financial transaction monitoring, sanction rule triggers, customer verification rates, and monitored account pipelines.",
        "icon": "security",
        "sheets": ["Transaction Summary", "Rule Performance", "Verification Activity", "Report Pipeline", "Monitored Accounts"]
    }
}

class ReportEngine:
    def __init__(self):
        self.loader = get_data_loader()

    def generate_excel_report(self, report_key, platform, start_date, end_date, org_id=None, file_path=None):
        """
        Generate a multi-sheet premium Excel report using high-fidelity queries.
        """
        if report_key not in REPORT_CATALOG:
            raise ValueError(f"Report key '{report_key}' not found in catalog.")
            
        wb = Workbook()
        wb.remove(wb.active)  # Remove default active sheet
        
        # Helper to format and run the high-fidelity queries
        def run_sheet_query(query_template):
            # Resolve platform filter
            plat_filter = "" if platform == "All" else f"AND platform = '{platform}'"
            
            # Resolve organization filter
            org_filter = f"AND organization_id = '{org_id}'" if org_id else ""
            
            # Format query cleanly
            fmt_query = query_template.format(
                platform=platform,
                start_date=start_date,
                end_date=end_date,
                platform_filter_orgs=plat_filter,
                platform_filter_users=plat_filter,
                platform_filter_dom=plat_filter,
                platform_filter_dpm=plat_filter,
                platform_filter_dum=plat_filter,
                platform_filter_geo=plat_filter,
                platform_filter_tsm=plat_filter,
                org_filter_audit=org_filter,
                org_filter_rp=org_filter
            )
            return self.loader.execute_query(fmt_query)

        try:
            if report_key == "exec_health":
                # Sheet 1: Snapshot
                df1 = run_sheet_query(rq.EXEC_PLATFORM_SNAPSHOT)
                self._add_df_to_sheet(wb, df1, "Platform Snapshot")
                
                # Sheet 2: Org Health
                df2 = run_sheet_query(rq.EXEC_ORG_HEALTH)
                self._add_df_to_sheet(wb, df2, "Org Health")
                
                # Sheet 3: User Growth
                df3 = run_sheet_query(rq.EXEC_USER_GROWTH_TREND)
                self._add_df_to_sheet(wb, df3, "User Growth Trend")
                
                # Sheet 4: RegComply Audits (RegComply/All scope only)
                if platform in ("All", "RegComply"):
                    df4 = run_sheet_query(rq.EXEC_AUDIT_PERFORMANCE)
                    self._add_df_to_sheet(wb, df4, "Audit Performance")
                    
            elif report_key == "sales_churn":
                # Sheet 1: Churn Risk
                df1 = run_sheet_query(rq.SALES_CHURN_RISK)
                self._add_df_to_sheet(wb, df1, "Churn Risk")
                
                # Sheet 2: Expansion
                df2 = run_sheet_query(rq.SALES_EXPANSION_SIGNALS)
                self._add_df_to_sheet(wb, df2, "Expansion Signals")
                
                # Sheet 3: Leaderboard
                df3 = run_sheet_query(rq.SALES_ORG_LEADERBOARD)
                self._add_df_to_sheet(wb, df3, "Org Leaderboard")
                
            elif report_key == "product_adoption":
                # Sheet 1: Module Usage
                df1 = run_sheet_query(rq.PRODUCT_MODULE_USAGE)
                self._add_df_to_sheet(wb, df1, "Module Usage")
                
                # Sheet 2: Audit Funnel (RegComply/All scope only)
                if platform in ("All", "RegComply"):
                    df2 = run_sheet_query(rq.PRODUCT_AUDIT_FUNNEL)
                    self._add_df_to_sheet(wb, df2, "Audit Funnel Depth")
                    
                # Sheet 3: Feature Signals
                df3 = run_sheet_query(rq.PRODUCT_FEATURE_SIGNALS)
                self._add_df_to_sheet(wb, df3, "Feature Signals")
                
                # Sheet 4: User Roles
                df4 = run_sheet_query(rq.PRODUCT_USER_ROLES)
                self._add_df_to_sheet(wb, df4, "User Roles")
                
            elif report_key == "user_engagement":
                # Sheet 1: Engagement KPIs
                df1 = run_sheet_query(rq.ENGAGEMENT_KPIS)
                self._add_df_to_sheet(wb, df1, "Engagement KPIs")
                
                # Sheet 2: Daily Trend
                df2 = run_sheet_query(rq.ENGAGEMENT_DAILY_TREND)
                self._add_df_to_sheet(wb, df2, "Daily Trend")
                
                # Sheet 3: User Segments
                df3 = run_sheet_query(rq.ENGAGEMENT_USER_SEGMENTS)
                self._add_df_to_sheet(wb, df3, "User Segments")
                
                # Sheet 4: Traffic Quality
                df4 = run_sheet_query(rq.ENGAGEMENT_TRAFFIC_QUALITY)
                self._add_df_to_sheet(wb, df4, "Traffic Quality")
                
                # Sheet 5: Geo Dist
                df5 = run_sheet_query(rq.ENGAGEMENT_GEO)
                self._add_df_to_sheet(wb, df5, "Geographic Dist")
                
            elif report_key == "aml_operations":
                # Sheet 1: Transaction Summary
                df1 = run_sheet_query(rq.AML_TRANSACTION_SUMMARY)
                self._add_df_to_sheet(wb, df1, "Transaction Summary")
                
                # Sheet 2: Rule Performance
                df2 = run_sheet_query(rq.AML_RULE_PERFORMANCE)
                self._add_df_to_sheet(wb, df2, "Rule Performance")
                
                # Sheet 3: Verification
                df3 = run_sheet_query(rq.AML_VERIFICATION_ACTIVITY)
                self._add_df_to_sheet(wb, df3, "Verification Activity")
                
                # Sheet 4: Report Pipeline
                df4 = run_sheet_query(rq.AML_REPORT_PIPELINE)
                self._add_df_to_sheet(wb, df4, "Report Pipeline")
                
                # Sheet 5: Monitored Accounts
                df5 = run_sheet_query(rq.AML_MONITORED_ACCOUNTS)
                self._add_df_to_sheet(wb, df5, "Monitored Accounts")
                
            else:
                raise NotImplementedError(f"Report Logic for '{report_key}' is not implemented.")

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
        """Helper to add a DataFrame to a new sheet in the workbook with dynamic width auto-fit."""
        ws = wb.create_sheet(title=sheet_title)
        
        # Ensure column headers and row values are clean
        for r in dataframe_to_rows(df, index=False, header=True):
            ws.append(r)
        
        # Simple column width adjustment
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if cell.value is not None:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            adjusted_width = (max_length + 3)
            ws.column_dimensions[column_letter].width = min(adjusted_width, 60)

_engine_instance = None
def get_report_engine():
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ReportEngine()
    return _engine_instance
