#!/usr/bin/env python3
"""
Product Intelligence Hub - Table Downloader Script
Downloads all tables/queries associated with a platform (e.g. RegComply, RegPort, RegWatch)
and generates a structured text file describing their schema, description, and visual usage.
"""

import os
import sys
import argparse
import pandas as pd
import duckdb
from datetime import datetime, timedelta
from pathlib import Path

# Add current directory to path to ensure imports work correctly
sys.path.append(os.getcwd())

try:
    from data_engine.query_store import QUERIES
    from data_engine.chart_descriptions import METRIC_INFO
    from data_engine.data_config import DB_PATH
except ImportError:
    print("Error: Could not import data engine files. Please run this script from the workspace root.")
    sys.exit(1)

# Visual component & "Used For" mapping dictionary
METRIC_VISUAL_MAPPING = {
    # Common Product Queries
    'product_active_org_count': {
        'component': 'KPI card',
        'used_for': 'Displaying the total number of unique active organizations in the current period.'
    },
    'product_active_signed_in_users': {
        'component': 'KPI card',
        'used_for': 'Displaying the total number of registered users active on the platform in the current period.'
    },
    'product_anonymous_users_pct': {
        'component': 'KPI card',
        'used_for': 'Showing the percentage of unauthenticated (anonymous) visitors vs signed-in users.'
    },
    'product_engagement_rate': {
        'component': 'KPI card / Metric',
        'used_for': 'Showing the overall platform engagement rate (percentage of sessions with high activity).'
    },
    'product_user_acquisition_trend': {
        'component': 'Line Chart',
        'used_for': 'Visualizing daily active session trends, split by signed-in users and anonymous visitors.'
    },
    'product_geographic_metrics': {
        'component': 'Geographic Map / Metrics Table',
        'used_for': 'Plotting user distribution and session volume by country and city.'
    },
    'product_stickiness': {
        'component': 'Line Chart',
        'used_for': 'Tracking user stickiness ratios (DAU/WAU, DAU/MAU, WAU/MAU) to measure retention.'
    },
    'product_traffic_source_metrics': {
        'component': 'Traffic Split Rows / Bar Chart',
        'used_for': 'Analyzing the channels and sources (e.g. Google, direct) where new users are acquired.'
    },
    'product_session_traffic_metrics': {
        'component': 'Traffic Split Rows / Bar Chart',
        'used_for': 'Analyzing the channels and mediums through which sessions are initiated.'
    },
    'product_avg_pages_per_session': {
        'component': 'KPI card',
        'used_for': 'Displaying the average, max, and min page views per session.'
    },
    'product_time_to_signup': {
        'component': 'KPI card',
        'used_for': 'Showing the average and median cumulative engagement time before a user completes signup.'
    },
    'product_exit_rate_landing': {
        'component': 'KPI card',
        'used_for': 'Indicating the percentage of single-page sessions starting and ending on the landing page.'
    },
    'product_user_journey': {
        'component': 'Path Navigation List',
        'used_for': 'Listing the top 3 high-engagement conversion page pathways followed by users.'
    },
    'product_landing_page_funnel': {
        'component': 'Metrics Table / Funnel',
        'used_for': 'Mapping progression of users from landing pages to key functional modules.'
    },
    'product_engaged_vs_churned_metrics': {
        'component': 'Comparison Cards',
        'used_for': 'Comparing behavior patterns (engagement time, pages per session, key events) between engaged and churned users.'
    },
    'product_engagement_kpis': {
        'component': 'KPI Grid',
        'used_for': 'Showing high-level engagement KPIs: active duration, engaged sessions, key events, and page views.'
    },
    'product_page_engagement_table': {
        'component': 'Metrics Table',
        'used_for': 'Detailed reporting on scroll depth, average time, key events, and pageviews grouped by page path.'
    },
    'product_org_engagement_table': {
        'component': 'Metrics Table',
        'used_for': 'Ranking organizations by session count, key events, and overall engagement rate.'
    },
    'product_org_list': {
        'component': 'Dropdown Selector',
        'used_for': 'Populating the filter selector with all registered organizations for the product.'
    },
    
    # RegComply specific queries
    'regcomply_audit_count': {
        'component': 'KPI card',
        'used_for': 'Displaying the total number of audits conducted.'
    },
    'regcomply_delayed_audits': {
        'component': 'KPI card',
        'used_for': 'Displaying the total number of delayed audits (exceeding planned end date).'
    },
    'regcomply_active_audits': {
        'component': 'KPI card',
        'used_for': 'Displaying the number of audits currently in request, pending, or ongoing status.'
    },
    'regcomply_external_audit_pct': {
        'component': 'KPI card',
        'used_for': 'Showing the percentage of total audits that were conducted by external parties.'
    },
    'regcomply_audit_completion_rate': {
        'component': 'KPI card',
        'used_for': 'Showing the percentage of audits that have reached the completed or audited stage.'
    },
    'regcomply_extension_rate': {
        'component': 'KPI card',
        'used_for': 'Displaying the rate of audits requiring end-date extensions.'
    },
    'regcomply_lifecycle_duration_table': {
        'component': 'Metrics Table',
        'used_for': 'Analyzing average planned vs actual duration at each lifecycle stage grouped by audit title.'
    },
    'regcomply_audit_funnel': {
        'component': 'Funnel Chart',
        'used_for': 'Visualizing audit completion progression: Created -> Questions Set -> Responded -> Audited -> Completed.'
    },
    'regcomply_status_distribution': {
        'component': 'Donut Chart',
        'used_for': 'Displaying the split of active, completed, or failed audits.'
    },
    'regcomply_audit_type_split': {
        'component': 'Bar Chart',
        'used_for': 'Visualizing audit count breakdown by type (Internal vs External).'
    },
    'regcomply_audits_by_standard': {
        'component': 'Column Chart',
        'used_for': 'Comparing total audits conducted per compliance standard (e.g. ISO 27001).'
    },
    'regcomply_audit_duration_trend': {
        'component': 'Line Chart',
        'used_for': 'Tracking the trend of average audit completion times over the current period.'
    },
    'regcomply_org_performance_table': {
        'component': 'Metrics Table',
        'used_for': 'Reporting total audits, completion rates, and average completion duration per organization.'
    },
    
    # RegPort specific queries
    'regport_pulse_active_orgs': {
        'component': 'KPI Card with MoM delta',
        'used_for': 'Showing unique active organizations on RegPort compared with the prior period.'
    },
    'regport_pulse_workflow_completion': {
        'component': 'KPI card',
        'used_for': 'Displaying E2E workflow completion rate (ingestion -> screening -> reporting).'
    },
    'regport_pulse_avg_modules': {
        'component': 'KPI card',
        'used_for': 'Showing the average number of unique modules adopted per active organization.'
    },
    'regport_pulse_flag_resolution': {
        'component': 'KPI card',
        'used_for': 'Showing Suspicious Transaction Flag resolution rate.'
    },
    'regport_pulse_report_approval': {
        'component': 'KPI card',
        'used_for': 'Displaying the approval rate of generated regulatory reports.'
    },
    'regport_pulse_support_touch': {
        'component': 'KPI card',
        'used_for': 'Showing support touch rate (percentage of active orgs opening support tickets).'
    },
    'regport_flag_resolution_funnel': {
        'component': 'Funnel Chart',
        'used_for': 'Tracking user flag resolution steps from dashboard access to final action.'
    },
    'regport_flag_manual_vs_rule': {
        'component': 'Donut Chart',
        'used_for': 'Comparing manual transaction flagging volume vs rule-triggered flagging.'
    },
    'regport_rule_effectiveness': {
        'component': 'Stacked Bar Chart',
        'used_for': 'Analyzing rule outcomes (confirmed, dismissed, escalated) per rule template.'
    },
    'regport_flag_weekly_trend': {
        'component': 'Dual-Axis Line/Bar Chart',
        'used_for': 'Correlating weekly flag volumes (bars) with resolution rates (line).'
    },
    'regport_flag_debit_credit': {
        'component': 'Bar Chart',
        'used_for': 'Displaying flag count split between debit and credit transaction classes.'
    },
    'regport_flag_rate_by_org': {
        'component': 'Metrics Table',
        'used_for': 'Ranking organizations by total transactions, flagged count, and flagging rates.'
    },

    # RegWatch specific queries
    'regwatch_assessment_summary': {
        'component': 'KPI Grid',
        'used_for': 'Summarizing assessments conducted, compliance score, and expired status.'
    },
    'regwatch_assessment_trend_monthly': {
        'component': 'Line Chart',
        'used_for': 'Tracking monthly assessment run volume.'
    },
    'regwatch_assessment_status_breakdown': {
        'component': 'Donut Chart',
        'used_for': 'Visualizing the status distribution of assessments (Completed, Pending, etc.).'
    },
    'regwatch_deadline_adherence': {
        'component': 'KPI card',
        'used_for': 'Displaying deadline adherence rate for regulatory assessments.'
    },
    'regwatch_compliance_score_distribution': {
        'component': 'Column Chart',
        'used_for': 'Showing the distribution of final compliance scores across assessments.'
    },
    'regwatch_regulatory_area_coverage': {
        'component': 'Radar/Bar Chart',
        'used_for': 'Comparing assessment counts and average compliance rates by regulatory area.'
    },
    'regwatch_repeat_assessment_rate': {
        'component': 'KPI card',
        'used_for': 'Representing the rate of organizations repeating the same assessment.'
    },
    'regwatch_regulator_usage': {
        'component': 'Bar Chart',
        'used_for': 'Comparing total assessments run per regulatory body.'
    },
    'regwatch_low_compliance_regulations': {
        'component': 'Metrics Table',
        'used_for': 'Listing regulations with the lowest average compliance scores.'
    },
    
    # Organization deep-dive queries
    'regcomply_org_deep_dive_details': {
        'component': 'Header Profile',
        'used_for': 'Fetching basic organization profile details like plan, country, and members.'
    },
    'regcomply_org_engagement_summary': {
        'component': 'KPI card / Profile Summary',
        'used_for': 'Summarizing active sessions, key events, page views, and engagement rates.'
    },
    'regcomply_org_engagement_daily_trend': {
        'component': 'Line Chart',
        'used_for': 'Visualizing daily active session trends for a specific organization.'
    },
    'regcomply_org_session_device_split': {
        'component': 'Donut Chart',
        'used_for': 'Showing the split of user devices (desktop, mobile, tablet) used by the organization.'
    },
    'regcomply_org_traffic_source': {
        'component': 'Metrics Table',
        'used_for': 'Analyzing traffic acquisition source and medium metrics for the organization.'
    },
    'regcomply_org_conversion_milestones': {
        'component': 'Metrics Table / Milestones',
        'used_for': 'Tracking the timeline and count of key compliance milestone achievements.'
    },
    'regcomply_org_audit_funnel': {
        'component': 'Funnel Chart',
        'used_for': 'Visualizing the audit completion funnel specifically for this organization.'
    },
    'regcomply_org_module_deepdive': {
        'component': 'Metrics Table',
        'used_for': 'Tracking interactive engagement at a detailed module/feature level.'
    },
    'regcomply_org_stage_bottleneck': {
        'component': 'Metrics Table',
        'used_for': 'Identifying stages in the audit lifecycle where this organization experiences the longest delays.'
    },
    'regcomply_org_user_breakdown': {
        'component': 'Metrics Table',
        'used_for': 'Reporting individual user activity, active days, and key event contributions.'
    },
    'product_deep_ga4_weekly_pattern': {
        'component': 'Activity Grid / Heatmap',
        'used_for': 'Showing the weekly/hourly session pattern of the organization.'
    },
    'product_deep_traffic_source': {
        'component': 'Metrics Table',
        'used_for': 'Deep-dive source campaign attribution for the organization.'
    }
}


# Global tables that contain the word 'org' or are mapping lists, which are NOT single-org deep-dives
GLOBAL_ORG_KEYS = {
    'product_org_list',
    'product_org_engagement_table',
    'regcomply_org_performance_table',
    'regcomply_audits_per_org',
    'regport_flag_rate_by_org'
}


def build_parameters(query_key, query_sql, platform, org_id, start_date, end_date):
    """
    Constructs the correct query parameters dynamically based on conventions.
    """
    param_count = query_sql.count('?')
    if param_count == 0:
        return []

    if query_key == 'product_org_list':
        return [platform]

    # Handle Growth & Churn queries which expect years
    if query_key in ('product_churn_rate', 'product_growth_rate'):
        try:
            year = int(end_date.split('-')[0])
        except Exception:
            year = datetime.today().year
        if param_count == 2:
            return [year, year]
        return [year]

    # Check if this is an organization deep dive query
    is_org_query = (
        ('_org_' in query_key or '_deep_' in query_key or query_key.startswith('product_deep_'))
        and query_key not in GLOBAL_ORG_KEYS
    )
    if is_org_query:
        if not org_id:
            return None  # Skip if no org selected
        if param_count == 1:
            return [org_id]
        elif param_count == 2:
            return [org_id, org_id]
        elif param_count == 3:
            return [org_id, start_date, end_date]
        elif param_count == 4:
            if 'platform' in query_sql.lower():
                return [org_id, platform, start_date, end_date]
            else:
                return [org_id, start_date, end_date, org_id]
        elif param_count == 5:
            return [org_id, platform, start_date, end_date, org_id]

    # For standard product/global metrics
    if 'platform' in query_sql.lower() and param_count % 3 == 0:
        return [start_date, end_date, platform] * (param_count // 3)
    else:
        return [start_date, end_date] * (param_count // 2)


def main():
    parser = argparse.ArgumentParser(description="Download product performance tables and schema definitions.")
    parser.add_argument("--platform", required=True, type=str, help="Target platform (e.g. regcomply, regport, regwatch)")
    parser.add_argument("--start-date", type=str, default=None, help="Start date in YYYY-MM-DD format (defaults to 30 days ago)")
    parser.add_argument("--end-date", type=str, default=None, help="End date in YYYY-MM-DD format (defaults to today)")
    parser.add_argument("--org-id", type=str, default=None, help="Specific organization ID for deep-dive queries (default fetches top organization)")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory path (defaults to downloads/<platform>)")
    args = parser.parse_args()

    # 1. Normalize and validate platform name
    platform_input = args.platform.lower().strip()
    valid_platforms = {
        "regcomply": "RegComply",
        "regport": "RegPort",
        "regwatch": "RegWatch"
    }

    if platform_input not in valid_platforms:
        print(f"Error: Invalid platform '{args.platform}'. Must be one of: {', '.join(valid_platforms.keys())}")
        sys.exit(1)

    platform_proper = valid_platforms[platform_input]
    print(f"==================================================")
    print(f"[INFO] INITIALIZING DOWNLOAD FOR PLATFORM: {platform_proper}")
    print(f"==================================================")

    # 2. Setup dates
    if args.end_date:
        end_date = args.end_date
    else:
        end_date = datetime.today().strftime('%Y-%m-%d')

    if args.start_date:
        start_date = args.start_date
    else:
        start_date = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')

    print(f"[INFO] Selected Date Range: {start_date} to {end_date}")

    # 3. Setup paths
    out_dir_path = Path(args.output_dir) if args.output_dir else Path("downloads") / platform_input
    global_dir = out_dir_path / "global_tables"
    org_dir = out_dir_path / "org_deep_dive"

    os.makedirs(global_dir, exist_ok=True)
    os.makedirs(org_dir, exist_ok=True)

    print(f"[INFO] Output directory: {out_dir_path.resolve()}")

    # 4. Connect to DuckDB in read-only mode to prevent file locks with NiceGUI
    if not DB_PATH.exists():
        print(f"Error: Database file does not exist at '{DB_PATH}'")
        sys.exit(1)

    # Workaround: copy the database to a temporary location to prevent locking conflicts
    temp_db_path = DB_PATH.parent / f"temp_{DB_PATH.name}"
    print(f"[INFO] Creating a temporary database copy to avoid process locks: {temp_db_path.name}")
    import shutil
    try:
        shutil.copy2(str(DB_PATH), str(temp_db_path))
        # If WAL file exists, copy it too to prevent recovery errors
        wal_path = DB_PATH.parent / f"{DB_PATH.name}.wal"
        temp_wal_path = DB_PATH.parent / f"temp_{DB_PATH.name}.wal"
        if wal_path.exists():
            shutil.copy2(str(wal_path), str(temp_wal_path))
    except Exception as e:
        print(f"[WARNING] Could not create temporary copy ({e}). Attempting direct read-only connection...")
        temp_db_path = DB_PATH

    print(f"[INFO] Connecting to database: {temp_db_path.name}")
    try:
        con = duckdb.connect(str(temp_db_path), read_only=True)
    except Exception as e:
        print(f"Error connecting to database: {e}")
        # Clean up temp files if created
        if temp_db_path != DB_PATH and temp_db_path.exists():
            try:
                os.remove(str(temp_db_path))
                temp_wal_path = DB_PATH.parent / f"temp_{DB_PATH.name}.wal"
                if temp_wal_path.exists():
                    os.remove(str(temp_wal_path))
            except Exception:
                pass
        sys.exit(1)

    # 5. Retrieve organization list and top org (to use for deep dive)
    org_list_query = QUERIES.get('product_org_list')
    org_df = pd.DataFrame()
    org_id = args.org_id
    org_name = "Selected Org"

    if org_list_query:
        try:
            org_df = con.execute(org_list_query, [platform_proper]).fetchdf()
            if not org_df.empty:
                # Save org list
                org_list_csv = global_dir / "product_org_list.csv"
                org_df.to_csv(org_list_csv, index=False)
                print(f"[SUCCESS] Downloaded Organization list ({len(org_df)} rows) -> {org_list_csv.name}")

                if not org_id:
                    # Select the first org as default
                    row = org_df.iloc[0]
                    org_id = row.get('organization_id') or row.get('organizationId')
                    org_name = row.get('organizationName') or row.get('name') or "Default_Org"
                    print(f"[INFO] No --org-id provided. Automatically selected top organization: '{org_name}' (ID: {org_id})")
            else:
                print("[WARNING] Warning: No organizations found for this platform in database.")
        except Exception as e:
            print(f"Error retrieving organization list: {e}")

    # Build target subfolder for organization deep dive
    safe_org_name = "".join([c if c.isalnum() else "_" for c in str(org_name)])
    org_sub_dir = org_dir / f"{safe_org_name}_{org_id}" if org_id else None
    if org_sub_dir:
        os.makedirs(org_sub_dir, exist_ok=True)

    # 6. Filter queries relevant to the platform
    print(f"[INFO] Categorizing and filtering queries from query store...")
    target_queries = {}
    
    # Platform prefixes
    prefix_map = {
        "regcomply": "regcomply_",
        "regport": "regport_",
        "regwatch": "regwatch_"
    }
    platform_prefix = prefix_map[platform_input]

    # Pulse keys are specifically for regport
    for k, sql in QUERIES.items():
        # A query is relevant if:
        # - It is a common product metrics query (starts with product_)
        # - It starts with the specific platform prefix
        # - It is a pulse query (and platform is regport)
        is_relevant = (
            k.startswith("product_") or
            k.startswith(platform_prefix) or
            (platform_input == "regport" and k.startswith("pulse_"))
        )
        
        # Exclude other platform specific keys
        for p, pref in prefix_map.items():
            if p != platform_input and k.startswith(pref):
                is_relevant = False
                
        # Exclude other specific pulse keys if platform is not regport
        if platform_input != "regport" and k.startswith("pulse_"):
            is_relevant = False
            
        if is_relevant:
            target_queries[k] = sql

    print(f"[INFO] Found {len(target_queries)} relevant queries in store.")

    # 7. Execute queries and download tables
    table_metadata = []

    for key, sql in sorted(target_queries.items()):
        is_org_query = (
            ('_org_' in key or '_deep_' in key or key.startswith('product_deep_'))
            and key not in GLOBAL_ORG_KEYS
        )
        
        # Skip org queries if we don't have an org_id
        if is_org_query and not org_id:
            print(f"[INFO] Skipping organization deep-dive table '{key}' (no active organization ID)")
            continue

        print(f"[INFO] Executing query: '{key}'...")
        params = build_parameters(key, sql, platform_proper, org_id, start_date, end_date)
        
        if params is None:
            print(f"[WARNING] Skipping '{key}' - parameters could not be constructed.")
            continue

        try:
            # Run the query
            if params:
                df = con.execute(sql, params).fetchdf()
            else:
                df = con.execute(sql).fetchdf()

            # Define output path
            if is_org_query and org_sub_dir:
                filename = f"{key}.csv"
                file_path = org_sub_dir / filename
                rel_path = f"org_deep_dive/{org_sub_dir.name}/{filename}"
            else:
                filename = f"{key}.csv"
                file_path = global_dir / filename
                rel_path = f"global_tables/{filename}"

            # Save to CSV
            df.to_csv(file_path, index=False)
            num_rows = len(df)
            print(f"  [SUCCESS] Downloaded {num_rows} rows -> {rel_path}")

            # Grab metadata
            mapped_info = METRIC_VISUAL_MAPPING.get(key, {})
            metric_info_entry = METRIC_INFO.get(key, {})
            
            title = metric_info_entry.get('title') or key.replace('_', ' ').title()
            description = metric_info_entry.get('description') or mapped_info.get('used_for') or "Product intelligence metrics table."
            component_type = mapped_info.get('component') or "Metrics Table"
            used_for = mapped_info.get('used_for') or f"Visualized as a {component_type} in the platform dashboard."
            
            schema_explanation = metric_info_entry.get('schema_explanation')
            
            # Format columns list
            columns_str = ""
            for idx, col in enumerate(df.columns):
                columns_str += f"      - {col}\n"

            table_metadata.append({
                'key': key,
                'rel_path': rel_path,
                'rows': num_rows,
                'title': title,
                'description': description,
                'component_type': component_type,
                'used_for': used_for,
                'schema_explanation': schema_explanation,
                'columns': columns_str,
                'is_org': is_org_query
            })

        except Exception as e:
            print(f"[ERROR] Error executing '{key}': {e}")

    # 8. Create the Table Descriptions text file
    desc_file_path = out_dir_path / "table_descriptions.txt"
    print(f"[INFO] Writing table descriptions file to '{desc_file_path}'...")
    
    with open(desc_file_path, "w", encoding="utf-8") as f:
        f.write("=========================================================================\n")
        f.write(f"DATA PLATFORM EXPORT SUMMARY: {platform_proper.upper()}\n")
        f.write("=========================================================================\n")
        f.write(f"Generated On: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Date Range  : {start_date} to {end_date}\n")
        f.write(f"Platform    : {platform_proper}\n")
        if org_id:
            f.write(f"Deep-Dive Org: {org_name} (ID: {org_id})\n")
        f.write(f"Total Tables: {len(table_metadata)}\n")
        f.write("=========================================================================\n\n")

        # Global Tables Section
        f.write("-------------------------------------------------------------------------\n")
        f.write("GLOBAL METRICS & PLATFORM TREND TABLES\n")
        f.write("-------------------------------------------------------------------------\n")
        global_tables = [t for t in table_metadata if not t['is_org']]
        for idx, t in enumerate(global_tables, 1):
            f.write(f"{idx}. TABLE: {t['key']}\n")
            f.write(f"   - File Path   : {t['rel_path']}\n")
            f.write(f"   - Total Rows  : {t['rows']}\n")
            f.write(f"   - Title       : {t['title']}\n")
            f.write(f"   - Description : {t['description']}\n")
            f.write(f"   - Visual Component: {t['component_type']}\n")
            f.write(f"   - Used For    : {t['used_for']}\n")
            if t['schema_explanation']:
                f.write(f"   - Calculation/Logic: {t['schema_explanation']}\n")
            f.write(f"   - Schema (Columns):\n{t['columns']}")
            f.write("\n")

        # Organization Deep Dive Section
        org_tables = [t for t in table_metadata if t['is_org']]
        if org_tables:
            f.write("\n-------------------------------------------------------------------------\n")
            f.write(f"ORGANIZATION DEEP-DIVE TABLES ({org_name.upper()})\n")
            f.write("-------------------------------------------------------------------------\n")
            for idx, t in enumerate(org_tables, 1):
                f.write(f"{idx}. TABLE: {t['key']}\n")
                f.write(f"   - File Path   : {t['rel_path']}\n")
                f.write(f"   - Total Rows  : {t['rows']}\n")
                f.write(f"   - Title       : {t['title']}\n")
                f.write(f"   - Description : {t['description']}\n")
                f.write(f"   - Visual Component: {t['component_type']}\n")
                f.write(f"   - Used For    : {t['used_for']}\n")
                if t['schema_explanation']:
                    f.write(f"   - Calculation/Logic: {t['schema_explanation']}\n")
                f.write(f"   - Schema (Columns):\n{t['columns']}")
                f.write("\n")

    con.close()
    
    # Clean up temporary database copy if we created one
    if temp_db_path != DB_PATH:
        print(f"[INFO] Cleaning up temporary database copies...")
        try:
            if temp_db_path.exists():
                os.remove(str(temp_db_path))
            temp_wal_path = DB_PATH.parent / f"temp_{DB_PATH.name}.wal"
            if temp_wal_path.exists():
                os.remove(str(temp_wal_path))
        except Exception as e:
            print(f"[WARNING] Could not delete temporary copy: {e}")

    print(f"==================================================")
    print(f"[SUCCESS] DOWNLOAD COMPLETE!")
    print(f"[INFO] Exited successfully. Tables and descriptions saved.")
    print(f"[INFO] View descriptions: {desc_file_path.resolve()}")
    print(f"==================================================")


if __name__ == "__main__":
    main()
