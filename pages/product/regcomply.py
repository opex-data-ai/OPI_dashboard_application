import asyncio
from datetime import datetime, timedelta
from nicegui import ui, app, run
from components.dashboard_layout import dashboard_layout
from components.page_template import create_page_template
from components.chart_components import (
    create_kpi_metrics,
    create_comparison_cards,
    create_bar_chart,
    create_donut_chart,
    create_metric_table,
    create_country_metrics_row,
    create_line_chart,
    create_traffic_source_row,
    create_user_journey_section,
    create_placeholder_card
)
from data_engine.data_loader import get_data_loader
from data_engine.query_store import QUERIES
import pandas as pd
import inspect
from components.theme_manager import ThemeManager
from data_engine.module_mapping import map_path_to_module, map_path_to_landing
from utils.formatters import format_msec_to_time
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

                    # Visitor Type Metrics (Anonymous vs Signed-In)
                    anon_data = results['anonymous_users_pct']
                    anonymous_visitors = int(anon_data.iloc[0]['anonymous_visitors']) if not anon_data.empty else 0
                    signed_in_visitors = active_users

                    # Populate METRIC_INFO with raw data for AI insights
                    METRIC_INFO['active_org_rate']['chart_data'] = {'active_orgs': active_orgs, 'total_orgs': total_orgs}
                    METRIC_INFO['active_users_rate']['chart_data'] = {'active_users': active_users, 'total_users': total_users}
                    METRIC_INFO['anonymous_users_rate']['chart_data'] = {'anonymous_visitors': anonymous_visitors, 'signed_in_visitors': signed_in_visitors}

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
                            'id': 'anonymous_users_rate',
                            'title': 'Anonymous User Rate',
                            'metric_a_name': 'Anonymous Visitors',
                            'metric_a_value': anonymous_visitors,
                            'metric_b_name': 'Signed-In Users',
                            'metric_b_value': signed_in_visitors,
                            'icon': 'group_work',
                            'pct_method': 'total',
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
                
                # Fetch geographic metrics
                # Fetch geographic and stickiness metrics
                queries = {
                    'geographic_metrics': QUERIES['product_geographic_metrics'],
                    'stickiness': QUERIES['product_stickiness'],
                    'traffic_source': QUERIES['product_traffic_source_metrics'],
                    'session_traffic': QUERIES['product_session_traffic_metrics']
                }
                
                results = loader.execute_batch_queries(queries, start_date, end_date, platform='RegComply')
                
                container.clear()
                with container:
                    # Geographic Distribution
                    ui.label('Geographic Distribution').classes(ThemeManager.TYPOGRAPHY['h2'] + ' mb-4')
                    
                    if not results['geographic_metrics'].empty:
                        geo_data = results['geographic_metrics']
                        # Aggregate by country for the map
                        country_data = geo_data.groupby('country', as_index=False).agg({
                            'total_visitors': 'sum',
                        })
                        
                        # Data for AI
                        METRIC_INFO['map_distribution']['chart_data'] = country_data.to_dict('records')
                        METRIC_INFO['country_breakdown']['chart_data'] = country_data.to_dict('records')
                        
                        create_country_metrics_row(
                            data=country_data,
                            title='User Distribution by Country',
                            value_col='total_visitors',
                            id_1='map_distribution',
                            id_2='country_breakdown'
                        )
                    else:
                        ui.label('No geographic data available for the selected period').classes(f'{ThemeManager.COLORS["text"]["muted"]} italic')

                    # New Users by Primary Medium & Source
                    if not results['traffic_source'].empty:
                        traffic_source_medium_data = results['traffic_source']
                        traffic_source = traffic_source_medium_data.groupby('acquisition_source', as_index=False).agg({'new_visitors': 'sum'})
                        traffic_medium = traffic_source_medium_data.groupby('acquisition_medium', as_index=False).agg({'new_visitors': 'sum'})
                        
                        # Data for AI (using full traffic metrics for context)
                        METRIC_INFO['traffic_source']['chart_data'] = traffic_source.to_dict('records')
                        METRIC_INFO['traffic_medium']['chart_data'] = traffic_medium.to_dict('records')

                        create_traffic_source_row(source_data=traffic_source,
                                                  source_title='Users Acquisition Source',
                                                  id_1='traffic_source',
                                                  medium_data=traffic_medium,
                                                  medium_title='Users Acquisition Medium',
                                                  value_col='new_visitors',
                                                  value_label='New Users',
                                                  id_2='traffic_medium'
                        )
                    else:
                        ui.label('No traffic source data available for the selected period').classes(f'{ThemeManager.COLORS["text"]["muted"]} italic')

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


                    # User Stickiness Chart
                    if not results['stickiness'].empty:
                        stickiness_data = results['stickiness']
                        # Ensure date is datetime and string format for chart
                        stickiness_data['date'] = pd.to_datetime(stickiness_data['date']).dt.strftime('%Y-%m-%d')
                        
                        # Data for AI
                        METRIC_INFO['stickiness_ratios']['chart_data'] = stickiness_data.to_dict('records')

                        create_line_chart(
                            stickiness_data,
                            'User Stickiness (DAU/WAU, DAU/MAU, WAU/MAU)',
                            'date',
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
                    'funnel_analysis': QUERIES['product_landing_page_funnel'],
                    'user_journey': QUERIES['product_user_journey'],
                    'comparison_metrics': QUERIES['product_engaged_vs_churned_metrics']
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
                                    'metric_a_value': float(row['engaged_value']),
                                    'metric_b_name': 'Churned',
                                    'metric_b_value': float(row['churned_value']),
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

                    # 2. Funnel Analysis (Full Width Row)
                    ui.label('Landing Page Funnel Analysis').classes(ThemeManager.TYPOGRAPHY['h3'] + ' mt-8 mb-4')
                    if not results['funnel_analysis'].empty:
                        df_raw = results['funnel_analysis'].copy()
                        
                        # Apply strict mapping
                        df_raw['landing_page_label'] = df_raw['landing_page'].apply(lambda x: map_path_to_landing(x, 'RegComply'))
                        df_raw['next_action_label'] = df_raw['next_common_action'].apply(lambda x: map_path_to_module(x, 'RegComply'))
                        
                        # Filter rows where both are valid (next action MUST be a module, landing must be is_landing=True)
                        df_filtered = df_raw.dropna(subset=['landing_page_label', 'next_action_label']).copy()
                        
                        if not df_filtered.empty:
                            # Aggregate by labels (landing_page_label is raw path, next_action_label is module name)
                            df_funnel = df_filtered.groupby(['landing_page_label', 'next_action_label'])['user_count'].sum().reset_index()
                            df_funnel.columns = ['landing_page', 'next_common_action', 'user_count']
                            
                            # Calculate pct_users relative to total active users
                            total_active = results['active_signed_in_users']['active_signed_in_users'].iloc[0] if not results['active_signed_in_users'].empty else 0
                            if total_active > 0:
                                df_funnel['pct_users'] = (df_funnel['user_count'] / total_active * 100).round(2)
                            else:
                                df_funnel['pct_users'] = 0.0
                                
                            df_funnel = df_funnel.sort_values('user_count', ascending=False)
                            
                            METRIC_INFO['funnel_analysis']['chart_data'] = df_funnel.to_dict('records')
                            
                            create_metric_table(df_funnel, title="Next Common Action by Landing Page", height='h-[400px]', id='funnel_analysis')
                        else:
                            ui.label('No module-level conversion actions found').classes(f'{ThemeManager.COLORS["text"]["muted"]} italic')
                    else:
                        ui.label('No funnel analysis data available').classes(f'{ThemeManager.COLORS["text"]["muted"]} italic')

                    # User Journeys
                    if not results['user_journey'].empty:
                        METRIC_INFO['user_journeys']['chart_data'] = results['user_journey'].to_dict('records')
                        create_user_journey_section(results['user_journey'], id='user_journeys')
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
                        'org_engagement': QUERIES['product_org_engagement_table']
                    },
                    start_date, end_date, platform='RegComply'
                )
                
                with container:
                    ui.label('User Engagement Analysis').classes(ThemeManager.TYPOGRAPHY['h2'] + ' mb-4')
                    ui.label('Detailed engagement metrics and user behavior analytics').classes(ThemeManager.TYPOGRAPHY['body'])
                    # ui.label(f'Date range: {start_date} to {end_date}').classes('text-sm text-slate-400 mt-2')

                    # Engagement KPIs
                    if not results['engagement_kpis'].empty:
                        row = results['engagement_kpis'].iloc[0]
                        kpis = [
                            {'id': 'avg_engagement_time_msec', 'label': 'Avg Engaged Duration', 'value': format_msec_to_time(row['avg_engaged_duration_msec']), 'icon': 'timer', 'color': 'blue', 'subtitle': 'Total time per user'},
                            {'label': 'Engaged Sessions', 'value': row['engaged_sessions'], 'icon': 'bolt', 'color': 'green'},
                            {'id': 'engagement_rate', 'label': 'Engagement Rate', 'value': f"{row['engagement_rate']}%", 'icon': 'trending_up', 'color': 'orange'},
                            {'label': 'Total Events', 'value': row['total_event_count'], 'icon': 'event', 'color': 'indigo'},
                            {'label': 'Key Events', 'value': row['key_event_count'], 'icon': 'stars', 'color': 'purple'},
                            {'label': 'Page Views', 'value': row['total_page_views'], 'icon': 'description', 'color': 'pink'}
                        ]
                        # Data for AI
                        METRIC_INFO['engagement_rate']['chart_data'] = row.to_dict()
                        
                        create_kpi_metrics(kpis)
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
                container.clear()
                with container:
                    ui.label('Feature Adoption Analysis').classes(ThemeManager.TYPOGRAPHY['h2'] + ' mb-4')
                    ui.label('Detailed feature adoption metrics and user behavior analytics').classes(ThemeManager.TYPOGRAPHY['body'])
                    ui.label('The development is in progress').classes(ThemeManager.TYPOGRAPHY['body'])
                    ui.label(f'Date range: {start_date} to {end_date}').classes('text-sm text-slate-400 mt-2')
            
            refresh_callbacks.append(load_data)
            asyncio.create_task(load_data())
            
        async def organization_deep_dive_content():
            container = ui.column().classes('w-full')
            with container:
                ui.label('Organization Deep-Dive').classes(ThemeManager.TYPOGRAPHY['h2'] + ' mb-4')
                ui.label('The tab provides a deeper dive into organizations activities.').classes(ThemeManager.TYPOGRAPHY['body'])
                ui.label('The development is in progress').classes(ThemeManager.TYPOGRAPHY['body'])

        async def handle_refresh():
            # Trigger all refresh callbacks
            for callback in refresh_callbacks:
                if inspect.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
                    
        # Initial fetch of core metrics
        await fetch_core_metrics()
        
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
            on_filter_change=handle_refresh
        )
    
    await dashboard_layout(content, page_title="RegComply Report", active_page="product/regcomply")
