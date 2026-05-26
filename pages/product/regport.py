import asyncio
from datetime import datetime, timedelta
import logging
from nicegui import ui, app, run

logger = logging.getLogger(__name__)
from components.dashboard_layout import dashboard_layout
from components.page_template import create_page_template
from components.chart_components import (
    create_kpi_metrics,
    render_kpi_info_icon,
    create_comparison_cards,
    create_bar_chart,
    create_donut_chart,
    create_metric_table,
    create_line_chart,
    create_traffic_source_row,
    create_user_journey_section,
    create_placeholder_card,
    create_engagement_analysis_charts,
    create_geographic_distribution_table,
    create_device_browser_breakdown,
    create_weekly_signup_login_trend,
    create_dormant_organizations_card,
    render_chart_header,
    _download_csv_helper
)
from data_engine.data_loader import get_data_loader
from data_engine.query_store import QUERIES
import pandas as pd
import inspect
from components.theme_manager import ThemeManager
from data_engine.module_mapping import map_path_to_module, map_path_to_landing
from utils.formatters import format_msec_to_time, format_msec_to_compact_time
from data_engine.chart_descriptions import METRIC_INFO


async def show_regport_product_page():
    async def content():
        # Keep track of functions to refresh data
        refresh_callbacks = []
        ui.add_head_html('''
        <style>
            /* ── Team Members sticky-header QTable ── */
            .my-sticky-header-table .q-table__middle {
                max-height: 240px !important;
                scrollbar-width: thin;
            }
            .my-sticky-header-table thead tr th {
                position: sticky !important;
                z-index: 10 !important;
                top: 0 !important;
                background-color: white !important;
                box-shadow: inset 0 -1px 0 #e2e8f0 !important;
                padding: 6px 8px !important;
            }
            .my-sticky-header-table tbody tr td {
                padding: 6px 8px !important;
                height: auto !important;
            }
            .my-sticky-header-table .q-table__bottom {
                display: none !important;
            }
        </style>
        ''')
        loader = get_data_loader()
        shared_data = {} # Shared results for common metrics
        
        def get_current_dates():
            date_range = app.storage.user.get('date_range', {})
            default_end = datetime.today().strftime('%Y-%m-%d')
            default_start = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')
            start = date_range.get('from', default_start).replace('/', '-')
            end = date_range.get('to', default_end).replace('/', '-')
            return start, end

        PLATFORM = 'RegPort'
        ORG_SESSION_KEY = 'regport_selected_org_id'
        ORG_NAME_SESSION_KEY = 'regport_selected_org_name'

        # Fetch org list for global filter
        org_df = loader.execute_query(QUERIES['product_org_list'], [PLATFORM])
        # Mapping name to its metadata (id, start_date, domain) - ensure unique index
        org_data_map = org_df.drop_duplicates(subset=['organizationName']).set_index('organizationName').to_dict('index') if not org_df.empty else {}
        org_names = list(org_data_map.keys())

        async def fetch_core_metrics():
            """Fetch metrics used across multiple tabs"""
            start, end = get_current_dates()
            core_queries = {
                'active_org_count': QUERIES['product_active_org_count'],
                'organization_by_platform': QUERIES['organization_by_platform'],
                'user_by_platform': QUERIES['user_by_platform'],
                'active_signed_in_users': QUERIES['product_active_signed_in_users'],
            }
            results = loader.execute_batch_queries(core_queries, start, end, platform='RegPort')
            shared_data.update(results)

        refresh_callbacks.append(fetch_core_metrics)

        async def overview_content():
            container = ui.column().classes('w-full')
            
            async def load_data():
                start_date, end_date = get_current_dates()
                
                # Fetch Overview specific KPIs
                overview_queries = {
                    'anonymous_users_pct': QUERIES['product_anonymous_users_pct'],
                    'engagement_rate': QUERIES['product_engagement_rate'],
                    'user_acquisition_trend': QUERIES['product_user_acquisition_trend']
                }
                
                # Fetch data for RegPort
                results = loader.execute_batch_queries(overview_queries, start_date, end_date, platform='RegPort')
                
                # Merge with shared results
                results.update(shared_data)

                container.clear()
                with container:
                    # Pre-calculate or fetch needed values
                    active_orgs = results['active_org_count'].iloc[0,0] if not results['active_org_count'].empty else 0
                    
                    # Total Organization from results['organization_by_platform'] where platform = 'RegPort'
                    total_orgs = 0
                    if not results['organization_by_platform'].empty:
                        # Find the row for RegPort platform
                        mask = results['organization_by_platform']['platform'].str.lower() == 'regport'
                        regport_org_row = results['organization_by_platform'][mask]
                        if not regport_org_row.empty:
                            total_orgs = int(regport_org_row.iloc[0]['total_orgs'])

                    # Total Users for RegPort
                    total_users = 0
                    if not results['user_by_platform'].empty:
                        user_mask = results['user_by_platform']['platform'].str.lower() == 'regport'
                        reg_user_row = results['user_by_platform'][user_mask]
                        if not reg_user_row.empty:
                            total_users = int(reg_user_row.iloc[0]['total_users'])
                    
                    active_users = results['active_signed_in_users'].iloc[0,0] if not results['active_signed_in_users'].empty else 0

                    # Engagement Rate Comparison Metrics
                    eng_data = results['engagement_rate']
                    total_sessions = int(eng_data.iloc[0]['total_sessions']) if not eng_data.empty and pd.notna(eng_data.iloc[0]['total_sessions']) else 0
                    engaged_sessions = int(eng_data.iloc[0]['engaged_sessions']) if not eng_data.empty and pd.notna(eng_data.iloc[0]['engaged_sessions']) else 0

                    # Populate METRIC_INFO with raw data for AI insights
                    METRIC_INFO['active_org_rate']['chart_data'] = {'active_orgs': active_orgs, 'total_orgs': total_orgs}
                    METRIC_INFO['active_users_rate']['chart_data'] = {'active_users': active_users, 'total_users': total_users}
                    METRIC_INFO['engagement_rate']['chart_data'] = {'total_sessions': total_sessions, 'engaged_sessions': engaged_sessions}

                    # 1. Comparison Cards
                    create_comparison_cards([
                        {
                            'id': 'active_org_rate',
                            'title': 'Active Organization Rate',
                            'metric_a_name': 'All Organization',
                            'metric_a_value': total_orgs,
                            'metric_b_name': 'Active Organization',
                            'metric_b_value': active_orgs,
                            'icon': 'corporate_fare',
                            'pct_method': 'divide',
                            'pct_bar': True
                        },
                        {
                            'id': 'active_users_rate',
                            'title': 'Active User Rate',
                            'metric_a_name': 'All Users',
                            'metric_a_value': total_users,
                            'metric_b_name': 'Active Users',
                            'metric_b_value': active_users,
                            'icon': 'person_search',
                            'pct_method': 'divide',
                            'pct_bar': True
                        },
                        {
                            'id': 'engagement_rate',
                            'title': 'Engagement Rate',
                            'metric_a_name': 'Total Sessions',
                            'metric_a_value': total_sessions,
                            'metric_b_name': 'Engaged Sessions',
                            'metric_b_value': engaged_sessions,
                            'icon': 'bolt',
                            'pct_method': 'divide',
                            'pct_bar': True
                        }
                    ])


                    # 2. User Acquisition Trend Chart
                    if not results['user_acquisition_trend'].empty:
                        trend_data = results['user_acquisition_trend']
                        # Ensure date is string format for chart
                        trend_data['date_str'] = pd.to_datetime(trend_data['date']).dt.strftime('%Y-%m-%d')
                        
                        # Data for AI
                        METRIC_INFO['user_acquisition_trend']['chart_data'] = trend_data.to_dict('records')

                        create_line_chart(
                            trend_data,
                            'User Acquisition Trend',
                            'date_str',
                            {
                                'signed_in_users': 'Signed-In Users',
                                'anonymous_users': 'Anonymous Users'
                            },
                            y_axis_name='Users',
                            id='user_acquisition_trend'
                        )
                    else:
                        ui.label('No trend data available').classes('text-slate-500 italic')

                    # 3. Top 3 User Journeys
                    # (Moved to Conversion tab)




            refresh_callbacks.append(load_data)
            # Start loading data immediately but asynchronously
            asyncio.create_task(load_data())

        
        async def acquisition_content():
            container = ui.column().classes('w-full')
            async def load_data():
                start_date, end_date = get_current_dates()
                # Fetch acquisition and stickiness metrics
                queries = {
                    'stickiness': QUERIES['product_stickiness'],
                    'traffic_source': QUERIES['product_traffic_source_metrics'],
                    'session_traffic': QUERIES['product_session_traffic_metrics'],
                    'acquisition_kpis': QUERIES['product_acquisition_kpis'],
                    'new_orgs_trend': QUERIES['product_acquisition_new_orgs_trend'],
                    'new_users_trend': QUERIES['product_acquisition_new_users_trend'],
                    'top_sources': QUERIES['product_acquisition_top_sources'],
                    'new_vs_returning': QUERIES['product_acq_new_vs_returning'],
                    'geographic_dist': QUERIES['product_acquisition_geographic'],
                    'device_browser': QUERIES['product_acquisition_device_browser']
                }
                
                results = loader.execute_batch_queries(queries, start_date, end_date, platform='RegPort')
                
                container.clear()
                with container:
                    ui.label('User Acquisition Analysis').classes(ThemeManager.TYPOGRAPHY['h2'] + ' mb-2')
                    ui.label('Detailed user, organization, and traffic acquisition metrics.').classes(ThemeManager.TYPOGRAPHY['body'] + ' mb-6')
                    
                    # 5 KPI Cards
                    if not results['acquisition_kpis'].empty:
                        row = results['acquisition_kpis'].iloc[0]
                        kpis = [
                            {'id': 'new_orgs', 'label': 'New Orgs (period)', 'value': int(row['new_orgs']), 'color': 'blue'},
                            {'id': 'new_users', 'label': 'New Users (period)', 'value': int(row['new_users']), 'color': 'emerald'},
                            {'id': 'new_visitors', 'label': 'New Visitors (GA4)', 'value': int(row['new_visitors']), 'color': 'amber'},
                            {'id': 'signed_in_rate_pct', 'label': 'Signed-In Rate', 'value': f"{row['signed_in_rate_pct']:.1f}%", 'color': 'indigo'},
                            {'id': 'avg_users_org', 'label': 'Avg Users / Org', 'value': f"{row['avg_users_per_org']:.1f}", 'color': 'purple'}
                        ]
                        create_kpi_metrics(kpis)

                    # New org & user acquisition trend and channel breakdown charts
                    orgs_df = results['new_orgs_trend']
                    users_df = results['new_users_trend']
                    top_sources_df = results['top_sources']
                    
                    with ui.grid(columns=2).classes('w-full gap-4 mb-6 grid-cols-1 lg:grid-cols-2'):
                        # Chart 1: New org & user acquisition trend
                        with ui.card().classes(f'w-full p-6 pt-4 {ThemeManager.get_card_style()}'):
                            with ui.row().classes('w-full items-start justify-between mb-1'):
                                render_chart_header('New org & user acquisition trend', 'acquisition_trend_port', True, lambda: ui.run_javascript(f"downloadChart('{trend_chart_el.id}', 'New org and user acquisition trend')"), trend_df if 'trend_df' in locals() else orgs_df)
                            
                            if not orgs_df.empty or not users_df.empty:
                                # Merge trend dataframes
                                trend_df = pd.merge(orgs_df, users_df, on='month', how='outer').fillna(0).sort_values('month')
                                trend_df['month_label'] = pd.to_datetime(trend_df['month']).dt.strftime('%b')
                                
                                trend_chart_el = ui.echart({
                                    'tooltip': {
                                        'trigger': 'axis',
                                        'axisPointer': {'type': 'cross'}
                                    },
                                    'legend': {
                                        'data': ['New orgs', 'New users'],
                                        'left': 'left'
                                    },
                                    'xAxis': [{
                                        'type': 'category',
                                        'data': trend_df['month_label'].tolist(),
                                        'axisLabel': {'fontSize': 10, 'color': '#64748b'}
                                    }],
                                    'yAxis': [
                                        {
                                            'type': 'value',
                                            'name': 'Orgs',
                                            'min': 0,
                                            'alignTicks': True,
                                            'axisLabel': {'color': '#64748b'},
                                            'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                                        },
                                        {
                                            'type': 'value',
                                            'name': 'Users',
                                            'min': 0,
                                            'alignTicks': True,
                                            'axisLabel': {'color': '#64748b'},
                                            'splitLine': {'show': False}
                                        }
                                    ],
                                    'series': [
                                        {
                                            'name': 'New orgs',
                                            'type': 'bar',
                                            'data': trend_df['new_orgs'].tolist(),
                                            'itemStyle': {'color': '#2563eb', 'borderRadius': [4, 4, 0, 0]}
                                        },
                                        {
                                            'name': 'New users',
                                            'type': 'line',
                                            'yAxisIndex': 1,
                                            'data': trend_df['new_users'].tolist(),
                                            'smooth': True,
                                            'itemStyle': {'color': '#10b981'},
                                            'lineStyle': {'width': 3},
                                            'symbol': 'circle',
                                            'symbolSize': 8
                                        }
                                    ],
                                    'grid': {
                                        'left': '3%',
                                        'right': '4%',
                                        'top': '18%',
                                        'bottom': '10%',
                                        'containLabel': True
                                    }
                                }).classes('w-full h-80')
                            else:
                                ui.label('No acquisition trend data available').classes('text-slate-500 italic py-20 w-full text-center')
                                
                        # Chart 2: Device & browser breakdown
                        create_device_browser_breakdown(results['device_browser'], 'RegPort')

                    # New Users by Primary Medium & Source
                    if not results['traffic_source'].empty:
                        traffic_source_medium_data = results['traffic_source']
                        traffic_source = traffic_source_medium_data.groupby('acquisition_source', as_index=False).agg({'new_visitors': 'sum'})
                        traffic_medium = traffic_source_medium_data.groupby('acquisition_medium', as_index=False).agg({'new_visitors': 'sum'})
                        
                        # Data for AI
                        METRIC_INFO['traffic_source']['chart_data'] = traffic_source_medium_data.to_dict('records')

                    # Session Traffic by Primary Medium & Source
                    if not results['session_traffic'].empty:
                        session_source_medium_data = results['session_traffic']
                        session_source = session_source_medium_data.groupby('session_source', as_index=False).agg({'session_count': 'sum'})
                        session_medium = session_source_medium_data.groupby('session_medium', as_index=False).agg({'session_count': 'sum'})

                        # Data for AI
                        METRIC_INFO['traffic_source']['chart_data'] = session_source_medium_data.to_dict('records')

                        create_traffic_source_row(source_data=session_source,
                                                  source_title='Traffic Acquisition Source',
                                                  id_1='traffic_source',
                                                  medium_data=session_medium,
                                                  medium_title='Traffic Acquisition Medium',
                                                  value_col='session_count',
                                                  value_label='Sessions',
                                                  id_2='traffic_medium'
                        )
                    else:
                        ui.label('No session traffic data available for the selected period').classes(f'{ThemeManager.COLORS["text"]["muted"]} italic')


                    # Row 1: Stickiness (DAU/WAU, etc.) & New vs Returning Users (Weekly)
                    with ui.grid(columns=2).classes('w-full gap-4 items-stretch mb-6'):
                        # Left chart: User Stickiness
                        if not results['stickiness'].empty:
                            stickiness_data = results['stickiness'].copy()
                            # Group by month and calculate the average ratio
                            stickiness_data['month_sort'] = pd.to_datetime(stickiness_data['date']).dt.strftime('%Y-%m')
                            stickiness_monthly = stickiness_data.groupby('month_sort', as_index=False).agg({
                                'dau_wau_ratio': 'mean',
                                'dau_mau_ratio': 'mean',
                                'wau_mau_ratio': 'mean'
                            }).sort_values('month_sort')
                            
                            # Label with uppercase short month names (e.g. JAN, FEB, MAR)
                            stickiness_monthly['month'] = pd.to_datetime(stickiness_monthly['month_sort'] + '-01').dt.strftime('%b').str.upper()
                            
                            # Data for AI
                            METRIC_INFO['stickiness_ratios']['chart_data'] = stickiness_monthly.to_dict('records')

                            create_line_chart(
                                stickiness_monthly,
                                'User Stickiness',
                                'month',
                                {
                                    'dau_wau_ratio': 'DAU/WAU',
                                    'dau_mau_ratio': 'DAU/MAU',
                                    'wau_mau_ratio': 'WAU/MAU'
                                },
                                y_axis_name='Ratio',
                                id='stickiness_ratios'
                            )
                        else:
                            ui.label('No stickiness data available for the selected period').classes(f'{ThemeManager.COLORS["text"]["muted"]} italic')
                            
                        # Right chart: New vs Returning Users
                        if not results['new_vs_returning'].empty:
                            new_vs_ret = results['new_vs_returning'].copy()
                            # Format date for display (e.g. Nov 03)
                            new_vs_ret['week_label'] = pd.to_datetime(new_vs_ret['week_start']).dt.strftime('%b %d').str.upper()
                            # Data for AI
                            METRIC_INFO['acq_new_vs_returning']['chart_data'] = new_vs_ret.to_dict('records')
                            
                            create_line_chart(
                                new_vs_ret,
                                'New vs Returning Users (Weekly)',
                                'week_label',
                                {
                                    'new_users': 'New Users',
                                    'returning_users': 'Returning Users'
                                },
                                show_area=False,
                                id='acq_new_vs_returning'
                            )
                        else:
                            ui.label('No new vs returning user data available').classes(f'{ThemeManager.COLORS["text"]["muted"]} italic')

                    # Row 2: Geographic distribution (full width and scrollable)
                    with ui.row().classes('w-full mb-6'):
                        create_geographic_distribution_table(results['geographic_dist'], 'RegPort')
            
            refresh_callbacks.append(load_data)
            asyncio.create_task(load_data())
        
        async def conversion_content():
            container = ui.column().classes('w-full')
            


            async def load_data():
                start_date, end_date = get_current_dates()
                
                # Fetch Conversion KPIs
                conversion_queries = {
                    'avg_pages': QUERIES['product_avg_pages_per_session'],
                    'time_to_signup': QUERIES['product_time_to_signup'],
                    'exit_rate': QUERIES['product_exit_rate_landing'],
                    #'funnel_analysis': QUERIES['product_landing_page_funnel'],
                    'user_journey': QUERIES['product_user_journey'],
                    'comparison_metrics': QUERIES['product_engaged_vs_churned_metrics'],
                    'signup_login_trend': QUERIES['product_conversion_login_signup_trend'],
                    'churn_signal': QUERIES['regport_conversion_churn_signal']
                }
                
                results = loader.execute_batch_queries(conversion_queries, start_date, end_date, platform='RegPort')
                
                # Merge with shared results
                results.update(shared_data)

                container.clear()
                with container:
                    ui.label('Conversion Analytics').classes(ThemeManager.TYPOGRAPHY['h2'] + ' mb-4')
                    
                    # KPI Metrics Row
                    kpis = []
                    
                    # KPI 1: Avg Pages per Session
                    if not results['avg_pages'].empty:
                        row = results['avg_pages'].iloc[0]
                        avg_pages = row.get('avg_pages_per_session')
                        if pd.notna(avg_pages):
                            kpis.append({'id': 'avg_pages_session', 'label': 'Avg Pages / Session', 'value': f"{avg_pages:.1f}", 'color': 'indigo', 'subtitle': f"Max: {row.get('max_pages_in_session', 0)} | Min: {row.get('min_pages_in_session', 0)}"})
                    
                    # KPI 2: Time to Signup
                    if not results['time_to_signup'].empty:
                        row = results['time_to_signup'].iloc[0]
                        avg_msec = row.get('avg_time_to_first_signup_msec')
                        median_msec = row.get('median_time_to_first_signup_msec')
                        if pd.notna(avg_msec):
                            kpis.append({'id': 'avg_time_signup', 'label': 'Avg Time to Signup', 'value': format_msec_to_time(avg_msec), 'color': 'emerald', 'subtitle': f"Median: {format_msec_to_time(median_msec)}"})
                    
                    # KPI 3: Exit Rate on Landing Page
                    if not results['exit_rate'].empty:
                        row = results['exit_rate'].iloc[0]
                        exit_rate = row.get('exit_rate_pct')
                        if pd.notna(exit_rate):
                            kpis.append({'id': 'landing_exit_rate', 'label': 'Landing Page Exit Rate', 'value': f"{exit_rate:.1f}%", 'color': 'rose', 'subtitle': 'Single page sessions'})
                    
                    if kpis:
                        # KPI data for AI
                        METRIC_INFO['avg_pages_session']['chart_data'] = results['avg_pages'].to_dict('records') if not results['avg_pages'].empty else None
                        METRIC_INFO['avg_time_signup']['chart_data'] = results['time_to_signup'].to_dict('records') if not results['time_to_signup'].empty else None
                        METRIC_INFO['landing_exit_rate']['chart_data'] = results['exit_rate'].to_dict('records') if not results['exit_rate'].empty else None

                        create_kpi_metrics(kpis)
                    else:
                        ui.label('No conversion data available').classes(f'{ThemeManager.COLORS["text"]["muted"]} italic')

                    # 1. Metrics Comparison (Full Width Row)
                    ui.label('Engaged vs Churned User Comparison').classes(ThemeManager.TYPOGRAPHY['h3'] + ' mt-8 mb-4')
                    if not results['comparison_metrics'].empty:
                        comparison_data = []
                        for _, row in results['comparison_metrics'].iterrows():
                            m = row['metric']
                            if m == 'avg_engagement_time_msec':
                                comparison_data.append({
                                    'id': 'engaged_vs_churned',
                                    'title': 'Avg Engagement Time',
                                    'metric_a_name': 'Engaged',
                                    'metric_a_value': format_msec_to_compact_time(float(row['engaged_value'])),
                                    'metric_b_name': 'Churned',
                                    'metric_b_value': format_msec_to_compact_time(float(row['churned_value'])),
                                    'icon': 'timer',
                                    'pct_bar': False
                                })
                            elif m == 'avg_pages_per_session':
                                comparison_data.append({
                                    'id': 'engaged_vs_churned',
                                    'title': 'Avg Pages Per Session',
                                    'metric_a_name': 'Engaged',
                                    'metric_a_value': float(row['engaged_value']),
                                    'metric_b_name': 'Churned',
                                    'metric_b_value': float(row['churned_value']),
                                    'icon': 'description',
                                    'pct_bar': False
                                })
                            elif m == 'avg_key_events':
                                comparison_data.append({
                                    'id': 'engaged_vs_churned',
                                    'title': 'Avg Key Events',
                                    'metric_a_name': 'Engaged',
                                    'metric_a_value': float(row['engaged_value']),
                                    'metric_b_name': 'Churned',
                                    'metric_b_value': float(row['churned_value']),
                                    'icon': 'stars',
                                    'pct_bar': False
                                })
                        
                        # Data for AI
                        METRIC_INFO['engaged_vs_churned']['chart_data'] = results['comparison_metrics'].to_dict('records')

                        # Display all 3 cards in one row
                        create_comparison_cards(comparison_data)
                    else:
                        ui.label('No comparison data available').classes(f'{ThemeManager.COLORS["text"]["muted"]} italic')

                    # 2. Churn Risk & SignUp/Login Trend side-by-side (Left / Right)
                    with ui.grid(columns=2).classes('w-full gap-4 items-stretch mt-8 mb-6'):
                        # Left: Churn Risk - Dormant Orgs
                        create_dormant_organizations_card(results['churn_signal'], 'RegPort')
                        
                        # Right: Weekly Sign-up & Login Trend
                        create_weekly_signup_login_trend(results['signup_login_trend'])

                    # 2. Funnel Analysis (Full Width Row)
                    #ui.label('Landing Page Funnel Analysis').classes(ThemeManager.TYPOGRAPHY['h3'] + ' mt-8 mb-4')
                    #if not results['funnel_analysis'].empty:
                    #    df_raw = results['funnel_analysis'].copy()
                        
                        # Apply strict mapping
                    #    df_raw['landing_page_label'] = df_raw['landing_page'].apply(lambda x: map_path_to_landing(x, 'RegPort'))
                    #    df_raw['next_action_label'] = df_raw['next_common_action'].apply(lambda x: map_path_to_module(x, 'RegPort'))
                        
                        # Filter rows where both are valid (next action MUST be a module, landing must be is_landing=True)
                    #    df_filtered = df_raw.dropna(subset=['landing_page_label', 'next_action_label']).copy()
                        
                    #    if not df_filtered.empty:
                            # Aggregate by labels (landing_page_label is raw path, next_action_label is module name)
                    #        df_funnel = df_filtered.groupby(['landing_page_label', 'next_action_label'])['user_count'].sum().reset_index()
                    #        df_funnel.columns = ['landing_page', 'next_common_action', 'user_count']
                            
                            # Calculate pct_users relative to total active users
                    #        total_active = results['active_signed_in_users']['active_signed_in_users'].iloc[0] if not results['active_signed_in_users'].empty else 0
                    #        if total_active > 0:
                    #            df_funnel['pct_users'] = (df_funnel['user_count'] / total_active * 100).round(2)
                    #        else:
                    #            df_funnel['pct_users'] = 0.0
                                
                    #        df_funnel = df_funnel.sort_values('user_count', ascending=False)
                            
                    #        METRIC_INFO['funnel_analysis']['chart_data'] = df_funnel.to_dict('records')
                            
                    #        create_metric_table(df_funnel, title="Next Common Action by Landing Page", height='h-[400px]', id='funnel_analysis')
                    #    else:
                    #        ui.label('No module-level conversion actions found').classes(f'{ThemeManager.COLORS["text"]["muted"]} italic')
                    #else:
                    #    ui.label('No funnel analysis data available').classes(f'{ThemeManager.COLORS["text"]["muted"]} italic')

                    # User Journeys
                    if not results['user_journey'].empty:
                        METRIC_INFO['user_journeys']['chart_data'] = results['user_journey'].to_dict('records')
                        create_user_journey_section(results['user_journey'], platform_name='RegPort', id='user_journeys')
                    else:
                        ui.label('No user journey data available for the selected period').classes(f'{ThemeManager.COLORS["text"]["muted"]} italic')
            
            refresh_callbacks.append(load_data)
            asyncio.create_task(load_data())
        
        async def engagement_content():
            container = ui.column().classes('w-full')
            


            async def load_data():
                start_date, end_date = get_current_dates()
                container.clear()
                
                results = loader.execute_batch_queries(
                    {
                        'engagement_kpis': QUERIES['product_engagement_kpis'],
                        'page_engagement': QUERIES['product_page_engagement_table'],
                        'org_engagement': QUERIES['product_org_engagement_table'],
                        'freq_segments': QUERIES['product_engagement_user_frequency_segments'],
                        'time_buckets': QUERIES['product_engagement_time_buckets'],
                        'depth_buckets': QUERIES['product_engagement_session_depth_buckets']
                    },
                    start_date, end_date, platform='RegPort'
                )
                
                with container:
                    ui.label('User Engagement Analysis').classes(ThemeManager.TYPOGRAPHY['h2'] + ' mb-4')

                    # Engagement KPIs
                    if not results['engagement_kpis'].empty:
                        row = results['engagement_kpis'].iloc[0]
                        kpis = [
                            {'id': 'avg_engagement_time_msec', 'label': 'Avg Engaged Duration', 'value': format_msec_to_compact_time(row['avg_engaged_duration_msec']), 'icon': 'timer', 'color': 'blue'},
                            {'label': 'Engaged Sessions', 'value': row['engaged_sessions'], 'icon': 'bolt', 'color': 'green'},
                            {'id': 'engagement_rate', 'label': 'Engagement Rate', 'value': f"{row['engagement_rate']}%", 'icon': 'trending_up', 'color': 'orange'},
                            {'label': 'Total Events', 'value': row['total_event_count'], 'icon': 'event', 'color': 'indigo'},
                            {'label': 'Key Events', 'value': row['key_event_count'], 'icon': 'stars', 'color': 'purple'},
                            {'label': 'Page Views', 'value': row['total_page_views'], 'icon': 'description', 'color': 'pink'}
                        ]
                        # Data for AI
                        METRIC_INFO['engagement_rate']['chart_data'] = row.to_dict()
                        
                        create_kpi_metrics(kpis[:3])  # Row 1: Avg Engaged Duration, Engaged Sessions, Engagement Rate
                        create_kpi_metrics(kpis[3:])  # Row 2: Total Events, Key Events, Page Views
                        
                        # Row of three bar charts (User Frequency Segments, Session Time Distribution, Session Depth)
                        create_engagement_analysis_charts(
                            results.get('freq_segments', pd.DataFrame()),
                            results.get('time_buckets', pd.DataFrame()),
                            results.get('depth_buckets', pd.DataFrame())
                        )
                    else:
                        ui.label('No engagement data available').classes(f'{ThemeManager.COLORS["text"]["muted"]} italic mt-4')

                    # 1. Page Engagement Table
                    ui.label('Page Engagement Analysis').classes(ThemeManager.TYPOGRAPHY['h3'] + ' mt-8 mb-4')
                    if not results['page_engagement'].empty:
                        METRIC_INFO['page_engagement']['chart_data'] = results['page_engagement'].to_dict('records')
                        create_metric_table(results['page_engagement'], title="Engagement Metrics by Page", height='h-[400px]', id='page_engagement')
                    else:
                        ui.label('No page engagement data available').classes(f'{ThemeManager.COLORS["text"]["muted"]} italic')

                    # 2. Organization Engagement Table
                    ui.label('Organization Engagement Analysis').classes(ThemeManager.TYPOGRAPHY['h3'] + ' mt-8 mb-4')
                    if not results['org_engagement'].empty:
                        METRIC_INFO['org_engagement']['chart_data'] = results['org_engagement'].to_dict('records')
                        create_metric_table(results['org_engagement'], title="Engagement Metrics by Organization", height='h-[400px]', id='org_engagement')
                    else:
                        ui.label('No organization engagement data available').classes(f'{ThemeManager.COLORS["text"]["muted"]} italic')
            
            refresh_callbacks.append(load_data)
            asyncio.create_task(load_data())
        
        async def feature_adoption_content():
            # Inject custom CSS for Pulse KPIs once for this tab
            ui.add_head_html("""
            <style>
              @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap');
              
              /* ── GENERAL ── */
              .fa-container { font-family: 'DM Sans', sans-serif; }
              
              /* ── SECTION LABEL ── */
              .fa-section-label {
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: #98a2b3;
                margin-bottom: 12px;
                margin-top: 4px;
              }

              /* ── KPI STRIP ── */
              .pulse-kpi-card {
                background: #fff;
                border: 1px solid #e4e7ec;
                border-radius: 12px;
                padding: 16px 20px;
                box-shadow: 0 1px 3px rgba(16,24,40,0.06), 0 1px 2px rgba(16,24,40,0.04);
                height: 100%;
                display: flex;
                flex-direction: column;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
              }
              .pulse-kpi-card:hover {
                box-shadow: 0 10px 15px -3px rgba(16,24,40,0.08);
                border-color: #d0d5dd;
                transform: translateY(-2px);
              }
              .pulse-kpi-label {
                font-size: 11px;
                font-weight: 600;
                color: #667085;
                margin-bottom: 8px;
                text-transform: uppercase;
                letter-spacing: 0.05em;
              }
              .pulse-kpi-value {
                font-size: 28px;
                font-weight: 700;
                color: #101828;
                line-height: 1.1;
                letter-spacing: -0.03em;
              }
              .pulse-kpi-unit {
                font-size: 14px;
                font-weight: 500;
                color: #98a2b3;
                margin-left: 2px;
              }
              .pulse-kpi-sub {
                font-size: 11px;
                color: #98a2b3;
                margin-top: 6px;
                line-height: 1.4;
              }
              .pulse-kpi-delta {
                font-size: 11px;
                font-weight: 600;
                margin-top: 10px;
                display: inline-flex;
                align-items: center;
                gap: 4px;
                width: fit-content;
                padding: 2px 8px;
                border-radius: 6px;
              }
              .pulse-kpi-delta.up      { color: #067647; background: #ecfdf3; }
              .pulse-kpi-delta.down    { color: #b42318; background: #fef3f2; }
              .pulse-kpi-delta.neutral { color: #344054; background: #f2f4f7; }

              /* ── CHART CARDS ── */
              .fa-card {
                background: #fff;
                border: 1px solid #e4e7ec;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 1px 3px rgba(16,24,40,0.06);
                display: flex;
                flex-direction: column;
                height: 100%;
              }
              .fa-card-title {
                font-size: 14px;
                font-weight: 700;
                color: #101828;
                margin-bottom: 4px;
                letter-spacing: -0.01em;
              }
              .fa-card-sub {
                font-size: 11px;
                color: #667085;
                margin-bottom: 16px;
              }

              /* ── LEGEND & DOTS ── */
              .fa-legend { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 12px; }
              .fa-legend span { display: flex; align-items: center; gap: 6px; font-size: 11px; color: #475467; font-weight: 500; }
              .fa-dot { width: 8px; height: 8px; border-radius: 2px; flex-shrink: 0; display: inline-block; }

              /* ── PROGRESS BARS ── */
              .fa-hrow { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
              .fa-hlbl { font-size: 11px; color: #475467; width: 180px; flex-shrink: 0; font-weight: 500; }
              .fa-htrk { flex: 1; background: #f2f4f7; border-radius: 4px; height: 16px; overflow: hidden; }
              .fa-hfil { height: 100%; border-radius: 4px; transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1); }
              .fa-hval { font-size: 11px; font-weight: 700; color: #101828; width: 50px; text-align: right; font-variant-numeric: tabular-nums; }

              /* ── STACKED RULE BARS ── */
              .fa-rrow { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
              .fa-rlbl { font-size: 11px; color: #344054; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
              .fa-rbar { display: flex; height: 12px; border-radius: 6px; overflow: hidden; background: #f9fafb; }
              .fa-rseg { height: 100%; transition: width 0.6s ease; }

              /* ── ORGANIZATION LIST ── */
              .fa-orow { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid #f2f4f7; }
              .fa-orow:last-child { border-bottom: none; }
              .fa-oname { font-size: 12px; color: #101828; font-weight: 600; flex: 1; }
              .fa-opct  { font-size: 13px; font-weight: 700; }
              .fa-ocnt  { font-size: 11px; color: #667085; font-weight: 400; }

              /* ── TABS ── */
              .q-tab { text-transform: none !important; font-weight: 600 !important; font-size: 13px !important; letter-spacing: 0 !important; min-height: 48px !important; }
              .q-tab--active { color: #1570ef !important; }
            </style>
            """)
            
            container = ui.column().classes('w-full')
            async def load_data():
                start_date, end_date = get_current_dates()
                container.clear()
                
                # 1. Prepare Date Range for Prior Period (for Active Orgs delta)
                try:
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                    days_diff = (end_dt - start_dt).days + 1
                    prior_start = (start_dt - timedelta(days=days_diff)).strftime('%Y-%m-%d')
                    prior_end = (start_dt - timedelta(days=1)).strftime('%Y-%m-%d')
                except Exception as e:
                    logger.error(f"Date parsing error in feature_adoption_content: {e}")
                    prior_start, prior_end = start_date, end_date

                # 2. Fetch Data
                queries = {
                    'active_orgs': QUERIES['regport_pulse_active_orgs'],
                    'workflow_completion': QUERIES['regport_pulse_workflow_completion'],
                    'avg_modules': QUERIES['regport_pulse_avg_modules'],
                    'flag_resolution': QUERIES['regport_pulse_flag_resolution'],
                    'report_approval': QUERIES['regport_pulse_report_approval'],
                    'support_touch': QUERIES['regport_pulse_support_touch'],
                }
                
                results = loader.execute_batch_queries(queries, start_date, end_date)
                
                # Fetch Prior Active Orgs for Delta calculation
                prior_active_df = loader.execute_query(QUERIES['regport_pulse_active_orgs'], [prior_start, prior_end])
                prior_count = prior_active_df.iloc[0,0] if not prior_active_df.empty else 0
                
                with container.classes('fa-container'):
                    with ui.column().classes('w-full mb-6 gap-1'):
                        ui.html('<div class="fa-section-label">Feature Adoption Analysis</div>')

                    # 6 KPI Cards in a row
                    with ui.grid(columns=6).classes('w-full gap-4 mb-10'):
                        
                        # 1. Active Orgs
                        with ui.element('div').classes('pulse-kpi-card'):
                            ui.label('Active orgs').classes('pulse-kpi-label')
                            if not results['active_orgs'].empty:
                                curr_count = int(results['active_orgs'].iloc[0,0])
                                ui.label(str(curr_count)).classes('pulse-kpi-value')
                                delta = curr_count - prior_count
                                delta_class = 'up' if delta > 0 else ('down' if delta < 0 else 'neutral')
                                delta_icon = '↑' if delta > 0 else ('↓' if delta < 0 else '•')
                                delta_pct = (abs(delta) / prior_count * 100) if prior_count > 0 else 0
                                ui.label(f"{delta_icon} {abs(delta)} ({delta_pct:.1f}%) vs prior").classes(f'pulse-kpi-delta {delta_class}')
                            else:
                                ui.label('0').classes('pulse-kpi-value')
                                ui.label('No data').classes('pulse-kpi-sub')

                        # 2. Workflow Completion
                        with ui.element('div').classes('pulse-kpi-card'):
                            ui.label('Workflow completion').classes('pulse-kpi-label')
                            if not results['workflow_completion'].empty:
                                row = results['workflow_completion'].iloc[0]
                                ui.html(f'<div class="pulse-kpi-value">{row["completion_rate_pct"]:.0f}<span class="pulse-kpi-unit">%</span></div>')
                                ui.label('ingest → screen → report').classes('pulse-kpi-sub')
                            else:
                                ui.label('0%').classes('pulse-kpi-value')
                                ui.label('No data').classes('pulse-kpi-sub')

                        # 3. Avg Modules / Org
                        with ui.element('div').classes('pulse-kpi-card'):
                            ui.label('Avg modules / org').classes('pulse-kpi-label')
                            if not results['avg_modules'].empty:
                                row = results['avg_modules'].iloc[0]
                                ui.label(f"{row['avg_modules_per_org']:.1f}").classes('pulse-kpi-value')
                                ui.label('of 8 core modules').classes('pulse-kpi-sub')
                            else:
                                ui.label('0').classes('pulse-kpi-value')
                                ui.label('No data').classes('pulse-kpi-sub')

                        # 4. Flag Resolution
                        with ui.element('div').classes('pulse-kpi-card'):
                            ui.label('Flag resolution').classes('pulse-kpi-label')
                            if not results['flag_resolution'].empty:
                                row = results['flag_resolution'].iloc[0]
                                ui.html(f'<div class="pulse-kpi-value">{row["resolution_rate_pct"]:.0f}<span class="pulse-kpi-unit">%</span></div>')
                                ui.label('confirmed + dismissed + escalated').classes('pulse-kpi-sub')
                            else:
                                ui.label('0%').classes('pulse-kpi-value')
                                ui.label('No data').classes('pulse-kpi-sub')

                        # 5. Report Approval
                        with ui.element('div').classes('pulse-kpi-card'):
                            ui.label('Report approval').classes('pulse-kpi-label')
                            if not results['report_approval'].empty:
                                row = results['report_approval'].iloc[0]
                                ui.html(f'<div class="pulse-kpi-value">{row["approval_rate_pct"]:.0f}<span class="pulse-kpi-unit">%</span></div>')
                                ui.label('approved / total generated').classes('pulse-kpi-sub')
                            else:
                                ui.label('0%').classes('pulse-kpi-value')
                                ui.label('No data').classes('pulse-kpi-sub')

                        # 6. Support Touch Rate
                        with ui.element('div').classes('pulse-kpi-card'):
                            ui.label('Support touch rate').classes('pulse-kpi-label')
                            if not results['support_touch'].empty:
                                row = results['support_touch'].iloc[0]
                                ui.html(f'<div class="pulse-kpi-value">{row["support_touch_rate_pct"]:.0f}<span class="pulse-kpi-unit">%</span></div>')
                                ui.label('orgs opening support').classes('pulse-kpi-sub')
                            else:
                                ui.label('0%').classes('pulse-kpi-value')
                                ui.label('No data').classes('pulse-kpi-sub')

                    # --- Nested Tabs for Feature Adoption ---
                    with ui.column().classes('w-full'):
                        with ui.tabs().classes('w-full border-b border-slate-200') as sub_tabs:
                            ui.tab('Flagged Transactions')
                            ui.tab('Case Management')
                            ui.tab('CDD & Verification')
                            ui.tab('Reports')
                            ui.tab('Batch Upload')
                            ui.tab('Compliance Chain')
                            ui.tab('Org Health')

                        with ui.tab_panels(sub_tabs, value='Flagged Transactions').classes('w-full bg-transparent p-0 mt-6'):
                            with ui.tab_panel('Flagged Transactions'):
                                async def load_flagged_data():
                                    flagged_container.clear()
                                    with flagged_container:
                                        ui.spinner(size='lg').classes('mx-auto my-8')

                                    f_queries = {
                                        'funnel':         QUERIES['regport_flag_resolution_funnel'],
                                        'manual_vs_rule': QUERIES['regport_flag_manual_vs_rule'],
                                        'effectiveness':  QUERIES['regport_rule_effectiveness'],
                                        'trend':          QUERIES['regport_flag_weekly_trend'],
                                        'debit_credit':   QUERIES['regport_flag_debit_credit'],
                                        'rate_by_org':    QUERIES['regport_flag_rate_by_org'],
                                    }
                                    f_results = loader.execute_batch_queries(f_queries, start_date, end_date)

                                    flagged_container.clear()
                                    with flagged_container:
                                        # ── ROW 1: Funnel (8/12) + Donut (4/12) ─────────────────────
                                        with ui.grid(columns=12).classes('w-full gap-4 mb-4'):
                                            with ui.column().classes('col-span-8'):
                                                from components.chart_components import create_funnel_analysis_row
                                                LABEL_MAP = {
                                                    'Dashboard Access':                'Dashboard accessed',
                                                    'Transaction Monitoring':          'Transaction viewed',
                                                    'Suspicious Transaction Flagged':  'Flagged events',
                                                    'Transaction Confirmation':        'Confirmed',
                                                    'Transaction Dismissal':           'Dismissed',
                                                    'Transaction Escalation':          'Escalated',
                                                }
                                                FCOLORS = {
                                                    'Dashboard Access':                '#b2ddff',
                                                    'Transaction Monitoring':          '#b2ddff',
                                                    'Suspicious Transaction Flagged':  '#b2ddff',
                                                    'Transaction Confirmation':        '#b2ddff',
                                                    'Transaction Dismissal':           '#b2ddff',
                                                    'Transaction Escalation':          '#b2ddff',
                                                }
                                                create_funnel_analysis_row(
                                                    f_results['funnel'],
                                                    title='Flag Resolution Funnel',
                                                    subtitle='Dashboard access → resolution action by audit event type',
                                                    label_col='actionType',
                                                    value_col='event_count',
                                                    mapping=LABEL_MAP,
                                                    colors=FCOLORS,
                                                    id='flag_resolution_funnel_port'
                                                )

                                            with ui.column().classes('col-span-4'):
                                                from components.chart_components import create_analytical_donut_chart
                                                if not f_results['manual_vs_rule'].empty:
                                                    mvr = f_results['manual_vs_rule'].iloc[0]
                                                    m = int(mvr['manual_flags'])
                                                    r = int(mvr['rule_triggered_actions'])
                                                    create_analytical_donut_chart(
                                                        data={'Manual': m, 'Rule': r},
                                                        title='Manual vs Rule-Triggered',
                                                        subtitle='Detection coverage gap',
                                                        footer_text='High manual % signals rule coverage gaps',
                                                        id='manual_vs_rule_triggered_port'
                                                    )
                                                else:
                                                    ui.html('<p style="text-align:center;color:#98a2b3;padding:32px 0;font-size:12px;font-style:italic">No data</p>')

                                        # ── ROW 2: Rule Effectiveness + Weekly Trend ─────────────────
                                        with ui.grid(columns=2).classes('w-full gap-4 mb-4'):
                                            with ui.column():
                                                from components.chart_components import create_stacked_effectiveness_chart
                                                SEGMENTS = [
                                                    {'col': 'confirmed', 'label': 'Confirmed', 'color': '#10b981'},
                                                    {'col': 'dismissed', 'label': 'Dismissed', 'color': '#b42318'},
                                                    {'col': 'escalated', 'label': 'Escalated', 'color': '#b54708'},
                                                ]
                                                # Pre-process labels to be more readable
                                                df_eff = f_results['effectiveness'].copy()

                                                if not df_eff.empty:
                                                    df_eff['rule_display'] = df_eff.apply(lambda r: f"{r['ruleCode']} · {r['ruleTemplateName']}" if r['ruleTemplateName'] else str(r['ruleCode']), axis=1)
                                                
                                                create_stacked_effectiveness_chart(
                                                    df_eff,
                                                    title='Rule Effectiveness',
                                                    subtitle='Distribution of flag outcomes by rule template',
                                                    label_col='rule_display',
                                                    segments=SEGMENTS,
                                                    total_col='total_flagged',
                                                    id='rule_effectiveness_port'
                                                )

                                            with ui.column():
                                                from components.chart_components import create_dual_axis_trend_chart
                                                create_dual_axis_trend_chart(
                                                    f_results['trend'],
                                                    title='Weekly flag volume & resolution rate',
                                                    subtitle='Dual axis · volume (bars) + resolution % (line)',
                                                    x_col='week_start',
                                                    bar_col='flag_volume',
                                                    line_col='resolution_rate_pct',
                                                    bar_label='Flag volume',
                                                    line_label='Resolution %',
                                                    id='weekly_flag_volume_resolution_rate_port'
                                                )

                                        # ── ROW 3: Debit vs Credit + Flag Rate by Org ────────────────
                                        with ui.grid(columns=2).classes('w-full gap-4'):
                                            create_stacked_effectiveness_chart(
                                                f_results['debit_credit'],
                                                title='Debit vs Credit Flag Split',
                                                subtitle='Outcome distribution by transaction type',
                                                label_col='transactionType',
                                                segments=SEGMENTS,
                                                total_col='flagged_count',
                                                id='debit_credit_flag_split_port'
                                            )

                                            from components.chart_components import create_flag_rate_chart
                                            create_flag_rate_chart(
                                                f_results['rate_by_org'],
                                                title='Flag Rate by Organisation',
                                                subtitle='Flagged ÷ total transactions · red > 5%, amber > 2%',
                                                label_col='organizationName',
                                                rate_col='flag_rate_pct',
                                                count_col='flagged_count',
                                                total_col='total_transactions',
                                                id='flag_rate_by_org_port'
                                            )

                                flagged_container = ui.column().classes('w-full')
                                asyncio.create_task(load_flagged_data())
                            
                            with ui.tab_panel('Case Management'):
                                async def load_case_data():
                                    case_container.clear()
                                    with case_container:
                                        ui.spinner(size='lg').classes('mx-auto my-8')
                                        
                                    c_queries = {
                                        'status_distribution': QUERIES['regport_case_status_distribution'],
                                        'resolution_time':     QUERIES['regport_case_resolution_time'],
                                        'action_depth':        QUERIES['regport_case_action_depth'],
                                        'flag_to_case_ratio':  QUERIES['regport_flag_to_case_ratio'],
                                        'age_buckets':         QUERIES['regport_case_age_buckets']
                                    }
                                    c_results = loader.execute_batch_queries(c_queries, start_date, end_date)
                                    
                                    case_container.clear()
                                    with case_container:
                                        # ROW 1: Case status pipeline (col-span-4), Avg resolution time (col-span-4), Case action depth (col-span-4)
                                        with ui.grid(columns=12).classes('w-full gap-4 mb-4'):
                                            # Card 1: Case status pipeline
                                            with ui.card().classes('col-span-4 p-6 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col justify-between'):
                                                with ui.row().classes('w-full items-start justify-between mb-2'):
                                                    render_chart_header('Case status pipeline', 'case_status_pipeline_port', True, lambda: _download_csv_helper(c_results['status_distribution'], 'Case Status Pipeline'), c_results['status_distribution'])
                                                ui.label('monitoredAccountStatus distribution').classes('text-[11px] text-slate-500 mb-6')
                                                
                                                # Initialize status list and calculate total
                                                status_counts = {'NEW': 0, 'UNDER REVIEW': 0, 'CLOSED': 0}
                                                df_status = c_results['status_distribution']
                                                if not df_status.empty:
                                                    for _, row in df_status.iterrows():
                                                         st = str(row['monitoredAccountStatus']).upper()
                                                         if st in status_counts:
                                                             status_counts[st] = int(row['case_count'])
                                                             
                                                max_status_val = max(status_counts.values()) or 1
                                                
                                                # Render pipeline items
                                                pipeline_styles = {
                                                    'NEW':         {'color': '#e29e6f', 'bg': '#fcf4ed', 'bar_bg': '#f6dec9'},
                                                    'UNDER REVIEW': {'color': '#1570ef', 'bg': '#eff8ff', 'bar_bg': '#d1e9ff'},
                                                    'CLOSED':       {'color': '#027a48', 'bg': '#ecfdf3', 'bar_bg': '#d1fadf'}
                                                }
                                                
                                                with ui.column().classes('w-full gap-3 flex-1 justify-center'):
                                                    for status_name in ['NEW', 'UNDER REVIEW', 'CLOSED']:
                                                        count = status_counts[status_name]
                                                        style = pipeline_styles[status_name]
                                                        pct = (count / max_status_val) * 100 if max_status_val > 0 else 0
                                                        
                                                        with ui.row().classes('w-full items-center gap-2 h-7 flex-nowrap'):
                                                            # Label
                                                            ui.label(status_name).classes('text-[11px] font-bold text-slate-600 w-24 truncate')
                                                            # Badge count
                                                            with ui.element('div').classes('px-2 py-0.5 rounded-sm text-center font-bold text-[10px] min-w-9 shrink-0').style(f'background-color: {style["bg"]}; color: {style["color"]}; border: 1px solid {style["bar_bg"]}'):
                                                                ui.label(str(count))
                                                            # Bar container
                                                            with ui.element('div').classes('flex-1 bg-slate-50 rounded-sm h-4 overflow-hidden relative border border-slate-100'):
                                                                ui.element('div').classes('h-full transition-all duration-700').style(f'width: {pct}%; background-color: {style["bar_bg"]};')
                                                                
                                            # Card 2: Avg resolution time (horizontal bar chart)
                                            with ui.card().classes('col-span-4 p-6 border border-slate-200 shadow-sm bg-white rounded-xl'):
                                                with ui.row().classes('w-full items-start justify-between mb-2'):
                                                    render_chart_header('Avg resolution time', 'avg_resolution_time_port', True, lambda: _download_csv_helper(c_results['resolution_time'], 'Avg Resolution Time'), c_results['resolution_time'])
                                                ui.label('Days to CLOSED per org').classes('text-[11px] text-slate-500 mb-4')
                                                
                                                df_res = c_results['resolution_time']
                                                if df_res.empty:
                                                    ui.label('No resolution data').classes('text-slate-400 italic text-xs py-12 text-center w-full')
                                                else:
                                                    df_res_top = df_res.head(6).iloc[::-1]
                                                    org_names = df_res_top['organizationName'].tolist()
                                                    
                                                    series_data = []
                                                    for _, row in df_res_top.iterrows():
                                                        val = float(row['avg_days_to_close'])
                                                        if val < 15:
                                                            color = '#027a48'
                                                        elif val <= 30:
                                                            color = '#b54708'
                                                        else:
                                                            color = '#b42318'
                                                        series_data.append({
                                                            'value': val,
                                                            'itemStyle': {'color': color}
                                                        })
                                                        
                                                    ui.echart({
                                                        'tooltip': {'trigger': 'axis', 'backgroundColor': 'rgba(255, 255, 255, 0.98)', 'textStyle': {'fontSize': 11}},
                                                        'grid': {'left': '3%', 'right': '12%', 'top': '3%', 'bottom': '12%', 'containLabel': True},
                                                        'xAxis': {
                                                            'type': 'value',
                                                            'axisLabel': {'fontSize': 9, 'color': '#64748b'},
                                                            'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                                                        },
                                                        'yAxis': {
                                                            'type': 'category',
                                                            'data': org_names,
                                                            'axisLabel': {'fontSize': 9, 'color': '#334155', 'width': 70, 'overflow': 'truncate'},
                                                            'axisTick': {'show': False},
                                                            'axisLine': {'show': False}
                                                        },
                                                        'series': [{
                                                            'type': 'bar',
                                                            'data': series_data,
                                                            'barWidth': 11,
                                                            'itemStyle': {'borderRadius': [0, 2, 2, 0]},
                                                            'label': {'show': True, 'position': 'right', 'fontSize': 9, 'fontWeight': 'bold', 'color': '#475569'}
                                                        }]
                                                     }).classes('h-44 w-full')
                                                     
                                            # Card 3: Case action depth (horizontal bar chart)
                                            with ui.card().classes('col-span-4 p-6 border border-slate-200 shadow-sm bg-white rounded-xl'):
                                                with ui.row().classes('w-full items-start justify-between mb-2'):
                                                    render_chart_header('Case action depth', 'case_action_depth_port', True, lambda: _download_csv_helper(c_results['action_depth'], 'Case Action Depth'), c_results['action_depth'])
                                                ui.label('Avg audit events per case per org').classes('text-[11px] text-slate-500 mb-4')
                                                
                                                df_depth = c_results['action_depth']
                                                if df_depth.empty:
                                                    ui.label('No event action data').classes('text-slate-400 italic text-xs py-12 text-center w-full')
                                                else:
                                                    df_depth_top = df_depth.head(6).iloc[::-1]
                                                    org_names_depth = df_depth_top['organizationName'].tolist()
                                                     
                                                    series_data_depth = []
                                                    for _, row in df_depth_top.iterrows():
                                                        val = float(row['avg_actions_per_case'])
                                                        series_data_depth.append({
                                                            'value': val,
                                                            'itemStyle': {'color': '#9e77ed'}
                                                        })
                                                         
                                                    ui.echart({
                                                        'tooltip': {'trigger': 'axis', 'backgroundColor': 'rgba(255, 255, 255, 0.98)', 'textStyle': {'fontSize': 11}},
                                                        'grid': {'left': '3%', 'right': '12%', 'top': '3%', 'bottom': '12%', 'containLabel': True},
                                                        'xAxis': {
                                                            'type': 'value',
                                                            'axisLabel': {'fontSize': 9, 'color': '#64748b'},
                                                            'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                                                        },
                                                        'yAxis': {
                                                            'type': 'category',
                                                            'data': org_names_depth,
                                                            'axisLabel': {'fontSize': 9, 'color': '#334155', 'width': 70, 'overflow': 'truncate'},
                                                            'axisTick': {'show': False},
                                                            'axisLine': {'show': False}
                                                        },
                                                        'series': [{
                                                            'type': 'bar',
                                                            'data': series_data_depth,
                                                            'barWidth': 11,
                                                            'itemStyle': {'borderRadius': [0, 2, 2, 0]},
                                                            'label': {'show': True, 'position': 'right', 'fontSize': 9, 'fontWeight': 'bold', 'color': '#475569'}
                                                        }]
                                                     }).classes('h-44 w-full')
                                                     
                                        # ROW 2: Flags-to-case ratio (col-span-6), Open case age buckets (col-span-6)
                                        with ui.grid(columns=12).classes('w-full gap-4'):
                                            # Card 4: Flags-to-case ratio list
                                            with ui.card().classes('col-span-6 p-6 border border-slate-200 shadow-sm bg-white rounded-xl'):
                                                with ui.row().classes('w-full items-start justify-between mb-2'):
                                                    render_chart_header('Flags-to-case ratio', 'flags_to_case_ratio_port', True, lambda: _download_csv_helper(c_results['flag_to_case_ratio'], 'Flags-to-Case Ratio'), c_results['flag_to_case_ratio'])
                                                ui.label('flaggedTransactionCount per monitored case · high ratio = under-escalation').classes('text-[11px] text-slate-500 mb-6')
                                                
                                                df_ratio = c_results['flag_to_case_ratio']
                                                if df_ratio.empty:
                                                    ui.label('No flags-to-case ratio data').classes('text-slate-400 italic text-xs py-12 text-center w-full')
                                                else:
                                                    with ui.column().classes('w-full gap-3.5'):
                                                        for _, row in df_ratio.head(5).iterrows():
                                                            org_name = str(row['organizationName'])
                                                            cases = int(row['total_cases'])
                                                            flags = int(row['total_flagged_txns'])
                                                            ratio_val = row['flags_per_case']
                                                             
                                                            if pd.isna(ratio_val) or cases == 0:
                                                                 ratio_text = '∞'
                                                                 bg_pill = '#fef3f2'
                                                                 text_pill = '#b42318'
                                                            elif ratio_val >= 50:
                                                                 ratio_text = f'{ratio_val:.0f}:1'
                                                                 bg_pill = '#fef3f2'
                                                                 text_pill = '#b42318'
                                                            elif ratio_val >= 10:
                                                                 ratio_text = f'{ratio_val:.0f}:1'
                                                                 bg_pill = '#fef0c7'
                                                                 text_pill = '#b54708'
                                                            else:
                                                                 ratio_text = f'{ratio_val:.0f}:1'
                                                                 bg_pill = '#ecfdf3'
                                                                 text_pill = '#027a48'
                                                                 
                                                            with ui.row().classes('w-full items-center justify-between flex-nowrap'):
                                                                 with ui.row().classes('items-center gap-3'):
                                                                     ui.label(org_name).classes('text-[11px] font-bold text-slate-700 w-32 truncate')
                                                                     ui.label(f'{flags:,} flags → {cases:,} cases').classes('text-[11px] text-slate-500 font-medium')
                                                                 with ui.element('div').classes('px-2.5 py-0.5 rounded-sm text-center font-bold text-[10px] min-w-10 shrink-0').style(f'background-color: {bg_pill}; color: {text_pill};'):
                                                                     ui.label(ratio_text)
                                                                     
                                            # Card 5: Open case age buckets stacked column chart
                                            with ui.card().classes('col-span-6 p-6 border border-slate-200 shadow-sm bg-white rounded-xl'):
                                                with ui.row().classes('w-full items-start justify-between mb-2'):
                                                    render_chart_header('Open case age buckets', 'open_case_age_buckets_port', True, lambda: _download_csv_helper(c_results['age_buckets'], 'Open Case Age Buckets'), c_results['age_buckets'])
                                                ui.label('NEW + UNDER REVIEW cases by days since createdAt').classes('text-[11px] text-slate-500 mb-4')
                                                
                                                df_age = c_results['age_buckets']
                                                if df_age.empty:
                                                    ui.label('No active cases found').classes('text-slate-400 italic text-xs py-12 text-center w-full')
                                                else:
                                                    df_age_top = df_age.head(5)
                                                    org_names_age = df_age_top['organizationName'].tolist()
                                                     
                                                    u7 = df_age_top['under_7d'].tolist()
                                                    d7_30 = df_age_top['d7_to_30'].tolist()
                                                    d31_90 = df_age_top['d31_to_90'].tolist()
                                                    o90 = df_age_top['over_90d'].tolist()
                                                     
                                                    ui.echart({
                                                         'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}, 'textStyle': {'fontSize': 11}},
                                                         'legend': {'data': ['<7d', '7-30d', '30-90d', '>90d'], 'bottom': 0, 'icon': 'circle', 'textStyle': {'fontSize': 9, 'color': '#64748b'}},
                                                         'grid': {'left': '3%', 'right': '4%', 'top': '10%', 'bottom': '18%', 'containLabel': True},
                                                         'xAxis': {
                                                             'type': 'category',
                                                             'data': org_names_age,
                                                             'axisLabel': {'fontSize': 9, 'color': '#475569', 'interval': 0, 'rotate': 15}
                                                         },
                                                         'yAxis': {
                                                             'type': 'value',
                                                             'axisLabel': {'fontSize': 9, 'color': '#64748b'},
                                                             'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                                                         },
                                                         'series': [
                                                             {'name': '<7d', 'type': 'bar', 'stack': 'total', 'color': '#12b76a', 'data': u7, 'barMaxWidth': 28},
                                                             {'name': '7-30d', 'type': 'bar', 'stack': 'total', 'color': '#f79009', 'data': d7_30},
                                                             {'name': '30-90d', 'type': 'bar', 'stack': 'total', 'color': '#f04438', 'data': d31_90},
                                                             {'name': '>90d', 'type': 'bar', 'stack': 'total', 'color': '#7a271a', 'data': o90}
                                                         ]
                                                     }).classes('h-56 w-full')
                                                     
                                case_container = ui.column().classes('w-full')
                                asyncio.create_task(load_case_data())

                            with ui.tab_panel('CDD & Verification'):
                                async def load_cdd_data():
                                    cdd_container.clear()
                                    with cdd_container:
                                        ui.spinner(size='lg').classes('mx-auto my-8')
                                        
                                    cdd_queries = {
                                        'verify_pass_fail':   QUERIES['regport_verify_pass_fail_by_service'],
                                        'screening_hit_rate': QUERIES['regport_screening_hit_rate'],
                                        'screening_depth':     QUERIES['regport_screening_depth_score'],
                                        'kyc_kyb_split':       QUERIES['regport_kyc_kyb_split'],
                                        'adverse_media_lag':   QUERIES['regport_adverse_media_lag']
                                    }
                                    cdd_results = loader.execute_batch_queries(cdd_queries, start_date, end_date)
                                    
                                    cdd_container.clear()
                                    with cdd_container:
                                        # Build an organization mapping to resolve names
                                        org_id_to_name = {}
                                        if not cdd_results['screening_depth'].empty:
                                            for _, row in cdd_results['screening_depth'].iterrows():
                                                org_id_to_name[row['organizationId']] = row['organizationName']
                                        if not cdd_results['screening_hit_rate'].empty:
                                            for _, row in cdd_results['screening_hit_rate'].iterrows():
                                                org_id_to_name[row['organizationId']] = row['organizationName']
                                                
                                        # ── ROW 1: 2-column Grid (Verification pass/fail, Screening hit rate) ──
                                        with ui.grid(columns=12).classes('w-full gap-4 mb-4'):
                                            # Card 1: Verification pass / fail
                                            with ui.card().classes('col-span-6 p-6 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col justify-between'):
                                                with ui.row().classes('w-full items-start justify-between mb-2'):
                                                    render_chart_header('Verification pass / fail', 'verification_pass_fail_port', True, lambda: _download_csv_helper(cdd_results['verify_pass_fail'], 'Verification Pass Fail'), cdd_results['verify_pass_fail'])
                                                ui.label('By verificationService from regport_verify_customers').classes('text-[11px] text-slate-500 mb-4')
                                                
                                                df_verify = cdd_results['verify_pass_fail']
                                                if df_verify.empty:
                                                    ui.label('No verification data').classes('text-slate-400 italic text-xs py-12 text-center w-full')
                                                else:
                                                    x_verify = df_verify['verificationService'].tolist()
                                                    pass_counts = df_verify['total_pass'].tolist()
                                                    fail_counts = df_verify['total_fail'].tolist()
                                                            
                                                    ui.echart({
                                                        'tooltip': {
                                                            'trigger': 'axis',
                                                            'axisPointer': {'type': 'shadow'},
                                                            'formatter': '{b}<br/>Pass: {c0}<br/>Fail: {c1}',
                                                            'textStyle': {'fontSize': 11}
                                                        },
                                                        'legend': {
                                                            'data': ['Pass', 'Fail'],
                                                            'bottom': 0,
                                                            'icon': 'circle',
                                                            'textStyle': {'color': '#64748b', 'fontSize': 9}
                                                        },
                                                        'grid': {
                                                            'left': '3%',
                                                            'right': '4%',
                                                            'top': '5%',
                                                            'bottom': '22%',
                                                            'containLabel': True
                                                        },
                                                        'xAxis': {
                                                            'type': 'category',
                                                            'data': x_verify,
                                                            'axisLabel': {'color': '#475569', 'fontSize': 9, 'interval': 0, 'rotate': 15},
                                                            'axisLine': {'lineStyle': {'color': '#e2e8f0'}}
                                                        },
                                                        'yAxis': {
                                                            'type': 'value',
                                                            'axisLabel': {'color': '#64748b', 'fontSize': 9},
                                                            'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                                                        },
                                                        'series': [
                                                            {
                                                                'name': 'Pass',
                                                                'type': 'bar',
                                                                'stack': 'verify',
                                                                'color': '#027a48',
                                                                'data': pass_counts,
                                                                'barMaxWidth': 28
                                                            },
                                                            {
                                                                'name': 'Fail',
                                                                'type': 'bar',
                                                                'stack': 'verify',
                                                                'color': '#b42318',
                                                                'data': fail_counts,
                                                                'barMaxWidth': 28
                                                            }
                                                        ]
                                                    }).classes('h-44 w-full')
                                                    
                                            # Card 2: Screening hit rate
                                            with ui.card().classes('col-span-6 p-6 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col justify-between'):
                                                with ui.row().classes('w-full items-start justify-between mb-2'):
                                                    render_chart_header('Screening hit rate', 'screening_hit_rate_port', True, lambda: _download_csv_helper(cdd_results['screening_hit_rate'], 'Screening Hit Rate'), cdd_results['screening_hit_rate'])
                                                ui.label('sanction_match_count > 0 or pep_match_count > 0').classes('text-[11px] text-slate-500 mb-4')
                                                
                                                df_screening = cdd_results['screening_hit_rate']
                                                total_clean = int(df_screening['clean_screenings'].sum()) if not df_screening.empty else 0
                                                total_sanction = int(df_screening['sanction_hits'].sum()) if not df_screening.empty else 0
                                                total_pep = int(df_screening['pep_hits'].sum()) if not df_screening.empty else 0
                                                
                                                if df_screening.empty or (total_clean == 0 and total_sanction == 0 and total_pep == 0):
                                                    ui.label('No screening data').classes('text-slate-400 italic text-xs py-12 text-center w-full')
                                                else:
                                                    ui.echart({
                                                        'tooltip': {
                                                            'trigger': 'item', 
                                                            'formatter': '{b}: {c} ({d}%)',
                                                            'textStyle': {'fontSize': 11}
                                                        },
                                                        'legend': {
                                                            'data': ['Clean', 'Sanction', 'PEP'], 
                                                            'bottom': 0, 
                                                            'icon': 'circle', 
                                                            'textStyle': {'color': '#64748b', 'fontSize': 9}
                                                        },
                                                        'series': [{
                                                            'type': 'pie',
                                                            'radius': ['55%', '80%'],
                                                            'avoidLabelOverlap': False,
                                                            'label': {'show': False},
                                                            'emphasis': {
                                                                'label': {'show': False}
                                                            },
                                                            'labelLine': {
                                                                'show': False
                                                            },
                                                            'data': [
                                                                {'value': total_clean, 'name': 'Clean', 'itemStyle': {'color': '#027a48'}},
                                                                {'value': total_sanction, 'name': 'Sanction', 'itemStyle': {'color': '#b42318'}},
                                                                {'value': total_pep, 'name': 'PEP', 'itemStyle': {'color': '#b54708'}}
                                                            ]
                                                        }]
                                                    }).classes('h-44 w-full')
                                                    
                                        # ── ROW 2: 2-column Grid (KYC vs KYB split, Adverse media response lag) ──
                                        with ui.grid(columns=12).classes('w-full gap-4'):
                                            # Card 4: KYC vs KYB split
                                            with ui.card().classes('col-span-6 p-6 border border-slate-200 shadow-sm bg-white rounded-xl'):
                                                with ui.row().classes('w-full items-start justify-between mb-2'):
                                                    render_chart_header('KYC vs KYB split', 'kyc_kyb_split_port', True, lambda: _download_csv_helper(cdd_results['kyc_kyb_split'], 'KYC vs KYB Split'), cdd_results['kyc_kyb_split'])
                                                ui.label('verificationType per org · regport_verify_customers').classes('text-[11px] text-slate-500 mb-4')
                                                
                                                df_split = cdd_results['kyc_kyb_split']
                                                if df_split.empty:
                                                    ui.label('No KYC/KYB data').classes('text-slate-400 italic text-xs py-12 text-center w-full')
                                                else:
                                                    all_org_ids = []
                                                    org_id_to_kyc = {}
                                                    org_id_to_kyb = {}
                                                    
                                                    for _, row in df_split.iterrows():
                                                        oid = row['organizationId']
                                                        vtype = str(row['verificationType']).upper()
                                                        vcount = int(row['verification_count'])
                                                        
                                                        if oid not in all_org_ids:
                                                            all_org_ids.append(oid)
                                                        if vtype == 'KYC':
                                                            org_id_to_kyc[oid] = vcount
                                                        elif vtype == 'KYB':
                                                            org_id_to_kyb[oid] = vcount
                                                            
                                                    # Sort by total verification count
                                                    top_org_ids = sorted(all_org_ids, key=lambda x: org_id_to_kyc.get(x, 0) + org_id_to_kyb.get(x, 0), reverse=True)[:5]
                                                    
                                                    x_split_orgs = [org_id_to_name.get(oid, f"Org {oid[:6]}") for oid in top_org_ids]
                                                    kyc_data = [org_id_to_kyc.get(oid, 0) for oid in top_org_ids]
                                                    kyb_data = [org_id_to_kyb.get(oid, 0) for oid in top_org_ids]
                                                    
                                                    ui.echart({
                                                        'tooltip': {
                                                            'trigger': 'axis',
                                                            'axisPointer': {'type': 'shadow'},
                                                            'textStyle': {'fontSize': 11}
                                                        },
                                                        'legend': {
                                                            'data': ['KYC', 'KYB'],
                                                            'bottom': 0,
                                                            'icon': 'circle',
                                                            'textStyle': {'color': '#64748b', 'fontSize': 9}
                                                        },
                                                        'grid': {
                                                            'left': '3%',
                                                            'right': '4%',
                                                            'top': '5%',
                                                            'bottom': '22%',
                                                            'containLabel': True
                                                        },
                                                        'xAxis': {
                                                            'type': 'category',
                                                            'data': x_split_orgs,
                                                            'axisLabel': {'color': '#475569', 'fontSize': 9, 'interval': 0, 'rotate': 15}
                                                        },
                                                        'yAxis': {
                                                            'type': 'value',
                                                            'axisLabel': {'color': '#64748b', 'fontSize': 9},
                                                            'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                                                        },
                                                        'series': [
                                                            {
                                                                'name': 'KYC',
                                                                'type': 'bar',
                                                                'stack': 'split',
                                                                'color': '#1570ef',
                                                                'data': kyc_data,
                                                                'barMaxWidth': 28
                                                            },
                                                            {
                                                                'name': 'KYB',
                                                                'type': 'bar',
                                                                'stack': 'split',
                                                                'color': '#027a48',
                                                                'data': kyb_data,
                                                                'barMaxWidth': 28
                                                            }
                                                        ]
                                                    }).classes('h-56 w-full')
                                                    
                                            # Card 5: Adverse media response lag
                                            with ui.card().classes('col-span-6 p-6 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col justify-between'):
                                                with ui.row().classes('w-full items-start justify-between mb-2'):
                                                    render_chart_header('Adverse media response lag', 'adverse_media_response_lag_port', True, lambda: _download_csv_helper(cdd_results['adverse_media_lag'], 'Adverse Media Response Lag'), cdd_results['adverse_media_lag'])
                                                ui.label('Hours: "Screening Completed (Flagged)" → "Conducted adverse media investigation"').classes('text-[11px] text-slate-500 mb-4')
                                                
                                                df_lag = cdd_results['adverse_media_lag']
                                                
                                                # Identify active orgs in lag
                                                org_id_to_lag = {}
                                                for _, row in df_lag.iterrows():
                                                    oid = row['organizationId']
                                                    org_id_to_lag[oid] = float(row['avg_lag_hours'])
                                                    
                                                # Scale relative to max lag (or 72h)
                                                max_lag_val = max(org_id_to_lag.values()) if org_id_to_lag else 72.0
                                                scale_max = max(max_lag_val, 72.0)
                                                
                                                # Let's align organizations with the top list from Card 4, or build top list from deep/hit results if Card 4 is empty
                                                if df_split.empty:
                                                    top_org_ids = list(org_id_to_name.keys())[:5]
                                                    
                                                if not top_org_ids:
                                                    ui.label('No adverse media lag data').classes('text-slate-400 italic text-xs py-12 text-center w-full')
                                                else:
                                                    with ui.column().classes('w-full gap-3 flex-1 justify-center mt-4'):
                                                        for oid in top_org_ids:
                                                            org_name = org_id_to_name.get(oid, f"Org {oid[:6]}")
                                                            lag_val = org_id_to_lag.get(oid, None)
                                                            
                                                            if lag_val is not None and not pd.isna(lag_val):
                                                                lag_text = f"{lag_val:.1f}h"
                                                                if lag_val <= 24.0:
                                                                    color = '#027a48'
                                                                    bg = '#ecfdf3'
                                                                    border_color = '#d1fadf'
                                                                elif lag_val <= 48.0:
                                                                    color = '#b54708'
                                                                    bg = '#fef0c7'
                                                                    border_color = '#fedf89'
                                                                else:
                                                                    color = '#b42318'
                                                                    bg = '#fef3f2'
                                                                    border_color = '#fee4e2'
                                                                pct = (lag_val / scale_max) * 100
                                                            else:
                                                                lag_text = 'n/a'
                                                                color = '#64748b'
                                                                bg = '#f8fafc'
                                                                border_color = '#e2e8f0'
                                                                pct = 0.0
                                                                
                                                            with ui.row().classes('w-full items-center gap-4 h-7 flex-nowrap'):
                                                                # Org Label
                                                                ui.label(org_name).classes('text-[11px] font-bold text-slate-700 w-24 truncate')
                                                                
                                                                # Progress Bar
                                                                with ui.element('div').classes('flex-1 bg-slate-50 rounded-sm h-4 overflow-hidden relative border border-slate-100'):
                                                                    if pct > 0:
                                                                        ui.element('div').classes('h-full transition-all duration-700').style(f'width: {pct}%; background-color: {color};')
                                                                    else:
                                                                        ui.element('div').classes('h-full w-[2px] bg-slate-200')
                                                                        
                                                                # Value Badge
                                                                with ui.element('div').classes('px-2.5 py-0.5 rounded-sm text-center font-bold text-[10px] min-w-10 shrink-0').style(f'background-color: {bg}; color: {color}; border: 1px solid {border_color};'):
                                                                    ui.label(lag_text)
                                                                    
                                                    # Caption
                                                    ui.label('Long lag indicates adverse media is handled outside the platform').classes('text-[10px] text-slate-400 italic mt-3 text-center w-full')
                                                    
                                        # ── ROW 3: Standalone 12-column Grid (Screening depth score) ──
                                        with ui.grid(columns=12).classes('w-full gap-4 mt-4'):
                                            # Card 3: Screening depth score
                                            with ui.card().classes('col-span-12 p-6 border border-slate-200 shadow-sm bg-white rounded-xl'):
                                                with ui.row().classes('w-full items-start justify-between mb-2'):
                                                    render_chart_header('Screening depth score', 'screening_depth_score_port', True, lambda: _download_csv_helper(cdd_results['screening_depth'], 'Screening Depth Score'), cdd_results['screening_depth'])
                                                ui.label('individual + batch + custom list + sanction + pep active modules (out of 5)').classes('text-[11px] text-slate-500 mb-4')
                                                
                                                df_depth = cdd_results['screening_depth']
                                                if df_depth.empty:
                                                    ui.label('No screening depth data').classes('text-slate-400 italic text-xs py-12 text-center w-full')
                                                else:
                                                    rows_html = ""
                                                    for _, r in df_depth.head(10).iterrows():
                                                        org_name = str(r['organizationName'])
                                                        indiv = '<span style="display:inline-flex;align-items:center;justify-content:center;width:32px;height:24px;background-color:#ecfdf3;border:1px solid #d1fadf;color:#12b76a;border-radius:4px;font-weight:bold;font-size:12px;">✓</span>' if r['has_individual'] else '<span style="display:inline-flex;align-items:center;justify-content:center;width:32px;height:24px;background-color:#f1f5f9;border:1px solid #e2e8f0;color:#94a3b8;border-radius:4px;font-weight:normal;font-size:12px;">—</span>'
                                                        batch = '<span style="display:inline-flex;align-items:center;justify-content:center;width:32px;height:24px;background-color:#ecfdf3;border:1px solid #d1fadf;color:#12b76a;border-radius:4px;font-weight:bold;font-size:12px;">✓</span>' if r['has_batch'] else '<span style="display:inline-flex;align-items:center;justify-content:center;width:32px;height:24px;background-color:#f1f5f9;border:1px solid #e2e8f0;color:#94a3b8;border-radius:4px;font-weight:normal;font-size:12px;">—</span>'
                                                        cust_list = '<span style="display:inline-flex;align-items:center;justify-content:center;width:32px;height:24px;background-color:#ecfdf3;border:1px solid #d1fadf;color:#12b76a;border-radius:4px;font-weight:bold;font-size:12px;">✓</span>' if r['has_custom_list'] else '<span style="display:inline-flex;align-items:center;justify-content:center;width:32px;height:24px;background-color:#f1f5f9;border:1px solid #e2e8f0;color:#94a3b8;border-radius:4px;font-weight:normal;font-size:12px;">—</span>'
                                                        sanct = '<span style="display:inline-flex;align-items:center;justify-content:center;width:32px;height:24px;background-color:#ecfdf3;border:1px solid #d1fadf;color:#12b76a;border-radius:4px;font-weight:bold;font-size:12px;">✓</span>' if r['has_sanction'] else '<span style="display:inline-flex;align-items:center;justify-content:center;width:32px;height:24px;background-color:#f1f5f9;border:1px solid #e2e8f0;color:#94a3b8;border-radius:4px;font-weight:normal;font-size:12px;">—</span>'
                                                        pep = '<span style="display:inline-flex;align-items:center;justify-content:center;width:32px;height:24px;background-color:#ecfdf3;border:1px solid #d1fadf;color:#12b76a;border-radius:4px;font-weight:bold;font-size:12px;">✓</span>' if r['has_pep'] else '<span style="display:inline-flex;align-items:center;justify-content:center;width:32px;height:24px;background-color:#f1f5f9;border:1px solid #e2e8f0;color:#94a3b8;border-radius:4px;font-weight:normal;font-size:12px;">—</span>'
                                                        
                                                        score = int(r['depth_score_out_of_5'])
                                                        if score >= 4:
                                                            score_color = '#027a48'
                                                        elif score >= 2:
                                                            score_color = '#b54708'
                                                        else:
                                                            score_color = '#b42318'
                                                        score_html = f'<span style="color:{score_color};font-weight:bold;font-family:var(--mono, monospace)">{score}/5</span>'
                                                        
                                                        rows_html += f"""
                                                        <tr class="border-b border-slate-100 hover:bg-slate-50/50">
                                                          <td class="py-3 font-semibold text-slate-700 truncate max-w-[200px] text-[12px]" title="{org_name}">{org_name}</td>
                                                          <td class="py-3 text-center text-[12px]">{indiv}</td>
                                                          <td class="py-3 text-center text-[12px]">{batch}</td>
                                                          <td class="py-3 text-center text-[12px]">{cust_list}</td>
                                                          <td class="py-3 text-center text-[12px]">{sanct}</td>
                                                          <td class="py-3 text-center text-[12px]">{pep}</td>
                                                          <td class="py-3 text-right font-bold text-[12px]">{score_html}</td>
                                                        </tr>
                                                        """
                                                        
                                                    table_html = f"""
                                                    <table style="width:100%; border-collapse:collapse; text-align:left;">
                                                      <thead>
                                                        <tr style="border-b: 1px solid #e2e8f0; color:#64748b; font-size:11px;">
                                                          <th style="padding-bottom:10px; font-weight:600; text-align:left;">Organization Name</th>
                                                          <th style="padding-bottom:10px; font-weight:600; text-align:center;">Individual</th>
                                                          <th style="padding-bottom:10px; font-weight:600; text-align:center;">Batch Screening</th>
                                                          <th style="padding-bottom:10px; font-weight:600; text-align:center;">Custom List</th>
                                                          <th style="padding-bottom:10px; font-weight:600; text-align:center;">Sanction Checks</th>
                                                          <th style="padding-bottom:10px; font-weight:600; text-align:center;">PEP Checks</th>
                                                          <th style="padding-bottom:10px; font-weight:600; text-align:right;">Depth Score</th>
                                                        </tr>
                                                      </thead>
                                                      <tbody>
                                                        {rows_html}
                                                      </tbody>
                                                    </table>
                                                    """
                                                    ui.html(table_html, sanitize=False).classes('w-full')

                                cdd_container = ui.column().classes('w-full')
                                asyncio.create_task(load_cdd_data())

                            with ui.tab_panel('Reports'):
                                async def load_reports_data():
                                    reports_container.clear()
                                    with reports_container:
                                        ui.spinner(size='lg').classes('mx-auto my-8')
                                        
                                    report_queries = {
                                        'report_pipeline': QUERIES['regport_report_pipeline']
                                    }
                                    report_results = loader.execute_batch_queries(report_queries, start_date, end_date)
                                    
                                    reports_container.clear()
                                    with reports_container:
                                        df_pipeline = report_results['report_pipeline']
                                        if df_pipeline.empty:
                                            ui.label('No report pipeline data for the selected date range.').classes('text-slate-400 italic text-xs py-12 text-center w-full bg-white border border-slate-100 rounded-xl')
                                        else:
                                            with ui.grid(columns=12).classes('w-full gap-4'):
                                                # Left Card: Report pipeline per org (col-span-8)
                                                with ui.card().classes('col-span-8 p-6 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col justify-between'):
                                                    with ui.row().classes('w-full items-start justify-between mb-2'):
                                                        render_chart_header('Report pipeline per org', 'report_pipeline_per_org_port', True, lambda: _download_csv_helper(df_pipeline, 'Report Pipeline Per Org'), df_pipeline)
                                                    ui.label('Generated → Approved vs Rejected · from regport_audit_trails actionType').classes('text-[11px] text-slate-500 mb-4')
                                                    
                                                    df_top = df_pipeline.head(6)
                                                    org_names = df_top['organizationName'].tolist()
                                                    generated = df_top['generated'].tolist()
                                                    approved = df_top['approved'].tolist()
                                                    rejected = df_top['rejected'].tolist()
                                                    
                                                    ui.echart({
                                                        'tooltip': {
                                                            'trigger': 'axis',
                                                            'axisPointer': {'type': 'shadow'},
                                                            'textStyle': {'fontSize': 11}
                                                        },
                                                        'legend': {
                                                            'data': ['Generated', 'Approved', 'Rejected'],
                                                            'top': 0,
                                                            'left': 0,
                                                            'icon': 'roundRect',
                                                            'textStyle': {'color': '#64748b', 'fontSize': 9}
                                                        },
                                                        'grid': {
                                                            'left': '3%',
                                                            'right': '4%',
                                                            'top': '18%',
                                                            'bottom': '22%',
                                                            'containLabel': True
                                                        },
                                                        'xAxis': {
                                                            'type': 'category',
                                                            'data': org_names,
                                                            'axisLabel': {'color': '#475569', 'fontSize': 9, 'interval': 0, 'rotate': 15}
                                                        },
                                                        'yAxis': {
                                                            'type': 'value',
                                                            'axisLabel': {'color': '#64748b', 'fontSize': 9},
                                                            'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                                                        },
                                                        'series': [
                                                            {
                                                                'name': 'Generated',
                                                                'type': 'bar',
                                                                'color': '#1570ef',
                                                                'data': generated,
                                                                'barMaxWidth': 20
                                                            },
                                                            {
                                                                'name': 'Approved',
                                                                'type': 'bar',
                                                                'color': '#027a48',
                                                                'data': approved,
                                                                'barMaxWidth': 20
                                                            },
                                                            {
                                                                'name': 'Rejected',
                                                                'type': 'bar',
                                                                'color': '#b42318',
                                                                'data': rejected,
                                                                'barMaxWidth': 20
                                                            }
                                                        ]
                                                    }).classes('h-64 w-full')
                                                    
                                                # Right Card: Approval rate (col-span-4)
                                                with ui.card().classes('col-span-4 p-6 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col justify-between'):
                                                    with ui.row().classes('w-full items-start justify-between mb-2'):
                                                        render_chart_header('Approval rate', 'approval_rate_port', True, lambda: _download_csv_helper(df_pipeline, 'Report Approval Rate'), df_pipeline)
                                                    ui.label('Approved ÷ (approved + rejected)').classes('text-[11px] text-slate-500 mb-4')
                                                    
                                                    total_approved = int(df_pipeline['approved'].sum())
                                                    total_rejected = int(df_pipeline['rejected'].sum())
                                                    
                                                    if total_approved == 0 and total_rejected == 0:
                                                        ui.label('No approvals or rejections').classes('text-slate-400 italic text-xs py-12 text-center w-full')
                                                    else:
                                                        ui.echart({
                                                            'tooltip': {
                                                                'trigger': 'item',
                                                                'formatter': '{b}: {c} ({d}%)',
                                                                'textStyle': {'fontSize': 11}
                                                            },
                                                            'legend': {
                                                                'data': ['Approved', 'Rejected'],
                                                                'bottom': 0,
                                                                'left': 0,
                                                                'icon': 'circle',
                                                                'textStyle': {'color': '#64748b', 'fontSize': 9}
                                                            },
                                                            'series': [{
                                                                'type': 'pie',
                                                                'radius': ['55%', '80%'],
                                                                'avoidLabelOverlap': False,
                                                                'label': {'show': False},
                                                                'emphasis': {
                                                                    'label': {'show': False}
                                                                },
                                                                'labelLine': {
                                                                    'show': False
                                                                },
                                                                'data': [
                                                                    {'value': total_approved, 'name': 'Approved', 'itemStyle': {'color': '#027a48'}},
                                                                    {'value': total_rejected, 'name': 'Rejected', 'itemStyle': {'color': '#b42318'}}
                                                                ]
                                                            }]
                                                        }).classes('h-64 w-full')
                                
                                reports_container = ui.column().classes('w-full')
                                asyncio.create_task(load_reports_data())

                            with ui.tab_panel('Batch Upload'):
                                async def load_batch_upload_data():
                                    batch_container.clear()
                                    with batch_container:
                                        ui.spinner(size='lg').classes('mx-auto my-8')
                                        
                                    batch_queries = {
                                        'quality':      QUERIES['regport_upload_quality_by_org'],
                                        'template':     QUERIES['regport_template_type_coverage'],
                                        'file_dist':    QUERIES['regport_file_type_distribution']
                                    }
                                    batch_results = loader.execute_batch_queries(batch_queries, start_date, end_date)
                                    
                                    batch_container.clear()
                                    with batch_container:
                                        df_quality = batch_results['quality']
                                        df_temp = batch_results['template']
                                        df_file_dist = batch_results['file_dist']
                                        
                                        if df_quality.empty and df_temp.empty and df_file_dist.empty:
                                            ui.label('No batch upload data for the selected date range.').classes('text-slate-400 italic text-xs py-12 text-center w-full bg-white border border-slate-100 rounded-xl')
                                        else:
                                            # Build name map
                                            org_id_to_name = {}
                                            for _, row in df_quality.iterrows():
                                                org_id_to_name[row['organizationId']] = row['organizationName']
                                            for _, row in df_temp.iterrows():
                                                org_id_to_name[row['organizationId']] = row['organizationName']
                                                
                                            # Row 1 Grid: 3 Cards (Upload quality score, Template coverage, File type dist)
                                            with ui.grid(columns=12).classes('w-full gap-4 mb-4'):
                                                
                                                # Card 1: Upload quality score (col-span-4)
                                                with ui.card().classes('col-span-4 p-6 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col justify-between h-80'):
                                                    with ui.row().classes('w-full items-start justify-between mb-2'):
                                                        render_chart_header('Upload quality score', 'upload_quality_score_port', True, lambda: _download_csv_helper(df_quality, 'Upload Quality Score'), df_quality)
                                                    ui.label('processed_successfully ÷ record_count per org').classes('text-[11px] text-slate-500')
                                                    
                                                    if df_quality.empty:
                                                        ui.label('No uploads').classes('text-slate-400 italic text-xs py-12 text-center w-full')
                                                    else:
                                                        quality_rows = []
                                                        for _, row in df_quality.head(5).iterrows():
                                                            org_name = row['organizationName']
                                                            score = float(row['quality_score_pct'])
                                                            if score >= 90.0:
                                                                color = '#027a48'
                                                            elif score >= 80.0:
                                                                color = '#b54708'
                                                            else:
                                                                color = '#b42318'
                                                            
                                                            quality_rows.append(f"""
                                                            <div style="display: flex; align-items: center; justify-content: space-between; width: 100%; py: 6px; font-family: 'DM Sans', sans-serif;">
                                                                <div style="font-size: 11px; color: #475569; font-weight: 500; width: 75px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">{org_name}</div>
                                                                <div style="flex: 1; margin: 0 12px; background-color: #f2f4f7; height: 8px; border-radius: 4px; overflow: hidden; position: relative;">
                                                                    <div style="background-color: {color}; width: {score}%; height: 100%; border-radius: 4px;"></div>
                                                                </div>
                                                                <div style="font-size: 11px; color: {color}; font-weight: 700; width: 40px; text-align: right;">{score:.0f}%</div>
                                                            </div>
                                                            """)
                                                            
                                                        with ui.column().classes('w-full gap-2 flex-1 justify-center'):
                                                            ui.html("<div style='display: flex; flex-direction: column; gap: 12px; width: 100%;'>" + "".join(quality_rows) + "</div>", sanitize=False).classes('w-full')
                                                            
                                                # Card 2: Template coverage (col-span-4)
                                                with ui.card().classes('col-span-4 p-6 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col justify-between h-80'):
                                                    with ui.row().classes('w-full items-start justify-between mb-2'):
                                                        render_chart_header('Template type coverage', 'template_type_coverage_port', True, lambda: _download_csv_helper(df_temp, 'Template Type Coverage'), df_temp)
                                                    ui.label('Distinct template_types used per org').classes('text-[11px] text-slate-500')
                                                    
                                                    if df_temp.empty:
                                                        ui.label('No template usage').classes('text-slate-400 italic text-xs py-12 text-center w-full')
                                                    else:
                                                        df_top_temp = df_temp.head(5)
                                                        temp_orgs = df_top_temp['organizationName'].tolist()
                                                        temp_counts = df_top_temp['distinct_template_types'].tolist()
                                                        
                                                        ui.echart({
                                                            'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}, 'textStyle': {'fontSize': 11}},
                                                            'grid': {'left': '3%', 'right': '4%', 'top': '10%', 'bottom': '22%', 'containLabel': True},
                                                            'xAxis': {
                                                                'type': 'category',
                                                                'data': temp_orgs,
                                                                'axisLabel': {'color': '#475569', 'fontSize': 9, 'interval': 0, 'rotate': 15}
                                                            },
                                                            'yAxis': {
                                                                'type': 'value',
                                                                'axisLabel': {'color': '#64748b', 'fontSize': 9},
                                                                'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                                                            },
                                                            'series': [{
                                                                'type': 'bar',
                                                                'color': '#027a48',
                                                                'data': temp_counts,
                                                                'barMaxWidth': 20
                                                            }]
                                                        }).classes('h-48 w-full')
                                                        
                                                # Card 3: File type distribution (col-span-4)
                                                with ui.card().classes('col-span-4 p-6 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col justify-between h-80'):
                                                    with ui.row().classes('w-full items-start justify-between mb-2'):
                                                        render_chart_header('File type distribution', 'file_type_distribution_port', True, lambda: _download_csv_helper(df_file_dist, 'File Type Distribution'), df_file_dist)
                                                    ui.label('CSV = automated · XLSX = manual preparation').classes('text-[11px] text-slate-500')
                                                    
                                                    if df_file_dist.empty:
                                                        ui.label('No files uploaded').classes('text-slate-400 italic text-xs py-12 text-center w-full')
                                                    else:
                                                        pie_data = []
                                                        for _, r in df_file_dist.iterrows():
                                                            ftype = str(r['file_type'])
                                                            cnt = int(r['upload_count'])
                                                            color = '#1570ef' if ftype == 'CSV' else '#b54708'
                                                            pie_data.append({'value': cnt, 'name': ftype, 'itemStyle': {'color': color}})
                                                            
                                                        ui.echart({
                                                            'tooltip': {'trigger': 'item', 'formatter': '{b}: {c} ({d}%)', 'textStyle': {'fontSize': 11}},
                                                            'legend': {
                                                                'data': [d['name'] for d in pie_data],
                                                                'bottom': 0,
                                                                'left': 0,
                                                                'icon': 'circle',
                                                                'textStyle': {'color': '#64748b', 'fontSize': 9}
                                                            },
                                                            'series': [{
                                                                'type': 'pie',
                                                                'radius': ['55%', '80%'],
                                                                'avoidLabelOverlap': False,
                                                                'label': {'show': False},
                                                                'emphasis': {'label': {'show': False}},
                                                                'labelLine': {'show': False},
                                                                'data': pie_data
                                                            }]
                                                        }).classes('h-48 w-full')
                                
                                batch_container = ui.column().classes('w-full')
                                asyncio.create_task(load_batch_upload_data())

                            with ui.tab_panel('Compliance Chain'):
                                async def load_compliance_chain_data():
                                    chain_container.clear()
                                    with chain_container:
                                        ui.spinner(size='lg').classes('mx-auto my-8')
                                        
                                    chain_queries = {
                                        'chain':    QUERIES['regport_compliance_chain_map'],
                                        'breadth':  QUERIES['regport_module_breadth_distribution'],
                                        'support':  QUERIES['regport_support_signal_by_module'],
                                        'volume':   QUERIES['regport_module_activity_volume']
                                    }
                                    chain_results = loader.execute_batch_queries(chain_queries, start_date, end_date)
                                    
                                    chain_container.clear()
                                    with chain_container:
                                        df_chain = chain_results['chain']
                                        df_breadth = chain_results['breadth']
                                        df_support = chain_results['support']
                                        df_volume = chain_results['volume']
                                        
                                        if df_chain.empty and df_breadth.empty and df_support.empty and df_volume.empty:
                                            ui.label('No compliance chain data for the selected date range.').classes('text-slate-400 italic text-xs py-12 text-center w-full bg-white border border-slate-100 rounded-xl')
                                        else:
                                            # Card 1: Compliance chain completion map (Full-width col-span-12)
                                            with ui.card().classes('w-full p-6 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col mb-4'):
                                                with ui.row().classes('w-full items-start justify-between mb-2'):
                                                    render_chart_header('Compliance chain completion map', 'compliance_chain_completion_map_port', True, lambda: _download_csv_helper(df_chain, 'Compliance Chain Completion Map'), df_chain)
                                                ui.label('Track integration maturity from ingestion through case resolution').classes('text-[11px] text-slate-500 mb-3')
                                                    
                                                # Legend HTML
                                                ui.html("""
                                                <div style="display: flex; align-items: center; gap: 16px; font-size: 11px; font-weight: 600; color: #64748b; font-family: 'DM Sans', sans-serif;">
                                                    <div style="display: flex; align-items: center; gap: 6px;">
                                                        <svg width="12" height="12" viewBox="0 0 16 16" fill="#12b76a"><circle cx="8" cy="8" r="6" /></svg>
                                                        <span>Active</span>
                                                    </div>
                                                    <div style="display: flex; align-items: center; gap: 6px;">
                                                        <svg width="12" height="12" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" fill="none" stroke="#f79009" stroke-width="2"/><path d="M8 2 A6 6 0 0 1 8 14 Z" fill="#f79009"/></svg>
                                                        <span>Partial</span>
                                                    </div>
                                                    <div style="display: flex; align-items: center; gap: 6px;">
                                                        <svg width="12" height="12" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" fill="none" stroke="#fda29b" stroke-width="2"/></svg>
                                                        <span>None</span>
                                                    </div>
                                                </div>
                                                """, sanitize=False)
                                                
                                                if df_chain.empty:
                                                    ui.label('No organization activity found').classes('text-slate-400 italic text-xs py-12 text-center w-full')
                                                else:
                                                    table_rows = []
                                                    for _, row in df_chain.iterrows():
                                                        org_name = row['organizationName']
                                                        
                                                        def get_icon(count_val):
                                                            try:
                                                                count = int(count_val)
                                                            except:
                                                                count = 0
                                                            
                                                            if count == 0:
                                                                return '<svg class="w-4 h-4 mx-auto" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" fill="none" stroke="#fda29b" stroke-width="2"/></svg>'
                                                            elif count < 5:
                                                                return '<svg class="w-4 h-4 mx-auto" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" fill="none" stroke="#f79009" stroke-width="2"/><path d="M8 2 A6 6 0 0 1 8 14 Z" fill="#f79009"/></svg>'
                                                            else:
                                                                return '<svg class="w-4 h-4 mx-auto" viewBox="0 0 16 16" fill="#12b76a"><circle cx="8" cy="8" r="6" /></svg>'

                                                        ing_icon = get_icon(row['ingestion'])
                                                        scr_icon = get_icon(row['screening'])
                                                        mon_icon = get_icon(row['monitoring'])
                                                        cas_icon = get_icon(row['cases'])
                                                        rep_icon = get_icon(row['reports'])
                                                        
                                                        table_rows.append(f"""
                                                        <tr style="border-bottom: 1px solid #f1f5f9;">
                                                            <td style="padding: 12px 16px; text-align: left; font-size: 11px; font-weight: 700; color: #1e293b;">{org_name}</td>
                                                            <td style="padding: 12px 16px; text-align: center;">{ing_icon}</td>
                                                            <td style="padding: 12px 16px; text-align: center;">{scr_icon}</td>
                                                            <td style="padding: 12px 16px; text-align: center;">{mon_icon}</td>
                                                            <td style="padding: 12px 16px; text-align: center;">{cas_icon}</td>
                                                            <td style="padding: 12px 16px; text-align: center;">{rep_icon}</td>
                                                        </tr>
                                                        """)
                                                        
                                                    ui.html(f"""
                                                    <div style="overflow-x: auto; width: 100%; margin-top: 8px;">
                                                        <table style="width: 100%; border-collapse: collapse; font-family: 'DM Sans', sans-serif;">
                                                            <thead>
                                                                <tr style="border-bottom: 2px solid #e2e8f0; font-size: 11px; color: #94a3b8; font-weight: 700;">
                                                                    <th style="padding: 10px 16px; text-align: left; font-weight: 600;">Org</th>
                                                                    <th style="padding: 10px 16px; text-align: center; font-weight: 600;">Ingestion</th>
                                                                    <th style="padding: 10px 16px; text-align: center; font-weight: 600;">Screening</th>
                                                                    <th style="padding: 10px 16px; text-align: center; font-weight: 600;">Tx Monitoring</th>
                                                                    <th style="padding: 10px 16px; text-align: center; font-weight: 600;">Cases</th>
                                                                    <th style="padding: 10px 16px; text-align: center; font-weight: 600;">Reports</th>
                                                                </tr>
                                                            </thead>
                                                            <tbody>
                                                                {"".join(table_rows)}
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                    """, sanitize=False).classes('w-full')
                                                    
                                            # Row 2 Grid: 2 Cards (Module breadth, Activity volume)
                                            with ui.grid(columns=12).classes('w-full gap-4 mb-4'):
                                                
                                                # Card 2: Module breadth distribution (col-span-6)
                                                with ui.card().classes('col-span-6 p-6 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col justify-between h-80'):
                                                    with ui.row().classes('w-full items-start justify-between mb-2'):
                                                        render_chart_header('Module breadth distribution', 'module_breadth_distribution_port', True, lambda: _download_csv_helper(df_breadth, 'Module Breadth Distribution'), df_breadth)
                                                    ui.label('Orgs grouped by distinct modules used (of 8 core)').classes('text-[11px] text-slate-500')
                                                    
                                                    if df_breadth.empty:
                                                        ui.label('No breadth data').classes('text-slate-400 italic text-xs py-12 text-center w-full')
                                                    else:
                                                        bucket_vals = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
                                                        for _, r in df_breadth.iterrows():
                                                            m_used = min(int(r['modules_used']), 6)
                                                            bucket_vals[m_used] += int(r['org_count'])
                                                            
                                                        breadth_labels = ['1 module', '2 modules', '3 modules', '4 modules', '5 modules', '6+ modules']
                                                        breadth_counts = [bucket_vals[i] for i in range(1, 7)]
                                                        color_palette = ['#b42318', '#b42318', '#b54708', '#1570ef', '#027a48', '#027a48']
                                                        
                                                        series_data = []
                                                        for idx, val in enumerate(breadth_counts):
                                                            series_data.append({
                                                                'value': val,
                                                                'itemStyle': {'color': color_palette[idx]}
                                                            })
                                                            
                                                        ui.echart({
                                                            'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}, 'textStyle': {'fontSize': 11}},
                                                            'grid': {'left': '3%', 'right': '4%', 'top': '10%', 'bottom': '12%', 'containLabel': True},
                                                            'xAxis': {
                                                                'type': 'category',
                                                                'data': breadth_labels,
                                                                'axisLabel': {'color': '#475569', 'fontSize': 9, 'interval': 0}
                                                            },
                                                            'yAxis': {
                                                                'type': 'value',
                                                                'axisLabel': {'color': '#64748b', 'fontSize': 9},
                                                                'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                                                            },
                                                            'series': [{
                                                                'type': 'bar',
                                                                'data': series_data,
                                                                'barMaxWidth': 28
                                                            }]
                                                        }).classes('h-48 w-full')
                                                        
                                                # Card 3: Module activity volume (col-span-6)
                                                with ui.card().classes('col-span-6 p-6 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col justify-between h-80'):
                                                    with ui.row().classes('w-full items-start justify-between mb-2'):
                                                        render_chart_header('Module activity volume', 'module_activity_volume_port', True, lambda: _download_csv_helper(df_volume, 'Module Activity Volume'), df_volume)
                                                    ui.label('Total audit_trails events per module · right = active org count').classes('text-[11px] text-slate-500')
                                                    
                                                    if df_volume.empty:
                                                        ui.label('No activity records').classes('text-slate-400 italic text-xs py-12 text-center w-full')
                                                    else:
                                                        max_events = df_volume['total_events'].max() if not df_volume.empty else 1
                                                        volume_rows = []
                                                        for _, r in df_volume.head(6).iterrows():
                                                            mod = str(r['module'])
                                                            events = int(r['total_events'])
                                                            orgs = int(r['active_orgs'])
                                                            pct = (events / max_events) * 100
                                                            volume_rows.append(f"""
                                                            <div style="display: flex; align-items: center; justify-content: space-between; width: 100%; py: 6px; font-family: 'DM Sans', sans-serif;">
                                                                <div style="font-size: 11px; color: #475569; font-weight: 500; width: 120px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">{mod}</div>
                                                                <div style="flex: 1; margin: 0 12px; background-color: #f2f4f7; height: 8px; border-radius: 4px; overflow: hidden; position: relative;">
                                                                    <div style="background-color: #a4d9ff; width: {pct}%; height: 100%; border-radius: 4px;"></div>
                                                                </div>
                                                                <div style="font-size: 11px; color: #475569; font-weight: 500; width: 90px; text-align: right;">
                                                                    <span style="font-weight: 700; color: #1e293b;">{events:,}</span>
                                                                    <span style="color: #94a3b8; margin-left: 8px;">{orgs} orgs</span>
                                                                </div>
                                                            </div>
                                                            """)
                                                            
                                                        with ui.column().classes('w-full gap-1.5 flex-1 justify-center'):
                                                            ui.html("<div style='display: flex; flex-direction: column; gap: 8px; width: 100%;'>" + "".join(volume_rows) + "</div>", sanitize=False).classes('w-full')
                                                            
                                            # Row 3: Support signal by module (Full-width col-span-12)
                                            with ui.card().classes('w-full p-6 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col'):
                                                with ui.row().classes('w-full items-start justify-between mb-2'):
                                                    render_chart_header('Support signal by module', 'support_signal_by_module_port', True, lambda: _download_csv_helper(df_support, 'Support Signal By Module'), df_support)
                                                ui.label('Support events opened within 30 min of visiting each module · identifies UX friction').classes('text-[11px] text-slate-500 mb-4')
                                                
                                                if df_support.empty:
                                                    ui.label('No support signals tracked').classes('text-slate-400 italic text-xs py-12 text-center w-full')
                                                else:
                                                    max_support = df_support['total_support_events'].max() if not df_support.empty else 1
                                                    support_rows = []
                                                    for _, r in df_support.head(6).iterrows():
                                                        mod = str(r['module_before_support'])
                                                        touches = int(r['total_support_events'])
                                                        orgs = int(r['orgs_affected'])
                                                        pct = (touches / max_support) * 100
                                                        support_rows.append(f"""
                                                        <div style="display: flex; align-items: center; justify-content: space-between; width: 100%; py: 6px; font-family: 'DM Sans', sans-serif;">
                                                            <div style="font-size: 11px; color: #475569; font-weight: 500; width: 120px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">{mod}</div>
                                                            <div style="flex: 1; margin: 0 12px; background-color: #f2f4f7; height: 8px; border-radius: 4px; overflow: hidden; position: relative;">
                                                                    <div style="background-color: #fedf89; width: {pct}%; height: 100%; border-radius: 4px;"></div>
                                                            </div>
                                                            <div style="font-size: 11px; color: #1e293b; font-weight: 700; width: 120px; text-align: right;">{touches} events · {orgs} {"org" if orgs == 1 else "orgs"}</div>
                                                        </div>
                                                        """)
                                                        
                                                    with ui.column().classes('w-full gap-1.5 mt-2'):
                                                        ui.html("<div style='display: flex; flex-direction: column; gap: 8px; width: 100%;'>" + "".join(support_rows) + "</div>", sanitize=False).classes('w-full')
                                
                                chain_container = ui.column().classes('w-full')
                                asyncio.create_task(load_compliance_chain_data())

                            with ui.tab_panel('Org Health'):
                                async def load_org_health_data():
                                    health_container.clear()
                                    with health_container:
                                        ui.spinner(size='lg').classes('mx-auto my-8')
                                        
                                    health_queries = {
                                        'matrix':      QUERIES['regport_org_health_matrix'],
                                        'dormancy':    QUERIES['regport_dormancy_risk_list'],
                                        'segmentation': QUERIES['regport_org_tier_segmentation']
                                    }
                                    health_results = loader.execute_batch_queries(health_queries, start_date, end_date)
                                    
                                    health_container.clear()
                                    with health_container:
                                        df_matrix = health_results['matrix']
                                        df_dormancy = health_results['dormancy']
                                        df_segmentation = health_results['segmentation']
                                        
                                        if df_matrix.empty and df_dormancy.empty and df_segmentation.empty:
                                            ui.label('No organization health data for the selected date range.').classes('text-slate-400 italic text-xs py-12 text-center w-full bg-white border border-slate-100 rounded-xl')
                                        else:
                                            # ── ROW 1: Organisation Health Matrix (Full Width) ──
                                            with ui.card().classes('w-full p-6 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col justify-between h-96 mb-4'):
                                                with ui.row().classes('w-full items-start justify-between mb-2'):
                                                    render_chart_header('Organisation health matrix', 'organisation_health_matrix_port', True, lambda: _download_csv_helper(df_matrix, 'Organisation Health Matrix'), df_matrix)
                                                ui.label('Recency · breadth · resolution · upload quality · report approval · risk tier').classes('text-[11px] text-slate-500 mb-4')
                                                
                                                # Fixed height scrollable table wrapper
                                                with ui.element('div').classes('w-full flex-1 overflow-y-auto border border-slate-100 rounded-lg').style('max-height: 250px;'):
                                                    if df_matrix.empty:
                                                        ui.label('No organizations registered').classes('text-slate-400 italic text-xs py-12 text-center w-full')
                                                    else:
                                                        matrix_rows = []
                                                        for _, row in df_matrix.iterrows():
                                                            org_name = str(row['organizationName'])
                                                            
                                                            # 1. Recency
                                                            days = int(row['days_since_active']) if not pd.isna(row['days_since_active']) else 99
                                                            if days <= 1:
                                                                rec_color = '#12b76a'
                                                                rec_text = '1d ago' if days == 1 else 'Active today'
                                                            elif days <= 7:
                                                                rec_color = '#f79009'
                                                                rec_text = f'{days}d ago'
                                                            else:
                                                                rec_color = '#b42318'
                                                                rec_text = f'{days}d ago'
                                                                
                                                            # 2. Modules count
                                                            modules = f"{int(row['modules_used'])}/8"
                                                            
                                                            # 3. Workflow Completion Pill
                                                            completed = int(row['modules_used'])
                                                            if completed >= 6:
                                                                wf_bg, wf_color = '#ecfdf3', '#027a48'
                                                                wf_text = 'Complete'
                                                            elif completed >= 3:
                                                                wf_bg, wf_color = '#fffaeb', '#b54708'
                                                                wf_text = 'Partial'
                                                            else:
                                                                wf_bg, wf_color = '#fef3f2', '#b42318'
                                                                wf_text = 'None'
                                                            wf_pill = f'<span style="background-color:{wf_bg}; color:{wf_color}; border-radius:100px; text-[10px] font-bold px-2 py-0.5 inline-block text-center min-w-16">{wf_text}</span>'
                                                            
                                                            # 4. Flag resolution %
                                                            flag_pct = row['flag_resolution_pct']
                                                            flag_text = f"{flag_pct:.0f}%" if not pd.isna(flag_pct) else '—'
                                                            
                                                            # 5. Report approval %
                                                            rpt_pct = row['report_approval_pct']
                                                            rpt_text = f"{rpt_pct:.0f}%" if not pd.isna(rpt_pct) else '—'
                                                            
                                                            # 6. Upload quality %
                                                            upl_pct = row['upload_quality_pct']
                                                            upl_text = f"{upl_pct:.0f}%" if not pd.isna(upl_pct) else '—'
                                                            
                                                            # 7. MoM trend
                                                            mom = row['mom_change_pct']
                                                            if pd.isna(mom):
                                                                mom_text = '—'
                                                                mom_style = 'color: #64748b;'
                                                            elif mom >= 0:
                                                                mom_text = f"+{mom:.0f}%"
                                                                mom_style = 'color: #027a48; font-weight: 700;'
                                                            else:
                                                                mom_text = f"{mom:.0f}%"
                                                                mom_style = 'color: #b42318; font-weight: 700;'
                                                                
                                                            # 8. Support count
                                                            support = str(int(row['support_touches']))
                                                            
                                                            # 9. Risk tier
                                                            risk = str(row['risk_tier']).lower()
                                                            if risk == 'low' or risk == 'healthy':
                                                                risk_bg, risk_color, risk_lbl = '#ecfdf3', '#027a48', 'Healthy'
                                                            elif risk == 'medium' or risk == 'watch':
                                                                risk_bg, risk_color, risk_lbl = '#fffaeb', '#b54708', 'Watch'
                                                            elif risk == 'high' or risk == 'at-risk':
                                                                risk_bg, risk_color, risk_lbl = '#fef3f2', '#b42318', 'At-risk'
                                                            else:
                                                                risk_bg, risk_color, risk_lbl = '#f1f5f9', '#475569', 'Dormant'
                                                            risk_pill = f'<span style="background-color:{risk_bg}; color:{risk_color}; border-radius:100px; text-[10px] font-bold px-2 py-0.5 inline-block text-center min-w-16">{risk_lbl}</span>'
                                                            
                                                            matrix_rows.append(f"""
                                                            <tr style="border-bottom: 1px solid #f1f5f9; font-family: 'DM Sans', sans-serif; font-size: 11px;">
                                                                <td style="padding: 10px 12px; text-align: left; font-weight: 700; color: #1e293b;">{org_name}</td>
                                                                <td style="padding: 10px 12px; text-align: center; color: {rec_color}; font-weight: 600;">{rec_text}</td>
                                                                <td style="padding: 10px 12px; text-align: center; font-weight: 500; color: #475569;">{modules}</td>
                                                                <td style="padding: 10px 12px; text-align: center;">{wf_pill}</td>
                                                                <td style="padding: 10px 12px; text-align: center; font-weight: 700; color: #475569;">{flag_text}</td>
                                                                <td style="padding: 10px 12px; text-align: center; font-weight: 700; color: #475569;">{rpt_text}</td>
                                                                <td style="padding: 10px 12px; text-align: center; font-weight: 700; color: #475569;">{upl_text}</td>
                                                                <td style="padding: 10px 12px; text-align: center; {mom_style}">{mom_text}</td>
                                                                <td style="padding: 10px 12px; text-align: center; font-weight: 600; color: #475569;">{support}</td>
                                                                <td style="padding: 10px 12px; text-align: center;">{risk_pill}</td>
                                                            </tr>
                                                            """)
                                                        
                                                        table_html = f"""
                                                        <table style="width: 100%; border-collapse: collapse; text-align: center;">
                                                          <thead>
                                                            <tr style="border-bottom: 2px solid #e2e8f0; font-family: 'DM Sans', sans-serif; font-size: 10px; font-weight: bold; color: #64748b;">
                                                              <th style="padding: 8px 12px; text-align: left;">Organisation</th>
                                                              <th style="padding: 8px 12px; text-align: center;">Last active</th>
                                                              <th style="padding: 8px 12px; text-align: center;">Modules</th>
                                                              <th style="padding: 8px 12px; text-align: center;">Workflow</th>
                                                              <th style="padding: 8px 12px; text-align: center;">Flag res.</th>
                                                              <th style="padding: 8px 12px; text-align: center;">Rpt approval</th>
                                                              <th style="padding: 8px 12px; text-align: center;">Upload qual.</th>
                                                              <th style="padding: 8px 12px; text-align: center;">MoM</th>
                                                              <th style="padding: 8px 12px; text-align: center;">Support</th>
                                                              <th style="padding: 8px 12px; text-align: center;">Risk</th>
                                                            </tr>
                                                          </thead>
                                                          <tbody>
                                                            {"".join(matrix_rows)}
                                                          </tbody>
                                                        </table>
                                                        """
                                                        ui.html(table_html, sanitize=False).classes('w-full')
                                            
                                            # ── ROW 2: Dormancy Risk List and Tier Segmentation ──
                                            with ui.grid(columns=12).classes('w-full gap-4 mt-2'):
                                                # Left Card: Dormancy Risk List (col-span-8)
                                                with ui.card().classes('col-span-8 p-6 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col justify-between h-96'):
                                                    with ui.row().classes('w-full items-start justify-between mb-2'):
                                                        render_chart_header('Dormancy risk list', 'dormancy_risk_list_port', True, lambda: _download_csv_helper(df_dormancy, 'Dormancy Risk List'), df_dormancy)
                                                    ui.label('Organisations that were active (20+ events/week) but went silent for 21+ days').classes('text-[11px] text-slate-500 mb-4')
                                                    
                                                    # Fixed height scrollable wrapper for dormant list
                                                    with ui.element('div').classes('w-full flex-1 overflow-y-auto border border-slate-55 rounded-lg p-2').style('max-height: 250px;'):
                                                        if df_dormancy.empty:
                                                            ui.label('No organizations currently dormant or at immediate risk of dormancy.').classes('text-slate-400 italic text-xs py-8 text-center w-full bg-slate-50 rounded-lg border border-dashed border-slate-200')
                                                        else:
                                                            dormant_rows = []
                                                            for _, r in df_dormancy.iterrows():
                                                                o_name = str(r['organizationName'])
                                                                days_silent = int(r['days_silent'])
                                                                weekly_avg = int(r['prior_weekly_avg_events'])
                                                                
                                                                dormant_rows.append(f"""
                                                                <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; background-color: #fcfcfd; border: 1px solid #f2f4f7; border-radius: 8px; margin-bottom: 8px; font-family: 'DM Sans', sans-serif;">
                                                                    <div style="display: flex; flex-direction: column; gap: 4px;">
                                                                        <span style="font-size: 13px; font-weight: 700; color: #101828;">{o_name}</span>
                                                                        <span style="font-size: 11px; color: #667085;">Last active {days_silent} days ago &middot; was averaging {weekly_avg} events/week</span>
                                                                    </div>
                                                                    <span style="background-color: #fef3f2; color: #b42318; padding: 6px 12px; border-radius: 6px; font-size: 11px; font-weight: 700; border: 1px solid #fda29b;">Silent</span>
                                                                </div>
                                                                """)
                                                            
                                                            ui.html("<div style='display: flex; flex-direction: column; gap: 8px; width: 100%;'>" + "".join(dormant_rows) + "</div>", sanitize=False).classes('w-full')
                                                
                                                # Right Card: Tier segmentation (col-span-4)
                                                with ui.card().classes('col-span-4 p-6 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col justify-between h-96'):
                                                    with ui.row().classes('w-full items-start justify-between mb-2'):
                                                        render_chart_header('Tier segmentation', 'tier_segmentation_port', True, lambda: _download_csv_helper(df_segmentation, 'Tier Segmentation'), df_segmentation)
                                                    ui.label('Power · Steady · At-risk · Dormant').classes('text-[11px] text-slate-500')
                                                    
                                                    if df_segmentation.empty:
                                                        ui.label('No segmentation records').classes('text-slate-400 italic text-xs py-12 text-center w-full')
                                                    else:
                                                        counts = df_segmentation['tier'].value_counts()
                                                        tier_colors = {
                                                            'power':   '#1570ef',
                                                            'steady':  '#027a48',
                                                            'at-risk': '#b54708',
                                                            'dormant': '#b42318'
                                                        }
                                                        pie_data = []
                                                        for tier_name in ['power', 'steady', 'at-risk', 'dormant']:
                                                            val = int(counts.get(tier_name, 0))
                                                            pie_data.append({
                                                                'name': tier_name.capitalize(),
                                                                'value': val,
                                                                'itemStyle': {'color': tier_colors[tier_name]}
                                                            })
                                                        
                                                        ui.echart({
                                                            'tooltip': {
                                                                'trigger': 'item',
                                                                'formatter': '{b}: {c} ({d}%)',
                                                                'textStyle': {'fontSize': 11}
                                                            },
                                                            'legend': {
                                                                'data': ['Power', 'Steady', 'At-risk', 'Dormant'],
                                                                'bottom': 0,
                                                                'left': 'center',
                                                                'icon': 'circle',
                                                                'textStyle': {'color': '#64748b', 'fontSize': 9}
                                                            },
                                                            'series': [{
                                                                'type': 'pie',
                                                                'radius': ['50%', '75%'],
                                                                'avoidLabelOverlap': False,
                                                                'label': {'show': False},
                                                                'emphasis': {'label': {'show': False}},
                                                                'labelLine': {'show': False},
                                                                'data': pie_data
                                                            }]
                                                        }).classes('h-56 w-full')
                                
                                health_container = ui.column().classes('w-full')
                                asyncio.create_task(load_org_health_data())

            refresh_callbacks.append(load_data)
            asyncio.create_task(load_data())
            
        async def organization_deep_dive_content():

            with ui.column().classes('w-full gap-4') as outer:
                # ---- Page header ----
                #ui.label('Organization Deep-Dive').classes(ThemeManager.TYPOGRAPHY['h2'] + ' mb-1')
                # ui.label(
                #     'Explore activity, engagement and usage metrics for the selected organization and date range.'
                # ).classes(ThemeManager.TYPOGRAPHY['body'] + ' mb-4')

                # ---- Data results area (populated on selection / date change) ----
                data_container = ui.column().classes('w-full mt-2')


            async def load_org_data():
                """Re-fetch and render metrics for the currently selected org+date."""
                org_id   = app.storage.user.get(ORG_SESSION_KEY)
                org_name = app.storage.user.get(ORG_NAME_SESSION_KEY, 'Unknown')
                start_date, end_date = get_current_dates()

                data_container.clear()
                with data_container:
                    if not org_id:
                        with ui.column().classes('w-full items-center justify-center py-16'):
                            ui.icon('corporate_fare', size='4rem').classes('text-slate-300 mb-4')
                            ui.label('Select an organization above to view its deep-dive analytics').classes(
                                f'{ThemeManager.COLORS["text"]["muted"]} text-center text-lg'
                            )
                        return

                    with ui.row().classes('w-full items-center gap-2 mb-4'):
                        ui.spinner(size='sm').classes('text-indigo-500')
                        ui.label(f'Loading data for {org_name}…').classes(ThemeManager.COLORS['text']['muted'])

                user_count_df = loader.execute_query(QUERIES['product_org_deep_dive_user_count'], [org_id, PLATFORM])
                last_activity_df = loader.execute_query(QUERIES['product_org_deep_dive_last_activity_date'], [org_id, PLATFORM])
                
                try:
                    details_df = loader.execute_query(QUERIES['regport_org_deep_dive_details'], [org_id])
                    user_stats_df = loader.execute_query(QUERIES['regport_org_deep_dive_user_stats'], [org_id])
                    summary_df = loader.execute_query(QUERIES['regport_org_engagement_summary'], [org_id, PLATFORM, start_date, end_date])
                    daily_trend_df = loader.execute_query(QUERIES['regport_org_engagement_daily_trend'], [org_id, PLATFORM, start_date, end_date])
                    device_df = loader.execute_query(QUERIES['regport_org_session_device_split'], [org_id, PLATFORM, start_date, end_date])
                    traffic_df = loader.execute_query(QUERIES['regport_org_traffic_source'], [org_id, PLATFORM, start_date, end_date])
                    module_usage_df = loader.execute_query(QUERIES['regport_org_module_usage_from_audit'], [org_id, start_date, end_date])
                    action_type_df = loader.execute_query(QUERIES['regport_org_action_type_breakdown'], [org_id, start_date, end_date])
                    heatmap_df = loader.execute_query(QUERIES['regport_org_activity_heatmap'], [org_id, start_date, end_date])
                    audit_timeline_df = loader.execute_query(QUERIES['regport_org_audit_timeline'], [org_id, start_date, end_date])
                    weekly_adoption_df = loader.execute_query(QUERIES['regport_org_module_adoption_weekly'], [org_id, start_date, end_date])
                    user_journey_df = loader.execute_query(QUERIES['regport_org_user_journey_first_actions'], [org_id, start_date, end_date])
                    module_breadth_df = loader.execute_query(QUERIES['regport_org_module_breadth'], [org_id, start_date, end_date])
                    
                    txn_summary_df = loader.execute_query(QUERIES['regport_org_transaction_summary'], [org_id, start_date, end_date])
                    monitored_accounts_df = loader.execute_query(QUERIES['regport_org_monitored_accounts_summary'], [org_id, start_date, end_date])
                    verification_df = loader.execute_query(QUERIES['regport_org_verification_daily_trend'], [org_id, start_date, end_date])
                    screening_df = loader.execute_query(QUERIES['regport_org_screening_summary'], [org_id, start_date, end_date])
                    batch_upload_df = loader.execute_query(QUERIES['regport_org_batch_upload_summary'], [org_id, start_date, end_date])
                    txn_trend_df = loader.execute_query(QUERIES['regport_org_transaction_daily_trend'], [org_id, start_date, end_date])
                    txn_split_df = loader.execute_query(QUERIES['regport_org_transaction_type_split'], [org_id, start_date, end_date])
                    rules_df = loader.execute_query(QUERIES['regport_org_rules_by_code'], [org_id])
                    batch_upload_by_template_df = loader.execute_query(QUERIES['regport_org_batch_upload_by_template'], [org_id, start_date, end_date])
                    users_df = loader.execute_query(QUERIES['regport_org_users'], [org_id])
                    user_activity_role_df = loader.execute_query(QUERIES['regport_org_user_activity_by_role'], [org_id, start_date, end_date])
                    weekly_pattern_df = loader.execute_query(QUERIES['product_deep_ga4_weekly_pattern'], [org_id, PLATFORM, start_date, end_date])
                    traffic_source_df = loader.execute_query(QUERIES['product_deep_traffic_source'], [org_id, PLATFORM, start_date, end_date])
                    org_uj_df = loader.execute_query(QUERIES['org_user_journey_paths'], [start_date, end_date, org_id, PLATFORM])
                except Exception as e:
                    data_container.clear()
                    with data_container:
                        ui.label(f"Error fetching deep-dive details: {str(e)}").classes('text-red-500')
                    return

                if details_df.empty:
                    row = {
                        'organizationName': org_name,
                        'industry': 'Unknown Industry',
                        'email': 'N/A',
                        'org_created_at': None,
                        'country_name': 'Unknown',
                        'org_status': 'Active',
                        'autoMonitoring': False,
                        'account_status': 'Standard',
                        'businessSubCategory': 'Standard Plan'
                    }
                else:
                    row = details_df.iloc[0]
                
                stats_row = user_stats_df.iloc[0] if not user_stats_df.empty else None

                # Extract and process card data
                display_name = row['organizationName']
                industry = row['industry'] if pd.notna(row['industry']) else 'Unknown Industry'
                
                email = row['email']
                email_domain = str(email).split('@')[1] if pd.notna(email) and '@' in str(email) else 'N/A'
                
                created_at = row['org_created_at']
                onboarded_str = f"Onboarded {pd.to_datetime(created_at).strftime('%b %d, %Y')}" if pd.notna(created_at) else "Unknown Date"
                
                country = row['country_name'] if pd.notna(row['country_name']) else 'Unknown'
                if isinstance(country, dict):
                    country = country.get('common', 'Unknown')
                elif isinstance(country, str):
                    if country.startswith('{') and 'common' in country:
                        import ast
                        try:
                            c_dict = ast.literal_eval(country)
                            if isinstance(c_dict, dict):
                                country = c_dict.get('common', country)
                        except:
                            pass
                
                org_status = row['org_status']
                auto_mon = str(row['autoMonitoring']).lower() == 'true'
                account_status = row['account_status']
                
                last_active = stats_row['last_team_activity'] if stats_row is not None and pd.notna(stats_row['last_team_activity']) else None
                last_active_str = pd.to_datetime(last_active).strftime('%b %d, %Y') if last_active else "No Activity"

                user_cnt = int(user_count_df.iloc[0]['user_count']) if not user_count_df.empty else 0
                session_cnt = int(last_activity_df.iloc[0]['total_sessions']) if not last_activity_df.empty else 0

                if summary_df.empty or pd.isna(summary_df.iloc[0]['total_sessions']):
                    active_days = 0
                    total_sessions = 0
                    peak_users = 0
                    engaged_session_pct = 0.0
                    avg_session_min = 0.0
                    total_key_events = 0
                else:
                    s_row = summary_df.iloc[0]
                    active_days = int(s_row['active_days']) if pd.notna(s_row['active_days']) else 0
                    total_sessions = int(s_row['total_sessions']) if pd.notna(s_row['total_sessions']) else 0
                    peak_users = int(s_row['peak_active_users']) if pd.notna(s_row['peak_active_users']) else 0
                    engaged_session_pct = float(s_row['engaged_session_pct']) if pd.notna(s_row['engaged_session_pct']) else 0.0
                    avg_session_min = float(s_row['avg_session_engagement_min']) if pd.notna(s_row['avg_session_engagement_min']) else 0.0
                    total_key_events = int(s_row['total_key_events']) if pd.notna(s_row['total_key_events']) else 0

                # Operational Activity metrics parsing
                total_txns = int(txn_summary_df.iloc[0]['total_transactions']) if not txn_summary_df.empty and pd.notna(txn_summary_df.iloc[0]['total_transactions']) else 0
                flagged_txns = int(txn_summary_df.iloc[0]['flagged_count']) if not txn_summary_df.empty and pd.notna(txn_summary_df.iloc[0]['flagged_count']) else 0
                flag_rate_pct = float(txn_summary_df.iloc[0]['flag_rate_pct']) if not txn_summary_df.empty and pd.notna(txn_summary_df.iloc[0]['flag_rate_pct']) else 0.0
                
                total_monitored = int(monitored_accounts_df.iloc[0]['total_monitored']) if not monitored_accounts_df.empty and pd.notna(monitored_accounts_df.iloc[0]['total_monitored']) else 0
                new_monitored = int(monitored_accounts_df.iloc[0]['new_count']) if not monitored_accounts_df.empty and pd.notna(monitored_accounts_df.iloc[0]['new_count']) else 0
                closed_monitored = int(monitored_accounts_df.iloc[0]['closed_count']) if not monitored_accounts_df.empty and pd.notna(monitored_accounts_df.iloc[0]['closed_count']) else 0
                review_monitored = int(monitored_accounts_df.iloc[0]['review_count']) if not monitored_accounts_df.empty and pd.notna(monitored_accounts_df.iloc[0]['review_count']) else 0
                total_checks = int(verification_df['checks'].sum()) if not verification_df.empty else 0
                total_screenings = int(screening_df.iloc[0]['total_screenings']) if not screening_df.empty and pd.notna(screening_df.iloc[0]['total_screenings']) else 0
                screening_match_pct = float(screening_df.iloc[0]['flag_rate_pct']) if not screening_df.empty and pd.notna(screening_df.iloc[0]['flag_rate_pct']) else 0.0
                
                total_uploads = int(batch_upload_df.iloc[0]['total_uploads']) if not batch_upload_df.empty and pd.notna(batch_upload_df.iloc[0]['total_uploads']) else 0
                upload_error_pct = float(batch_upload_df.iloc[0]['error_rate_pct']) if not batch_upload_df.empty and pd.notna(batch_upload_df.iloc[0]['error_rate_pct']) else 0.0

                data_container.clear()
                with data_container:
                    # Render Beautiful Responsive Header Card
                    with ui.card().classes('relative overflow-hidden w-full p-6 border border-slate-200 shadow-sm bg-white rounded-xl mb-6 hover:shadow-md transition-all duration-300'):
                        # Premium top border strip (blue to teal gradient)
                        ui.element('div').classes('absolute top-0 left-0 right-0 h-[4px] bg-gradient-to-r from-blue-500 via-indigo-600 to-teal-500')
                        
                        with ui.row().classes('w-full justify-between items-start flex-wrap gap-6 pt-1'):
                            # Left side: Title and Metadata
                            with ui.column().classes('flex-1 min-w-[280px] gap-3.5'):
                                
                                # Title
                                ui.label(display_name).classes('rp-org-name')
                                
                                # Metadata stack
                                with ui.column().classes('w-full gap-2.5 text-[13px] text-slate-500'):
                                    # Row 1: Industry
                                    with ui.row().classes('items-center gap-2'):
                                        ui.icon('domain', size='16px').classes('text-slate-400')
                                        ui.label(industry).classes('rp-org-meta')
                                    
                                    # Row 2: Email & Onboarded (with flex wrap)
                                    with ui.row().classes('items-center flex-wrap gap-x-4 gap-y-2'):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.icon('email', size='16px').classes('text-slate-400')
                                            ui.label(email_domain).classes('rp-org-meta')
                                        with ui.row().classes('items-center gap-2'):
                                            ui.icon('event', size='16px').classes('text-slate-400')
                                            ui.label(onboarded_str).classes('rp-org-meta')
                                            
                                    # Row 3: Country & Last Active (with flex wrap)
                                    with ui.row().classes('items-center flex-wrap gap-x-4 gap-y-2'):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.icon('flag', size='16px').classes('text-slate-400')
                                            ui.label(country).classes('rp-org-meta')
                                        with ui.row().classes('items-center gap-2'):
                                            ui.icon('schedule', size='16px').classes('text-slate-400')
                                            with ui.row().classes('items-center gap-1'):
                                                ui.label('Last active:').classes('rp-org-meta')
                                                ui.label(last_active_str).classes('rp-org-meta-bold')
                                                
                            # Right side: Badges row (horizontal flex on desktop/tablet, wraps cleanly, stacks vertically or wraps on mobile)
                            with ui.row().classes('flex flex-col sm:flex-row flex-wrap gap-2 items-start sm:items-center justify-start sm:justify-end mt-1 sm:mt-0'):
                                
                                # 1. Active badge
                                with ui.row().classes('bg-emerald-50 text-emerald-600 border border-emerald-100 rounded-full px-3 py-1 items-center gap-1.5 font-semibold text-[11px] shadow-xs'):
                                    ui.element('span').classes('w-1.5 h-1.5 rounded-full bg-emerald-500')
                                    ui.label(org_status)
                                    
                                # 2. Auto Monitoring badge
                                mon_text = 'Auto-Monitoring ON' if auto_mon else 'Auto-Monitoring OFF'
                                mon_bg = 'bg-blue-50 text-blue-600 border border-blue-100' if auto_mon else 'bg-slate-50 text-slate-500 border border-slate-100'
                                with ui.row().classes(f'{mon_bg} rounded-full px-3 py-1 items-center font-semibold text-[11px] shadow-xs'):
                                    ui.label(mon_text)
                                    
                                # 3. Plan badge
                                plan_color = 'amber' if 'standard' in account_status.lower() or 'trial' in account_status.lower() else 'purple'
                                with ui.row().classes(f'bg-{plan_color}-50 text-{plan_color}-600 border border-{plan_color}-100 rounded-full px-3 py-1 items-center font-semibold text-[11px] shadow-xs'):
                                    ui.label(f'{account_status} Plan')
                                    
                                # 4. Business Subcategory badge
                                subcat = row['businessSubCategory'] if pd.notna(row['businessSubCategory']) else 'Unknown Subcategory'
                                with ui.row().classes('bg-slate-50 text-slate-500 border border-slate-100 rounded-full px-3 py-1 items-center font-semibold text-[11px] font-mono shadow-xs'):
                                    ui.label(subcat)



                    # Render Subtitle block for ENGAGEMENT PULSE with an elegant separator line
                    with ui.row().classes('w-full items-center gap-2 mb-4 mt-6'):
                        with ui.element('div').classes('p-2 bg-slate-50 border border-slate-100 rounded-lg flex items-center justify-center shadow-xs'):
                            ui.icon('bolt', size='16px').classes('text-indigo-500')
                        ui.label('ENGAGEMENT PULSE').classes('rp-section-label')
                        ui.element('div').classes('flex-grow h-px bg-slate-200/60 ml-2')

                    # 6 Premium Interactive Vertical KPI Cards
                    with ui.row().classes('w-full justify-between items-stretch flex-wrap gap-4'):
                        
                        # Card 1: TOTAL SESSIONS
                        with ui.card().classes('flex-1 min-w-[150px] p-4 bg-white border border-slate-100 rounded-xl shadow-xs border-l-4 border-l-blue-500 relative overflow-hidden hover:shadow-md hover:scale-[1.02] cursor-pointer transition-all duration-300'):
                            with ui.row().classes('w-full justify-between items-center no-wrap'):
                                ui.label('TOTAL SESSIONS').classes('rp-kpi-label')
                                render_kpi_info_icon('total_sessions')
                            ui.label(f"{total_sessions:,}").classes('rp-kpi-value mt-1')
                            ui.label('Across date range').classes('rp-kpi-sub mt-1')
                        
                        # Card 2: ACTIVE USERS
                        with ui.card().classes('flex-1 min-w-[150px] p-4 bg-white border border-slate-100 rounded-xl shadow-xs border-l-4 border-l-emerald-500 relative overflow-hidden hover:shadow-md hover:scale-[1.02] cursor-pointer transition-all duration-300'):
                            with ui.row().classes('w-full justify-between items-center no-wrap'):
                                ui.label('ACTIVE USERS').classes('rp-kpi-label')
                                render_kpi_info_icon('active_users')
                            ui.label(f"{peak_users:,}").classes('rp-kpi-value mt-1')
                            ui.label('Peak daily count').classes('rp-kpi-sub mt-1')
                            
                            
                        # Card 4: AVG SESSION TIME
                        with ui.card().classes('flex-1 min-w-[150px] p-4 bg-white border border-slate-100 rounded-xl shadow-xs border-l-4 border-l-indigo-500 relative overflow-hidden hover:shadow-md hover:scale-[1.02] cursor-pointer transition-all duration-300'):
                            with ui.row().classes('w-full justify-between items-center no-wrap'):
                                ui.label('AVG SESSION TIME').classes('rp-kpi-label')
                                render_kpi_info_icon('avg_session_time')
                            with ui.row().classes('items-baseline gap-0.5 mt-1'):
                                ui.label(f"{avg_session_min:.1f}").classes('rp-kpi-value')
                                ui.label('m').classes('rp-kpi-sub font-bold')
                            ui.label('Per session').classes('rp-kpi-sub mt-1')
                            
                        # Card 5: KEY EVENTS
                        with ui.card().classes('flex-1 min-w-[150px] p-4 bg-white border border-slate-100 rounded-xl shadow-xs border-l-4 border-l-amber-500 relative overflow-hidden hover:shadow-md hover:scale-[1.02] cursor-pointer transition-all duration-300'):
                            with ui.row().classes('w-full justify-between items-center no-wrap'):
                                ui.label('KEY EVENTS').classes('rp-kpi-label')
                                render_kpi_info_icon('key_events')
                            ui.label(f"{total_key_events:,}").classes('rp-kpi-value mt-1')
                            ui.label('Core actions taken').classes('rp-kpi-sub mt-1')
                            
                        # Card 6: ACTIVE DAYS
                        with ui.card().classes('flex-1 min-w-[150px] p-4 bg-white border border-slate-100 rounded-xl shadow-xs border-l-4 border-l-blue-500 relative overflow-hidden hover:shadow-md hover:scale-[1.02] cursor-pointer transition-all duration-300'):
                            with ui.row().classes('w-full justify-between items-center no-wrap'):
                                ui.label('ACTIVE DAYS').classes('rp-kpi-label')
                                render_kpi_info_icon('active_days')
                            ui.label(f"{active_days:,}").classes('rp-kpi-value mt-1')
                            ui.label('Days with sessions').classes('rp-kpi-sub mt-1')

                    # Beautiful Charts Grid below KPI cards (Daily Active Users & Sessions + Session Device Split donut chart)
                    with ui.grid(columns=5).classes('w-full gap-6 mt-6 items-stretch'):
                        
                        # Left card: Daily Active Users & Sessions (3/5 width on desktop)
                        with ui.card().classes('col-span-3 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden'):
                            with ui.row().classes('w-full items-start justify-between mb-1'):
                                render_chart_header('Daily Active Users & Sessions', 'daily_active_users_sessions_port', True, lambda: ui.run_javascript(f"downloadChart('{daily_trend_chart_el.id}', 'Daily Active Users and Sessions')"), daily_trend_df)
                            ui.label('From daily_organization_metrics — active_users + sessions by date').classes('rp-card-sub mb-4')
                            
                            # Format daily trend data for highcharts/echarts
                            x_data = []
                            users_data = []
                            sessions_data = []
                            if not daily_trend_df.empty:
                                # Ensure date sorting is correct
                                trend_sorted = daily_trend_df.sort_values('date', ascending=True)
                                for _, trend_row in trend_sorted.iterrows():
                                    dt = pd.to_datetime(trend_row['date'])
                                    x_data.append(dt.strftime('%b %d') if pd.notna(dt) else '')
                                    users_data.append(int(trend_row['active_users']) if pd.notna(trend_row['active_users']) else 0)
                                    sessions_data.append(int(trend_row['sessions']) if pd.notna(trend_row['sessions']) else 0)
                            else:
                                x_data = ['']
                                users_data = [0]
                                sessions_data = [0]

                            echart_options = {
                                'tooltip': {
                                    'trigger': 'axis',
                                    'axisPointer': {'type': 'cross'}
                                },
                                'legend': {
                                    'data': ['Active Users', 'Sessions'],
                                    'bottom': 0,
                                    'icon': 'circle',
                                    'textStyle': {'color': '#64748b', 'fontSize': 11}
                                },
                                'grid': {
                                    'left': '3%',
                                    'right': '4%',
                                    'top': '10%',
                                    'bottom': '15%',
                                    'containLabel': True
                                },
                                'xAxis': {
                                    'type': 'category',
                                    'boundaryGap': False,
                                    'data': x_data,
                                    'axisLabel': {'color': '#64748b', 'fontSize': 10},
                                    'axisLine': {'lineStyle': {'color': '#e2e8f0'}}
                                },
                                'yAxis': {
                                    'type': 'value',
                                    'axisLabel': {'color': '#64748b', 'fontSize': 10},
                                    'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                                },
                                'series': [
                                    {
                                        'name': 'Active Users',
                                        'type': 'line',
                                        'data': users_data,
                                        'smooth': True,
                                        'itemStyle': {'color': '#3b82f6'},
                                        'lineStyle': {'width': 3, 'type': 'solid'},
                                        'symbol': 'circle',
                                        'symbolSize': 8,
                                        'areaStyle': {'color': {
                                            'type': 'linear',
                                            'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                                            'colorStops': [
                                                {'offset': 0, 'color': 'rgba(59, 130, 246, 0.15)'},
                                                {'offset': 1, 'color': 'rgba(59, 130, 246, 0.01)'}
                                            ]
                                        }}
                                    },
                                    {
                                        'name': 'Sessions',
                                        'type': 'line',
                                        'data': sessions_data,
                                        'smooth': True,
                                        'itemStyle': {'color': '#0d9488'},
                                        'lineStyle': {'width': 2.5, 'type': 'dashed'},
                                        'symbol': 'circle',
                                        'symbolSize': 8,
                                        'areaStyle': {'color': {
                                            'type': 'linear',
                                            'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                                            'colorStops': [
                                                {'offset': 0, 'color': 'rgba(13, 148, 136, 0.12)'},
                                                {'offset': 1, 'color': 'rgba(13, 148, 136, 0.01)'}
                                            ]
                                        }}
                                    }
                                ]
                            }
                            daily_trend_chart_el = ui.echart(echart_options).classes('w-full h-80')

                        # Right card: Session Device Split (2/5 width on desktop)
                        with ui.card().classes('col-span-2 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden justify-between h-full flex-grow'):
                            with ui.row().classes('w-full items-start justify-between mb-1'):
                                render_chart_header('Session Device Split', 'session_device_split_port', True, lambda: ui.run_javascript(f"downloadChart('{device_donut_chart_el.id}', 'Session Device Split')"), device_df)
                            ui.label('From daily_session_metrics — device_category').classes('text-[11px] text-slate-400 mb-4')
                            
                            # Donut chart + Legend side-by-side row
                            with ui.row().classes('w-full items-center justify-between gap-4 flex-grow my-auto'):
                                donut_data = []
                                device_pcts = {}
                                colors_map = {'desktop': '#3b82f6', 'mobile': '#6366f1', 'tablet': '#14b8a6', 'other': '#94a3b8'}
                                device_colors = []
                                
                                if not device_df.empty:
                                    for _, dev_row in device_df.iterrows():
                                        cat = str(dev_row['device_category']).capitalize()
                                        raw_cat = str(dev_row['device_category']).lower()
                                        pct = float(dev_row['pct']) if pd.notna(dev_row['pct']) else 0.0
                                        donut_data.append({'value': pct, 'name': cat})
                                        device_pcts[cat] = pct
                                        device_colors.append(colors_map.get(raw_cat, '#94a3b8'))
                                else:
                                    donut_data = [{'value': 100.0, 'name': 'No Data'}]
                                    device_colors = ['#cbd5e1']
                                    device_pcts = {'No Data': 0.0}

                                donut_options = {
                                    'tooltip': {'trigger': 'item', 'formatter': '{b}: {c}%'},
                                    'series': [{
                                        'type': 'pie',
                                        'radius': ['55%', '80%'],
                                        'avoidLabelOverlap': False,
                                        'label': {'show': False},
                                        'emphasis': {
                                            'label': {'show': False}
                                        },
                                        'labelLine': {'show': False},
                                        'data': donut_data,
                                        'color': device_colors
                                    }]
                                }
                                
                                # Donut echart on the left (50% width) - taller h-64 to fill empty spaces!
                                with ui.element('div').classes('w-[50%] h-64 flex items-center justify-center'):
                                    device_donut_chart_el = ui.echart(donut_options).classes('w-full h-full')
                                
                                # Legend list on the right (45% width) - spaced out nicely to balance the chart height
                                with ui.column().classes('w-[45%] gap-4 text-sm text-slate-500 py-4'):
                                    for dev_name, pct_val in device_pcts.items():
                                        dev_color = colors_map.get(dev_name.lower(), '#94a3b8')
                                        with ui.row().classes('w-full items-center justify-between'):
                                            with ui.row().classes('items-center gap-2'):
                                                ui.element('span').classes('w-3 h-3 rounded-full').style(f'background-color: {dev_color}')
                                                ui.label(dev_name).classes('font-semibold text-slate-700 text-sm')
                                            ui.label(f"{pct_val:.0f}%" if pct_val > 0 else '0%').classes('font-bold text-slate-800 text-sm')

                    # Beautiful Charts Grid below Platform Engagement KPI cards (Day-of-Week + Top Traffic Sources progress bar list)
                    with ui.grid(columns=5).classes('w-full gap-6 mt-6 items-stretch'):
                        
                        # Left card: Day-of-Week Engagement Pattern (3/5 width on desktop)
                        with ui.card().classes('col-span-3 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden'):
                            with ui.row().classes('w-full items-start justify-between mb-1'):
                                render_chart_header('Day-of-Week Engagement Pattern', 'day_of_week_engagement_port', True, lambda: ui.run_javascript(f"downloadChart('{weekly_pattern_chart_el.id}', 'Day of Week Engagement Pattern')"), weekly_pattern_df)
                            ui.label('daily_organization_metrics — AVG(active_users) BY DAYOFWEEK(date)').classes('rp-card-sub mb-4')
                            
                            # Format daily trend data for highcharts/echarts
                            day_names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
                            weekly_users = [0.0] * 7
                            if not weekly_pattern_df.empty:
                                for _, wp_row in weekly_pattern_df.iterrows():
                                    dow = int(wp_row['day_of_week'])
                                    val = float(wp_row['avg_active_users']) if pd.notna(wp_row['avg_active_users']) else 0.0
                                    # Standard DuckDB returns 1 (Sunday) to 7 (Saturday)
                                    idx = dow - 1
                                    if 0 <= idx < 7:
                                        weekly_users[idx] = val

                            # Custom series coloring as shown in the mockup
                            bar_colors = [
                                'rgba(13, 148, 136, 0.3)', # Sun: light
                                '#0d9488',                  # Mon: dark
                                '#0d9488',                  # Tue: dark
                                '#0d9488',                  # Wed: dark
                                '#0d9488',                  # Thu: dark
                                'rgba(13, 148, 136, 0.6)', # Fri: medium-light
                                'rgba(13, 148, 136, 0.3)'  # Sat: light
                            ]
                            
                            series_data = []
                            for i in range(7):
                                series_data.append({
                                    'value': weekly_users[i],
                                    'itemStyle': {'color': bar_colors[i]}
                                })

                            weekly_chart_options = {
                                'tooltip': {
                                    'trigger': 'axis',
                                    'formatter': '{b}: {c} avg users'
                                },
                                'grid': {
                                    'left': '4%',
                                    'right': '4%',
                                    'top': '10%',
                                    'bottom': '12%',
                                    'containLabel': True
                                },
                                'xAxis': {
                                    'type': 'category',
                                    'data': day_names,
                                    'axisLabel': {'color': '#64748b', 'fontSize': 10},
                                    'axisLine': {'lineStyle': {'color': '#e2e8f0'}}
                                },
                                'yAxis': {
                                    'type': 'value',
                                    'axisLabel': {'color': '#64748b', 'fontSize': 10},
                                    'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                                },
                                'series': [{
                                    'type': 'bar',
                                    'barWidth': '55%',
                                    'data': series_data,
                                    'itemStyle': {
                                        'borderRadius': [4, 4, 0, 0]
                                    }
                                }]
                            }
                            weekly_pattern_chart_el = ui.echart(weekly_chart_options).classes('w-full h-80')

                        # Right card: Top Traffic Sources (2/5 width on desktop)
                        with ui.card().classes('col-span-2 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden'):
                            with ui.row().classes('w-full items-start justify-between mb-1'):
                                render_chart_header('Top Traffic Sources', 'top_traffic_sources_port', True, lambda: _download_csv_helper(traffic_source_df, 'Top Traffic Sources'), traffic_source_df)
                            ui.label('daily_session_metrics — session_traffic_source, session_traffic_medium GROUP BY source, medium').classes('rp-card-sub mb-4')
                            
                            # Fetch and sort data
                            traffic_list = []
                            max_sess = 1
                            if not traffic_source_df.empty:
                                for _, t_row in traffic_source_df.iterrows():
                                    src = str(t_row['source'])
                                    med = str(t_row['medium'])
                                    sess = int(t_row['sessions']) if pd.notna(t_row['sessions']) else 0
                                    traffic_list.append({'source': src, 'medium': med, 'sessions': sess})
                                max_sess = max([t['sessions'] for t in traffic_list]) if traffic_list else 1
                            
                            # Row-by-row colors matching the mockup
                            row_colors = [
                                '#2563eb', # 1. Direct: blue-600
                                '#0d9488', # 2. Webmail: teal-600
                                '#15803d', # 3. Google: green-700
                                '#b45309', # 4. RegTech: brown/orange
                                '#7c3aed', # 5. newsletter: purple
                            ]

                            with ui.column().classes('w-full gap-4 mt-2'):
                                if traffic_list:
                                    for idx, item in enumerate(traffic_list[:5]):
                                        src = item['source']
                                        sess = item['sessions']
                                        pct = (sess / max_sess) * 100
                                        color = row_colors[idx] if idx < len(row_colors) else '#64748b'
                                        
                                        # Limit source length nicely
                                        src_display = src if len(src) <= 22 else f"{src[:19]}..."
                                        
                                        with ui.row().classes('w-full items-center justify-between text-xs py-0.5 flex-nowrap'):
                                            # Left label
                                            ui.label(src_display).classes('w-[32%] font-semibold text-slate-700 text-left truncate whitespace-nowrap').tooltip(src)
                                            
                                            # Center progress track
                                            with ui.element('div').classes('w-[53%] h-2 bg-slate-100 rounded-full overflow-hidden relative'):
                                                ui.element('div').classes('h-full rounded-full transition-all duration-500').style(f'width: {pct}%; background-color: {color}')
                                            
                                            # Right value
                                            ui.label(f"{sess:,}").classes('w-[12%] font-bold text-slate-600 text-right whitespace-nowrap')
                                else:
                                    with ui.row().classes('w-full justify-center py-10'):
                                        ui.label('No traffic source data available').classes('text-slate-400 italic text-xs')

    

                    # Render Subtitle block for FEATURE & MODULE ADOPTION with an elegant separator line
                    with ui.row().classes('w-full items-center gap-2 mb-4 mt-8'):
                        with ui.element('div').classes('p-2 bg-slate-50 border border-slate-100 rounded-lg flex items-center justify-center shadow-xs'):
                            ui.icon('apps', size='16px').classes('text-indigo-500')
                        ui.label('FEATURE & MODULE ADOPTION').classes('text-[11px] font-extrabold text-slate-400 tracking-wider')
                        ui.element('div').classes('flex-grow h-px bg-slate-200/60 ml-2')

                    # 2-column grid layout for Feature Adoption
                    with ui.grid(columns=5).classes('w-full gap-6 items-stretch'):
                        
                        # Left card: Module Usage by Action Count (2/5 width on desktop)
                        with ui.card().classes('col-span-2 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden'):
                            with ui.column().classes('w-full gap-1 mb-4'):
                                ui.label('Module Usage by Action Count').classes('text-base font-bold text-slate-800 tracking-tight')
                                ui.label('From regport_audit_trails — GROUP BY module').classes('text-[11px] text-slate-400')
                            
                            if not module_usage_df.empty:
                                max_actions = module_usage_df['total_actions'].max() or 1
                                # Elegant mapping of module names to premium colors
                                color_map = {
                                    'transaction monitoring': '#3b82f6',
                                    'reports': '#10b981',
                                    'customer verification': '#22c55e',
                                    'cdd screening': '#f97316',
                                    'cases': '#a855f7',
                                    'batch upload': '#6366f1',
                                    'monitoring rules': '#ef4444',
                                    'audit trail': '#64748b',
                                    'team management': '#0ea5e9',
                                    'regulatory setup': '#ec4899'
                                }
                                
                                with ui.column().classes('w-full gap-3 mt-2'):
                                    for _, m_row in module_usage_df.iterrows():
                                        mod_name = str(m_row['module'])
                                        actions_cnt = int(m_row['total_actions'])
                                        pct = (actions_cnt / max_actions) * 100
                                        
                                        # Match color
                                        bar_color = color_map.get(mod_name.lower(), '#94a3b8')
                                        
                                        with ui.row().classes('w-full items-center justify-between flex-nowrap gap-4 text-xs py-0.5'):
                                            # Left: Label
                                            ui.label(mod_name).classes('w-[140px] shrink-0 font-medium text-slate-700 truncate').tooltip(mod_name)
                                            
                                            # Center: Custom Horizontal Progress Bar with rounded background
                                            with ui.element('div').classes('grow h-2 bg-slate-100 rounded-full overflow-hidden relative'):
                                                ui.element('span').classes('absolute left-0 top-0 h-full rounded-full').style(f'width: {pct}%; background-color: {bar_color};')
                                            
                                            # Right: Value
                                            ui.label(f"{actions_cnt:,}").classes('w-[50px] shrink-0 font-bold text-slate-600 text-right')
                            else:
                                with ui.row().classes('w-full justify-center py-12'):
                                    ui.label('No module usage data found').classes('text-slate-400 italic text-xs')

                        # Right card: Action Type Breakdown (3/5 width on desktop)
                        with ui.card().classes('col-span-3 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden'):
                            with ui.column().classes('w-full gap-1 mb-4'):
                                ui.label('Action Type Breakdown').classes('text-base font-bold text-slate-800 tracking-tight')
                                ui.label('From regport_audit_trails — GROUP BY actionType').classes('text-[11px] text-slate-400')
                            
                            categories = []
                            series_data = []
                            action_color_map = {
                                'txn monitoring': '#3b82f6',
                                'batch upload': '#3b82f6',
                                'cdd screening': '#3b82f6',
                                'reports': '#10b981',
                                'cases': '#10b981',
                                'verification': '#10b981',
                                'rules mgmt': '#f59e0b',
                                'team mgmt': '#f59e0b',
                                'support': '#ef4444',
                                'wallet': '#ef4444'
                            }
                            
                            if not action_type_df.empty:
                                for _, act_row in action_type_df.iterrows():
                                    act_name = str(act_row['actionType'])
                                    act_count = int(act_row['action_count'])
                                    categories.append(act_name)
                                    
                                    # Determine color
                                    b_color = action_color_map.get(act_name.lower(), '#3b82f6')
                                    series_data.append({
                                        'value': act_count,
                                        'itemStyle': {'color': b_color, 'borderRadius': [0, 4, 4, 0]}
                                    })
                            else:
                                categories = ['']
                                series_data = [0]
                                
                            action_chart_options = {
                                'tooltip': {
                                    'trigger': 'axis',
                                    'axisPointer': {'type': 'shadow'}
                                },
                                'grid': {
                                    'left': '3%',
                                    'right': '4%',
                                    'top': '2%',
                                    'bottom': '2%',
                                    'containLabel': True
                                },
                                'xAxis': {
                                    'type': 'value',
                                    'axisLabel': {'color': '#64748b', 'fontSize': 10},
                                    'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                                },
                                'yAxis': {
                                    'type': 'category',
                                    'data': categories,
                                    'inverse': True,  # Keep top values at the top of the chart!
                                    'axisLabel': {'color': '#64748b', 'fontSize': 10},
                                    'axisLine': {'lineStyle': {'color': '#e2e8f0'}}
                                },
                                'series': [{
                                    'type': 'bar',
                                    'data': series_data,
                                    'barWidth': '50%'
                                }]
                            }
                            ui.echart(action_chart_options).classes('w-full h-80')

                    # Row 2 grid layout for Feature Adoption Heatmap & Timeline
                    with ui.grid(columns=5).classes('w-full gap-6 mt-6 items-stretch'):
                        
                        # Left card: Weekly Module Activity Heatmap (2/5 width on desktop)
                        with ui.card().classes('col-span-2 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden'):
                            with ui.column().classes('w-full gap-1 mb-4'):
                                ui.label('Weekly Module Activity Heatmap').classes('text-base font-bold text-slate-800 tracking-tight')
                                ui.label('From regport_audit_trails — DAYOFWEEK × HOUR(createdAt)').classes('text-[11px] text-slate-400')
                            
                            heatmap_data = []
                            max_hm_count = 0
                            slots = {}
                            for d in range(7):
                                for h in range(24):
                                    slots[(d, h)] = 0
                                    
                            if not heatmap_df.empty:
                                for _, hm_row in heatmap_df.iterrows():
                                    d_val = int(hm_row['day_of_week'])
                                    h_val = int(hm_row['hour_of_day'])
                                    c_val = int(hm_row['action_count'])
                                    slots[(d_val, h_val)] = c_val
                                    if c_val > max_hm_count:
                                        max_hm_count = c_val
                                        
                            for (d_val, h_val), c_val in slots.items():
                                heatmap_data.append([h_val, d_val, c_val])
                                
                            hours_axis = [str(h) for h in range(24)]
                            days_axis = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
                            
                            heatmap_options = {
                                'tooltip': {
                                    'position': 'top',
                                    'formatter': '{b} Day, {c} Hour: {d} Actions'
                                },
                                'grid': {
                                    'height': '65%',
                                    'top': '5%',
                                    'bottom': '20%',
                                    'left': '10%',
                                    'right': '5%'
                                },
                                'xAxis': {
                                    'type': 'category',
                                    'data': hours_axis,
                                    'splitArea': {'show': True},
                                    'axisLabel': {'interval': 2, 'color': '#64748b', 'fontSize': 9}
                                },
                                'yAxis': {
                                    'type': 'category',
                                    'data': days_axis,
                                    'splitArea': {'show': True},
                                    'axisLabel': {'color': '#64748b', 'fontSize': 9}
                                },
                                'visualMap': {
                                    'min': 0,
                                    'max': max(max_hm_count, 10),
                                    'calculable': True,
                                    'orient': 'horizontal',
                                    'left': 'center',
                                    'bottom': '0%',
                                    'itemWidth': 12,
                                    'itemHeight': 120,
                                    'inRange': {
                                        'color': ['#ede9fe', '#3b82f6', '#ef4444'] # Lavender to Blue to Red
                                    },
                                    'textStyle': {'color': '#64748b', 'fontSize': 10}
                                },
                                'series': [{
                                    'name': 'Activity Count',
                                    'type': 'heatmap',
                                    'data': heatmap_data,
                                    'label': {'show': False},
                                    'emphasis': {
                                        'itemStyle': {
                                            'shadowBlur': 10,
                                            'shadowColor': 'rgba(0, 0, 0, 0.3)'
                                        }
                                    }
                                }]
                            }
                            ui.echart(heatmap_options).classes('w-full h-80')

                        # Right card: Audit Activity Over Time (3/5 width on desktop)
                        with ui.card().classes('col-span-3 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden'):
                            with ui.column().classes('w-full gap-1 mb-4'):
                                ui.label('Audit Activity Over Time').classes('text-base font-bold text-slate-800 tracking-tight')
                                ui.label('From regport_audit_trails — daily action + user count').classes('text-[11px] text-slate-400')
                            
                            timeline_dates = []
                            timeline_actions = []
                            timeline_users = []
                            if not audit_timeline_df.empty:
                                timeline_sorted = audit_timeline_df.sort_values('action_date', ascending=True)
                                for _, tl_row in timeline_sorted.iterrows():
                                    dt = pd.to_datetime(tl_row['action_date'])
                                    timeline_dates.append(dt.strftime('%b %d') if pd.notna(dt) else '')
                                    timeline_actions.append(int(tl_row['actions']) if pd.notna(tl_row['actions']) else 0)
                                    timeline_users.append(int(tl_row['distinct_users']) if pd.notna(tl_row['distinct_users']) else 0)
                            else:
                                timeline_dates = ['']
                                timeline_actions = [0]
                                timeline_users = [0]

                            timeline_options = {
                                'tooltip': {
                                    'trigger': 'axis',
                                    'axisPointer': {'type': 'cross'}
                                },
                                'legend': {
                                    'data': ['Actions', 'Users'],
                                    'right': '10%',
                                    'top': '0%',
                                    'icon': 'rect',
                                    'textStyle': {'color': '#64748b', 'fontSize': 11}
                                },
                                'grid': {
                                    'left': '5%',
                                    'right': '5%',
                                    'top': '12%',
                                    'bottom': '12%',
                                    'containLabel': True
                                },
                                'xAxis': {
                                    'type': 'category',
                                    'boundaryGap': False,
                                    'data': timeline_dates,
                                    'axisLabel': {'color': '#64748b', 'fontSize': 10},
                                    'axisLine': {'lineStyle': {'color': '#e2e8f0'}}
                                },
                                'yAxis': [
                                    {
                                        'type': 'value',
                                        'name': 'Actions',
                                        'nameTextStyle': {'color': '#64748b', 'fontSize': 10},
                                        'axisLabel': {'color': '#64748b', 'fontSize': 10},
                                        'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                                    },
                                    {
                                        'type': 'value',
                                        'name': 'Users',
                                        'nameTextStyle': {'color': '#64748b', 'fontSize': 10},
                                        'axisLabel': {'color': '#64748b', 'fontSize': 10},
                                        'splitLine': {'show': False}
                                    }
                                ],
                                'series': [
                                    {
                                        'name': 'Actions',
                                        'type': 'line',
                                        'data': timeline_actions,
                                        'smooth': True,
                                        'yAxisIndex': 0,
                                        'itemStyle': {'color': '#a855f7'}, # Purple
                                        'lineStyle': {'width': 3, 'type': 'solid'},
                                        'symbol': 'circle',
                                        'symbolSize': 8,
                                        'areaStyle': {'color': {
                                            'type': 'linear',
                                            'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                                            'colorStops': [
                                                {'offset': 0, 'color': 'rgba(168, 85, 247, 0.12)'},
                                                {'offset': 1, 'color': 'rgba(168, 85, 247, 0.01)'}
                                            ]
                                        }}
                                    },
                                    {
                                        'name': 'Users',
                                        'type': 'line',
                                        'data': timeline_users,
                                        'smooth': True,
                                        'yAxisIndex': 1,
                                        'itemStyle': {'color': '#f59e0b'}, # Amber
                                        'lineStyle': {'width': 2.5, 'type': 'dashed'},
                                        'symbol': 'circle',
                                        'symbolSize': 8
                                    }
                                ]
                            }
                            ui.echart(timeline_options).classes('w-full h-80')

                    # Render Subtitle block for OPERATIONAL ACTIVITY with an elegant separator line
                    with ui.row().classes('w-full items-center gap-2 mb-4 mt-6'):
                        with ui.element('div').classes('p-2 bg-white border border-slate-100 rounded-lg flex items-center justify-center shadow-xs'):
                            ui.icon('compare_arrows', size='16px').classes('text-blue-500')
                        ui.label('OPERATIONAL ACTIVITY').classes('text-[11px] font-extrabold text-slate-400 tracking-wider')
                        ui.element('div').classes('flex-grow h-px bg-slate-200/60 ml-2')

                    # 6 Premium Interactive Vertical KPI Cards for Operational Activity
                    with ui.row().classes('w-full justify-between items-stretch flex-wrap gap-4'):
                        
                        # Card 1: TOTAL TRANSACTIONS
                        with ui.card().classes('flex-1 min-w-[150px] p-4 bg-white border border-slate-100 rounded-xl shadow-xs border-l-4 border-l-blue-500 relative overflow-hidden hover:shadow-md hover:scale-[1.02] cursor-pointer transition-all duration-300'):
                            ui.label('TOTAL TRANSACTIONS').classes('text-[9px] font-bold text-slate-400 tracking-wider')
                            ui.label(f"{total_txns:,}").classes('text-2xl font-extrabold text-slate-800 mt-1')
                            ui.label('In date range').classes('text-[11px] text-slate-400 mt-1')
                        
                        # Card 2: FLAGGED TXNS
                        with ui.card().classes('flex-1 min-w-[150px] p-4 bg-white border border-slate-100 rounded-xl shadow-xs border-l-4 border-l-rose-500 relative overflow-hidden hover:shadow-md hover:scale-[1.02] cursor-pointer transition-all duration-300'):
                            ui.label('FLAGGED TXNS').classes('text-[9px] font-bold text-slate-400 tracking-wider')
                            ui.label(f"{flagged_txns:,}").classes('text-2xl font-extrabold text-slate-800 mt-1')
                            with ui.row().classes('items-center gap-1 mt-1 text-[11px]'):
                                ui.label(f"{flag_rate_pct:.2f}%").classes('font-bold text-rose-500')
                                ui.label('flag rate').classes('text-slate-400')
                            
                        # Card 3: MONITORED ACCOUNTS
                        with ui.card().classes('flex-1 min-w-[150px] p-4 bg-white border border-slate-100 rounded-xl shadow-xs border-l-4 border-l-teal-500 relative overflow-hidden hover:shadow-md hover:scale-[1.02] cursor-pointer transition-all duration-300'):
                            ui.label('MONITORED ACCOUNTS').classes('text-[9px] font-bold text-slate-400 tracking-wider')
                            ui.label(f"{total_monitored:,}").classes('text-2xl font-extrabold text-slate-800 mt-1')
                            ui.label(f"{new_monitored} new · {review_monitored} under review · {closed_monitored} closed").classes('text-[11px] text-slate-400 mt-1')
                            
                        # Card 4: KYC/KYB CHECKS
                        with ui.card().classes('flex-1 min-w-[150px] p-4 bg-white border border-slate-100 rounded-xl shadow-xs border-l-4 border-l-emerald-500 relative overflow-hidden hover:shadow-md hover:scale-[1.02] cursor-pointer transition-all duration-300'):
                            ui.label('KYC/KYB CHECKS').classes('text-[9px] font-bold text-slate-400 tracking-wider')
                            ui.label(f"{total_checks:,}").classes('text-2xl font-extrabold text-slate-800 mt-1')
                            ui.label('Verifications run').classes('text-[11px] text-slate-400 mt-1')
                            
                        # Card 5: CDD SCREENINGS
                        with ui.card().classes('flex-1 min-w-[150px] p-4 bg-white border border-slate-100 rounded-xl shadow-xs border-l-4 border-l-amber-500 relative overflow-hidden hover:shadow-md hover:scale-[1.02] cursor-pointer transition-all duration-300'):
                            ui.label('CDD SCREENINGS').classes('text-[9px] font-bold text-slate-400 tracking-wider')
                            ui.label(f"{total_screenings:,}").classes('text-2xl font-extrabold text-slate-800 mt-1')
                            with ui.row().classes('items-center gap-1 mt-1 text-[11px]'):
                                ui.label(f"{screening_match_pct:.1f}%").classes('font-bold text-amber-500')
                                ui.label('match rate').classes('text-slate-400')
                            
                        # Card 6: BATCH UPLOADS
                        with ui.card().classes('flex-1 min-w-[150px] p-4 bg-white border border-slate-100 rounded-xl shadow-xs border-l-4 border-l-purple-500 relative overflow-hidden hover:shadow-md hover:scale-[1.02] cursor-pointer transition-all duration-300'):
                            ui.label('BATCH UPLOADS').classes('text-[9px] font-bold text-slate-400 tracking-wider')
                            ui.label(f"{total_uploads:,}").classes('text-2xl font-extrabold text-slate-800 mt-1')
                            with ui.row().classes('items-center gap-1 mt-1 text-[11px]'):
                                ui.label(f"{upload_error_pct:.1f}%").classes('font-bold text-purple-500')
                                ui.label('error rate').classes('text-slate-400')

                    # Format daily trend data for transactions
                    x_txn_data = []
                    total_txn_data = []
                    flagged_txn_data = []
                    if not txn_trend_df.empty:
                        trend_sorted = txn_trend_df.sort_values('txn_date', ascending=True)
                        for _, trend_row in trend_sorted.iterrows():
                            dt = pd.to_datetime(trend_row['txn_date'])
                            x_txn_data.append(dt.strftime('%b %d') if pd.notna(dt) else '')
                            total_txn_data.append(int(trend_row['txn_count']) if pd.notna(trend_row['txn_count']) else 0)
                            flagged_txn_data.append(int(trend_row['flagged_count']) if pd.notna(trend_row['flagged_count']) else 0)
                    else:
                        x_txn_data = ['']
                        total_txn_data = [0]
                        flagged_txn_data = [0]

                    # Format transaction type split data
                    split_data = []
                    total_txns_sum = txn_split_df['count'].sum() if not txn_split_df.empty else 0
                    if not txn_split_df.empty and total_txns_sum > 0:
                        for _, split_row in txn_split_df.iterrows():
                            name = str(split_row['transactionType'])
                            count = int(split_row['count'])
                            pct = (count / total_txns_sum) * 100
                            display_name = f"{name.capitalize()}     {pct:.0f}%"
                            color = '#3b82f6' if name.lower() == 'debit' else '#10b981' if name.lower() == 'credit' else '#ef4444'
                            split_data.append({
                                'name': display_name,
                                'value': count,
                                'itemStyle': {'color': color}
                            })
                    else:
                        split_data = [
                            {'name': 'Debit     0%', 'value': 0, 'itemStyle': {'color': '#3b82f6'}},
                            {'name': 'Credit    0%', 'value': 0, 'itemStyle': {'color': '#10b981'}}
                        ]

                    # 1. Format daily verification trend data (stacked bar chart: KYC & KYB)
                    x_verify_dates = []
                    kyc_counts = []
                    kyb_counts = []
                    if not verification_df.empty:
                        verification_df['check_date_parsed'] = pd.to_datetime(verification_df['check_date'])
                        verify_pivoted = verification_df.pivot_table(
                            index='check_date_parsed',
                            columns='verificationType',
                            values='checks',
                            aggfunc='sum'
                        ).fillna(0).reset_index()
                        
                        verify_sorted = verify_pivoted.sort_values('check_date_parsed', ascending=True)
                        for _, v_row in verify_sorted.iterrows():
                            dt = v_row['check_date_parsed']
                            x_verify_dates.append(dt.strftime('%b %d') if pd.notna(dt) else '')
                            kyc_val = int(v_row.get('kyc', 0)) if 'kyc' in v_row else 0
                            kyb_val = int(v_row.get('kyb', 0)) if 'kyb' in v_row else 0
                            kyc_counts.append(kyc_val)
                            kyb_counts.append(kyb_val)
                    else:
                        x_verify_dates = ['']
                        kyc_counts = [0]
                        kyb_counts = [0]

                    # 2. Format rules by code split data
                    rules_split_data = []
                    total_rules_sum = rules_df['rule_count'].sum() if not rules_df.empty else 0
                    if not rules_df.empty and total_rules_sum > 0:
                        for _, r_row in rules_df.iterrows():
                            code = str(r_row['ruleCode'])
                            count = int(r_row['rule_count'])
                            pct = (count / total_rules_sum) * 100
                            disp_name = f"{code}     {pct:.0f}%"
                            rules_split_data.append({
                                'name': disp_name,
                                'value': count
                            })
                    else:
                        rules_split_data = [
                            {'name': 'No Rules Configured', 'value': 0}
                        ]

                    # 3. Format monitored account status distribution data (bar chart)
                    new_cnt = 0
                    closed_cnt = 0
                    review_cnt = 0
                    if not monitored_accounts_df.empty:
                        m_row = monitored_accounts_df.iloc[0]
                        new_cnt = int(m_row['new_count']) if pd.notna(m_row['new_count']) else 0
                        closed_cnt = int(m_row['closed_count']) if pd.notna(m_row['closed_count']) else 0
                        review_cnt = int(m_row['review_count']) if pd.notna(m_row['review_count']) else 0

                    # 4. Format batch upload template split data (grouped bar chart)
                    x_templates = []
                    processed_counts = []
                    error_counts = []
                    if not batch_upload_by_template_df.empty:
                        templ_grouped = batch_upload_by_template_df.groupby('template_type').agg({
                            'total_records': 'sum',
                            'total_errors': 'sum',
                            'uploads': 'sum'
                        }).reset_index().sort_values('uploads', ascending=False)
                        
                        for _, tmpl_row in templ_grouped.iterrows():
                            tmpl_name = str(tmpl_row['template_type']).upper()
                            tot_rec = int(tmpl_row['total_records']) if pd.notna(tmpl_row['total_records']) else 0
                            tot_err = int(tmpl_row['total_errors']) if pd.notna(tmpl_row['total_errors']) else 0
                            ok_rec = max(0, tot_rec - tot_err)
                            
                            x_templates.append(tmpl_name)
                            processed_counts.append(ok_rec)
                            error_counts.append(tot_err)
                    else:
                        x_templates = ['CTR', 'STR', 'KYC', 'SAR']
                        processed_counts = [0, 0, 0, 0]
                        error_counts = [0, 0, 0, 0]

                    # Render side-by-side charts for OPERATIONAL ACTIVITY
                    with ui.grid(columns=2).classes('w-full gap-6 mt-6 items-stretch'):
                        
                        # Left card: Transaction Volume Trend
                        with ui.card().classes('p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden'):
                            with ui.column().classes('w-full gap-1 mb-4'):
                                ui.label('Transaction Volume Trend').classes('text-base font-bold text-slate-800 tracking-tight')
                                ui.label('From regport_transactions — daily txn_count + flagged').classes('text-[11px] text-slate-400')
                            
                            txn_trend_options = {
                                'tooltip': {
                                    'trigger': 'axis',
                                    'axisPointer': {'type': 'shadow'}
                                },
                                'legend': {
                                    'data': ['Total', 'Flagged'],
                                    'bottom': 0,
                                    'icon': 'rect',
                                    'textStyle': {'color': '#64748b', 'fontSize': 11}
                                },
                                'grid': {
                                    'left': '3%',
                                    'right': '4%',
                                    'top': '15%',
                                    'bottom': '15%',
                                    'containLabel': True
                                },
                                'xAxis': {
                                    'type': 'category',
                                    'data': x_txn_data,
                                    'axisLabel': {'color': '#64748b', 'fontSize': 10},
                                    'axisLine': {'lineStyle': {'color': '#e2e8f0'}}
                                },
                                'yAxis': {
                                    'type': 'value',
                                    'axisLabel': {'color': '#64748b', 'fontSize': 10},
                                    'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                                },
                                'series': [
                                    {
                                        'name': 'Total',
                                        'type': 'bar',
                                        'data': total_txn_data,
                                        'itemStyle': {'color': '#3b82f6', 'borderRadius': [4, 4, 0, 0]}
                                    },
                                    {
                                        'name': 'Flagged',
                                        'type': 'bar',
                                        'data': flagged_txn_data,
                                        'itemStyle': {'color': '#ef4444', 'borderRadius': [4, 4, 0, 0]}
                                    }
                                ]
                            }
                            ui.echart(txn_trend_options).classes('w-full h-80')
                            
                        # Right card: Transaction Type Split
                        with ui.card().classes('p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden'):
                            with ui.column().classes('w-full gap-1 mb-4'):
                                ui.label('Transaction Type Split').classes('text-base font-bold text-slate-800 tracking-tight')
                                ui.label('From regport_transactions — transactionType').classes('text-[11px] text-slate-400')
                            
                            txn_split_options = {
                                'tooltip': {
                                    'trigger': 'item',
                                    'formatter': '{b}: {c} ({d}%)'
                                },
                                'legend': {
                                    'orient': 'vertical',
                                    'right': '15%',
                                    'top': 'center',
                                    'icon': 'circle',
                                    'textStyle': {'color': '#64748b', 'fontSize': 12, 'fontFamily': 'monospace'}
                                },
                                'series': [
                                    {
                                        'name': 'Transaction Type',
                                        'type': 'pie',
                                        'radius': ['50%', '75%'],
                                        'center': ['35%', '50%'],
                                        'avoidLabelOverlap': False,
                                        'label': {
                                            'show': False,
                                            'position': 'center'
                                        },
                                        'emphasis': {
                                            'label': {
                                                'show': False
                                            }
                                        },
                                        'labelLine': {
                                            'show': False
                                        },
                                        'data': split_data
                                    }
                                ]
                            }
                            ui.echart(txn_split_options).classes('w-full h-80')

                        # Left card (Row 2): Rules by Code (Pie chart)
                        with ui.card().classes('p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden'):
                            with ui.column().classes('w-full gap-1 mb-4'):
                                ui.label('Rules by Code').classes('text-base font-bold text-slate-800 tracking-tight')
                                ui.label('From regport_rules — ruleCode').classes('text-[11px] text-slate-400')
                            
                            rules_pie_options = {
                                'tooltip': {
                                    'trigger': 'item',
                                    'formatter': '{b}: {c} ({d}%)'
                                },
                                'legend': {
                                    'orient': 'vertical',
                                    'right': '15%',
                                    'top': 'center',
                                    'icon': 'circle',
                                    'textStyle': {'color': '#64748b', 'fontSize': 12, 'fontFamily': 'monospace'}
                                },
                                'series': [
                                    {
                                        'name': 'Rules',
                                        'type': 'pie',
                                        'radius': ['50%', '75%'],
                                        'center': ['35%', '50%'],
                                        'avoidLabelOverlap': False,
                                        'label': {
                                            'show': False,
                                            'position': 'center'
                                        },
                                        'emphasis': {
                                            'label': {
                                                'show': False
                                            }
                                        },
                                        'labelLine': {
                                            'show': False
                                        },
                                        'data': rules_split_data
                                    }
                                ]
                            }
                            ui.echart(rules_pie_options).classes('w-full h-80')

                        # Right card (Row 2): KYC/KYB Daily Verifications (Stacked Bar chart)
                        with ui.card().classes('p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden'):
                            with ui.column().classes('w-full gap-1 mb-4'):
                                ui.label('KYC/KYB Daily Verifications').classes('text-base font-bold text-slate-800 tracking-tight')
                                ui.label('From regport_verify_customers — by verificationType').classes('text-[11px] text-slate-400')
                            
                            verify_trend_options = {
                                'tooltip': {
                                    'trigger': 'axis',
                                    'axisPointer': {'type': 'shadow'}
                                },
                                'legend': {
                                    'data': ['KYC', 'KYB'],
                                    'top': 0,
                                    'icon': 'rect',
                                    'textStyle': {'color': '#64748b', 'fontSize': 11}
                                },
                                'grid': {
                                    'left': '3%',
                                    'right': '4%',
                                    'top': '15%',
                                    'bottom': '15%',
                                    'containLabel': True
                                },
                                'xAxis': {
                                    'type': 'category',
                                    'data': x_verify_dates,
                                    'axisLabel': {'color': '#64748b', 'fontSize': 10},
                                    'axisLine': {'lineStyle': {'color': '#e2e8f0'}}
                                },
                                'yAxis': {
                                    'type': 'value',
                                    'axisLabel': {'color': '#64748b', 'fontSize': 10},
                                    'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                                },
                                'series': [
                                    {
                                        'name': 'KYC',
                                        'type': 'bar',
                                        'stack': 'verification',
                                        'data': kyc_counts,
                                        'itemStyle': {'color': '#2ec4b6'} # Elegant emerald-teal
                                    },
                                    {
                                        'name': 'KYB',
                                        'type': 'bar',
                                        'stack': 'verification',
                                        'data': kyb_counts,
                                        'itemStyle': {'color': '#b084f4'} # Elegant lavender-purple
                                    }
                                ]
                            }
                            ui.echart(verify_trend_options).classes('w-full h-80')

                        # Left card (Row 3): Monitored Account Status Distribution (Bar chart)
                        with ui.card().classes('p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden'):
                            with ui.column().classes('w-full gap-1 mb-4'):
                                ui.label('Monitored Account Status Distribution').classes('text-base font-bold text-slate-800 tracking-tight')
                                ui.label('From regport_monitored_accounts — monitoredAccountStatus').classes('text-[11px] text-slate-400')
                            
                            monitored_dist_options = {
                                'tooltip': {
                                    'trigger': 'axis',
                                    'axisPointer': {'type': 'shadow'}
                                },
                                'grid': {
                                    'left': '3%',
                                    'right': '4%',
                                    'top': '15%',
                                    'bottom': '15%',
                                    'containLabel': True
                                },
                                'xAxis': {
                                    'type': 'category',
                                    'data': ['New', 'Closed', 'Under Review'],
                                    'axisLabel': {'color': '#64748b', 'fontSize': 10},
                                    'axisLine': {'lineStyle': {'color': '#e2e8f0'}}
                                },
                                'yAxis': {
                                    'type': 'value',
                                    'axisLabel': {'color': '#64748b', 'fontSize': 10},
                                    'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                                },
                                'series': [
                                    {
                                        'type': 'bar',
                                        'barWidth': '40%',
                                        'data': [
                                            {'value': new_cnt, 'itemStyle': {'color': '#2ecc71', 'borderRadius': [4, 4, 0, 0]}},
                                            {'value': closed_cnt, 'itemStyle': {'color': '#34495e', 'borderRadius': [4, 4, 0, 0]}},
                                            {'value': review_cnt, 'itemStyle': {'color': '#f59e0b', 'borderRadius': [4, 4, 0, 0]}}
                                        ]
                                    }
                                ]
                            }
                            ui.echart(monitored_dist_options).classes('w-full h-80')

                        # Right card (Row 3): Batch Upload Performance (Grouped Bar chart)
                        with ui.card().classes('p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden'):
                            with ui.column().classes('w-full gap-1 mb-4'):
                                ui.label('Batch Upload Performance').classes('text-base font-bold text-slate-800 tracking-tight')
                                ui.label('From regport_uploaded_files — by template_type, records processed vs errors').classes('text-[11px] text-slate-400')
                            
                            batch_perf_options = {
                                'tooltip': {
                                    'trigger': 'axis',
                                    'axisPointer': {'type': 'shadow'}
                                },
                                'legend': {
                                    'data': ['Processed OK', 'Errors'],
                                    'top': 0,
                                    'icon': 'rect',
                                    'textStyle': {'color': '#64748b', 'fontSize': 11}
                                },
                                'grid': {
                                    'left': '3%',
                                    'right': '4%',
                                    'top': '15%',
                                    'bottom': '15%',
                                    'containLabel': True
                                },
                                'xAxis': {
                                    'type': 'category',
                                    'data': x_templates,
                                    'axisLabel': {'color': '#64748b', 'fontSize': 10},
                                    'axisLine': {'lineStyle': {'color': '#e2e8f0'}}
                                },
                                'yAxis': {
                                    'type': 'value',
                                    'axisLabel': {'color': '#64748b', 'fontSize': 10},
                                    'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                                },
                                'series': [
                                    {
                                        'name': 'Processed OK',
                                        'type': 'bar',
                                        'data': processed_counts,
                                        'itemStyle': {'color': '#2ecc71', 'borderRadius': [4, 4, 0, 0]}
                                    },
                                    {
                                        'name': 'Errors',
                                        'type': 'bar',
                                        'data': error_counts,
                                        'itemStyle': {'color': '#ef4444', 'borderRadius': [4, 4, 0, 0]}
                                    }
                                ]
                            }
                            ui.echart(batch_perf_options).classes('w-full h-80')

                    # Render Subtitle block for TEAM USAGE with an elegant separator line
                    with ui.row().classes('w-full items-center gap-2 mb-4 mt-8'):
                        with ui.element('div').classes('p-2 bg-white border border-slate-100 rounded-lg flex items-center justify-center shadow-xs'):
                            ui.icon('group', size='16px').classes('text-indigo-500')
                        ui.label('TEAM USAGE').classes('text-[11px] font-extrabold text-slate-400 tracking-wider')
                        ui.element('div').classes('flex-grow h-px bg-slate-200/60 ml-2')

                    # Parse user activity role bar chart data
                    role_names = []
                    role_action_counts = []
                    if not user_activity_role_df.empty:
                        for _, act_row in user_activity_role_df.iterrows():
                            r_name = str(act_row.get('roleName', 'Viewer') or 'Viewer').strip()
                            cnt = int(act_row.get('user_action_count', 0))
                            
                            color = '#f59e0b' # Default Amber/Orange
                            if 'superadmin' in r_name.lower():
                                color = '#a855f7' # Purple
                            elif 'admin' in r_name.lower():
                                color = '#3b82f6' # Blue
                            elif 'viewer' in r_name.lower():
                                color = '#14b8a6' # Teal
                                
                            role_names.append(r_name)
                            role_action_counts.append({
                                'value': cnt,
                                'itemStyle': {'color': color, 'borderRadius': [4, 4, 0, 0]}
                            })
                    else:
                        role_names = ['SuperAdmin', 'Admin', 'Viewer', 'Analyst']
                        role_action_counts = [
                            {'value': 0, 'itemStyle': {'color': '#a855f7', 'borderRadius': [4, 4, 0, 0]}},
                            {'value': 0, 'itemStyle': {'color': '#3b82f6', 'borderRadius': [4, 4, 0, 0]}},
                            {'value': 0, 'itemStyle': {'color': '#14b8a6', 'borderRadius': [4, 4, 0, 0]}},
                            {'value': 0, 'itemStyle': {'color': '#f59e0b', 'borderRadius': [4, 4, 0, 0]}}
                        ]

                    with ui.element('div').classes('grid grid-cols-1 lg:grid-cols-3 w-full gap-6 mt-6 items-stretch'):
                        
                        # Left card: Team Members (2/3 width)
                        with ui.card().classes('col-span-1 lg:col-span-2 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden'):
                            with ui.column().classes('w-full gap-1 mb-4'):
                                ui.label('Team Members').classes('text-base font-bold text-slate-800 tracking-tight')
                                ui.label('From regport_users — isActive, roleName').classes('text-[11px] text-slate-400')
                            
                            columns = [
                                {'name': 'email', 'label': 'EMAIL', 'field': 'email', 'align': 'left', 'sortable': True, 'style': 'width: 35%;'},
                                {'name': 'role', 'label': 'ROLE', 'field': 'role', 'align': 'left', 'sortable': True, 'style': 'width: 22%;'},
                                {'name': 'sub_acct', 'label': 'SUB-ACCT', 'field': 'sub_acct', 'align': 'left', 'sortable': True, 'style': 'width: 13%;'},
                                {'name': 'status', 'label': 'STATUS', 'field': 'status', 'align': 'left', 'sortable': True, 'style': 'width: 15%;'},
                                {'name': 'last_active', 'label': 'LAST ACTIVE', 'field': 'last_active', 'align': 'left', 'sortable': True, 'style': 'width: 15%;'},
                            ]
                            rows = []
                            if not users_df.empty:
                                for _, u_row in users_df.iterrows():
                                    email_val = str(u_row.get('email', ''))
                                    if '@' in email_val:
                                        parts = email_val.split('@')
                                        name_part = parts[0]
                                        domain_part = parts[1]
                                        if len(name_part) <= 2:
                                            display_email = f"{name_part}***@{domain_part}"
                                        else:
                                            display_email = f"{name_part[:2]}***@{domain_part}"
                                    else:
                                        display_email = email_val
                                    
                                    role_val = str(u_row.get('roleName', '') or u_row.get('RoleName', 'Viewer')).strip()
                                    is_sub = str(u_row.get('isSubAccount', ''))
                                    sub_acct_disp = "Yes" if is_sub.lower() in ('true', '1') else "No"
                                    
                                    is_act = str(u_row.get('isActive', ''))
                                    status_disp = "Active" if is_act.lower() in ('true', '1') else "Inactive"
                                    
                                    last_act_raw = u_row.get('lastActive', '')
                                    last_act_disp = "N/A"
                                    if pd.notna(last_act_raw) and last_act_raw:
                                        try:
                                            last_act_disp = pd.to_datetime(last_act_raw).strftime('%Y-%m-%d')
                                        except Exception:
                                            last_act_disp = str(last_act_raw)[:10]
                                    
                                    rows.append({
                                        'email': display_email,
                                        'role': role_val,
                                        'sub_acct': sub_acct_disp,
                                        'status': status_disp,
                                        'last_active': last_act_disp,
                                        'full_email': email_val
                                    })
                            
                            table = ui.table(
                                columns=columns,
                                rows=rows,
                                row_key='email'
                            ).classes('w-full border-none shadow-none bg-transparent my-sticky-header-table')
                            
                            table.add_slot('body-cell-email', '''
                                <q-td :props="props" class="text-xs text-slate-600 font-medium">
                                    <span :title="props.row.full_email">{{ props.value }}</span>
                                </q-td>
                            ''')
                            table.add_slot('body-cell-role', '''
                                <q-td :props="props">
                                    <span v-if="props.value.toLowerCase().includes('superadmin')" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-semibold border text-purple-600 bg-purple-50 border-purple-100">{{ props.value }}</span>
                                    <span v-else-if="props.value.toLowerCase().includes('admin')" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-semibold border text-blue-600 bg-blue-50 border-blue-100">{{ props.value }}</span>
                                    <span v-else-if="props.value.toLowerCase().includes('viewer')" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-semibold border text-teal-600 bg-teal-50 border-teal-100">{{ props.value }}</span>
                                    <span v-else class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-semibold border text-amber-600 bg-amber-50 border-amber-100">{{ props.value }}</span>
                                </q-td>
                            ''')
                            table.add_slot('body-cell-sub_acct', '''
                                <q-td :props="props" class="text-xs text-slate-500 font-medium">
                                    {{ props.value }}
                                </q-td>
                            ''')
                            table.add_slot('body-cell-status', '''
                                <q-td :props="props">
                                    <span v-if="props.value === 'Active'" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-semibold border text-emerald-600 bg-emerald-50 border-emerald-100">{{ props.value }}</span>
                                    <span v-else class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-semibold border text-amber-600 bg-amber-50 border-amber-100">{{ props.value }}</span>
                                </q-td>
                            ''')
                            table.add_slot('body-cell-last_active', '''
                                <q-td :props="props" class="text-xs text-slate-500 font-mono">
                                    {{ props.value }}
                                </q-td>
                            ''')
                            
                            table.props('flat bordered dense hide-pagination :pagination="{rowsPerPage: 0}"')

                        # Right card: User Activity by Role (ECharts Bar Chart)
                        with ui.card().classes('p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden'):
                            with ui.column().classes('w-full gap-1 mb-4'):
                                ui.label('User Activity by Role').classes('text-base font-bold text-slate-800 tracking-tight')
                                ui.label('From regport_audit_trails ⋈ regport_users — actions per role').classes('text-[11px] text-slate-400')
                            
                            activity_role_options = {
                                'tooltip': {
                                    'trigger': 'axis',
                                    'axisPointer': {'type': 'shadow'},
                                    'formatter': '{b}: {c} actions'
                                },
                                'grid': {
                                    'left': '3%',
                                    'right': '4%',
                                    'top': '8%',
                                    'bottom': '12%',
                                    'containLabel': True
                                },
                                'xAxis': {
                                    'type': 'category',
                                    'data': role_names,
                                    'axisLabel': {'color': '#64748b', 'fontSize': 11, 'fontWeight': 500},
                                    'axisLine': {'lineStyle': {'color': '#e2e8f0'}},
                                    'axisTick': {'show': False}
                                },
                                'yAxis': {
                                    'type': 'value',
                                    'axisLabel': {'color': '#94a3b8', 'fontSize': 10},
                                    'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}},
                                    'axisLine': {'show': False},
                                    'axisTick': {'show': False}
                                },
                                'series': [{
                                    'type': 'bar',
                                    'barWidth': '42%',
                                    'data': role_action_counts,
                                    'label': {
                                        'show': True,
                                        'position': 'top',
                                        'color': '#475569',
                                        'fontSize': 11,
                                        'fontWeight': 600
                                    }
                                }]
                            }
                            ui.echart(activity_role_options).classes('w-full h-56')

                    # Render Subtitle block for USER JOURNEY PATHS with an elegant separator line
                    with ui.row().classes('w-full items-center gap-2 mb-4 mt-8'):
                        with ui.element('div').classes('p-2 bg-white border border-slate-100 rounded-lg flex items-center justify-center shadow-xs'):
                            ui.icon('explore', size='16px').classes('text-indigo-500')
                        ui.label('USER JOURNEY PATHS').classes('text-[11px] font-extrabold text-slate-400 tracking-wider')
                        ui.element('div').classes('flex-grow h-px bg-slate-200/60 ml-2')

                    create_user_journey_section(org_uj_df, platform_name=PLATFORM, id='user_journeys_port', show_info=True, title=f"{org_name} Journey Paths")


            async def on_org_selected(org_id: str, org_name: str):
                app.storage.user[ORG_SESSION_KEY]      = org_id
                app.storage.user[ORG_NAME_SESSION_KEY] = org_name
                await load_org_data()

            # Dropdown is now handled in the main filter bar

            refresh_callbacks.append(load_org_data)
            asyncio.create_task(load_org_data())

        async def handle_refresh():
            # Trigger all refresh callbacks
            for callback in refresh_callbacks:
                if inspect.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()

        # Initial fetch of core metrics
        await fetch_core_metrics()
        
        current_org_name = app.storage.user.get(ORG_NAME_SESSION_KEY)

        async def on_org_filter_change(e):
            chosen_name = e.value
            if chosen_name and chosen_name in org_data_map:
                app.storage.user[ORG_SESSION_KEY] = org_data_map[chosen_name]['organization_id']
                app.storage.user[ORG_NAME_SESSION_KEY] = chosen_name
                await handle_refresh()

        # Create page with tabs
        await create_page_template(
            page_title='RegPort Performance',
            #page_subtitle='Comprehensive regulatory compliance platform metrics and analytics',
            tabs=[
                {'name': 'Overview', 'content_func': overview_content},
                {'name': 'Acquisition', 'content_func': acquisition_content},
                {'name': 'Conversion', 'content_func': conversion_content},
                {'name': 'Engagement', 'content_func': engagement_content},
                {'name': 'Feature Adoption', 'content_func': feature_adoption_content},
                {'name': 'Organization Deep-Dive', 'content_func': organization_deep_dive_content}
            ],
            active_tab='Overview',
            show_filters=True,
            on_filter_change=handle_refresh,
            org_filter_config={
                'options': org_names,
                'current_val': current_org_name,
                'on_change': on_org_filter_change
            }
        )
    
    await dashboard_layout(content, page_title="RegPort Performance", active_page="product/regport")