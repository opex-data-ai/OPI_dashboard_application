import asyncio
from datetime import datetime, timedelta
from nicegui import ui, app, run
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
    create_column_chart,
    create_funnel_chart,
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
from data_engine.chart_descriptions import METRIC_INFO
import pandas as pd
import inspect
from components.theme_manager import ThemeManager
from data_engine.module_mapping import map_path_to_module, map_path_to_landing
from utils.formatters import format_msec_to_time, format_msec_to_compact_time
from data_engine.chart_descriptions import METRIC_INFO



async def show_regcomply_product_page():
    async def content():
        # Keep track of functions to refresh data
        refresh_callbacks = []
        loader = get_data_loader()
        shared_data = {} # Shared results for common metrics
        

        def get_current_dates():
            date_range = app.storage.user.get('date_range', {})
            default_end = datetime.today().strftime('%Y-%m-%d')
            default_start = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')
            start = date_range.get('from', default_start).replace('/', '-')
            end = date_range.get('to', default_end).replace('/', '-')
            return start, end

        PLATFORM = 'RegComply'
        ORG_SESSION_KEY = 'regcomply_selected_org_id'
        ORG_NAME_SESSION_KEY = 'regcomply_selected_org_name'

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
            results = loader.execute_batch_queries(core_queries, start, end, platform='RegComply')
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
                
                # RegComply maps to regcomply in the data
                results = loader.execute_batch_queries(overview_queries, start_date, end_date, platform='RegComply')
                
                # Merge with shared results
                results.update(shared_data)

                container.clear()
                with container:
                    # Pre-calculate or fetch needed values
                    active_orgs = results['active_org_count'].iloc[0,0] if not results['active_org_count'].empty else 0
                    
                    # Total Organization from results['organization_by_platform'] where platform = 'RegComply'
                    total_orgs = 0
                    if not results['organization_by_platform'].empty:
                        # Find the row for RegComply platform
                        mask = results['organization_by_platform']['platform'].str.lower() == 'regcomply'
                        regcomply_org_row = results['organization_by_platform'][mask]
                        if not regcomply_org_row.empty:
                            # Using column 'total_orgs', from query_store.py line 10
                            total_orgs = int(regcomply_org_row.iloc[0]['total_orgs'])

                    # Total Users for RegComply
                    total_users = 0
                    if not results['user_by_platform'].empty:
                        user_mask = results['user_by_platform']['platform'].str.lower() == 'regcomply'
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
                                'signed_in_users': 'Active Signed-In Users',
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
                
                results = loader.execute_batch_queries(queries, start_date, end_date, platform='RegComply')
                
                container.clear()
                with container:
                    ui.label('User Acquisition Analysis').classes(ThemeManager.TYPOGRAPHY['h2'] + ' mb-2')
                    
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
                                render_chart_header('New org & user acquisition trend', 'acquisition_trend_comply', True, lambda: ui.run_javascript(f"downloadChart('{trend_chart_el.id}', 'New org and user acquisition trend')"), trend_df if 'trend_df' in locals() else orgs_df)
                            
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
                        create_device_browser_breakdown(results['device_browser'], 'RegComply')

                    # New Users by Primary Medium & Source
                    if not results['traffic_source'].empty:
                        traffic_source_medium_data = results['traffic_source']
                        traffic_source = traffic_source_medium_data.groupby('acquisition_source', as_index=False).agg({'new_visitors': 'sum'})
                        traffic_medium = traffic_source_medium_data.groupby('acquisition_medium', as_index=False).agg({'new_visitors': 'sum'})
                        
                        # Data for AI (using full traffic metrics for context)
                        METRIC_INFO['traffic_source']['chart_data'] = traffic_source.to_dict('records')
                        METRIC_INFO['traffic_medium']['chart_data'] = traffic_medium.to_dict('records')

                    # Session Traffic by Primary Medium & Source
                    if not results['session_traffic'].empty:
                        session_source_medium_data = results['session_traffic']
                        session_source = session_source_medium_data.groupby('session_source', as_index=False).agg({'session_count': 'sum'})
                        session_medium = session_source_medium_data.groupby('session_medium', as_index=False).agg({'session_count': 'sum'})

                        # Data for AI (using full session traffic metrics for context)
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
                        create_geographic_distribution_table(results['geographic_dist'], 'RegComply')
            
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
                    'churn_signal': QUERIES['regcomply_conversion_churn_signal']
                }
                
                results = loader.execute_batch_queries(conversion_queries, start_date, end_date, platform='RegComply')
                
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
                        create_dormant_organizations_card(results['churn_signal'], 'RegComply')
                        
                        # Right: Weekly Sign-up & Login Trend
                        create_weekly_signup_login_trend(results['signup_login_trend'])

                    # 2. Funnel Analysis (Full Width Row)
                    #ui.label('Landing Page Funnel Analysis').classes(ThemeManager.TYPOGRAPHY['h3'] + ' mt-8 mb-4')
                    #if not results['funnel_analysis'].empty:
                    #    df_raw = results['funnel_analysis'].copy()
                        
                        # Apply strict mapping
                    #    df_raw['landing_page_label'] = df_raw['landing_page'].apply(lambda x: map_path_to_landing(x, 'RegComply'))
                    #    df_raw['next_action_label'] = df_raw['next_common_action'].apply(lambda x: map_path_to_module(x, 'RegComply'))
                        
                        # Filter rows where both are valid (next action MUST be a module, landing must be is_landing=True)
                    #   df_filtered = df_raw.dropna(subset=['landing_page_label', 'next_action_label']).copy()
                        
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
                        create_user_journey_section(results['user_journey'], platform_name='RegComply', id='user_journeys')
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
                    start_date, end_date, platform='RegComply'
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
            container = ui.column().classes('w-full')
            async def load_data():
                start_date, end_date = get_current_dates()
                
                # Fetch RegComply Feature Adoption Analytics
                adoption_queries = {
                    'audit_count': QUERIES['regcomply_audit_count'],
                    'completion_rate': QUERIES['regcomply_audit_completion_rate'],
                    'active_audits': QUERIES['regcomply_active_audits'],
                    'avg_duration': QUERIES['regcomply_average_audit_duration'],
                    'external_pct': QUERIES['regcomply_external_audit_pct'],
                    'audit_funnel': QUERIES['regcomply_audit_funnel'],
                    'status_dist': QUERIES['regcomply_status_distribution'],
                    'type_split': QUERIES['regcomply_audit_type_split'],
                    'standard_split': QUERIES['regcomply_audits_by_standard'],
                    'duration_trend': QUERIES['regcomply_audit_duration_trend'],
                    'time_to_q': QUERIES['regcomply_time_to_questions'],
                    'time_to_r': QUERIES['regcomply_time_to_respond'],
                    'time_to_c': QUERIES['regcomply_time_to_complete'],
                    'extension_rate': QUERIES['regcomply_extension_rate'],
                    'delayed_audits': QUERIES['regcomply_delayed_audits'],
                    'org_performance': QUERIES['regcomply_org_performance_table'],
                    'lifecycle_duration': QUERIES['regcomply_lifecycle_duration_table'],
                }
                
                results = loader.execute_batch_queries(adoption_queries, start_date, end_date)
                
                # Pre-process results to handle JSON serialization (convert Timestamps to strings)
                for df_name in results:
                    df = results[df_name]
                    if not df.empty:
                        for col in df.columns:
                            if pd.api.types.is_datetime64_any_dtype(df[col]) or df[col].dtype == object:
                                # Try to detect if it's a date/time object and convert to string
                                try:
                                    # This handles cases where DuckDB/Pandas objects are not JSON serializable
                                    df[col] = df[col].apply(lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x))
                                except Exception:
                                    df[col] = df[col].astype(str)
                
                container.clear()
                with container:
                    ui.label('Feature Adoption Analysis').classes(ThemeManager.TYPOGRAPHY['h2'] + ' mb-4')
                    
                    # --- ROW 1: CORE KPIs ---
                    kpis = []
                    ui.label('Core Audit Module Metrics').classes(ThemeManager.TYPOGRAPHY['h3'] + ' mb-4')
                    if not results['audit_count'].empty:
                        val = results['audit_count'].iloc[0]['total_audits']
                        kpis.append({'id': 'regcomply_total_audits', 'label': 'Total Audits', 'value': int(val), 'color': 'blue'})
                    if not results['delayed_audits'].empty:
                        val = results['delayed_audits'].iloc[0]['delayed_audits']
                        kpis.append({'id': 'regcomply_delayed_audits', 'label': 'Delayed Audits', 'value': str(int(val)), 'color': 'red'})
                    if not results['active_audits'].empty:
                        val = results['active_audits'].iloc[0]['active_audits']
                        kpis.append({'id': 'regcomply_active_audits', 'label': 'Active Audits', 'value': int(val), 'color': 'orange'})
                    if kpis:
                        create_kpi_metrics(kpis)
                    
                    #Row 2: Completion & Extension Metrics
                    row2_kpis = []
                    if not results['external_pct'].empty:
                        val = results['external_pct'].iloc[0]['external_audit_pct']
                        row2_kpis.append({'id': 'regcomply_external_pct', 'label': 'External %', 'value': f"{val:.1f}%", 'color': 'purple'})
                    if not results['completion_rate'].empty:
                        val = results['completion_rate'].iloc[0]['completion_rate']
                        row2_kpis.append({'id': 'regcomply_completion_rate', 'label': 'Completion Rate', 'value': f"{val:.1f}%", 'color': 'green'})
                    if not results['extension_rate'].empty:
                        val = results['extension_rate'].iloc[0]['extension_rate']
                        row2_kpis.append({'id': 'regcomply_extension_rate', 'label': 'Extension Rate', 'value': f"{val*100:.1f}%", 'color': 'purple'})
                    if row2_kpis:
                        create_kpi_metrics(row2_kpis)

                    #Row 3: Average Duration
                    #row3_kpis = []
                    #if not results['avg_duration'].empty:
                       #val = results['avg_duration'].iloc[0]['avg_duration_days']
                        #if pd.notna(val):
                            #row3_kpis.append({'id': 'regcomply_avg_duration', 'label': 'Avg Duration', 'value': f"{val:.1f} Days", 'color': 'indigo'})

                    
                    
                    # --- LIFECYCLE DURATION TABLE ---
                    def _fmt_secs(secs):
                        """Convert seconds to a readable d h m string."""
                        if secs is None or (isinstance(secs, float) and pd.isna(secs)):
                            return 'N/A'
                        secs = int(abs(secs))
                        d, rem = divmod(secs, 86400)
                        h, rem = divmod(rem, 3600)
                        m = rem // 60
                        parts = []
                        if d: parts.append(f"{d}d")
                        if h: parts.append(f"{h}h")
                        if m or not parts: parts.append(f"{m}m")
                        return ' '.join(parts)

                    if not results['lifecycle_duration'].empty:
                        lc_df = results['lifecycle_duration'].copy()
                        METRIC_INFO['regcomply_lifecycle_duration_table']['chart_data'] = lc_df.to_dict('records')
                        duration_cols = [
                            'secs_planned_duration',
                            'secs_actual_duration'
                        ]
                        rename_map = {
                            'audit_title': 'Audit Title',
                            'total_audits': 'Total Audits',
                            'total_completed_audits': 'Completed Audits',
                            'secs_planned_duration': 'Average Planned Duration',
                            'secs_actual_duration': 'Average Actual Duration',
                        }
                        for col in duration_cols:
                            if col in lc_df.columns:
                                lc_df[col] = lc_df[col].apply(_fmt_secs)
                        lc_df.rename(columns=rename_map, inplace=True)
                        #ui.label('Audit Lifecycle Duration Analysis').classes(ThemeManager.TYPOGRAPHY['h3'] + ' mt-8 mb-2')
                        create_metric_table(
                            data=lc_df,
                            title='Audit Lifecycle Duration Analysis',
                            height='h-[400px]',
                            id='regcomply_lifecycle_duration_table'
                        )

                    # --- ROW 2: FUNNEL & STATUS ---
                    with ui.grid(columns=2).classes('w-full gap-6 grid-cols-1 lg:grid-cols-2 items-stretch mt-4'):
                        if not results['audit_funnel'].empty:
                            funnel_df = results['audit_funnel']
                            METRIC_INFO['regcomply_audit_funnel']['chart_data'] = funnel_df.to_dict('records')
                            create_funnel_chart(
                                data=funnel_df,
                                title='Audit Lifecycle Funnel',
                                x_col='stage',
                                y_col='audits',
                                id='regcomply_audit_funnel',
                                height='h-96'
                            )
                        if not results['status_dist'].empty:
                            dist_df = results['status_dist']
                            METRIC_INFO['regcomply_status_distribution']['chart_data'] = dist_df.to_dict('records')
                            # Convert to dict for donut chart
                            dist_data = dict(zip(dist_df['status_group'], dist_df['audits']))
                            create_donut_chart(
                                data=dist_data,
                                title='Audit Status Distribution',
                                id='regcomply_status_distribution'
                            )
                    
                    


                    # --- ROW 3: TYPE & STANDARD ---
                    with ui.grid(columns=2).classes('w-full gap-6 grid-cols-1 lg:grid-cols-2 items-stretch mt-4'):
                        if not results['type_split'].empty:
                            type_df = results['type_split']
                            METRIC_INFO['regcomply_audit_type_split']['chart_data'] = type_df.to_dict('records')
                            create_bar_chart(
                                    data=type_df,
                                    title='Audit Type Breakdown',
                                    x_col='auditType',
                                    y_cols=['audits'],
                                    id='regcomply_audit_type_split',
                                    height='h-96'
                                )
                        if not results['standard_split'].empty:
                            std_df = results['standard_split']
                            METRIC_INFO['regcomply_audits_by_standard']['chart_data'] = std_df.to_dict('records')
                            create_column_chart(
                                data=std_df,
                                title='Audits by Compliance Standard',
                                    x_col='standardName',
                                    y_cols=['audits'],
                                    id='regcomply_audits_by_standard',
                                    height='h-96'
                                )

                    # --- ROW 4: DURATION TREND ---
                    with ui.row().classes('w-full mt-8'):
                        if not results['duration_trend'].empty:
                            trend_df = results['duration_trend']
                            METRIC_INFO['regcomply_audit_duration_trend']['chart_data'] = trend_df.to_dict('records')
                            create_line_chart(
                                data=trend_df,
                                title='Average Audit Duration Trend',
                                x_col='audit_date',
                                y_cols=['avg_duration'],
                                id='regcomply_audit_duration_trend'
                            )

                    # --- ROW 6: PERFORMANCE TABLE ---
                    with ui.row().classes('w-full mt-8'):
                        if not results['org_performance'].empty:
                            perf_df = results['org_performance']
                            # Formatting for display
                            display_df = perf_df.copy()
                            if 'completion_rate' in display_df.columns:
                                display_df['completion_rate'] = display_df['completion_rate'].apply(lambda x: f"{x*100:.1f}%")
                            if 'avg_duration' in display_df.columns:
                                display_df['avg_duration'] = display_df['avg_duration'].apply(lambda x: f"{x:.1f} Days" if pd.notna(x) else "N/A")
                            
                            create_metric_table(
                                data=display_df,
                                title='Organizational Audit Performance',
                                height='h-[400px]',
                                id='regcomply_org_performance_table'
                            )

                    
            
            refresh_callbacks.append(load_data)
            asyncio.create_task(load_data())
            
        async def organization_deep_dive_content():
            with ui.column().classes('w-full gap-4') as outer:
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

                    # Render Loading spinner initially
                    loading_spinner = ui.row().classes('w-full items-center gap-2 mb-4')
                    with loading_spinner:
                        ui.spinner(size='sm').classes('text-indigo-500')
                        ui.label(f'Loading data for {org_name}…').classes(ThemeManager.COLORS['text']['muted'])

                    try:
                        header_df = loader.execute_query(QUERIES['regcomply_org_deep_dive_details'], [org_id, org_id])
                        summary_df = loader.execute_query(QUERIES['regcomply_org_engagement_summary'], [org_id, PLATFORM, start_date, end_date])
                        daily_trend_df = loader.execute_query(QUERIES['regcomply_org_engagement_daily_trend'], [org_id, PLATFORM, start_date, end_date])
                        device_df = loader.execute_query(QUERIES['regcomply_org_session_device_split'], [org_id, PLATFORM, start_date, end_date])
                        traffic_df = loader.execute_query(QUERIES['regcomply_org_traffic_source'], [org_id, PLATFORM, start_date, end_date])
                        milestones_df = loader.execute_query(QUERIES['regcomply_org_conversion_milestones'], [org_id, start_date, end_date, org_id])
                        funnel_df = loader.execute_query(QUERIES['regcomply_org_audit_funnel'], [org_id, start_date, end_date])
                        module_df = loader.execute_query(QUERIES['regcomply_org_module_deepdive'], [org_id, start_date, end_date])
                        bottleneck_df = loader.execute_query(QUERIES['regcomply_org_stage_bottleneck'], [org_id, start_date, end_date])
                        user_breakdown_df = loader.execute_query(QUERIES['regcomply_org_user_breakdown'], [org_id, start_date, end_date, org_id])
                        weekly_pattern_df = loader.execute_query(QUERIES['product_deep_ga4_weekly_pattern'], [org_id, PLATFORM, start_date, end_date])
                        traffic_source_df = loader.execute_query(QUERIES['product_deep_traffic_source'], [org_id, PLATFORM, start_date, end_date])
                        org_uj_df = loader.execute_query(QUERIES['org_user_journey_paths'], [start_date, end_date, org_id, PLATFORM])
                    except Exception as e:
                        loading_spinner.delete()
                        ui.label(f"Error fetching deep-dive details: {str(e)}").classes('text-red-500')
                        return

                    loading_spinner.delete()

                    if header_df.empty:
                        row = {
                            'organizationName': org_name,
                            'industry': 'Unknown Industry',
                            'email': 'N/A',
                            'member_since': None,
                            'country_name': 'Unknown',
                            'subscriptionPlan': 'Standard',
                            'subscriptionStatus': 'Active',
                            'upgrade': False,
                            'total_members': 0,
                            'last_member_active': None
                        }
                    else:
                        row = header_df.iloc[0]

                    # Parse fields cleanly
                    display_name = row['organizationName']
                    industry = row['industry'] if pd.notna(row['industry']) else 'Unknown Industry'
                    
                    email = row['email']
                    email_domain = str(email).split('@')[1] if pd.notna(email) and '@' in str(email) else 'N/A'
                    
                    member_since = row['member_since']
                    onboarded_str = f"Member since {pd.to_datetime(member_since).strftime('%b %d, %Y')}" if pd.notna(member_since) else "Unknown Onboard Date"
                    
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
                    
                    last_active = row['last_member_active']
                    last_active_str = pd.to_datetime(last_active).strftime('%b %d, %Y') if pd.notna(last_active) else "No Activity"
                    
                    total_members = int(row['total_members']) if pd.notna(row['total_members']) else 0

                    sub_status = str(row['subscriptionStatus']) if pd.notna(row['subscriptionStatus']) else 'Active'
                    status_color = 'emerald' if sub_status.lower() == 'active' else 'amber' if 'trial' in sub_status.lower() else 'slate'
                    
                    sub_plan = str(row['subscriptionPlan']) if pd.notna(row['subscriptionPlan']) else 'Standard'
                    plan_color = 'purple' if 'enterprise' in sub_plan.lower() or 'pro' in sub_plan.lower() else 'amber'
                    
                    is_upgraded = str(row['upgrade']).lower() in ['true', '1', 'yes']
                    upgrade_text = 'Upgraded Tier' if is_upgraded else 'Standard Tier'
                    upgrade_bg = 'bg-blue-50 text-blue-600 border border-blue-100' if is_upgraded else 'bg-slate-50 text-slate-500 border border-slate-100'
                    
                    member_text = f"{total_members} Active Members" if total_members > 0 else "No Members"

                    # Process summary engagement metrics
                    if summary_df.empty or pd.isna(summary_df.iloc[0]['total_sessions']):
                        active_days = 0
                        total_sessions = 0
                        peak_users = 0
                        avg_session_min = 0.0
                        total_key_events = 0
                    else:
                        s_row = summary_df.iloc[0]
                        active_days = int(s_row['active_days']) if pd.notna(s_row['active_days']) else 0
                        total_sessions = int(s_row['total_sessions']) if pd.notna(s_row['total_sessions']) else 0
                        peak_users = int(s_row['peak_active_users']) if pd.notna(s_row['peak_active_users']) else 0
                        avg_session_min = float(s_row['avg_session_engagement_min']) if pd.notna(s_row['avg_session_engagement_min']) else 0.0
                        total_key_events = int(s_row['total_key_events']) if pd.notna(s_row['total_key_events']) else 0

                    # Render Beautiful Responsive Header Card (matching regport style exactly)
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
                                                ui.label('Last active member:').classes('rp-org-meta')
                                                ui.label(last_active_str).classes('rp-org-meta-bold')
                                                
                            # Right side: Badges row (horizontal flex on desktop/tablet, wraps cleanly, stacks vertically or wraps on mobile)
                            with ui.row().classes('flex flex-col sm:flex-row flex-wrap gap-2 items-start sm:items-center justify-start sm:justify-end mt-1 sm:mt-0'):
                                
                                # 1. Active / Status badge
                                with ui.row().classes(f'bg-{status_color}-50 text-{status_color}-600 border border-{status_color}-100 rounded-full px-3 py-1 items-center gap-1.5 font-semibold text-[11px] shadow-xs'):
                                    ui.element('span').classes(f'w-1.5 h-1.5 rounded-full bg-{status_color}-500')
                                    ui.label(sub_status.title())
                                    
                                # 2. Upgrade / Tier badge
                                with ui.row().classes(f'{upgrade_bg} rounded-full px-3 py-1 items-center font-semibold text-[11px] shadow-xs'):
                                    ui.label(upgrade_text)
                                    
                                # 3. Plan badge
                                with ui.row().classes(f'bg-{plan_color}-50 text-{plan_color}-600 border border-{plan_color}-100 rounded-full px-3 py-1 items-center font-semibold text-[11px] shadow-xs'):
                                    ui.label(f'{sub_plan.title()} Plan')
                                    
                                # 4. Active Members badge
                                with ui.row().classes('bg-slate-50 text-slate-500 border border-slate-100 rounded-full px-3 py-1 items-center font-semibold text-[11px] font-mono shadow-xs'):
                                    ui.label(member_text)

                    # Render Subtitle block for ENGAGEMENT PULSE with an elegant separator line
                    with ui.row().classes('w-full items-center gap-2 mb-4 mt-6'):
                        with ui.element('div').classes('p-2 bg-slate-50 border border-slate-100 rounded-lg flex items-center justify-center shadow-xs'):
                            ui.icon('bolt', size='16px').classes('text-indigo-500')
                        ui.label('ENGAGEMENT PULSE').classes('rp-section-label')
                        ui.element('div').classes('flex-grow h-px bg-slate-200/60 ml-2')

                    # 5 Premium Interactive Vertical KPI Cards (matching the updated 5-card layout)
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
                            
                        # Card 3: AVG SESSION TIME
                        with ui.card().classes('flex-1 min-w-[150px] p-4 bg-white border border-slate-100 rounded-xl shadow-xs border-l-4 border-l-indigo-500 relative overflow-hidden hover:shadow-md hover:scale-[1.02] cursor-pointer transition-all duration-300'):
                            with ui.row().classes('w-full justify-between items-center no-wrap'):
                                ui.label('AVG SESSION TIME').classes('rp-kpi-label')
                                render_kpi_info_icon('avg_session_time')
                            with ui.row().classes('items-baseline gap-0.5 mt-1'):
                                ui.label(f"{avg_session_min:.1f}").classes('rp-kpi-value')
                                ui.label('m').classes('rp-kpi-sub font-bold')
                            ui.label('Per session').classes('rp-kpi-sub mt-1')
                            
                        # Card 4: KEY EVENTS
                        with ui.card().classes('flex-1 min-w-[150px] p-4 bg-white border border-slate-100 rounded-xl shadow-xs border-l-4 border-l-amber-500 relative overflow-hidden hover:shadow-md hover:scale-[1.02] cursor-pointer transition-all duration-300'):
                            with ui.row().classes('w-full justify-between items-center no-wrap'):
                                ui.label('KEY EVENTS').classes('rp-kpi-label')
                                render_kpi_info_icon('key_events')
                            ui.label(f"{total_key_events:,}").classes('rp-kpi-value mt-1')
                            ui.label('Core actions taken').classes('rp-kpi-sub mt-1')
                            
                        # Card 5: ACTIVE DAYS
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
                                render_chart_header('Daily Active Users & Sessions', 'daily_active_users_sessions_comply', True, lambda: ui.run_javascript(f"downloadChart('{daily_trend_chart_el.id}', 'Daily Active Users and Sessions')"), daily_trend_df)
                            
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
                                render_chart_header('Session Device Split', 'session_device_split_comply', True, lambda: ui.run_javascript(f"downloadChart('{device_donut_chart_el.id}', 'Session Device Split')"), device_df)
                            
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
                                render_chart_header('Day-of-Week Engagement Pattern', 'day_of_week_engagement_comply', True, lambda: ui.run_javascript(f"downloadChart('{weekly_pattern_chart_el.id}', 'Day of Week Engagement Pattern')"), weekly_pattern_df)
                            
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
                                render_chart_header('Top Traffic Sources', 'top_traffic_sources_comply', True, lambda: _download_csv_helper(traffic_source_df, 'Top Traffic Sources'), traffic_source_df)
                            
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

                    # Parse milestones data safely
                    if milestones_df.empty:
                        first_audit_created_str = 'N/A'
                        m_sub_plan = sub_plan
                        m_sub_status = sub_status
                        total_audits = 0
                        completed_audits = 0
                        avg_planned_days = 0.0
                        checklist_used = 0
                        extensions_requested = 0
                    else:
                        m_row = milestones_df.iloc[0]
                        first_audit = m_row['first_audit_created']
                        first_audit_created_str = pd.to_datetime(first_audit).strftime('%d %b %Y') if pd.notna(first_audit) else 'N/A'
                        m_sub_plan = str(m_row['subscriptionPlan']) if pd.notna(m_row['subscriptionPlan']) else sub_plan
                        m_sub_status = str(m_row['subscriptionStatus']) if pd.notna(m_row['subscriptionStatus']) else sub_status
                        total_audits = int(m_row['total_audits']) if pd.notna(m_row['total_audits']) else 0
                        completed_audits = int(m_row['completed_audits']) if pd.notna(m_row['completed_audits']) else 0
                        avg_planned_days = float(m_row['avg_planned_days']) if pd.notna(m_row['avg_planned_days']) else 0.0
                        checklist_used = int(m_row['checklist_used']) if pd.notna(m_row['checklist_used']) else 0
                        extensions_requested = int(m_row['extensions_requested']) if pd.notna(m_row['extensions_requested']) else 0

                    # Parse funnel data safely
                    stages_list = []
                    if not funnel_df.empty:
                        # Ensure sorted by stage_order
                        funnel_sorted = funnel_df.sort_values('stage_order', ascending=True)
                        for _, f_row in funnel_sorted.iterrows():
                            stages_list.append({
                                'stage': str(f_row['stage']),
                                'count': int(f_row['count']) if pd.notna(f_row['count']) else 0
                            })
                    else:
                        stages_list = [
                            {'stage': 'Created', 'count': 0},
                            {'stage': 'Approved', 'count': 0},
                            {'stage': 'Questions Set', 'count': 0},
                            {'stage': 'Responded', 'count': 0},
                            {'stage': 'Audited', 'count': 0},
                            {'stage': 'Completed', 'count': 0}
                        ]

                    max_val = stages_list[0]['count'] if stages_list else 0
                    for i, stage_data in enumerate(stages_list):
                        val = stage_data['count']
                        # Width of progress bar relative to max value
                        stage_data['pct_width'] = (val / max_val * 100) if max_val > 0 else 0
                        
                        # Drop relative to previous stage
                        if i == 0:
                            stage_data['drop_str'] = '-'
                            stage_data['drop_color'] = 'text-slate-400'
                        else:
                            prev_val = stages_list[i-1]['count']
                            if prev_val == 0:
                                stage_data['drop_str'] = '-'
                                stage_data['drop_color'] = 'text-slate-400'
                            elif val == prev_val:
                                stage_data['drop_str'] = '-'
                                stage_data['drop_color'] = 'text-slate-400'
                            else:
                                drop_pct = int(round((val - prev_val) / prev_val * 100))
                                if drop_pct < 0:
                                    stage_data['drop_str'] = f"{drop_pct}%"
                                    stage_data['drop_color'] = 'text-rose-500 font-semibold'
                                else:
                                    stage_data['drop_str'] = f"+{drop_pct}%"
                                    stage_data['drop_color'] = 'text-emerald-500 font-semibold'

                    # Render Subtitle block for CONVERSIONS & AUDIT FUNNEL with an elegant separator line
                    with ui.row().classes('w-full items-center gap-2 mb-4 mt-8'):
                        with ui.element('div').classes('p-2 bg-slate-50 border border-slate-100 rounded-lg flex items-center justify-center shadow-xs'):
                            ui.icon('filter_alt', size='16px').classes('text-indigo-500')
                        ui.label('CONVERSIONS & AUDIT FUNNEL').classes('rp-section-label')
                        ui.element('div').classes('flex-grow h-px bg-slate-200/60 ml-2')

                    with ui.grid(columns=2).classes('w-full gap-6 items-stretch'):
                        
                        # Left Card: Conversion milestones
                        with ui.card().classes('p-6 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden'):
                            with ui.row().classes('w-full items-start justify-between mb-4'):
                                render_chart_header('Conversion Milestones', 'conversion_milestones_comply', True, lambda: _download_csv_helper(milestones_df, 'Conversion Milestones'), milestones_df)
                            
                            # Table structure
                            with ui.column().classes('w-full gap-0'):
                                # Table Header
                                with ui.row().classes('w-full border-b border-slate-100 pb-2 text-xs font-bold text-slate-400 tracking-wider mb-2 justify-between items-center px-1'):
                                    ui.label('Milestone').classes('text-left')
                                    ui.label('Value').classes('text-right')

                                # Row helper function
                                def milestone_row(label, value_element_func):
                                    with ui.row().classes('w-full items-center justify-between py-3 border-b border-slate-50 hover:bg-slate-50/50 rounded px-1 transition-colors'):
                                        ui.label(label).classes('text-xs font-medium text-slate-600')
                                        with ui.row().classes('justify-end items-center'):
                                            value_element_func()

                                # 1. First audit created
                                def render_first_audit():
                                    ui.label(first_audit_created_str).classes('text-xs font-mono text-slate-900 font-bold')
                                milestone_row('First audit created', render_first_audit)

                                # 2. Subscription plan
                                def render_sub_plan():
                                    with ui.row().classes(f'bg-{plan_color}-50 text-{plan_color}-600 border border-{plan_color}-100 rounded-full px-2.5 py-0.5 items-center font-semibold text-[11px] shadow-xs'):
                                        ui.label(m_sub_plan.title())
                                milestone_row('Subscription plan', render_sub_plan)

                                # 3. Subscription status
                                def render_sub_status():
                                    with ui.row().classes(f'bg-{status_color}-50 text-{status_color}-600 border border-{status_color}-100 rounded-full px-2.5 py-0.5 items-center font-semibold text-[11px] shadow-xs'):
                                        ui.label(m_sub_status.title())
                                milestone_row('Subscription status', render_sub_status)

                                # 4. Audits created
                                def render_total_audits():
                                    ui.label(f"{total_audits:,}").classes('text-xs font-mono text-slate-900 font-bold')
                                milestone_row('Audits created', render_total_audits)

                                # 5. Audits completed
                                def render_completed_audits():
                                    if completed_audits == 0:
                                        with ui.row().classes('bg-rose-50 text-rose-600 border border-rose-100 rounded-full px-2.5 py-0.5 items-center font-semibold text-[11px] shadow-xs'):
                                            ui.label('0')
                                    else:
                                        ui.label(f"{completed_audits:,}").classes('text-xs font-mono text-slate-900 font-bold')
                                milestone_row('Audits completed', render_completed_audits)

                                # 6. Avg planned duration
                                def render_planned_duration():
                                    ui.label(f"{avg_planned_days:.0f}d" if avg_planned_days > 0 else '0d').classes('text-xs font-mono text-slate-900 font-bold')
                                milestone_row('Avg planned duration', render_planned_duration)

                                # 7. Checklist used
                                def render_checklist():
                                    chk_color = 'emerald' if checklist_used > 0 else 'slate'
                                    with ui.row().classes(f'bg-{chk_color}-50 text-{chk_color}-600 border border-{chk_color}-100 rounded-full px-2.5 py-0.5 items-center font-semibold text-[11px] shadow-xs'):
                                        ui.label(f"{checklist_used} of {max(total_audits, 1)}")
                                milestone_row('Checklist used', render_checklist)

                                # 8. Extensions requested
                                def render_extensions():
                                    ui.label(f"{extensions_requested:,}").classes('text-xs font-mono text-slate-900 font-bold')
                                milestone_row('Extensions requested', render_extensions)

                        # Right Card: Audit lifecycle funnel
                        with ui.card().classes('p-6 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden'):
                            with ui.row().classes('w-full items-start justify-between mb-6'):
                                render_chart_header('Audit Lifecycle Funnel', 'regcomply_audit_funnel_comply', True, lambda: _download_csv_helper(funnel_df, 'Audit Lifecycle Funnel'), funnel_df)
                            
                            # Funnel stages list view
                            with ui.column().classes('w-full gap-4'):
                                for i, stage_data in enumerate(stages_list):
                                    stage_name = stage_data['stage']
                                    count_val = stage_data['count']
                                    pct_width = stage_data['pct_width']
                                    drop_str = stage_data['drop_str']
                                    drop_color = stage_data['drop_color']
                                    
                                    # Pick color based on stage
                                    if count_val == 0:
                                        bar_color_class = 'bg-slate-200'
                                    else:
                                        if stage_name in ['Created', 'Approved']:
                                            bar_color_class = 'bg-blue-500'
                                        elif stage_name == 'Questions Set':
                                            bar_color_class = 'bg-amber-500'
                                        elif stage_name == 'Responded':
                                            bar_color_class = 'bg-rose-500'
                                        else:
                                            bar_color_class = 'bg-slate-400'

                                    with ui.row().classes('w-full items-center gap-3 text-xs'):
                                        # Stage Label (Left side, right aligned, fixed width)
                                        ui.label(stage_name).classes('w-24 text-right font-medium text-slate-600')
                                        
                                        # Bar container (Middle)
                                        with ui.row().classes('flex-grow h-7 bg-slate-50 border border-slate-100 rounded-lg overflow-hidden relative items-center'):
                                            if count_val > 0:
                                                # Draw colored filled progress bar
                                                with ui.element('div').classes(f'h-full {bar_color_class} rounded-l-md flex items-center justify-start px-2.5 transition-all duration-500 shadow-xs').style(f'width: {pct_width}%'):
                                                    ui.label(str(count_val)).classes('text-white font-bold font-mono text-[11px]')
                                            else:
                                                # Sliver for zero count
                                                ui.element('div').classes('w-[5px] h-full bg-slate-300 rounded-l-md')
                                        
                                        # Count Label (Right of bar)
                                        with ui.row().classes('w-8 justify-start items-center'):
                                            ui.label(str(count_val)).classes('font-bold font-mono text-slate-800')
                                                
                                        # Drop/Change indicator (Far right)
                                        with ui.row().classes('w-12 justify-end items-center'):
                                            ui.label(drop_str).classes(f'{drop_color} font-mono text-[11px] text-right')
                            
                    # Render Subtitle block for MODULE DEEP-DIVE with an elegant separator line
                    with ui.row().classes('w-full items-center gap-2 mb-4 mt-8'):
                        with ui.element('div').classes('p-2 bg-slate-50 border border-slate-100 rounded-lg flex items-center justify-center shadow-xs'):
                            ui.icon('lan', size='16px').classes('text-indigo-500')
                        ui.label('MODULE DEEP-DIVE').classes('rp-section-label')
                        ui.element('div').classes('flex-grow h-px bg-slate-200/60 ml-2')

                    with ui.column().classes('w-full gap-6'):
                        
                        # Left Card: Average days per stage
                        with ui.card().classes('w-full p-6 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden'):
                            with ui.row().classes('w-full items-start justify-between mb-2'):
                                render_chart_header('Average Days Per Stage', 'avg_days_per_stage_comply', True, lambda: _download_csv_helper(bottleneck_df, 'Average Days Per Stage'), bottleneck_df)
                            
                            # Parse stage bottlenecks safely
                            bottleneck_stages = []
                            if not bottleneck_df.empty:
                                b_row = bottleneck_df.iloc[0]
                                bottleneck_stages = [
                                    {'name': 'Creation → Approval', 'val': float(b_row['days_creation_to_approval']) if pd.notna(b_row['days_creation_to_approval']) else 0.0},
                                    {'name': 'Approval → Questions', 'val': float(b_row['days_approval_to_questions']) if pd.notna(b_row['days_approval_to_questions']) else 0.0},
                                    {'name': 'Questions → Response', 'val': float(b_row['days_questions_to_response']) if pd.notna(b_row['days_questions_to_response']) else 0.0},
                                    {'name': 'Response → Audited', 'val': float(b_row['days_response_to_audited']) if pd.notna(b_row['days_response_to_audited']) else 0.0},
                                    {'name': 'Audited → Complete', 'val': float(b_row['days_audited_to_complete']) if pd.notna(b_row['days_audited_to_complete']) else 0.0}
                                ]
                            else:
                                bottleneck_stages = [
                                    {'name': 'Creation → Approval', 'val': 0.0},
                                    {'name': 'Approval → Questions', 'val': 0.0},
                                    {'name': 'Questions → Response', 'val': 0.0},
                                    {'name': 'Response → Audited', 'val': 0.0},
                                    {'name': 'Audited → Complete', 'val': 0.0}
                                ]

                            # Compute statistics
                            b_vals = [s['val'] for s in bottleneck_stages]
                            avg_val = sum(b_vals) / len(b_vals) if b_vals else 0.0
                            max_val = max(b_vals) if b_vals else 0.0
                            if max_val == 0.0:
                                max_val = 1.0

                            # Render the bottleneck stages
                            with ui.column().classes('w-full gap-4 mt-4'):
                                for stage in bottleneck_stages:
                                    name = stage['name']
                                    val = stage['val']
                                    pct_width = (val / max_val * 100)
                                    is_bottleneck = val > avg_val and val > 0.0
                                    
                                    # Styling based on bottleneck status
                                    label_class = 'text-rose-500 font-semibold' if is_bottleneck else 'text-slate-500 font-medium'
                                    bar_color = 'bg-rose-500' if is_bottleneck else 'bg-blue-500'
                                    val_text_class = 'text-rose-500 font-bold font-mono' if is_bottleneck else 'text-slate-800 font-semibold font-mono'

                                    # Label split into two lines elegantly
                                    label_parts = name.split(' → ')
                                    label_display_1 = label_parts[0] + ' →'
                                    label_display_2 = label_parts[1]

                                    with ui.row().classes('w-full items-center gap-3 text-xs'):
                                        # Stage Labels (Left aligned/two-line)
                                        with ui.column().classes('w-28 items-start gap-0.5 leading-none'):
                                            ui.label(label_display_1).classes(f'{label_class} text-[10px]')
                                            ui.label(label_display_2).classes(f'{label_class} text-[10px]')

                                        # Bar container (Middle)
                                        with ui.row().classes('flex-grow h-7 bg-slate-50 border border-slate-100 rounded-lg overflow-hidden relative items-center'):
                                            if val > 0:
                                                ui.element('div').classes(f'h-full {bar_color} rounded-l-md transition-all duration-500 shadow-xs').style(f'width: {pct_width}%')
                                            else:
                                                ui.element('div').classes('w-[5px] h-full bg-slate-300 rounded-l-md')

                                        # Value Label (Right)
                                        with ui.row().classes('w-12 justify-end items-center'):
                                            ui.label(f"{val:.2f}d" if val < 1.0 and val > 0 else f"{val:.1f}d").classes(f'{val_text_class} text-[11px]')

                            # Bottleneck Legend & Footer
                            with ui.column().classes('w-full gap-1 mt-6 border-t border-slate-50 pt-3'):
                                ui.label('Red = above-average bottleneck stage  ·  Widths relative to longest stage').classes('text-[10px] text-slate-400 font-medium')

                        # Right Card: Per-standard performance & drop-off
                        with ui.card().classes('w-full p-6 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden'):
                            with ui.row().classes('w-full items-start justify-between mb-4'):
                                render_chart_header('Per-Standard Performance & Drop-Off', 'standard_performance_comply', True, lambda: _download_csv_helper(module_df, 'Per-Standard Performance and Drop-Off'), module_df)
                            
                            with ui.column().classes('w-full gap-0'):
                                # Table Headers
                                with ui.row().classes('w-full border-b border-slate-100 pb-2 text-[10px] font-bold text-slate-400 tracking-wider mb-2 items-center justify-between px-1 flex-nowrap gap-0'):
                                    ui.label('Standard').classes('w-[28%] text-left')
                                    ui.label('Type').classes('w-[10%] text-center')
                                    ui.label('Total').classes('w-[8%] text-center')
                                    ui.label('Completed').classes('w-[10%] text-center')
                                    ui.label('Drop-off').classes('w-[12%] text-center')
                                    ui.label('Avg planned').classes('w-[14%] text-right')
                                    ui.label('Avg actual').classes('w-[18%] text-right')
                                    ui.label('Checklist').classes('w-[10%] text-right')

                                # Data Rows
                                if not module_df.empty:
                                    for _, m_row in module_df.iterrows():
                                        std_name = str(m_row['standardName'])
                                        audit_type = str(m_row['auditType'])
                                        total_val = int(m_row['total_audits']) if pd.notna(m_row['total_audits']) else 0
                                        completed_val = int(m_row['completed_audits']) if pd.notna(m_row['completed_audits']) else 0
                                        drop_val = float(m_row['drop_off_rate']) if pd.notna(m_row['drop_off_rate']) else 0.0
                                        planned_days = float(m_row['avg_planned_days']) if pd.notna(m_row['avg_planned_days']) else 0.0
                                        actual_days = float(m_row['avg_actual_days']) if pd.notna(m_row['avg_actual_days']) else 0.0
                                        checklist_pct = float(m_row['checklist_pct']) if pd.notna(m_row['checklist_pct']) else 0.0

                                        # Format planned duration
                                        if planned_days == 0:
                                            planned_str = '0d'
                                        else:
                                            p_days = int(planned_days)
                                            p_hours = int((planned_days - p_days) * 24)
                                            planned_str = f"{p_days}d {p_hours}h" if p_hours > 0 else f"{p_days}d"

                                        # Format actual duration
                                        if completed_val == total_val and completed_val > 0:
                                            actual_str = f"{actual_days:.0f}d"
                                        else:
                                            actual_str = f"{actual_days:.0f}d (ongoing)" if actual_days > 0 else 'ongoing'

                                        # Capsule color for type
                                        type_clean = audit_type.lower()
                                        if type_clean == 'internal':
                                            type_bg = 'bg-slate-100 text-slate-600'
                                        else:
                                            type_bg = 'bg-slate-100 text-slate-500'

                                        # Drop-off badge styling
                                        if drop_val > 0.0:
                                            drop_badge = 'bg-rose-50 text-rose-600 border border-rose-100 font-semibold'
                                        else:
                                            drop_badge = 'bg-emerald-50 text-emerald-600 border border-emerald-100 font-semibold'

                                        with ui.row().classes('w-full items-center justify-between py-3 border-b border-slate-50 hover:bg-slate-50/50 rounded px-1 transition-colors flex-nowrap gap-0'):
                                            ui.label(std_name).classes('w-[28%] text-xs font-semibold text-slate-700 text-left truncate').tooltip(std_name)
                                            
                                            with ui.element('div').classes('w-[10%] flex justify-center'):
                                                with ui.row().classes(f'{type_bg} rounded-full px-2 py-0.5 items-center font-semibold text-[10px] shadow-xs'):
                                                    ui.label(audit_type)
                                                    
                                            ui.label(str(total_val)).classes('w-[8%] text-xs font-mono text-slate-900 font-bold text-center')
                                            ui.label(str(completed_val)).classes('w-[10%] text-xs font-mono text-slate-900 font-bold text-center')
                                            
                                            with ui.element('div').classes('w-[12%] flex justify-center'):
                                                with ui.row().classes(f'{drop_badge} rounded-full px-2 py-0.5 items-center text-[10px] shadow-xs'):
                                                    ui.label(f"{drop_val:.0f}%")
                                                    
                                            ui.label(planned_str).classes('w-[14%] text-xs font-mono text-slate-900 font-bold text-right')
                                            ui.label(actual_str).classes('w-[18%] text-xs font-mono text-slate-900 font-bold text-right')
                                            ui.label(f"{checklist_pct:.0f}%").classes('w-[10%] text-xs font-mono text-slate-900 font-bold text-right')
                                else:
                                    with ui.row().classes('w-full justify-center py-8'):
                                        ui.label('No standard performance metrics available').classes('text-slate-400 italic text-xs')

                    # Render Subtitle block for USER-LEVEL BREAKDOWN with an elegant separator line
                    with ui.row().classes('w-full items-center gap-2 mb-4 mt-8'):
                        with ui.element('div').classes('p-2 bg-slate-50 border border-slate-100 rounded-lg flex items-center justify-center shadow-xs'):
                            ui.icon('people', size='16px').classes('text-indigo-500')
                        ui.label('USER-LEVEL BREAKDOWN').classes('rp-section-label')
                        ui.element('div').classes('flex-grow h-px bg-slate-200/60 ml-2')

                    with ui.card().classes('w-full p-6 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden'):
                        with ui.column().classes('w-full gap-0'):
                            # Table Headers
                            with ui.row().classes('w-full border-b border-slate-100 pb-2 text-[10px] font-bold text-slate-400 tracking-wider mb-2 items-center justify-between px-1 flex-nowrap gap-0'):
                                ui.label('Email').classes('w-[32%] text-left')
                                ui.label('Role').classes('w-[12%] text-center')
                                ui.label('Last active').classes('w-[16%] text-center')
                                ui.label('Sessions').classes('w-[10%] text-center')
                                ui.label('Key events').classes('w-[10%] text-center')
                                ui.label('Active days').classes('w-[10%] text-center')
                                ui.label('Status').classes('w-[10%] text-right')

                            # Helper function to mask email
                            def mask_email(email_str):
                                if not email_str or '@' not in email_str:
                                    return email_str
                                parts = email_str.split('@')
                                name = parts[0]
                                domain = parts[1]
                                if len(name) <= 2:
                                    return f"{name}***@{domain}"
                                else:
                                    return f"{name[:2]}***@{domain}"

                            # Data Rows
                            if not user_breakdown_df.empty:
                                for _, u_row in user_breakdown_df.iterrows():
                                    email_raw = str(u_row['email'])
                                    masked_email_str = mask_email(email_raw)
                                    role_name = str(u_row['role_name'])
                                    
                                    # Parse activity_status and last_active safely
                                    act_status = str(u_row['activity_status'])
                                    last_act_val = u_row['last_active']
                                    if pd.notna(last_act_val):
                                        if hasattr(last_act_val, 'strftime'):
                                            last_active_str = last_act_val.strftime('%d %b %Y')
                                        else:
                                            try:
                                                dt = pd.to_datetime(last_act_val)
                                                last_active_str = dt.strftime('%d %b %Y')
                                            except:
                                                last_active_str = str(last_act_val)
                                    else:
                                        last_active_str = '-'

                                    sessions = int(u_row['sessions']) if pd.notna(u_row['sessions']) else 0
                                    key_events = int(u_row['key_events']) if pd.notna(u_row['key_events']) else 0
                                    active_days = int(u_row['active_days']) if pd.notna(u_row['active_days']) else 0

                                    # Role badge styling
                                    role_clean = role_name.strip().lower()
                                    if 'admin' in role_clean:
                                        role_badge = 'bg-purple-50 text-purple-600 border border-purple-100'
                                    elif 'audit' in role_clean:
                                        role_badge = 'bg-blue-50 text-blue-600 border border-blue-100'
                                    else:
                                        role_badge = 'bg-slate-100 text-slate-500'

                                    # Status badge styling
                                    status_clean = act_status.strip().lower()
                                    if status_clean == 'active':
                                        status_badge = 'bg-emerald-50 text-emerald-600 border border-emerald-100 font-semibold'
                                    elif status_clean == 'dormant':
                                        status_badge = 'bg-amber-50 text-amber-600 border border-amber-100 font-semibold'
                                    else:
                                        status_badge = 'bg-rose-50 text-rose-600 border border-rose-100 font-semibold'

                                    with ui.row().classes('w-full items-center justify-between py-3 border-b border-slate-50 hover:bg-slate-50/50 rounded px-1 transition-colors flex-nowrap gap-0'):
                                        ui.label(masked_email_str).classes('w-[32%] text-xs font-semibold text-slate-700 text-left truncate').tooltip(email_raw)
                                        
                                        with ui.element('div').classes('w-[12%] flex justify-center'):
                                            with ui.row().classes(f'{role_badge} rounded-full px-2.5 py-0.5 items-center font-semibold text-[10px] shadow-xs'):
                                                ui.label(role_name)
                                                
                                        ui.label(last_active_str).classes('w-[16%] text-xs text-slate-500 text-center font-medium')
                                        ui.label(str(sessions)).classes('w-[10%] text-xs font-mono text-slate-900 font-bold text-center')
                                        ui.label(str(key_events)).classes('w-[10%] text-xs font-mono text-slate-900 font-bold text-center')
                                        ui.label(str(active_days)).classes('w-[10%] text-xs font-mono text-slate-900 font-bold text-center')
                                        
                                        with ui.element('div').classes('w-[10%] flex justify-end'):
                                            with ui.row().classes(f'{status_badge} rounded-full px-2.5 py-0.5 items-center text-[10px] shadow-xs'):
                                                ui.label(act_status)
                            else:
                                with ui.row().classes('w-full justify-center py-8'):
                                    ui.label('No user breakdown metrics available').classes('text-slate-400 italic text-xs')

                        # Render Subtitle block for USER JOURNEY PATHS with an elegant separator line
                        with ui.row().classes('w-full items-center gap-2 mb-4 mt-8'):
                            with ui.element('div').classes('p-2 bg-slate-50 border border-slate-100 rounded-lg flex items-center justify-center shadow-xs'):
                                ui.icon('explore', size='16px').classes('text-indigo-500')
                            ui.label('USER JOURNEY PATHS').classes('rp-section-label')
                            ui.element('div').classes('flex-grow h-px bg-slate-200/60 ml-2')

                        create_user_journey_section(org_uj_df, platform_name=PLATFORM, id='user_journeys_comply', show_info=True, title=f"{org_name} Journey Paths")
            
             
            async def on_org_selected(org_id: str, org_name: str):
                app.storage.user[ORG_SESSION_KEY]      = org_id
                app.storage.user[ORG_NAME_SESSION_KEY] = org_name
                await load_org_data()
                        

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
            page_title='RegComply Performance',
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
    
    await dashboard_layout(content, page_title="RegComply Performance", active_page="product/regcomply")
