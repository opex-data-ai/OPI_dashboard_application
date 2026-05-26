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



async def show_regwatch_product_page():
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

        PLATFORM = 'RegWatch'
        ORG_SESSION_KEY = 'regwatch_selected_org_id'
        ORG_NAME_SESSION_KEY = 'regwatch_selected_org_name'

        # Fetch org list for global filter
        org_df = loader.execute_query(QUERIES['product_org_list'], [PLATFORM])
        # Mapping name to its metadata (id, start_date, domain) - ensure unique index
        org_data_map = org_df.drop_duplicates(subset=['organizationName']).set_index('organizationName').to_dict('index') if not org_df.empty else {}
        org_names = list(org_data_map.keys())

        # Ensure a default organization is selected if none is set in storage
        if not app.storage.user.get(ORG_SESSION_KEY) and org_names:
            first_org_name = org_names[0]
            app.storage.user[ORG_SESSION_KEY] = org_data_map[first_org_name]['organization_id']
            app.storage.user[ORG_NAME_SESSION_KEY] = first_org_name

        async def fetch_core_metrics():
            """Fetch metrics used across multiple tabs"""
            start, end = get_current_dates()
            core_queries = {
                'active_org_count': QUERIES['product_active_org_count'],
                'organization_by_platform': QUERIES['organization_by_platform'],
                'user_by_platform': QUERIES['user_by_platform'],
                'active_signed_in_users': QUERIES['product_active_signed_in_users'],
            }
            results = loader.execute_batch_queries(core_queries, start, end, platform='RegWatch')
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
                
                # Fetch data for RegWatch
                results = loader.execute_batch_queries(overview_queries, start_date, end_date, platform='RegWatch')
                
                # Merge with shared results
                results.update(shared_data)

                container.clear()
                with container:
                    # Pre-calculate or fetch needed values
                    active_orgs = results['active_org_count'].iloc[0,0] if not results['active_org_count'].empty else 0
                    
                    # Total Organization from results['organization_by_platform'] where platform = 'RegWatch'
                    total_orgs = 0
                    if not results['organization_by_platform'].empty:
                        # Find the row for RegWatch platform
                        mask = results['organization_by_platform']['platform'].str.lower() == 'regwatch'
                        regwatch_org_row = results['organization_by_platform'][mask]
                        if not regwatch_org_row.empty:
                            total_orgs = int(regwatch_org_row.iloc[0]['total_orgs'])

                    # Total Users for RegWatch
                    total_users = 0
                    if not results['user_by_platform'].empty:
                        user_mask = results['user_by_platform']['platform'].str.lower() == 'regwatch'
                        reg_user_row = results['user_by_platform'][user_mask]
                        if not reg_user_row.empty:
                            total_users = int(reg_user_row.iloc[0]['total_users'])
                    
                    active_users = results['active_signed_in_users'].iloc[0,0] if not results['active_signed_in_users'].empty else 0

                    # Engagement Rate Comparison Metrics
                    eng_data = results['engagement_rate']
                    total_sessions = int(eng_data.iloc[0]['total_sessions']) if not eng_data.empty and pd.notna(eng_data.iloc[0]['total_sessions']) else 0
                    engaged_sessions = int(eng_data.iloc[0]['engaged_sessions']) if not eng_data.empty and pd.notna(eng_data.iloc[0]['engaged_sessions']) else 0

                    # Populate METRIC_INFO with raw data for AI insights
                    METRIC_INFO['active_org_count']['chart_data'] = {'active_orgs': active_orgs, 'total_orgs': total_orgs}
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
                
                results = loader.execute_batch_queries(queries, start_date, end_date, platform='RegWatch')
                
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
                                render_chart_header('New org & user acquisition trend', 'acquisition_trend_watch', True, lambda: ui.run_javascript(f"downloadChart('{trend_chart_el.id}', 'New org and user acquisition trend')"), trend_df if 'trend_df' in locals() else orgs_df)
                            
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
                        create_device_browser_breakdown(results['device_browser'], 'RegWatch')

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
                        create_geographic_distribution_table(results['geographic_dist'], 'RegWatch')
            
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
                    'churn_signal': QUERIES['regwatch_conversion_churn_signal']
                }
                
                results = loader.execute_batch_queries(conversion_queries, start_date, end_date, platform='RegWatch')
                
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
                    ui.label('Engaged vs Churned User Comparison').classes('text-xl font-bold text-slate-900 mt-8 mb-4')
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
                        create_dormant_organizations_card(results['churn_signal'], 'RegWatch')
                        
                        # Right: Weekly Sign-up & Login Trend
                        create_weekly_signup_login_trend(results['signup_login_trend'])

                    # 2. Funnel Analysis (Full Width Row)
                    #ui.label('Landing Page Funnel Analysis').classes('text-xl font-bold text-slate-900 mt-8 mb-4')
                    #if not results['funnel_analysis'].empty:
                    #    df_raw = results['funnel_analysis'].copy()
                        
                        # Apply strict mapping
                    #    df_raw['landing_page_label'] = df_raw['landing_page'].apply(lambda x: map_path_to_landing(x, 'RegWatch'))
                    #    df_raw['next_action_label'] = df_raw['next_common_action'].apply(lambda x: map_path_to_module(x, 'RegWatch'))
                        
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
                        create_user_journey_section(results['user_journey'], platform_name='RegWatch', id='user_journeys')
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
                    start_date, end_date, platform='RegWatch'
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
                org_id = app.storage.user.get(ORG_SESSION_KEY)
                org_name = app.storage.user.get(ORG_NAME_SESSION_KEY, 'Unknown')
                start_date, end_date = get_current_dates()
                
                container.clear()
                with container:

                    # Render Section Header: ASSESSMENT ACTIVITY PULSE
                    with ui.row().classes('w-full items-center gap-2 mb-6 mt-4'):
                        with ui.element('div').classes('p-1.5 bg-orange-50 text-orange-500 rounded-lg flex items-center justify-center'):
                            ui.icon('bolt', size='1.2rem')
                        ui.label('ASSESSMENT ACTIVITY PULSE').classes('text-xs font-bold text-slate-500 tracking-widest')
                        ui.element('div').classes('flex-grow h-[1px] bg-slate-100 ml-4')

                    # Execute the query
                    assessment_df = pd.DataFrame()
                    try:
                        assessment_df = loader.execute_query(QUERIES['regwatch_assessment_summary'], [start_date, end_date])
                    except Exception as e:
                        print(f"Error executing regwatch_assessment_summary query: {e}")

                    # Parse results safely
                    if not assessment_df.empty:
                        row = assessment_df.iloc[0]
                        
                        def to_int(v):
                            return int(v) if pd.notna(v) else 0
                            
                        def to_float(v):
                            return float(v) if pd.notna(v) else 0.0

                        total_assessments = to_int(row.get('total_assessments'))
                        completed = to_int(row.get('completed'))
                        not_started = to_int(row.get('not_started'))
                        expired = to_int(row.get('expired'))
                        completion_rate = to_float(row.get('completion_rate_pct'))
                        avg_compliance = to_float(row.get('avg_compliance_pct'))
                        distinct_regs = to_int(row.get('distinct_regulations'))
                        distinct_assessors = to_int(row.get('distinct_assessors'))
                        avg_time_to_complete = to_float(row.get('avg_time_to_complete_min'))
                        avg_compliant = to_float(row.get('avg_compliant_items'))
                        avg_non_compliant = to_float(row.get('avg_non_compliant_items'))
                        avg_unanswered = to_float(row.get('avg_unanswered_items'))
                    else:
                        total_assessments = 0
                        completed = 0
                        not_started = 0
                        expired = 0
                        completion_rate = 0.0
                        avg_compliance = 0.0
                        distinct_regs = 0
                        distinct_assessors = 0
                        avg_time_to_complete = 0.0
                        avg_compliant = 0.0
                        avg_non_compliant = 0.0
                        avg_unanswered = 0.0

                    expired_pct = (expired / total_assessments * 100) if total_assessments > 0 else 0.0

                    def render_custom_kpi_card(title: str, value: str, subtitle: str = None, badge_text: str = None, badge_type: str = None, border_color: str = '#2563eb'):
                        with ui.card().classes('h-full p-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col justify-between hover:shadow-md transition-all duration-300 w-full') \
                                      .style(f'border-left: 4px solid {border_color} !important;'):
                            with ui.row().classes('w-full items-center justify-between mb-1 no-wrap shrink-0'):
                                ui.label(title).classes('text-[10px] font-bold text-slate-400 uppercase tracking-wider')
                                from data_engine.chart_descriptions import METRIC_INFO
                                m_id = title.lower().replace(' ', '_').replace('-', '_')
                                desc_data = METRIC_INFO.get(m_id)
                                if not desc_data:
                                    desc_data = {
                                        'title': title.title(),
                                        'description': f"Analytics and breakdown metrics for {title}."
                                    }
                                with ui.button(icon='info_outline').props('flat round size=xs').classes('text-slate-400 opacity-60 hover:opacity-100 p-0'):
                                    with ui.menu().classes('p-4 max-w-xs shadow-2xl rounded-xl border border-slate-100'):
                                        ui.label(desc_data['title']).classes('font-bold text-slate-900 mb-1')
                                        ui.label(desc_data['description']).classes('text-sm text-slate-600 leading-normal')
                                        
                            with ui.column().classes('gap-1 mt-auto w-full'):
                                ui.label(value).classes('text-2xl font-black text-slate-900 leading-none tracking-tight')
                                if badge_text:
                                    if badge_type == 'green':
                                        badge_cls = 'bg-emerald-50 text-emerald-700 border border-emerald-100'
                                    elif badge_type == 'orange':
                                        badge_cls = 'bg-amber-50 text-amber-700 border border-amber-100'
                                    elif badge_type == 'red':
                                        badge_cls = 'bg-rose-50 text-rose-700 border border-rose-100'
                                    else:
                                        badge_cls = 'bg-slate-50 text-slate-700 border border-slate-100'
                                    
                                    with ui.element('div').classes(f'inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold self-start mt-1.5 {badge_cls}'):
                                        ui.label(badge_text)
                                elif subtitle:
                                    ui.label(subtitle).classes('text-[10px] text-slate-400 font-semibold mt-1.5')

                    # 4 cards per row, organized in a beautifully symmetrical 4-column grid!
                    with ui.element('div').classes('grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 w-full gap-4 mb-6 items-stretch'):
                        render_custom_kpi_card('TOTAL ASSESSMENTS', f"{total_assessments}", subtitle='In selected period', border_color='#2563eb')
                        render_custom_kpi_card('COMPLETION RATE', f"{completion_rate:.0f}%", badge_text=f"{completed} completed", badge_type='green', border_color='#10b981')
                        render_custom_kpi_card('AVG COMPLIANCE', f"{avg_compliance:.0f}%", subtitle='Completed assessments', border_color='#06b6d4')
                        render_custom_kpi_card('EXPIRED', f"{expired}", badge_text=f"{expired_pct:.1f}% of total", badge_type='orange', border_color='#f59e0b')
                        render_custom_kpi_card('NOT STARTED', f"{not_started}", badge_text='Action needed', badge_type='red', border_color='#ef4444')
                        render_custom_kpi_card('DISTINCT ASSESSORS', f"{distinct_assessors}", subtitle='Across team', border_color='#6366f1')
                        render_custom_kpi_card('REGULATIONS COVERED', f"{distinct_regs}", subtitle='Regulations assessed', border_color='#1e3a8a')
                        render_custom_kpi_card('AVG TIME TO COMPLETE', f"{avg_time_to_complete:.1f}m", subtitle='Minutes per assessment', border_color='#8b5cf6')

                    trend_df = pd.DataFrame()
                    try:
                        trend_df = loader.execute_query(QUERIES['regwatch_assessment_trend_monthly'], [start_date, end_date])
                    except Exception as e:
                        print(f"Error executing regwatch_assessment_trend_monthly query: {e}")

                    status_df = pd.DataFrame()
                    try:
                        status_df = loader.execute_query(QUERIES['regwatch_assessment_status_breakdown'], [start_date, end_date])
                    except Exception as e:
                        print(f"Error executing regwatch_assessment_status_breakdown query: {e}")

                    deadline_df = pd.DataFrame()
                    try:
                        deadline_df = loader.execute_query(QUERIES['regwatch_deadline_adherence'], [start_date, end_date])
                    except Exception as e:
                        print(f"Error executing regwatch_deadline_adherence query: {e}")

                    score_df = pd.DataFrame()
                    try:
                        score_df = loader.execute_query(QUERIES['regwatch_compliance_score_distribution'], [start_date, end_date])
                    except Exception as e:
                        print(f"Error executing regwatch_compliance_score_distribution query: {e}")

                    coverage_df = pd.DataFrame()
                    try:
                        coverage_df = loader.execute_query(QUERIES['regwatch_regulatory_area_coverage'], [start_date, end_date])
                    except Exception as e:
                        print(f"Error executing regwatch_regulatory_area_coverage query: {e}")

                    repeat_df = pd.DataFrame()
                    try:
                        repeat_df = loader.execute_query(QUERIES['regwatch_repeat_assessment_rate'], [start_date, end_date])
                    except Exception as e:
                        print(f"Error executing regwatch_repeat_assessment_rate query: {e}")

                    regulator_df = pd.DataFrame()
                    try:
                        regulator_df = loader.execute_query(QUERIES['regwatch_regulator_usage'], [start_date, end_date])
                    except Exception as e:
                        print(f"Error executing regwatch_regulator_usage query: {e}")

                    low_comply_df = pd.DataFrame()
                    try:
                        low_comply_df = loader.execute_query(QUERIES['regwatch_low_compliance_regulations'], [start_date, end_date])
                    except Exception as e:
                        print(f"Error executing regwatch_low_compliance_regulations query: {e}")

                    # Parse trend_df safely
                    months_list = []
                    completed_list = []
                    expired_list = []
                    not_started_list = []
                    compliance_list = []
                    
                    avg_compliant_list = []
                    avg_non_compliant_list = []
                    avg_unanswered_list = []
                    
                    if not trend_df.empty:
                        for _, t_row in trend_df.iterrows():
                            m_val = t_row.get('month')
                            try:
                                m_name = pd.to_datetime(m_val).strftime('%b')
                            except Exception:
                                m_name = str(m_val)[:10]
                            
                            tot = int(t_row.get('total_started', 0) or 0)
                            comp = int(t_row.get('completed', 0) or 0)
                            exp = int(t_row.get('expired', 0) or 0)
                            not_st = max(0, tot - comp - exp)
                            
                            months_list.append(m_name)
                            completed_list.append(comp)
                            expired_list.append(exp)
                            not_started_list.append(not_st)
                            compliance_list.append(float(t_row.get('avg_compliance_pct', 0.0) or 0.0))
                            
                            avg_compliant_list.append(float(t_row.get('avg_compliant_items', 0.0) or 0.0))
                            avg_non_compliant_list.append(float(t_row.get('avg_non_compliant_items', 0.0) or 0.0))
                            avg_unanswered_list.append(float(t_row.get('avg_unanswered_items', 0.0) or 0.0))

                    # Parse score_df safely
                    score_bands_data = {
                        '100%': {'pct': 0.0, 'count': 0, 'color': '#10b981'},
                        '80–99%': {'pct': 0.0, 'count': 0, 'color': '#34d399'},
                        '60–79%': {'pct': 0.0, 'count': 0, 'color': '#d97706'},
                        '40–59%': {'pct': 0.0, 'count': 0, 'color': '#f97316'},
                        'Below 40%': {'pct': 0.0, 'count': 0, 'color': '#ef4444'}
                    }
                    
                    if not score_df.empty:
                        for _, s_row in score_df.iterrows():
                            band = str(s_row.get('score_band', ''))
                            clean_band = band
                            if '100' in band:
                                clean_band = '100%'
                            elif '80' in band:
                                clean_band = '80–99%'
                            elif '60' in band:
                                clean_band = '60–79%'
                            elif '40' in band:
                                clean_band = '40–59%'
                            elif 'Below' in band or 'under' in band or 'less' in band or '40' in band:
                                clean_band = 'Below 40%'
                            
                            if clean_band in score_bands_data:
                                score_bands_data[clean_band]['pct'] = float(s_row.get('pct', 0.0) or 0.0)
                                score_bands_data[clean_band]['count'] = int(s_row.get('assessments', 0) or 0)

                    # Parse coverage_df safely
                    coverage_data = []
                    if not coverage_df.empty:
                        for _, cov_row in coverage_df.iterrows():
                            area = str(cov_row.get('regulatory_area', ''))
                            run_count = int(cov_row.get('assessments_run', 0) or 0)
                            comp_pct = float(cov_row.get('avg_compliance_pct', 0.0) or 0.0)
                            coverage_data.append({
                                'area': area,
                                'count': run_count,
                                'pct': comp_pct
                            })

                    # Parse repeat_df safely
                    repeat_data = []
                    if not repeat_df.empty:
                        for _, rep_row in repeat_df.iterrows():
                            title = str(rep_row.get('regulation_title', ''))
                            times = int(rep_row.get('times_assessed', 0) or 0)
                            repeat_data.append({
                                'title': title,
                                'times': times
                            })

                    # Parse regulator_df safely
                    regulator_data = []
                    if not regulator_df.empty:
                        for _, reg_row in regulator_df.iterrows():
                            name = str(reg_row.get('regulator_name', ''))
                            code = str(reg_row.get('regulator_code', ''))
                            country = str(reg_row.get('regulator_country', ''))
                            runs = int(reg_row.get('assessments_run', 0) or 0)
                            regs_cnt = int(reg_row.get('distinct_regulations', 0) or 0)
                            pct = float(reg_row.get('avg_compliance_pct', 0.0) or 0.0)
                            regulator_data.append({
                                'name': name,
                                'code': code,
                                'country': country,
                                'runs': runs,
                                'regs_cnt': regs_cnt,
                                'pct': pct
                            })

                    # Parse low_comply_df safely
                    low_comply_data = []
                    if not low_comply_df.empty:
                        for _, low_row in low_comply_df.iterrows():
                            title = str(low_row.get('regulation_title', ''))
                            area = str(low_row.get('regulatory_area', ''))
                            risk = str(low_row.get('risk_level', ''))
                            pct = float(low_row.get('avg_compliance_pct', 0.0) or 0.0)
                            non_comply = float(low_row.get('avg_non_compliant_items', 0.0) or 0.0)
                            attempts = int(low_row.get('attempts', 0) or 0)
                            low_comply_data.append({
                                'title': title,
                                'area': area,
                                'risk': risk,
                                'pct': pct,
                                'non_comply': non_comply,
                                'attempts': attempts
                            })

                    # Parse status_df safely
                    status_donut_data = []
                    status_legend_data = []
                    if not status_df.empty:
                        for _, s_row in status_df.iterrows():
                            st_name = str(s_row.get('status', ''))
                            st_count = int(s_row.get('count', 0) or 0)
                            st_pct = float(s_row.get('pct', 0.0) or 0.0)
                            
                            if 'complete' in st_name.lower():
                                st_color = '#10b981' # green
                            elif 'expire' in st_name.lower():
                                st_color = '#f59e0b' # orange
                            else:
                                st_color = '#f43f5e' # rose/red
                            
                            status_donut_data.append({
                                'value': st_count,
                                'name': st_name,
                                'itemStyle': {'color': st_color}
                            })
                            status_legend_data.append({
                                'name': st_name,
                                'pct': f"{st_pct:.0f}%",
                                'color': st_color
                            })

                    # Parse deadline_df safely
                    on_time_count = 0
                    late_count = 0
                    missed_count = 0
                    total_adherence = 0
                    if not deadline_df.empty:
                        ad_row = deadline_df.iloc[0]
                        def to_int(v):
                            return int(v) if pd.notna(v) else 0
                        on_time_count = to_int(ad_row.get('completed_on_time'))
                        late_count = to_int(ad_row.get('completed_late'))
                        missed_count = to_int(ad_row.get('missed_deadline'))
                        total_adherence = to_int(ad_row.get('total'))
                        
                    on_time_pct = (on_time_count / total_adherence * 100) if total_adherence > 0 else 0
                    late_pct = (late_count / total_adherence * 100) if total_adherence > 0 else 0
                    missed_pct = (missed_count / total_adherence * 100) if total_adherence > 0 else 0

                    # 3-column layout grid (stretching to full width dynamically)
                    with ui.element('div').classes('grid grid-cols-1 lg:grid-cols-3 w-full gap-6 mt-6 items-stretch'):
                                      # Left Card: Monthly Assessment Volume & Avg Compliance (2/3 width)
                        with ui.card().classes('col-span-1 lg:col-span-2 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden w-full'):
                            with ui.row().classes('w-full items-start justify-between mb-2'):
                                render_chart_header('Monthly Assessment Volume & Avg Compliance', 'monthly_assessment_volume_watch', True, lambda: _download_csv_helper(trend_df, 'Monthly Assessment Volume and Avg Compliance'), trend_df)
                            
                            if not trend_df.empty:
                                ui.echart({
                                    'tooltip': {
                                        'trigger': 'axis',
                                        'axisPointer': {'type': 'shadow'}
                                    },
                                    'legend': {
                                        'data': ['Completed', 'Expired', 'Not Started', 'Avg Compliance %'],
                                        'bottom': 0,
                                        'icon': 'rect'
                                    },
                                    'grid': {
                                        'left': '3%',
                                        'right': '4%',
                                        'top': '15%',
                                        'bottom': '15%',
                                        'containLabel': True
                                    },
                                    'xAxis': [
                                        {
                                            'type': 'category',
                                            'data': months_list,
                                            'axisLine': {'lineStyle': {'color': '#cbd5e1'}},
                                            'axisLabel': {'color': '#64748b', 'fontWeight': 'bold'}
                                        }
                                    ],
                                    'yAxis': [
                                        {
                                            'type': 'value',
                                            'name': 'Assessments',
                                            'axisLine': {'lineStyle': {'color': '#cbd5e1'}},
                                            'axisLabel': {'color': '#64748b'},
                                            'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                                        },
                                        {
                                            'type': 'value',
                                            'name': 'Compliance %',
                                            'min': 0,
                                            'max': 100,
                                            'interval': 10,
                                            'axisLine': {'lineStyle': {'color': '#cbd5e1'}},
                                            'axisLabel': {'color': '#64748b', 'formatter': '{value}%'},
                                            'splitLine': {'show': False}
                                        }
                                    ],
                                    'series': [
                                        {
                                            'name': 'Completed',
                                            'type': 'bar',
                                            'stack': 'total',
                                            'barWidth': '40%',
                                            'data': completed_list,
                                            'itemStyle': {'color': '#10b981'}
                                        },
                                        {
                                            'name': 'Expired',
                                            'type': 'bar',
                                            'stack': 'total',
                                            'data': expired_list,
                                            'itemStyle': {'color': '#f59e0b'}
                                        },
                                        {
                                            'name': 'Not Started',
                                            'type': 'bar',
                                            'stack': 'total',
                                            'data': not_started_list,
                                            'itemStyle': {'color': '#f43f5e'}
                                        },
                                        {
                                            'name': 'Avg Compliance %',
                                            'type': 'line',
                                            'yAxisIndex': 1,
                                            'smooth': True,
                                            'symbol': 'circle',
                                            'symbolSize': 8,
                                            'lineStyle': {'width': 3, 'color': '#2563eb'},
                                            'itemStyle': {'color': '#2563eb'},
                                            'data': compliance_list
                                        }
                                    ]
                                }).classes('w-full h-80')
                            else:
                                ui.label('No monthly trend data available').classes('text-slate-400 italic py-20 text-center w-full text-sm')
 
                        # Right Card: Assessment Status Split & Deadline Adherence (1/3 width)
                        with ui.card().classes('col-span-1 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden justify-between w-full'):
                            
                            # Top half: Assessment Status Split
                            with ui.column().classes('w-full gap-0'):
                                with ui.row().classes('w-full items-start justify-between mb-2'):
                                    render_chart_header('Assessment Status Split', 'assessment_status_split_watch', True, lambda: _download_csv_helper(status_df, 'Assessment Status Split'), status_df)
                                
                                if not status_df.empty:
                                    with ui.row().classes('w-full items-center justify-between gap-4 flex-nowrap'):
                                        # Hollow Donut
                                        with ui.element('div').classes('w-[130px] h-[130px] shrink-0'):
                                            ui.echart({
                                                'series': [
                                                    {
                                                        'type': 'pie',
                                                        'radius': ['55%', '80%'],
                                                        'avoidLabelOverlap': False,
                                                        'label': {'show': False},
                                                        'labelLine': {'show': False},
                                                        'data': status_donut_data
                                                    }
                                                ]
                                            }).classes('w-full h-full')
                                        
                                        # Custom legend
                                        with ui.column().classes('flex-grow gap-2'):
                                            for leg in status_legend_data:
                                                with ui.row().classes('w-full items-center justify-between text-xs font-semibold'):
                                                    with ui.row().classes('items-center gap-2'):
                                                        ui.element('div').classes('w-2.5 h-2.5 rounded-full').style(f'background-color: {leg["color"]}')
                                                        ui.label(leg['name']).classes('text-slate-600')
                                                    ui.label(leg['pct']).classes('text-slate-800 font-bold')
                                else:
                                    ui.label('No status data available').classes('text-slate-400 italic py-8 text-center w-full text-sm')
 
                            # Bottom half: Deadline Adherence
                            with ui.column().classes('w-full gap-3 mt-6 border-t border-slate-100 pt-6'):
                                with ui.row().classes('w-full items-start justify-between mb-1'):
                                    render_chart_header('Deadline Adherence', 'deadline_adherence_watch', True, lambda: _download_csv_helper(deadline_df, 'Deadline Adherence'), deadline_df)
                                
                                if total_adherence > 0:
                                    # On Time
                                    with ui.row().classes('w-full items-center justify-between text-xs font-semibold flex-nowrap gap-2'):
                                        ui.label('On Time').classes('text-slate-600 w-24 shrink-0 truncate')
                                        with ui.element('div').classes('flex-grow bg-slate-100 h-2.5 rounded-full overflow-hidden'):
                                            ui.element('div').classes('h-full bg-emerald-500 rounded-full').style(f'width: {on_time_pct:.1f}%')
                                        ui.label(f"{on_time_count}").classes('text-emerald-600 font-bold w-6 text-right tabular-nums shrink-0')
                                        
                                    # Completed Late
                                    with ui.row().classes('w-full items-center justify-between text-xs font-semibold flex-nowrap gap-2'):
                                        ui.label('Completed Late').classes('text-slate-600 w-24 shrink-0 truncate')
                                        with ui.element('div').classes('flex-grow bg-slate-100 h-2.5 rounded-full overflow-hidden'):
                                            ui.element('div').classes('h-full bg-amber-500 rounded-full').style(f'width: {late_pct:.1f}%')
                                        ui.label(f"{late_count}").classes('text-amber-600 font-bold w-6 text-right tabular-nums shrink-0')
                                        
                                    # Missed / Expired
                                    with ui.row().classes('w-full items-center justify-between text-xs font-semibold flex-nowrap gap-2'):
                                        ui.label('Missed / Expired').classes('text-slate-600 w-24 shrink-0 truncate')
                                        with ui.element('div').classes('flex-grow bg-slate-100 h-2.5 rounded-full overflow-hidden'):
                                            ui.element('div').classes('h-full bg-rose-500 rounded-full').style(f'width: {missed_pct:.1f}%')
                                        ui.label(f"{missed_count}").classes('text-rose-600 font-bold w-6 text-right tabular-nums shrink-0')
                                else:
                                    ui.label('No deadline adherence data available').classes('text-slate-400 italic py-8 text-center w-full text-sm')

                    # Row 3: Compliance Score Distribution & Assessment Response Quality
                    with ui.element('div').classes('grid grid-cols-1 lg:grid-cols-2 w-full gap-6 mt-6 items-stretch'):
                        
                        # Left Card: Compliance Score Distribution
                        with ui.card().classes('col-span-1 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden w-full justify-between'):
                            with ui.row().classes('w-full items-start justify-between mb-2'):
                                render_chart_header('Compliance Score Distribution', 'compliance_score_distribution_watch', True, lambda: _download_csv_helper(score_df, 'Compliance Score Distribution'), score_df)
                            
                            with ui.column().classes('w-full gap-4 py-2 flex-grow justify-center'):
                                for band_name, band_info in score_bands_data.items():
                                    pct_val = band_info['pct']
                                    cnt_val = band_info['count']
                                    col_hex = band_info['color']
                                    
                                    with ui.row().classes('w-full items-center justify-between text-xs font-semibold flex-nowrap gap-4'):
                                        ui.label(band_name).classes('text-slate-600 w-20 shrink-0 font-bold')
                                        with ui.element('div').classes('flex-grow bg-slate-100 h-3.5 rounded-full overflow-hidden relative'):
                                            ui.element('div').classes('h-full rounded-full').style(f'background-color: {col_hex}; width: {pct_val}%;')
                                        with ui.row().classes('w-28 shrink-0 items-center justify-end gap-2'):
                                            ui.label(f"{pct_val:.0f}%").classes('text-slate-800 font-bold text-right w-10')
                                            ui.label(f"{cnt_val} runs").classes('text-slate-400 font-medium text-right w-14')
                                            
                        # Right Card: Assessment Response Quality
                        with ui.card().classes('col-span-1 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden justify-between w-full'):
                            with ui.row().classes('w-full items-start justify-between mb-2'):
                                render_chart_header('Assessment Response Quality', 'assessment_response_quality_watch', True, lambda: _download_csv_helper(trend_df, 'Assessment Response Quality'), trend_df)
                            
                            if not trend_df.empty:
                                ui.echart({
                                    'tooltip': {
                                        'trigger': 'axis',
                                        'axisPointer': {'type': 'shadow'}
                                    },
                                    'legend': {
                                        'data': ['Compliant', 'Non-Compliant', 'Unanswered'],
                                        'bottom': 0,
                                        'icon': 'rect'
                                    },
                                    'grid': {
                                        'left': '3%',
                                        'right': '4%',
                                        'top': '10%',
                                        'bottom': '15%',
                                        'containLabel': True
                                    },
                                    'xAxis': [
                                        {
                                            'type': 'category',
                                            'data': months_list,
                                            'axisLine': {'lineStyle': {'color': '#cbd5e1'}},
                                            'axisLabel': {'color': '#64748b', 'fontWeight': 'bold'}
                                        }
                                    ],
                                    'yAxis': [
                                        {
                                            'type': 'value',
                                            'axisLine': {'lineStyle': {'color': '#cbd5e1'}},
                                            'axisLabel': {'color': '#64748b'},
                                            'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                                        }
                                    ],
                                    'series': [
                                        {
                                            'name': 'Compliant',
                                            'type': 'bar',
                                            'stack': 'quality',
                                            'barWidth': '40%',
                                            'data': avg_compliant_list,
                                            'itemStyle': {'color': '#10b981'}
                                        },
                                        {
                                            'name': 'Non-Compliant',
                                            'type': 'bar',
                                            'stack': 'quality',
                                            'data': avg_non_compliant_list,
                                            'itemStyle': {'color': '#f43f5e'}
                                        },
                                        {
                                            'name': 'Unanswered',
                                            'type': 'bar',
                                            'stack': 'quality',
                                            'data': avg_unanswered_list,
                                            'itemStyle': {'color': '#f59e0b'}
                                        }
                                    ]
                                }).classes('w-full h-52')
                            else:
                                ui.label('No trend data available').classes('text-slate-400 italic py-16 text-center w-full text-sm')
                                
                            # Bottom Summary Box
                            with ui.column().classes('w-full mt-4 bg-slate-50 border border-slate-100 rounded-xl p-4 gap-2'):
                                ui.label('AVG PER COMPLETED ASSESSMENT').classes('text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1')
                                with ui.row().classes('w-full items-center justify-between gap-4'):
                                    with ui.column().classes('gap-0'):
                                        ui.label(f"{avg_compliant:.1f}").classes('text-2xl font-black text-emerald-600 leading-none tracking-tight')
                                        ui.label('Compliant').classes('text-[10px] font-bold text-slate-400 mt-1')
                                    with ui.column().classes('gap-0'):
                                        ui.label(f"{avg_non_compliant:.1f}").classes('text-2xl font-black text-rose-500 leading-none tracking-tight')
                                        ui.label('Non-compliant').classes('text-[10px] font-bold text-slate-400 mt-1')
                                    with ui.column().classes('gap-0'):
                                        ui.label(f"{avg_unanswered:.1f}").classes('text-2xl font-black text-amber-500 leading-none tracking-tight')
                                        ui.label('Unanswered').classes('text-[10px] font-bold text-slate-400 mt-1')

                    # Render Section Header: REGULATION COVERAGE
                    with ui.row().classes('w-full items-center gap-2 mb-6 mt-8'):
                        with ui.element('div').classes('p-1.5 bg-orange-50 text-orange-500 rounded-lg flex items-center justify-center'):
                            ui.icon('assignment', size='1.2rem')
                        ui.label('REGULATION COVERAGE').classes('text-xs font-bold text-slate-500 tracking-widest')
                        ui.element('div').classes('flex-grow h-[1px] bg-slate-100 ml-4')

                    # Row 4 Grid: 2 columns
                    with ui.element('div').classes('grid grid-cols-1 lg:grid-cols-2 w-full gap-6 mt-6 items-stretch'):
                        
                        # Left Card: Assessments by Regulatory Area
                        with ui.card().classes('col-span-1 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden w-full justify-between'):
                            with ui.row().classes('w-full items-start justify-between mb-2'):
                                render_chart_header('Assessments by Regulatory Area', 'assessments_by_regulatory_area_watch', True, lambda: _download_csv_helper(coverage_df, 'Assessments by Regulatory Area'), coverage_df)
                            
                            with ui.column().classes('w-full gap-4 py-2 flex-grow justify-center'):
                                if coverage_data:
                                    max_run = max(item['count'] for item in coverage_data) if coverage_data else 1
                                    
                                    # Cohesive colors from screenshot
                                    area_colors = {
                                        'AML / CFT': '#dc2626',
                                        'Data Protection': '#d97706',
                                        'KYC / CDD': '#10b981',
                                        'Consumer Protection': '#0d9488',
                                        'Capital Adequacy': '#2563eb',
                                        'Securities': '#4f46e5'
                                    }
                                    
                                    for cov_item in coverage_data:
                                        area_name = cov_item['area']
                                        run_cnt = cov_item['count']
                                        comp_pct = cov_item['pct']
                                        if pd.isna(comp_pct):
                                            comp_pct = 0.0
                                        
                                        bar_w = (run_cnt / max_run) * 100 if max_run > 0 else 0
                                        col_hex = area_colors.get(area_name, '#6366f1')
                                        
                                        # Dynamic compliance text color
                                        pct_color = 'text-emerald-600' if comp_pct >= 80 else ('text-amber-600' if comp_pct >= 60 else 'text-rose-600')
                                        
                                        with ui.row().classes('w-full items-center justify-between text-xs font-semibold flex-nowrap gap-4'):
                                            ui.label(area_name).classes('text-slate-600 w-36 shrink-0 font-bold truncate')
                                            with ui.element('div').classes('flex-grow bg-slate-100 h-3.5 rounded-full overflow-hidden relative'):
                                                ui.element('div').classes('h-full rounded-full').style(f'background-color: {col_hex}; width: {bar_w}%;')
                                            with ui.row().classes('w-20 shrink-0 items-center justify-end gap-2'):
                                                ui.label(f"{run_cnt}").classes('text-slate-400 font-medium text-right w-6')
                                                ui.label(f"{comp_pct:.0f}%").classes(f'{pct_color} font-bold text-right w-10')
                                else:
                                    ui.label('No regulatory area data available').classes('text-slate-400 italic py-16 text-center w-full text-sm')

                        # Right Card: Repeat Assessments (Same Regulation)
                        with ui.card().classes('col-span-1 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden w-full justify-between'):
                            with ui.row().classes('w-full items-start justify-between mb-2'):
                                render_chart_header('Repeat Assessments', 'repeat_assessments_watch', True, lambda: _download_csv_helper(repeat_df, 'Repeat Assessments'), repeat_df)
                            
                            with ui.column().classes('w-full gap-4 py-2 flex-grow justify-center'):
                                if repeat_data:
                                    max_times = max(item['times'] for item in repeat_data) if repeat_data else 1
                                    
                                    # Beautiful colorful sequence from screenshot
                                    color_seq = ['#dc2626', '#d97706', '#2563eb', '#10b981', '#0d9488', '#6366f1', '#8b5cf6']
                                    
                                    for idx, rep_item in enumerate(repeat_data[:6]):
                                        reg_title = rep_item['title']
                                        times_cnt = rep_item['times']
                                        
                                        bar_w = (times_cnt / max_times) * 100 if max_times > 0 else 0
                                        col_hex = color_seq[idx % len(color_seq)]
                                        
                                        with ui.row().classes('w-full items-center justify-between text-xs font-semibold flex-nowrap gap-4'):
                                            ui.label(reg_title).classes('text-slate-600 w-44 shrink-0 font-bold truncate')
                                            with ui.element('div').classes('flex-grow bg-slate-100 h-3.5 rounded-full overflow-hidden relative'):
                                                ui.element('div').classes('h-full rounded-full').style(f'background-color: {col_hex}; width: {bar_w}%;')
                                            with ui.row().classes('w-12 shrink-0 items-center justify-end'):
                                                ui.label(f"{times_cnt}x").classes('text-slate-400 font-bold text-right')
                                else:
                                    ui.label('No repeat assessments data available').classes('text-slate-400 italic py-16 text-center w-full text-sm')
                                    
                            # Bottom Dynamic Insight Box
                            num_repeat_regs = len(repeat_data)
                            with ui.column().classes('w-full mt-6 bg-blue-50/40 border border-blue-100 rounded-xl p-4 gap-2'):
                                with ui.row().classes('items-center gap-1.5'):
                                    ui.icon('lightbulb', size='1.2rem').classes('text-amber-500')
                                    ui.label('Insight').classes('text-xs font-black text-blue-700 uppercase tracking-wider')
                                ui.label(
                                    f"{num_repeat_regs} regulations reassessed 2+ times — likely driven by expiry-and-renewal cycles. "
                                    "These are candidate regulations for automated scheduling or alert nudges."
                                ).classes('text-xs font-medium text-slate-600 leading-normal')

                    # Row 5 Grid: Regulator Engagement and Low Compliance Alerts
                    with ui.element('div').classes('grid grid-cols-1 lg:grid-cols-2 w-full gap-6 mt-6 items-stretch'):
                        
                        # Left Card: Regulator Engagement
                        with ui.card().classes('col-span-1 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden w-full justify-between'):
                            with ui.row().classes('w-full items-start justify-between mb-2'):
                                render_chart_header('Regulator Engagement', 'regulator_engagement_watch', True, lambda: _download_csv_helper(regulator_df, 'Regulator Engagement'), regulator_df)
                            
                            with ui.column().classes('w-full flex-grow justify-start'):
                                if regulator_data:
                                    # Header row
                                    with ui.row().classes('w-full bg-slate-50 border-b border-slate-100 py-2.5 px-4 text-[10px] font-bold text-slate-400 uppercase tracking-wider flex-nowrap items-center mb-2'):
                                        ui.label('Regulator').classes('w-40 shrink-0')
                                        ui.label('Code').classes('w-12 shrink-0')
                                        ui.label('Country').classes('w-16 shrink-0')
                                        ui.label('Assessments').classes('w-20 shrink-0 text-right')
                                        ui.label('Regulations').classes('w-20 shrink-0 text-right')
                                        ui.label('Avg Compliance').classes('flex-grow text-left pl-4')
                                    
                                    # Body rows
                                    for reg_item in regulator_data:
                                        name = reg_item['name']
                                        code = reg_item['code']
                                        country = reg_item['country']
                                        runs = reg_item['runs']
                                        regs_cnt = reg_item['regs_cnt']
                                        pct = reg_item['pct']
                                        if pd.isna(pct):
                                            pct = 0.0
                                            
                                        bar_color = '#10b981' if pct >= 80 else ('#d97706' if pct >= 60 else '#dc2626')
                                        
                                        with ui.row().classes('w-full border-b border-slate-100 py-3 px-4 text-xs font-semibold text-slate-600 flex-nowrap items-center hover:bg-slate-50 transition-colors duration-150'):
                                            ui.label(name).classes('w-40 shrink-0 text-slate-700 font-bold truncate')
                                            ui.label(code).classes('w-12 shrink-0 text-slate-400 font-bold')
                                            ui.label(country).classes('w-16 shrink-0 text-slate-400 font-medium')
                                            ui.label(str(runs)).classes('w-20 shrink-0 text-right text-slate-600 font-bold')
                                            ui.label(str(regs_cnt)).classes('w-20 shrink-0 text-right text-blue-500 font-bold')
                                            
                                            with ui.row().classes('flex-grow items-center gap-2 pl-4 flex-nowrap'):
                                                with ui.element('div').classes('flex-grow bg-slate-100 h-2 rounded-full overflow-hidden max-w-[80px]'):
                                                    ui.element('div').classes('h-full rounded-full').style(f'background-color: {bar_color}; width: {pct}%')
                                                ui.label(f"{pct:.0f}%").classes('text-slate-700 font-bold w-8 text-right')
                                else:
                                    ui.label('No regulator engagement data available').classes('text-slate-400 italic py-16 text-center w-full text-sm')
                                    
                        # Right Card: Low Compliance Alerts (High Risk)
                        with ui.card().classes('col-span-1 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden w-full justify-between'):
                            with ui.row().classes('w-full items-start justify-between mb-2'):
                                render_chart_header('Low Compliance Alerts', 'low_compliance_alerts_watch', True, lambda: _download_csv_helper(low_comply_df, 'Low Compliance Alerts'), low_comply_df)
                            
                            with ui.column().classes('w-full flex-grow justify-start'):
                                if low_comply_data:
                                    # Header row
                                    with ui.row().classes('w-full bg-slate-50 border-b border-slate-100 py-2.5 px-4 text-[10px] font-bold text-slate-400 uppercase tracking-wider flex-nowrap items-center mb-2'):
                                        ui.label('Regulation').classes('w-52 shrink-0')
                                        ui.label('Area').classes('w-28 shrink-0 text-center')
                                        ui.label('Compliance').classes('flex-grow text-right')
                                    
                                    badge_colors = {
                                        'AML/CFT': {'bg': 'bg-rose-50', 'border': 'border-rose-100', 'text': 'text-rose-600'},
                                        'Data Protection': {'bg': 'bg-amber-50', 'border': 'border-amber-100', 'text': 'text-amber-600'},
                                        'KYC': {'bg': 'bg-orange-50', 'border': 'border-orange-100', 'text': 'text-orange-600'},
                                        'Securities': {'bg': 'bg-rose-50', 'border': 'border-rose-100', 'text': 'text-rose-600'}
                                    }
                                    
                                    for idx, item in enumerate(low_comply_data[:5]): # display top 5
                                        title = item['title']
                                        area = item['area']
                                        pct = item['pct']
                                        if pd.isna(pct):
                                            pct = 0.0
                                            
                                        clean_area = area
                                        if 'aml' in area.lower() or 'cft' in area.lower():
                                            clean_area = 'AML/CFT'
                                        elif 'data' in area.lower() or 'protect' in area.lower():
                                            clean_area = 'Data Protection'
                                        elif 'kyc' in area.lower() or 'cdd' in area.lower():
                                            clean_area = 'KYC'
                                        elif 'securit' in area.lower():
                                            clean_area = 'Securities'
                                            
                                        badge = badge_colors.get(clean_area, {'bg': 'bg-slate-50', 'border': 'border-slate-100', 'text': 'text-slate-600'})
                                        pct_color = 'text-rose-600' if pct < 60 else 'text-amber-600'
                                        
                                        with ui.row().classes('w-full border-b border-slate-100 py-3 px-4 text-xs font-semibold text-slate-600 flex-nowrap items-center hover:bg-slate-50 transition-colors duration-150'):
                                            ui.label(title).classes('w-52 shrink-0 text-slate-700 font-bold truncate')
                                            
                                            with ui.row().classes('w-28 shrink-0 justify-center'):
                                                with ui.element('div').classes(f'px-2.5 py-0.5 rounded-full border text-[10px] font-black uppercase tracking-wider {badge["bg"]} {badge["border"]} {badge["text"]}'):
                                                    ui.label(area)
                                                    
                                            ui.label(f"{pct:.0f}%").classes(f'flex-grow text-right font-black text-sm {pct_color}')
                                else:
                                    ui.label('No low-compliance alerts available').classes('text-slate-400 italic py-16 text-center w-full text-sm')

            refresh_callbacks.append(load_data)
            asyncio.create_task(load_data())
            
        async def organization_deep_dive_content():

            with ui.column().classes('w-full gap-4') as outer:
                # ---- Page header ----
                ui.label('Organization Deep-Dive').classes(ThemeManager.TYPOGRAPHY['h2'] + ' mb-1')
                ui.label(
                    'Explore activity, engagement and usage metrics for the selected organization and date range.'
                ).classes(ThemeManager.TYPOGRAPHY['body'] + ' mb-4')

                # ---- Data results area (populated on selection / date change) ----
                data_container = ui.column().classes('w-full mt-2')


            async def load_org_data():
                """Re-fetch and render metrics for the currently selected org+date."""
                org_id   = app.storage.user.get(ORG_SESSION_KEY)
                org_name = app.storage.user.get(ORG_NAME_SESSION_KEY, 'Unknown')
                start_date, end_date = get_current_dates()

                def render_premium_vertical_kpi_card(
                    title: str,
                    value: str,
                    unit: str = None,
                    subtitle: str = None,
                    badge_text: str = None,
                    badge_type: str = None,
                    border_color_class: str = 'border-l-blue-500',
                    metric_id: str = None
                ):
                    with ui.element('div').classes(
                        f'col-span-1 p-3.5 bg-white border border-slate-100 rounded-xl shadow-xs '
                        f'border-l-4 {border_color_class} relative overflow-hidden flex flex-col '
                        f'justify-between h-[115px] hover:shadow-md hover:scale-[1.02] cursor-pointer '
                        f'transition-all duration-300 w-full'
                    ):
                        # Title
                        with ui.row().classes('w-full justify-between items-center no-wrap'):
                            ui.label(title).classes('text-[9px] font-black text-slate-400 tracking-wider uppercase truncate')
                            render_kpi_info_icon(metric_id or title)
                        
                        # Value
                        with ui.row().classes('items-baseline gap-0.5 mt-1'):
                            ui.label(value).classes('text-2xl font-black text-slate-800 tracking-tight leading-none')
                            if unit:
                                ui.label(unit).classes('text-xs font-black text-slate-400')
                        
                        # Subtitle or Badge at the bottom
                        with ui.element('div').classes('mt-auto w-full'):
                            if badge_text:
                                if badge_type == 'green':
                                    badge_cls = 'bg-emerald-50 text-emerald-700 border-emerald-100'
                                elif badge_type == 'orange':
                                    badge_cls = 'bg-amber-50 text-amber-700 border-amber-100'
                                elif badge_type == 'red':
                                    badge_cls = 'bg-rose-50 text-rose-700 border-rose-100'
                                else:
                                    badge_cls = 'bg-slate-50 text-slate-700 border-slate-100'
                                
                                with ui.element('div').classes(f'inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold border {badge_cls} max-w-full truncate'):
                                    ui.label(badge_text)
                            elif subtitle:
                                ui.label(subtitle).classes('text-[10px] font-semibold text-slate-400 truncate')

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

                header_df = pd.DataFrame()
                try:
                    header_df = loader.execute_query(QUERIES['regwatch_deep_org_profile'], [org_id])
                except Exception as e:
                    print(f"Error executing regwatch_deep_org_profile query: {e}")

                ga4_summary_df = pd.DataFrame()
                try:
                    ga4_summary_df = loader.execute_query(QUERIES['regwatch_deep_ga4_summary'], [org_id, start_date, end_date])
                except Exception as e:
                    print(f"Error executing regwatch_deep_ga4_summary query: {e}")

                northstar_events_df = pd.DataFrame()
                try:
                    northstar_events_df = loader.execute_query(QUERIES['regwatch_deep_northstar_events'], [org_id, start_date, end_date])
                except Exception as e:
                    print(f"Error executing regwatch_deep_northstar_events query: {e}")

                assessment_summary_df = pd.DataFrame()
                try:
                    assessment_summary_df = loader.execute_query(QUERIES['regwatch_deep_assessment_summary'], [org_id, start_date, end_date])
                except Exception as e:
                    print(f"Error executing regwatch_deep_assessment_summary query: {e}")

                weekly_pattern_df = pd.DataFrame()
                try:
                    weekly_pattern_df = loader.execute_query(QUERIES['product_deep_ga4_weekly_pattern'], [org_id, PLATFORM, start_date, end_date])
                except Exception as e:
                    print(f"Error executing product_deep_ga4_weekly_pattern: {e}")

                traffic_source_df = pd.DataFrame()
                try:
                    traffic_source_df = loader.execute_query(QUERIES['product_deep_traffic_source'], [org_id, PLATFORM, start_date, end_date])
                except Exception as e:
                    print(f"Error executing product_deep_traffic_source: {e}")

                regwatch_deep_assessment_monthly_df = pd.DataFrame()
                try:
                    regwatch_deep_assessment_monthly_df = loader.execute_query(QUERIES['regwatch_deep_assessment_monthly'], [org_id, start_date, end_date])
                except Exception as e:
                    print(f"Error executing regwatch_deep_assessment_monthly: {e}")

                regwatch_deep_time_to_complete_df = pd.DataFrame()
                try:
                    regwatch_deep_time_to_complete_df = loader.execute_query(QUERIES['regwatch_deep_time_to_complete'], [org_id, start_date, end_date])
                except Exception as e:
                    print(f"Error executing regwatch_deep_time_to_complete: {e}")

                regwatch_deep_deadline_adherence_df = pd.DataFrame()
                try:
                    regwatch_deep_deadline_adherence_df = loader.execute_query(QUERIES['regwatch_deep_deadline_adherence'], [org_id, start_date, end_date])
                except Exception as e:
                    print(f"Error executing regwatch_deep_deadline_adherence: {e}")

                regwatch_deep_compliance_score_dist_df = pd.DataFrame()
                try:
                    regwatch_deep_compliance_score_dist_df = loader.execute_query(QUERIES['regwatch_deep_compliance_score_dist'], [org_id, start_date, end_date])
                except Exception as e:
                    print(f"Error executing regwatch_deep_compliance_score_dist: {e}")

                regwatch_deep_compliance_trend_df = pd.DataFrame()
                try:
                    regwatch_deep_compliance_trend_df = loader.execute_query(QUERIES['regwatch_deep_compliance_trend'], [org_id, start_date, end_date])
                except Exception as e:
                    print(f"Error executing regwatch_deep_compliance_trend: {e}")

                regwatch_deep_compliance_summary_df = pd.DataFrame()
                try:
                    regwatch_deep_compliance_summary_df = loader.execute_query(QUERIES['regwatch_deep_compliance_summary'], [org_id, start_date, end_date])
                except Exception as e:
                    print(f"Error executing regwatch_deep_compliance_summary: {e}")

                regwatch_deep_low_compliance_regs_df = pd.DataFrame()
                try:
                    regwatch_deep_low_compliance_regs_df = loader.execute_query(QUERIES['regwatch_deep_low_compliance_regs'], [org_id, start_date, end_date])
                except Exception as e:
                    print(f"Error executing regwatch_deep_low_compliance_regs: {e}")

                regwatch_deep_compliance_improvement_df = pd.DataFrame()
                try:
                    regwatch_deep_compliance_improvement_df = loader.execute_query(QUERIES['regwatch_deep_compliance_improvement'], [org_id, start_date, end_date])
                except Exception as e:
                    print(f"Error executing regwatch_deep_compliance_improvement: {e}")

                regwatch_deep_regulatory_area_df = pd.DataFrame()
                try:
                    regwatch_deep_regulatory_area_df = loader.execute_query(QUERIES['regwatch_deep_regulatory_area'], [org_id, start_date, end_date])
                except Exception as e:
                    print(f"Error executing regwatch_deep_regulatory_area: {e}")

                regwatch_deep_risk_level_profile_df = pd.DataFrame()
                try:
                    regwatch_deep_risk_level_profile_df = loader.execute_query(QUERIES['regwatch_deep_risk_level_profile'], [org_id, start_date, end_date])
                except Exception as e:
                    print(f"Error executing regwatch_deep_risk_level_profile: {e}")

                regwatch_deep_regulator_breakdown_df = pd.DataFrame()
                try:
                    regwatch_deep_regulator_breakdown_df = loader.execute_query(QUERIES['regwatch_deep_regulator_breakdown'], [org_id, start_date, end_date])
                except Exception as e:
                    print(f"Error executing regwatch_deep_regulator_breakdown: {e}")

                regwatch_deep_top_regulations_df = pd.DataFrame()
                try:
                    regwatch_deep_top_regulations_df = loader.execute_query(QUERIES['regwatch_deep_top_regulations'], [org_id, start_date, end_date])
                except Exception as e:
                    print(f"Error executing regwatch_deep_top_regulations: {e}")

                regwatch_deep_assessor_leaderboard_df = pd.DataFrame()
                try:
                    regwatch_deep_assessor_leaderboard_df = loader.execute_query(QUERIES['regwatch_deep_assessor_leaderboard'], [org_id, start_date, end_date])
                except Exception as e:
                    print(f"Error executing regwatch_deep_assessor_leaderboard: {e}")

                regwatch_deep_assessor_monthly_activity_df = pd.DataFrame()
                try:
                    regwatch_deep_assessor_monthly_activity_df = loader.execute_query(QUERIES['regwatch_deep_assessor_monthly_activity'], [org_id, start_date, end_date])
                except Exception as e:
                    print(f"Error executing regwatch_deep_assessor_monthly_activity: {e}")

                daily_trend_df = pd.DataFrame()
                try:
                    daily_trend_df = loader.execute_query(QUERIES['regwatch_org_engagement_daily_trend'], [org_id, PLATFORM, start_date, end_date])
                except Exception as e:
                    print(f"Error executing regwatch_org_engagement_daily_trend: {e}")

                device_df = pd.DataFrame()
                try:
                    device_df = loader.execute_query(QUERIES['regwatch_org_session_device_split'], [org_id, PLATFORM, start_date, end_date])
                except Exception as e:
                    print(f"Error executing regwatch_org_session_device_split: {e}")

                traffic_df = pd.DataFrame()
                try:
                    traffic_df = loader.execute_query(QUERIES['regwatch_org_traffic_source'], [org_id, PLATFORM, start_date, end_date])
                except Exception as e:
                    print(f"Error executing regwatch_org_traffic_source: {e}")

                org_uj_df = pd.DataFrame()
                try:
                    org_uj_df = loader.execute_query(QUERIES['org_user_journey_paths'], [start_date, end_date, org_id, PLATFORM])
                except Exception as e:
                    print(f"Error executing org_user_journey_paths in RegWatch: {e}")

                # Extra metadata for lifespan check
                org_info = org_data_map.get(org_name, {})
                org_start = org_info.get('organization_start_date')
                org_domain = org_info.get('email_domain', 'N/A')

                data_container.clear()
                with data_container:
                    if header_df.empty:
                        row = {
                            'organizationName': org_name,
                            'email': 'N/A',
                            'emailDomain': org_domain,
                            'industry': 'Unknown Industry',
                            'employeeSize': 'Unknown Size',
                            'description': 'No description available.',
                            'services': 'N/A',
                            'country_name': 'Unknown',
                            'isActive': True,
                            'isRegTechOrg': False,
                            'days_since_onboarding': 0,
                            'days_since_last_profile_update': 0
                        }
                    else:
                        row = header_df.iloc[0]

                    # Parse fields cleanly
                    display_name = row['organizationName']
                    industry = row['industry'] if pd.notna(row['industry']) else 'Unknown Industry'
                    email = row['email']
                    email_domain = row['emailDomain'] if pd.notna(row['emailDomain']) else org_domain
                    
                    # Mask email cleanly in full without ...
                    if pd.notna(email) and '@' in str(email):
                        email_str = str(email)
                        parts = email_str.split('@')
                        name_part, domain_part = parts[0], parts[1]
                        if len(name_part) <= 2:
                            masked_email = f"{name_part}***@{domain_part}"
                        else:
                            masked_email = f"{name_part[:2]}***@{domain_part}"
                    else:
                        masked_email = email_domain

                    days_onboard = int(row['days_since_onboarding']) if pd.notna(row['days_since_onboarding']) else 0
                    onboarded_str = f"Onboarded {days_onboard} days ago" if days_onboard > 0 else "Onboarded today"
                    
                    country = row['country_name'] if pd.notna(row['country_name']) else 'Unknown'
                    employee_size = row['employeeSize'] if pd.notna(row['employeeSize']) else 'Unknown Size'
                    
                    is_active = row['isActive'] if pd.notna(row['isActive']) else True
                    status_color = 'emerald' if is_active else 'slate'
                    status_text = 'Active Account' if is_active else 'Inactive Account'
                    
                    is_regtech = row['isRegTechOrg'] if pd.notna(row['isRegTechOrg']) else False
                    regtech_text = 'RegTech Partner' if is_regtech else 'Standard Org'
                    regtech_bg = 'bg-blue-50 text-blue-600 border border-blue-100' if is_regtech else 'bg-slate-50 text-slate-500 border border-slate-100'
                    
                    employee_text = f"Employees: {employee_size}"
                    
                    days_update = int(row['days_since_last_profile_update']) if pd.notna(row['days_since_last_profile_update']) else 0
                    update_str = f"Profile updated {days_update} days ago" if days_update > 0 else "Profile updated today"

                    # Render Beautiful Responsive Header Card (matching regcomply/regport style exactly)
                    with ui.card().classes('relative overflow-hidden w-full p-6 border border-slate-200 shadow-sm bg-white rounded-xl mb-6 hover:shadow-md transition-all duration-300'):
                        # Premium top border strip (blue to teal gradient)
                        ui.element('div').classes('absolute top-0 left-0 right-0 h-[4px] bg-gradient-to-r from-blue-500 via-indigo-600 to-teal-500')
                        
                        with ui.row().classes('w-full justify-between items-start flex-wrap gap-6 pt-1'):
                            # Left side: Title and Metadata
                            with ui.column().classes('flex-1 min-w-[280px] gap-3.5'):
                                
                                # Title
                                ui.label(display_name).classes('rp-org-name')
                                
                                # Description
                                if pd.notna(row.get('description')) and str(row.get('description')).strip():
                                    ui.label(str(row.get('description'))).classes('text-xs text-slate-500 italic mt-1 max-w-3xl leading-relaxed')
                                
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
                                            ui.label(masked_email).classes('rp-org-meta')
                                        with ui.row().classes('items-center gap-2'):
                                            ui.icon('event', size='16px').classes('text-slate-400')
                                            ui.label(onboarded_str).classes('rp-org-meta')
                                            
                                    # Row 3: Country & Profile Update (with flex wrap)
                                    with ui.row().classes('items-center flex-wrap gap-x-4 gap-y-2'):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.icon('flag', size='16px').classes('text-slate-400')
                                            ui.label(country).classes('rp-org-meta')
                                        with ui.row().classes('items-center gap-2'):
                                            ui.icon('schedule', size='16px').classes('text-slate-400')
                                            with ui.row().classes('items-center gap-1'):
                                                ui.label(update_str).classes('rp-org-meta-bold')
                                                
                            # Right side: Badges row
                            with ui.row().classes('flex flex-col sm:flex-row flex-wrap gap-2 items-start sm:items-center justify-start sm:justify-end mt-1 sm:mt-0'):
                                
                                # 1. Active / Status badge
                                with ui.row().classes(f'bg-{status_color}-50 text-{status_color}-600 border border-{status_color}-100 rounded-full px-3 py-1 items-center gap-1.5 font-semibold text-[11px] shadow-xs'):
                                    ui.element('span').classes(f'w-1.5 h-1.5 rounded-full bg-{status_color}-500')
                                    ui.label(status_text)
                                    
                                # 2. Tier / RegTech Partner badge
                                with ui.row().classes(f'{regtech_bg} rounded-full px-3 py-1 items-center font-semibold text-[11px] shadow-xs'):
                                    ui.label(regtech_text)
                                    
                                # 3. Employee Size badge
                                with ui.row().classes('bg-purple-50 text-purple-600 border border-purple-100 rounded-full px-3 py-1 items-center font-semibold text-[11px] shadow-xs'):
                                    ui.label(employee_text)

                    # KPI Data preparation
                    if ga4_summary_df.empty or pd.isna(ga4_summary_df.iloc[0]['total_sessions']):
                        active_days = 0
                        total_sessions = 0
                        total_engaged_sessions = 0
                        engaged_session_pct = 0.0
                        avg_session_min = 0.0
                        total_signed_in_users = 0
                        avg_daily_active_users = 0.0
                    else:
                        g_row = ga4_summary_df.iloc[0]
                        active_days = int(g_row['active_days']) if pd.notna(g_row['active_days']) else 0
                        total_sessions = int(g_row['total_sessions']) if pd.notna(g_row['total_sessions']) else 0
                        total_engaged_sessions = int(g_row['total_engaged_sessions']) if pd.notna(g_row['total_engaged_sessions']) else 0
                        engaged_session_pct = float(g_row['engaged_session_pct']) if pd.notna(g_row['engaged_session_pct']) else 0.0
                        avg_session_min = float(g_row['avg_session_engagement_min']) if pd.notna(g_row['avg_session_engagement_min']) else 0.0
                        total_signed_in_users = int(g_row['total_signed_in_users']) if pd.notna(g_row['total_signed_in_users']) else 0
                        avg_daily_active_users = float(g_row['avg_daily_active_users']) if pd.notna(g_row['avg_daily_active_users']) else 0.0
                    
                    if northstar_events_df.empty:
                        total_reg_views = 0
                    else:
                        total_reg_views = int(northstar_events_df['regulation_views'].sum())

                    # Render Subtitle block for Platform Engagement with an elegant separator line
                    with ui.row().classes('w-full items-center gap-2 mb-4 mt-6'):
                        with ui.element('div').classes('p-2 bg-slate-50 border border-slate-100 rounded-lg flex items-center justify-center shadow-xs'):
                            ui.icon('bolt', size='16px').classes('text-indigo-500')
                        ui.label('Platform Engagement').classes('rp-section-label')
                        ui.element('div').classes('flex-grow h-px bg-slate-200/60 ml-2')

                    # 6 Premium Interactive Vertical KPI Cards matching the user's screenshot exactly!
                    with ui.element('div').classes('grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 w-full gap-4'):
                        render_premium_vertical_kpi_card('TOTAL SESSIONS', f"{total_sessions:,}", subtitle='In date range', border_color_class='border-l-blue-500', metric_id='total_sessions')
                        render_premium_vertical_kpi_card('ENGAGED SESSIONS', f"{engaged_session_pct:.0f}", unit='%', badge_text=f"{total_engaged_sessions:,} of {total_sessions:,}", badge_type='green', border_color_class='border-l-emerald-500', metric_id='engagement_rate')
                        render_premium_vertical_kpi_card('AVG SESSION TIME', f"{avg_session_min:.1f}", unit='m', subtitle='Per session', border_color_class='border-l-teal-600', metric_id='avg_session_time')
                        render_premium_vertical_kpi_card('ACTIVE DAYS', f"{active_days:,}", subtitle='Days with sessions', border_color_class='border-l-amber-600', metric_id='active_days')
                        render_premium_vertical_kpi_card('REGULATION VIEWS', f"{total_reg_views:,}", subtitle='Northstar events', border_color_class='border-l-purple-500', metric_id='regulation_views')
                        render_premium_vertical_kpi_card('SIGNED-IN USERS', f"{int(avg_daily_active_users)}", subtitle='Avg daily peak', border_color_class='border-l-indigo-500', metric_id='active_signed_in_users')

                    # Beautiful Charts Grid below KPI cards (Daily Active Users & Sessions + Session Device Split & Traffic Sources table)
                    with ui.grid(columns=5).classes('w-full gap-6 mt-6 items-stretch'):
                        
                        # Left card: Daily Active Users & Sessions (3/5 width on desktop)
                        with ui.card().classes('col-span-3 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden'):
                            with ui.row().classes('w-full items-start justify-between mb-1'):
                                render_chart_header('Daily Active Users & Sessions', 'daily_active_users_sessions_watch', True, lambda: ui.run_javascript(f"downloadChart('{daily_trend_chart_el.id}', 'Daily Active Users and Sessions')"), daily_trend_df)
                            
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
                                render_chart_header('Session Device Split', 'session_device_split_watch', True, lambda: ui.run_javascript(f"downloadChart('{device_donut_chart_el.id}', 'Session Device Split')"), device_df)
                            
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
                            
                            
                    # Beautiful Charts Grid below Platform Engagement KPI cards
                    with ui.grid(columns=5).classes('w-full gap-6 mt-6 items-stretch'):
                        
                        # Left card: Day-of-Week Engagement Pattern (3/5 width on desktop)
                        with ui.card().classes('col-span-3 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden'):
                            with ui.row().classes('w-full items-start justify-between mb-1'):
                                render_chart_header('Day-of-Week Engagement Pattern', 'day_of_week_engagement_watch', True, lambda: ui.run_javascript(f"downloadChart('{weekly_pattern_chart_el.id}', 'Day of Week Engagement Pattern')"), weekly_pattern_df)
                            
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
                                render_chart_header('Top Traffic Sources', 'top_traffic_sources_watch', True, lambda: _download_csv_helper(traffic_source_df, 'Top Traffic Sources'), traffic_source_df)
                            
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

                    # Assessment Behaviour Data preparation
                    if assessment_summary_df.empty:
                        total_assessments = 0
                        completed = 0
                        not_started = 0
                        expired = 0
                        completion_rate_pct = 0.0
                        expiry_rate_pct = 0.0
                        distinct_regulations = 0
                        distinct_assessors = 0
                    else:
                        as_row = assessment_summary_df.iloc[0]
                        total_assessments = int(as_row['total_assessments']) if pd.notna(as_row['total_assessments']) else 0
                        completed = int(as_row['completed']) if pd.notna(as_row['completed']) else 0
                        not_started = int(as_row['not_started']) if pd.notna(as_row['not_started']) else 0
                        expired = int(as_row['expired']) if pd.notna(as_row['expired']) else 0
                        completion_rate_pct = float(as_row['completion_rate_pct']) if pd.notna(as_row['completion_rate_pct']) else 0.0
                        expiry_rate_pct = float(as_row['expiry_rate_pct']) if pd.notna(as_row['expiry_rate_pct']) else 0.0
                        distinct_regulations = int(as_row['distinct_regulations']) if pd.notna(as_row['distinct_regulations']) else 0
                        distinct_assessors = int(as_row['distinct_assessors']) if pd.notna(as_row['distinct_assessors']) else 0

                    # Parse true time-to-complete values from database
                    avg_time = 0.0
                    median_time = 0.0
                    if not regwatch_deep_time_to_complete_df.empty:
                        time_row = regwatch_deep_time_to_complete_df.iloc[0]
                        avg_time = float(time_row['avg_minutes']) if pd.notna(time_row['avg_minutes']) else 0.0
                        median_time = float(time_row['median_minutes']) if pd.notna(time_row['median_minutes']) else 0.0

                    # Parse true overdue count from database
                    overdue = 0
                    if not regwatch_deep_deadline_adherence_df.empty:
                        adh_row = regwatch_deep_deadline_adherence_df.iloc[0]
                        overdue = int(adh_row['overdue_not_started']) if pd.notna(adh_row['overdue_not_started']) else 0

                    # Render Subtitle block for Assessment Behaviour with an elegant separator line and database reference
                    with ui.row().classes('w-full items-center justify-between mb-4 mt-8 flex-nowrap'):
                        with ui.row().classes('items-center gap-2 flex-nowrap'):
                            with ui.element('div').classes('p-2 bg-slate-50 border border-slate-100 rounded-lg flex items-center justify-center shadow-xs'):
                                ui.icon('assignment', size='16px').classes('text-indigo-500')
                            ui.label('02 Assessment Behaviour').classes('rp-section-label whitespace-nowrap')

                    with ui.element('div').classes('grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 w-full gap-4'):
                        render_premium_vertical_kpi_card('TOTAL ASSESSMENTS', f"{total_assessments:,}", subtitle='In date range', border_color_class='border-l-blue-500')
                        render_premium_vertical_kpi_card('COMPLETION RATE', f"{completion_rate_pct:.0f}", unit='%', badge_text=f"{completed:,} completed", badge_type='green', border_color_class='border-l-emerald-500')
                        render_premium_vertical_kpi_card('EXPIRY RATE', f"{expiry_rate_pct:.0f}", unit='%', badge_text=f"{expired:,} expired", badge_type='orange', border_color_class='border-l-amber-600')
                        render_premium_vertical_kpi_card('AVG TIME TO COMPLETE', f"{avg_time:.1f}", unit='m', subtitle=f"Median: {median_time:.1f}m", border_color_class='border-l-teal-600')
                        render_premium_vertical_kpi_card('NOT STARTED', f"{not_started:,}", badge_text=f"{overdue:,} overdue", badge_type='red', border_color_class='border-l-red-500')
                        render_premium_vertical_kpi_card('DISTINCT REGS', f"{distinct_regulations:,}", subtitle='Unique regulations', border_color_class='border-l-purple-500')

                    # Parse Monthly Volume & Compliance
                    months_list = []
                    completed_list = []
                    expired_list = []
                    not_started_list = []
                    compliance_list = []

                    if not regwatch_deep_assessment_monthly_df.empty:
                        for _, row in regwatch_deep_assessment_monthly_df.iterrows():
                            dt = pd.to_datetime(row['month'])
                            months_list.append(dt.strftime('%b') if pd.notna(dt) else '')
                            completed_list.append(int(row['completed']) if pd.notna(row['completed']) else 0)
                            expired_list.append(int(row['expired']) if pd.notna(row['expired']) else 0)
                            not_started_list.append(int(row['not_started']) if pd.notna(row['not_started']) else 0)
                            compliance_list.append(float(row['avg_compliance_pct']) if pd.notna(row['avg_compliance_pct']) else 0.0)

                    # Parse Deadline Adherence
                    on_time_cnt = 0
                    late_cnt = 0
                    missed_cnt = 0
                    total_adh = 0
                    if not regwatch_deep_deadline_adherence_df.empty:
                        row = regwatch_deep_deadline_adherence_df.iloc[0]
                        on_time_cnt = int(row['on_time']) if pd.notna(row['on_time']) else 0
                        late_cnt = int(row['late']) if pd.notna(row['late']) else 0
                        missed_cnt = (int(row['expired_missed']) if pd.notna(row['expired_missed']) else 0) + (int(row['overdue_not_started']) if pd.notna(row['overdue_not_started']) else 0)
                        total_adh = int(row['total']) if pd.notna(row['total']) else (on_time_cnt + late_cnt + missed_cnt)

                    on_time_pct = (on_time_cnt / total_adh * 100) if total_adh > 0 else 0.0
                    late_pct = (late_cnt / total_adh * 100) if total_adh > 0 else 0.0
                    missed_pct = (missed_cnt / total_adh * 100) if total_adh > 0 else 0.0

                    # Parse Time-to-Complete Buckets
                    under_5 = 0
                    btw_5_30 = 0
                    over_30 = 0
                    if not regwatch_deep_time_to_complete_df.empty:
                        row = regwatch_deep_time_to_complete_df.iloc[0]
                        under_5 = int(row['under_5_min']) if pd.notna(row['under_5_min']) else 0
                        btw_5_30 = int(row['btw_5_30_min']) if pd.notna(row['btw_5_30_min']) else 0
                        over_30 = int(row['over_30_min']) if pd.notna(row['over_30_min']) else 0

                    # Beautiful charts grid below the 6 KPI cards
                    with ui.grid(columns=5).classes('w-full gap-6 mt-6 items-stretch'):
                         # Left card: Monthly Assessment Volume & Avg Compliance (3/5 width)
                        with ui.card().classes('col-span-3 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden w-full'):
                            with ui.row().classes('w-full items-start justify-between mb-2'):
                                render_chart_header('Monthly Assessment Volume & Compliance', 'monthly_assessment_volume_deep_watch', True, lambda: _download_csv_helper(regwatch_deep_assessment_monthly_df, 'Monthly Assessment Volume and Compliance'), regwatch_deep_assessment_monthly_df)
                            
                            ui.echart({
                                'tooltip': {
                                    'trigger': 'axis',
                                    'axisPointer': {'type': 'shadow'}
                                },
                                'legend': {
                                    'data': ['Completed', 'Expired', 'Not Started', 'Avg Compliance'],
                                    'bottom': 0,
                                    'icon': 'rect'
                                },
                                'grid': {
                                    'left': '3%',
                                    'right': '4%',
                                    'top': '15%',
                                    'bottom': '15%',
                                    'containLabel': True
                                },
                                'xAxis': [
                                    {
                                        'type': 'category',
                                        'data': months_list,
                                        'axisLine': {'lineStyle': {'color': '#cbd5e1'}},
                                        'axisLabel': {'color': '#64748b', 'fontWeight': 'bold'}
                                    }
                                ],
                                'yAxis': [
                                    {
                                        'type': 'value',
                                        'name': 'Assessments',
                                        'axisLine': {'lineStyle': {'color': '#cbd5e1'}},
                                        'axisLabel': {'color': '#64748b'},
                                        'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                                    },
                                    {
                                        'type': 'value',
                                        'name': 'Compliance %',
                                        'min': 0,
                                        'max': 100,
                                        'interval': 20,
                                        'axisLine': {'lineStyle': {'color': '#cbd5e1'}},
                                        'axisLabel': {'color': '#64748b', 'formatter': '{value}%'},
                                        'splitLine': {'show': False}
                                    }
                                ],
                                'series': [
                                    {
                                        'name': 'Completed',
                                        'type': 'bar',
                                        'stack': 'total',
                                        'barWidth': '40%',
                                        'data': completed_list,
                                        'itemStyle': {'color': '#10b981'}
                                    },
                                    {
                                        'name': 'Expired',
                                        'type': 'bar',
                                        'stack': 'total',
                                        'data': expired_list,
                                        'itemStyle': {'color': '#d97706'}
                                    },
                                    {
                                        'name': 'Not Started',
                                        'type': 'bar',
                                        'stack': 'total',
                                        'data': not_started_list,
                                        'itemStyle': {'color': '#ef4444'}
                                    },
                                    {
                                        'name': 'Avg Compliance',
                                        'type': 'line',
                                        'yAxisIndex': 1,
                                        'smooth': True,
                                        'symbol': 'circle',
                                        'symbolSize': 8,
                                        'lineStyle': {'width': 3, 'color': '#2563eb'},
                                        'itemStyle': {'color': '#2563eb'},
                                        'data': compliance_list
                                    }
                                ]
                            }).classes('w-full h-80')
 
                        # Right card: Assessment Pipeline / Current open + expiry state · no date filter (2/5 width)
                        with ui.card().classes('col-span-2 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden justify-between w-full'):
                            with ui.row().classes('w-full items-start justify-between mb-2'):
                                render_chart_header('Assessment Pipeline', 'assessment_pipeline_deep_watch', True, lambda: _download_csv_helper(regwatch_deep_deadline_adherence_df, 'Assessment Pipeline'), regwatch_deep_deadline_adherence_df)
                            
                            # Deadline Adherence Section
                            with ui.column().classes('w-full gap-3 border-t border-slate-100 pt-3'):
                                ui.label('Deadline Adherence').classes('text-xs font-black text-slate-400 uppercase tracking-wider')
                                
                                # On Time
                                with ui.row().classes('w-full items-center justify-between text-xs font-semibold flex-nowrap gap-2'):
                                    ui.label('On Time').classes('text-slate-600 w-24 shrink-0 truncate')
                                    with ui.element('div').classes('flex-grow bg-slate-100 h-2.5 rounded-full overflow-hidden'):
                                        ui.element('div').classes('h-full bg-emerald-500 rounded-full').style(f'width: {on_time_pct:.1f}%')
                                    ui.label(f"{on_time_cnt}").classes('text-emerald-600 font-bold w-6 text-right tabular-nums shrink-0')
                                    
                                # Completed Late
                                with ui.row().classes('w-full items-center justify-between text-xs font-semibold flex-nowrap gap-2'):
                                    ui.label('Completed Late').classes('text-slate-600 w-24 shrink-0 truncate')
                                    with ui.element('div').classes('flex-grow bg-slate-100 h-2.5 rounded-full overflow-hidden'):
                                        ui.element('div').classes('h-full bg-amber-600 rounded-full').style(f'width: {late_pct:.1f}%')
                                    ui.label(f"{late_cnt}").classes('text-amber-600 font-bold w-6 text-right tabular-nums shrink-0')
                                    
                                # Expired / Missed
                                with ui.row().classes('w-full items-center justify-between text-xs font-semibold flex-nowrap gap-2'):
                                    ui.label('Expired / Missed').classes('text-slate-600 w-24 shrink-0 truncate')
                                    with ui.element('div').classes('flex-grow bg-slate-100 h-2.5 rounded-full overflow-hidden'):
                                        ui.element('div').classes('h-full bg-rose-500 rounded-full').style(f'width: {missed_pct:.1f}%')
                                    ui.label(f"{missed_cnt}").classes('text-rose-600 font-bold w-6 text-right tabular-nums shrink-0')

                            # Time-to-Complete Buckets Section
                            with ui.column().classes('w-full gap-2 border-t border-slate-100 pt-4 mt-4'):
                                ui.label('Time-to-Complete Buckets').classes('text-xs font-black text-slate-400 uppercase tracking-wider')
                                
                                ui.echart({
                                    'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}},
                                    'grid': {'left': '3%', 'right': '4%', 'top': '12%', 'bottom': '8%', 'containLabel': True},
                                    'xAxis': {
                                        'type': 'category',
                                        'data': ['Under 5m', '5-30m', 'Over 30m'],
                                        'axisLabel': {'color': '#64748b', 'fontSize': 9},
                                        'axisLine': {'lineStyle': {'color': '#cbd5e1'}}
                                    },
                                    'yAxis': {
                                        'type': 'value',
                                        'axisLabel': {'color': '#64748b', 'fontSize': 9},
                                        'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                                    },
                                    'series': [{
                                        'type': 'bar',
                                        'barWidth': '40%',
                                        'data': [
                                            {'value': under_5, 'itemStyle': {'color': '#10b981'}},
                                            {'value': btw_5_30, 'itemStyle': {'color': '#d97706'}},
                                            {'value': over_30, 'itemStyle': {'color': '#ef4444'}}
                                        ],
                                        'label': {
                                            'show': True,
                                            'position': 'top',
                                            'color': '#475569',
                                            'fontSize': 9,
                                            'fontWeight': 'bold'
                                        }
                                    }]
                                }).classes('w-full h-[140px]')

                    # Parse Compliance Trend
                    trend_months = []
                    trend_compliance = []

                    if not regwatch_deep_compliance_trend_df.empty:
                        for _, row in regwatch_deep_compliance_trend_df.iterrows():
                            dt = pd.to_datetime(row['month'])
                            trend_months.append(dt.strftime('%b') if pd.notna(dt) else '')
                            trend_compliance.append(float(row['avg_compliance_pct']) if pd.notna(row['avg_compliance_pct']) else 0.0)

                    # Parse Compliance Score Distribution
                    bands = ['100%', '80–99%', '60–79%', '40–59%', 'Below 40%']
                    dist_data = {b: {'count': 0, 'pct': 0.0} for b in bands}

                    if not regwatch_deep_compliance_score_dist_df.empty:
                        for _, row in regwatch_deep_compliance_score_dist_df.iterrows():
                            band = str(row['score_band'])
                            if '100' in band:
                                band = '100%'
                            elif '80' in band or '99' in band:
                                band = '80–99%'
                            elif '60' in band or '79' in band:
                                band = '60–79%'
                            elif '40' in band or '59' in band:
                                band = '40–59%'
                            else:
                                band = 'Below 40%'
                            dist_data[band] = {
                                'count': int(row['count']) if pd.notna(row['count']) else 0,
                                'pct': float(row['pct']) if pd.notna(row['pct']) else 0.0
                            }

                    # Parse Response Quality Summary
                    avg_compliant = 0.0
                    avg_non_compliant = 0.0
                    avg_unanswered = 0.0
                    if not regwatch_deep_compliance_summary_df.empty:
                        row = regwatch_deep_compliance_summary_df.iloc[0]
                        avg_compliant = float(row['avg_compliant_items']) if pd.notna(row['avg_compliant_items']) else 0.0
                        avg_non_compliant = float(row['avg_non_compliant_items']) if pd.notna(row['avg_non_compliant_items']) else 0.0
                        avg_unanswered = float(row['avg_unanswered_items']) if pd.notna(row['avg_unanswered_items']) else 0.0

                    max_quality_val = max(5.0, avg_compliant + avg_non_compliant + avg_unanswered)

                    # Elegant divider header for Compliance Quality
                    with ui.row().classes('w-full items-center justify-between mb-4 mt-8 flex-nowrap'):
                        with ui.row().classes('items-center gap-2 flex-nowrap'):
                            with ui.element('div').classes('p-2 bg-slate-50 border border-slate-100 rounded-lg flex items-center justify-center shadow-xs'):
                                ui.icon('verified', size='16px').classes('text-emerald-500')
                            ui.label('03 Compliance Quality').classes('rp-section-label whitespace-nowrap')
                        with ui.row().classes('items-center gap-1.5 text-[11px] font-mono text-slate-400 flex-nowrap whitespace-nowrap'):
                            ui.label('regwatch_pre_assessment · status = Completed')

                    with ui.grid(columns=5).classes('w-full gap-6 mt-6 items-stretch'):
                        
                        # Left card: Compliance Score Trend (3/5 width)
                        with ui.card().classes('col-span-3 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden w-full'):
                            with ui.row().classes('w-full items-start justify-between mb-2'):
                                render_chart_header('Compliance Score Trend', 'compliance_score_trend_deep_watch', True, lambda: _download_csv_helper(regwatch_deep_compliance_trend_df, 'Compliance Score Trend'), regwatch_deep_compliance_trend_df)
                            
                            ui.echart({
                                'tooltip': {
                                    'trigger': 'axis',
                                    'formatter': '{b}: {c}% avg compliance'
                                },
                                'legend': {
                                    'data': ['Avg Compliance %', 'Target 80%'],
                                    'bottom': 0,
                                    'icon': 'rect'
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
                                    'data': trend_months,
                                    'axisLine': {'lineStyle': {'color': '#cbd5e1'}},
                                    'axisLabel': {'color': '#64748b', 'fontWeight': 'bold'}
                                },
                                'yAxis': {
                                    'type': 'value',
                                    'name': 'Compliance %',
                                    'min': 60,
                                    'max': 100,
                                    'interval': 5,
                                    'axisLine': {'lineStyle': {'color': '#cbd5e1'}},
                                    'axisLabel': {'color': '#64748b'},
                                    'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                                },
                                'series': [
                                    {
                                        'name': 'Avg Compliance %',
                                        'type': 'line',
                                        'smooth': True,
                                        'symbol': 'circle',
                                        'symbolSize': 8,
                                        'lineStyle': {'width': 3, 'color': '#0d9488'},
                                        'itemStyle': {'color': '#0d9488', 'borderColor': '#ffffff', 'borderWidth': 1.5},
                                        'areaStyle': {
                                            'color': {
                                                'type': 'linear',
                                                'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                                                'colorStops': [
                                                    {'offset': 0, 'color': 'rgba(13, 148, 136, 0.12)'},
                                                    {'offset': 1, 'color': 'rgba(13, 148, 136, 0.01)'}
                                                ]
                                            }
                                        },
                                        'data': trend_compliance,
                                        'markLine': {
                                            'symbol': 'none',
                                            'data': [
                                                {
                                                    'yAxis': 80,
                                                    'lineStyle': {'color': '#ef4444', 'type': 'dashed', 'width': 2},
                                                    'label': {'show': True, 'position': 'end', 'formatter': 'Target 80%', 'color': '#ef4444', 'fontSize': 10, 'fontWeight': 'bold'}
                                                }
                                            ]
                                        }
                                    }
                                ]
                            }).classes('w-full h-80')
 
                        # Right card: Compliance Score Distribution + Avg Response Quality (2/5 width)
                        with ui.card().classes('col-span-2 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden justify-between w-full'):
                            with ui.row().classes('w-full items-start justify-between mb-2'):
                                render_chart_header('Compliance Score Distribution', 'compliance_score_distribution_deep_watch', True, lambda: _download_csv_helper(regwatch_deep_compliance_score_dist_df, 'Compliance Score Distribution'), regwatch_deep_compliance_score_dist_df)
                            
                            # Progress bars for Score Bands
                            with ui.column().classes('w-full gap-3 mt-2'):
                                band_colors = {
                                    '100%': '#10b981',
                                    '80–99%': '#34d399',
                                    '60–79%': '#b45309',
                                    '40–59%': '#f97316',
                                    'Below 40%': '#ef4444'
                                }
                                for b in bands:
                                    b_data = dist_data[b]
                                    pct_val = b_data['pct']
                                    cnt_val = b_data['count']
                                    color = band_colors[b]
                                    
                                    with ui.row().classes('w-full items-center justify-between text-xs font-semibold flex-nowrap gap-2'):
                                        ui.label(b).classes('text-slate-600 w-16 shrink-0 truncate')
                                        with ui.element('div').classes('flex-grow bg-slate-100 h-2.5 rounded-full overflow-hidden relative'):
                                            ui.element('div').classes('h-full rounded-full').style(f'background-color: {color}; width: {pct_val:.1f}%')
                                        with ui.row().classes('w-16 shrink-0 items-center justify-end gap-1'):
                                            ui.label(f"{pct_val:.0f}%").classes('text-slate-500 font-medium w-8 text-right')
                                            ui.label(f"{cnt_val}").classes('text-slate-700 font-bold w-6 text-right tabular-nums')

                            # Response Quality Section
                            with ui.column().classes('w-full gap-2 border-t border-slate-100 pt-4 mt-4'):
                                ui.label('Avg Response Quality (Completed)').classes('text-xs font-black text-slate-400 uppercase tracking-wider')
                                
                                # Compliant bar
                                with ui.row().classes('w-full items-center justify-between text-xs font-semibold flex-nowrap gap-2'):
                                    ui.label('Compliant').classes('text-slate-600 w-24 shrink-0 truncate')
                                    with ui.element('div').classes('flex-grow bg-slate-100 h-2.5 rounded-full overflow-hidden relative'):
                                        ui.element('div').classes('h-full bg-emerald-500 rounded-full').style(f'width: {(avg_compliant / max_quality_val * 100):.1f}%')
                                    ui.label(f"{avg_compliant:.1f}").classes('text-slate-700 font-bold w-10 text-right tabular-nums shrink-0')
                                    
                                # Non-Compliant bar
                                with ui.row().classes('w-full items-center justify-between text-xs font-semibold flex-nowrap gap-2'):
                                    ui.label('n-Compliant').classes('text-slate-600 w-24 shrink-0 truncate')
                                    with ui.element('div').classes('flex-grow bg-slate-100 h-2.5 rounded-full overflow-hidden relative'):
                                        ui.element('div').classes('h-full bg-rose-500 rounded-full').style(f'width: {(avg_non_compliant / max_quality_val * 100):.1f}%')
                                    ui.label(f"{avg_non_compliant:.1f}").classes('text-slate-700 font-bold w-10 text-right tabular-nums shrink-0')
                                    
                                # Unanswered bar
                                with ui.row().classes('w-full items-center justify-between text-xs font-semibold flex-nowrap gap-2'):
                                    ui.label('Unanswered').classes('text-slate-600 w-24 shrink-0 truncate')
                                    with ui.element('div').classes('flex-grow bg-slate-100 h-2.5 rounded-full overflow-hidden relative'):
                                        ui.element('div').classes('h-full bg-amber-700 rounded-full').style(f'width: {(avg_unanswered / max_quality_val * 100):.1f}%')
                                    ui.label(f"{avg_unanswered:.1f}").classes('text-slate-700 font-bold w-10 text-right tabular-nums shrink-0')

                    # Parse Low Compliance Alerts
                    low_comp_list = []
                    if not regwatch_deep_low_compliance_regs_df.empty:
                        area_styles = {
                            'AML/CFT': {'bg': '#fee2e2', 'text': '#991b1b', 'border': '#fecaca'},
                            'Securities': {'bg': '#fce7f3', 'text': '#9d174d', 'border': '#fbcfe8'},
                            'Data Prot.': {'bg': '#fef3c7', 'text': '#92400e', 'border': '#fde68a'},
                            'KYC': {'bg': '#ffedd5', 'text': '#9a3412', 'border': '#fed7aa'},
                            'Privacy': {'bg': '#e0f2fe', 'text': '#075985', 'border': '#bae6fd'},
                            'Banking': {'bg': '#ecfdf5', 'text': '#065f46', 'border': '#a7f3d0'}
                        }
                        for _, row in regwatch_deep_low_compliance_regs_df.iterrows():
                            title = str(row['regulation_title'])
                            area = str(row['regulatory_area'])
                            score = float(row['avg_compliance_pct']) if pd.notna(row['avg_compliance_pct']) else 0.0
                            
                            style = area_styles.get(area, {'bg': '#f1f5f9', 'text': '#334155', 'border': '#e2e8f0'})
                            
                            low_comp_list.append({
                                'regulation': title,
                                'area': area,
                                'score': score,
                                'area_color': style['bg'],
                                'area_text': style['text'],
                                'area_border': style['border']
                            })

                    # Parse Compliance Improvement
                    improvement_names = []
                    improvement_deltas = []

                    if not regwatch_deep_compliance_improvement_df.empty:
                        sorted_df = regwatch_deep_compliance_improvement_df.sort_values(by='improvement_delta', ascending=True)
                        for _, row in sorted_df.tail(5).iterrows():
                            title = str(row['regulation_title'])
                            if len(title) > 15:
                                title = f"{title[:12]}..."
                            improvement_names.append(title)
                            improvement_deltas.append(float(row['improvement_delta']) if pd.notna(row['improvement_delta']) else 0.0)

                    series_data = []
                    for val in improvement_deltas:
                        color = '#15803d' if val >= 0 else '#b91c1c'
                        series_data.append({
                            'value': val,
                            'itemStyle': {'color': color}
                        })

                    with ui.grid(columns=5).classes('w-full gap-6 mt-6 items-stretch'):
                        
                        # Left card: Low-Compliance Alerts (<80%) — High Risk Only (3/5 width)
                        with ui.card().classes('col-span-3 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden w-full justify-between'):
                            with ui.row().classes('w-full items-start justify-between mb-2'):
                                render_chart_header('Low-Compliance Alerts', 'low_compliance_alerts_deep_watch', True, lambda: _download_csv_helper(regwatch_deep_low_compliance_regs_df, 'Low-Compliance Alerts'), regwatch_deep_low_compliance_regs_df)
                            
                            # Table Header
                            with ui.row().classes('w-full border-b border-slate-100 pb-2 text-[10px] font-black text-slate-400 uppercase tracking-wider flex-nowrap gap-4 items-center'):
                                ui.label('REGULATION').classes('w-[50%] text-left')
                                ui.label('AREA').classes('w-[25%] text-center')
                                ui.label('SCORE').classes('w-[25%] text-right')
                            
                            # Table Rows
                            with ui.column().classes('w-full gap-3 mt-3 flex-grow'):
                                if low_comp_list:
                                    for item in low_comp_list:
                                        reg = item['regulation']
                                        area = item['area']
                                        score = item['score']
                                        
                                        score_color = '#b91c1c' if score < 60 else '#b45309'
                                        reg_display = reg if len(reg) <= 38 else f"{reg[:35]}..."
                                        
                                        with ui.row().classes('w-full text-xs font-semibold text-slate-700 flex-nowrap gap-4 items-center py-1.5 border-b border-slate-50 last:border-0'):
                                            ui.label(reg_display).classes('w-[50%] text-left truncate font-semibold text-slate-700').tooltip(reg)
                                            
                                            with ui.row().classes('w-[25%] justify-center'):
                                                with ui.element('div').classes('px-2.5 py-0.5 rounded-full text-[10px] font-bold border').style(f"background-color: {item['area_color']}; color: {item['area_text']}; border-color: {item['area_border']}"):
                                                    ui.label(area)
                                                    
                                            with ui.row().classes('w-[25%] items-center justify-end gap-2 flex-nowrap'):
                                                with ui.element('div').classes('w-16 h-2 bg-slate-100 rounded-full overflow-hidden relative shrink-0'):
                                                    ui.element('div').classes('h-full rounded-full').style(f'background-color: {score_color}; width: {score:.1f}%')
                                                ui.label(f"{score:.0f}%").classes('font-bold text-slate-600 text-right tabular-nums w-8 shrink-0')
                                else:
                                    with ui.row().classes('w-full justify-center py-10'):
                                        ui.label('No low compliance alerts found').classes('text-slate-400 italic text-xs')
 
                        # Right card: Compliance Improvement Horizontal bar chart (2/5 width)
                        with ui.card().classes('col-span-2 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden justify-between w-full'):
                            with ui.row().classes('w-full items-start justify-between mb-2'):
                                render_chart_header('Compliance Improvement', 'compliance_improvement_deep_watch', True, lambda: _download_csv_helper(regwatch_deep_compliance_improvement_df, 'Compliance Improvement'), regwatch_deep_compliance_improvement_df)
                            
                            ui.echart({
                                'tooltip': {
                                    'trigger': 'axis',
                                    'formatter': '{b}: {c}% change',
                                    'axisPointer': {'type': 'shadow'}
                                },
                                'grid': {
                                    'left': '3%',
                                    'right': '10%',
                                    'top': '5%',
                                    'bottom': '5%',
                                    'containLabel': True
                                },
                                'xAxis': {
                                    'type': 'value',
                                    'axisLabel': {'color': '#64748b', 'fontSize': 9, 'formatter': '{value}%'},
                                    'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                                },
                                'yAxis': {
                                    'type': 'category',
                                    'data': improvement_names,
                                    'axisLabel': {'color': '#64748b', 'fontSize': 10, 'fontWeight': 'bold'},
                                    'axisLine': {'lineStyle': {'color': '#cbd5e1'}}
                                },
                                'series': [{
                                    'type': 'bar',
                                    'barWidth': '55%',
                                    'data': series_data,
                                    'label': {
                                        'show': True,
                                        'position': 'right',
                                        'color': '#475569',
                                        'fontSize': 9,
                                        'fontWeight': 'bold',
                                        'formatter': '{c}%'
                                    }
                                }]
                            }).classes('w-full h-[220px]')

                    # Parse Risk Level Profile
                    risk_levels = ['High', 'Medium', 'Low']
                    risk_assessments = [0, 0, 0]

                    if not regwatch_deep_risk_level_profile_df.empty:
                        for _, row in regwatch_deep_risk_level_profile_df.iterrows():
                            rl = str(row['risk_level']).strip()
                            cnt = int(row['assessments']) if pd.notna(row['assessments']) else 0
                            if rl == 'High':
                                risk_assessments[0] = cnt
                            elif rl == 'Medium':
                                risk_assessments[1] = cnt
                            elif rl == 'Low':
                                risk_assessments[2] = cnt

                    risk_chart_series = [
                        {'value': risk_assessments[0], 'itemStyle': {'color': '#b91c1c'}},
                        {'value': risk_assessments[1], 'itemStyle': {'color': '#b45309'}},
                        {'value': risk_assessments[2], 'itemStyle': {'color': '#15803d'}}
                    ]

                    # Parse Regulatory Area Coverage
                    reg_area_list = []
                    if not regwatch_deep_regulatory_area_df.empty:
                        area_colors = ['#b91c1c', '#b45309', '#15803d', '#0d9488', '#2563eb', '#7c3aed']
                        for idx, row in regwatch_deep_regulatory_area_df.iterrows():
                            area = str(row['regulatory_area'])
                            cnt = int(row['assessments_run']) if pd.notna(row['assessments_run']) else 0
                            pct = float(row['avg_compliance_pct']) if pd.notna(row['avg_compliance_pct']) else 0.0
                            color = area_colors[idx % len(area_colors)]
                            reg_area_list.append({
                                'area': area,
                                'count': cnt,
                                'pct': pct,
                                'color': color
                            })

                    # Parse Regulator Engagement
                    regulator_list = []
                    if not regwatch_deep_regulator_breakdown_df.empty:
                        for _, row in regwatch_deep_regulator_breakdown_df.iterrows():
                            name = str(row['regulator_name'])
                            code = str(row['regulator_code'])
                            cnt = int(row['assessments']) if pd.notna(row['assessments']) else 0
                            pct = float(row['avg_compliance_pct']) if pd.notna(row['avg_compliance_pct']) else 0.0
                            regulator_list.append({
                                'name': name,
                                'code': code,
                                'count': cnt,
                                'pct': pct
                            })

                    # Parse Most Assessed Regulations
                    top_regs_list = []
                    if not regwatch_deep_top_regulations_df.empty:
                        reg_colors = ['#b91c1c', '#b45309', '#2563eb', '#0d9488', '#15803d', '#7c3aed', '#0d9488', '#94a3b8']
                        for idx, row in regwatch_deep_top_regulations_df.head(8).iterrows():
                            title = str(row['regulation_title'])
                            cnt = int(row['times_assessed']) if pd.notna(row['times_assessed']) else 0
                            color = reg_colors[idx % len(reg_colors)]
                            top_regs_list.append({
                                'title': title,
                                'count': cnt,
                                'color': color
                            })

                    # Parse Assessor Leaderboard
                    assessor_leaderboard = []
                    if not regwatch_deep_assessor_leaderboard_df.empty:
                        for _, row in regwatch_deep_assessor_leaderboard_df.iterrows():
                            user_id = str(row['user_id'])
                            email = str(row['email'])
                            full_name = str(row['full_name']) if pd.notna(row['full_name']) and str(row['full_name']).strip() != '' else email
                            total_assessments = int(row['total_assessments']) if pd.notna(row['total_assessments']) else 0
                            completed = int(row['completed']) if pd.notna(row['completed']) else 0
                            expired = int(row['expired']) if pd.notna(row['expired']) else 0
                            avg_compliance = float(row['avg_compliance_pct']) if pd.notna(row['avg_compliance_pct']) else 0.0
                            distinct_regs = int(row['distinct_regulations']) if pd.notna(row['distinct_regulations']) else 0
                            
                            # Safely mask email
                            if '@' in email:
                                parts = email.split('@')
                                name_part, domain_part = parts[0], parts[1]
                                masked_email = f"{name_part[:2]}***@{domain_part}" if len(name_part) > 2 else f"{name_part}***@{domain_part}"
                            else:
                                masked_email = email

                            assessor_leaderboard.append({
                                'user_id': user_id,
                                'email': masked_email,
                                'full_name': full_name,
                                'total_assessments': total_assessments,
                                'completed': completed,
                                'expired': expired,
                                'avg_compliance_pct': avg_compliance,
                                'distinct_regulations': distinct_regs
                            })

                    # Parse Monthly Activity for EChart
                    assessor_emails = []
                    months_unique = []
                    monthly_data_map = {} # email -> {month -> assessments}
                    
                    if not regwatch_deep_assessor_monthly_activity_df.empty:
                        for _, row in regwatch_deep_assessor_monthly_activity_df.iterrows():
                            dt = pd.to_datetime(row['month'])
                            mon_str = dt.strftime('%b') if pd.notna(dt) else ''
                            email = str(row['assessor_email'])
                            count_val = int(row['assessments']) if pd.notna(row['assessments']) else 0
                            
                            # Mask email
                            if '@' in email:
                                parts = email.split('@')
                                name_part, domain_part = parts[0], parts[1]
                                masked_email = f"{name_part[:2]}***@{domain_part}" if len(name_part) > 2 else f"{name_part}***@{domain_part}"
                            else:
                                masked_email = email

                            if masked_email not in assessor_emails:
                                assessor_emails.append(masked_email)
                            if mon_str not in months_unique:
                                months_unique.append(mon_str)
                                
                            if masked_email not in monthly_data_map:
                                monthly_data_map[masked_email] = {}
                            monthly_data_map[masked_email][mon_str] = count_val

                    # Let's limit the chart to the top 5 assessors to keep it perfectly clean and readable!
                    top_5_assessors = [item['email'] for item in assessor_leaderboard[:5]]
                    
                    chart_series = []
                    for email in top_5_assessors:
                        series_data = []
                        for mon in months_unique:
                            series_data.append(monthly_data_map.get(email, {}).get(mon, 0))
                        chart_series.append({
                            'name': email,
                            'type': 'line',
                            'smooth': True,
                            'data': series_data
                        })

                    # Divider header for Regulation Coverage
                    with ui.row().classes('w-full items-center justify-between mb-4 mt-8 flex-nowrap'):
                        with ui.row().classes('items-center gap-2 flex-nowrap'):
                            with ui.element('div').classes('p-2 bg-slate-50 border border-slate-100 rounded-lg flex items-center justify-center shadow-xs'):
                                ui.icon('policy', size='16px').classes('text-emerald-500')
                            ui.label('04 Regulation Coverage').classes('rp-section-label whitespace-nowrap')
                        with ui.row().classes('items-center gap-1.5 text-[11px] font-mono text-slate-400 flex-nowrap whitespace-nowrap'):
                            ui.label('regwatch_pre_assessment JOIN regwatch_regulations ON regulation_id')

                    with ui.grid(columns=5).classes('w-full gap-6 mt-6 items-stretch'):
                        
                        # Left card: Risk Level Profile (2/5 width)
                        with ui.card().classes('col-span-2 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden w-full justify-between'):
                            with ui.row().classes('w-full items-start justify-between mb-2'):
                                render_chart_header('Risk Level Profile', 'risk_level_profile_deep_watch', True, lambda: _download_csv_helper(regwatch_deep_risk_level_profile_df, 'Risk Level Profile'), regwatch_deep_risk_level_profile_df)
                            
                            ui.echart({
                                'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}},
                                'grid': {'left': '5%', 'right': '5%', 'top': '10%', 'bottom': '10%', 'containLabel': True},
                                'xAxis': {
                                    'type': 'category',
                                    'data': ['High', 'Medium', 'Low'],
                                    'axisLabel': {'color': '#64748b', 'fontSize': 10},
                                    'axisLine': {'lineStyle': {'color': '#cbd5e1'}}
                                },
                                'yAxis': {
                                    'type': 'value',
                                    'axisLabel': {'color': '#64748b', 'fontSize': 9},
                                    'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
                                },
                                'series': [{
                                    'type': 'bar',
                                    'barWidth': '45%',
                                    'data': risk_chart_series,
                                    'label': {
                                        'show': True,
                                        'position': 'top',
                                        'color': '#475569',
                                        'fontSize': 9,
                                        'fontWeight': 'bold'
                                    }
                                }]
                            }).classes('w-full h-56')
 
                        # Right card: Regulatory Area Coverage (3/5 width)
                        with ui.card().classes('col-span-3 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden w-full justify-between'):
                            with ui.row().classes('w-full items-start justify-between mb-2'):
                                render_chart_header('Regulatory Area Coverage', 'regulatory_area_coverage_deep_watch', True, lambda: _download_csv_helper(regwatch_deep_regulatory_area_df, 'Regulatory Area Coverage'), regwatch_deep_regulatory_area_df)
                            
                            with ui.column().classes('w-full gap-2.5 mt-2 flex-grow justify-center'):
                                max_area_count = max(35, max([a['count'] for a in reg_area_list]) if reg_area_list else 35)
                                for item in reg_area_list:
                                    area_name = item['area']
                                    count_val = item['count']
                                    pct_val = item['pct']
                                    color = item['color']
                                    
                                    bar_width_pct = (count_val / max_area_count * 100)
                                    
                                    with ui.row().classes('w-full items-center justify-between text-xs font-semibold flex-nowrap gap-2'):
                                        ui.label(area_name).classes('text-slate-600 w-32 shrink-0 truncate')
                                        with ui.element('div').classes('flex-grow bg-slate-50 h-2.5 rounded-full overflow-hidden relative border border-slate-100/50'):
                                            ui.element('div').classes('h-full rounded-full').style(f'background-color: {color}; width: {bar_width_pct:.1f}%')
                                        with ui.row().classes('w-16 shrink-0 items-center justify-end gap-1.5 flex-nowrap'):
                                            ui.label(f"{count_val}").classes('text-slate-700 font-black w-6 text-right')
                                            ui.label(f"{pct_val:.0f}%").classes('text-slate-400 font-bold w-8 text-right')

                    with ui.grid(columns=5).classes('w-full gap-6 mt-6 items-stretch'):
                        
                        # Left card: Regulator Engagement (2/5 width)
                        with ui.card().classes('col-span-2 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden w-full justify-between'):
                            with ui.row().classes('w-full items-start justify-between mb-2'):
                                render_chart_header('Regulator Engagement', 'regulator_engagement_deep_watch', True, lambda: _download_csv_helper(regwatch_deep_regulator_breakdown_df, 'Regulator Engagement'), regwatch_deep_regulator_breakdown_df)
                            
                            # Table Header
                            with ui.row().classes('w-full border-b border-slate-100 pb-2 text-[10px] font-black text-slate-400 uppercase tracking-wider flex-nowrap gap-4 items-center'):
                                ui.label('REGULATOR').classes('w-[42%] text-left')
                                ui.label('CODE').classes('w-[18%] text-center')
                                ui.label('ASSESSMENTS').classes('w-[15%] text-center')
                                ui.label('AVG COMPLIANCE').classes('w-[25%] text-right')
 
                            # Table Rows
                            with ui.column().classes('w-full gap-3 mt-3 flex-grow'):
                                if regulator_list:
                                    for item in regulator_list:
                                        name = item['name']
                                        code = item['code']
                                        count_val = item['count']
                                        pct_val = item['pct']
                                        
                                        name_display = name if len(name) <= 24 else f"{name[:21]}..."
                                        score_color = '#15803d' if pct_val >= 80 else '#b45309'
                                        
                                        with ui.row().classes('w-full text-xs font-semibold text-slate-700 flex-nowrap gap-4 items-center py-1.5 border-b border-slate-50 last:border-0'):
                                            ui.label(name_display).classes('w-[42%] text-left truncate font-semibold text-slate-700').tooltip(name)
                                            ui.label(code).classes('w-[18%] text-center text-slate-400 font-mono text-[10px]')
                                            ui.label(f"{count_val}").classes('w-[15%] text-center text-slate-700 font-bold tabular-nums')
                                            
                                            with ui.row().classes('w-[25%] items-center justify-end gap-2 flex-nowrap'):
                                                with ui.element('div').classes('w-12 h-2 bg-slate-100 rounded-full overflow-hidden relative shrink-0'):
                                                    ui.element('div').classes('h-full rounded-full').style(f'background-color: {score_color}; width: {pct_val:.1f}%')
                                                ui.label(f"{pct_val:.0f}%").classes('font-bold text-slate-500 text-right tabular-nums w-8 shrink-0')
                                else:
                                    with ui.row().classes('w-full justify-center py-10'):
                                        ui.label('No regulator engagement found').classes('text-slate-400 italic text-xs')
 
                        # Right card: Most Assessed Regulations (3/5 width)
                        with ui.card().classes('col-span-3 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden w-full justify-between'):
                            with ui.row().classes('w-full items-start justify-between mb-2'):
                                render_chart_header('Most Assessed Regulations', 'most_assessed_regulations_deep_watch', True, lambda: _download_csv_helper(regwatch_deep_top_regulations_df, 'Most Assessed Regulations'), regwatch_deep_top_regulations_df)
                            
                            with ui.column().classes('w-full gap-2.5 mt-2 flex-grow justify-center'):
                                max_reg_count = max(10, max([r['count'] for r in top_regs_list]) if top_regs_list else 10)
                                for item in top_regs_list:
                                    title = item['title']
                                    count_val = item['count']
                                    color = item['color']
                                    
                                    bar_width_pct = (count_val / max_reg_count * 100)
                                    title_display = title if len(title) <= 32 else f"{title[:29]}..."
                                    
                                    with ui.row().classes('w-full items-center justify-between text-xs font-semibold flex-nowrap gap-2'):
                                        ui.label(title_display).classes('text-slate-600 w-36 shrink-0 truncate').tooltip(title)
                                        with ui.element('div').classes('flex-grow bg-slate-50 h-2.5 rounded-full overflow-hidden relative border border-slate-100/50'):
                                            ui.element('div').classes('h-full rounded-full').style(f'background-color: {color}; width: {bar_width_pct:.1f}%')
                                        ui.label(f"{count_val}").classes('text-slate-700 font-black w-8 text-right shrink-0')

                    # Divider header for Section 5 — Team Dynamics
                    with ui.row().classes('w-full items-center justify-between mb-4 mt-8 flex-nowrap'):
                        with ui.row().classes('items-center gap-2 flex-nowrap'):
                            with ui.element('div').classes('p-2 bg-slate-50 border border-slate-100 rounded-lg flex items-center justify-center shadow-xs'):
                                ui.icon('groups', size='16px').classes('text-blue-500')
                            ui.label('05 Team Dynamics').classes('rp-section-label whitespace-nowrap')

                    with ui.grid(columns=5).classes('w-full gap-6 mt-6 items-stretch'):
                        
                        # Left card: Assessor Leaderboard (3/5 width)
                        with ui.card().classes('col-span-3 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden w-full justify-between'):
                            with ui.row().classes('w-full items-start justify-between mb-2'):
                                render_chart_header('Assessor Performance Leaderboard', 'assessor_performance_leaderboard_deep_watch', True, lambda: _download_csv_helper(regwatch_deep_assessor_leaderboard_df, 'Assessor Performance Leaderboard'), regwatch_deep_assessor_leaderboard_df)
                            
                            # Custom table header
                            with ui.row().classes('w-full border-b border-slate-100 pb-2 text-[10px] font-black text-slate-400 uppercase tracking-wider flex-nowrap gap-4 items-center'):
                                ui.label('ASSESSOR').classes('w-[35%] text-left')
                                ui.label('TOTAL').classes('w-[13%] text-center')
                                ui.label('COMPLETED').classes('w-[18%] text-center')
                                ui.label('AVG COMPLIANCE').classes('w-[20%] text-center')
                                ui.label('REGS').classes('w-[14%] text-right')
 
                            # Custom table rows
                            with ui.column().classes('w-full gap-3 mt-3 flex-grow'):
                                if assessor_leaderboard:
                                    for item in assessor_leaderboard[:6]: # top 6 assessors
                                        name = item['full_name']
                                        email = item['email']
                                        total = item['total_assessments']
                                        comp = item['completed']
                                        compliance = item['avg_compliance_pct']
                                        regs = item['distinct_regulations']
                                        
                                        score_color = '#15803d' if compliance >= 80 else '#b45309'
                                        
                                        with ui.row().classes('w-full text-xs font-semibold text-slate-700 flex-nowrap gap-4 items-center py-1.5 border-b border-slate-50 last:border-0'):
                                            with ui.column().classes('w-[35%] gap-0.5 text-left truncate'):
                                                ui.label(name).classes('font-bold text-slate-800 truncate')
                                                ui.label(email).classes('text-[10px] text-slate-400 font-mono truncate')
                                            ui.label(f"{total}").classes('w-[13%] text-center text-slate-700 font-bold tabular-nums')
                                            ui.label(f"{comp}").classes('w-[18%] text-center text-slate-500 font-semibold tabular-nums')
                                            
                                            with ui.row().classes('w-[20%] items-center justify-center gap-1.5 flex-nowrap'):
                                                ui.element('span').classes('w-2 h-2 rounded-full shrink-0').style(f'background-color: {score_color}')
                                                ui.label(f"{compliance:.0f}%").classes('font-bold text-slate-700 tabular-nums')
                                                
                                            ui.label(f"{regs}").classes('w-[14%] text-right text-slate-600 font-mono text-[11px]')
                                else:
                                    with ui.row().classes('w-full justify-center py-10'):
                                        ui.label('No assessor activity recorded').classes('text-slate-400 italic text-xs')
 
                        # Right card: Assessor Activity Trend (2/5 width)
                        with ui.card().classes('col-span-2 p-6 pt-4 border border-slate-200 shadow-sm bg-white rounded-xl flex flex-col hover:shadow-md transition-all duration-300 overflow-hidden w-full justify-between'):
                            with ui.row().classes('w-full items-start justify-between mb-2'):
                                render_chart_header('Monthly Activity Trend', 'monthly_activity_trend_deep_watch', True, lambda: _download_csv_helper(regwatch_deep_assessor_monthly_activity_df, 'Monthly Activity Trend'), regwatch_deep_assessor_monthly_activity_df)
                            
                            if chart_series:
                                ui.echart({
                                    'tooltip': {
                                        'trigger': 'axis'
                                    },
                                    'legend': {
                                        'bottom': 0,
                                        'icon': 'circle',
                                        'textStyle': {'fontSize': 9}
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
                                        'data': months_unique,
                                        'axisLine': {'lineStyle': {'color': '#cbd5e1'}},
                                        'axisLabel': {'color': '#64748b', 'fontSize': 9}
                                    },
                                    'yAxis': {
                                        'type': 'value',
                                        'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}},
                                        'axisLabel': {'color': '#64748b', 'fontSize': 9}
                                    },
                                    'series': chart_series
                                }).classes('w-full h-56')
                            else:
                                with ui.row().classes('w-full justify-center py-10'):
                                    ui.label('No monthly activity trend data').classes('text-slate-400 italic text-xs')

                    # Render Subtitle block for USER JOURNEY PATHS with an elegant separator line
                    with ui.row().classes('w-full items-center gap-2 mb-4 mt-8'):
                        with ui.element('div').classes('p-2 bg-white border border-slate-100 rounded-lg flex items-center justify-center shadow-xs'):
                            ui.icon('explore', size='16px').classes('text-indigo-500')
                        ui.label('USER JOURNEY PATHS').classes('text-[11px] font-extrabold text-slate-400 tracking-wider')
                        ui.element('div').classes('flex-grow h-px bg-slate-200/60 ml-2')

                    create_user_journey_section(org_uj_df, platform_name=PLATFORM, id='user_journeys_watch', show_info=True, title=f"{org_name} Journey Paths")
    
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
            page_title='RegWatch Performance',
            #page_subtitle='Regulatory monitoring and alerts system',
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
    
    await dashboard_layout(content, page_title="RegWatch Performance", active_page="product/regwatch")
