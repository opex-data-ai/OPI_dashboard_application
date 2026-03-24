from nicegui import ui, app
from components.dashboard_layout import dashboard_layout
from components.page_template import create_page_template
from data_engine.data_loader import get_data_loader
from data_engine.query_store import QUERIES
from components.chart_components import create_bar_chart, create_column_chart, create_line_chart
from components.filters import create_filter_bar
from components.theme_manager import ThemeManager
from data_engine.chart_descriptions import METRIC_INFO
import asyncio
import inspect
import pandas as pd

async def show_product_home_page():
    
    loader = get_data_loader()
    
    async def load_data(start_date, end_date):
        # 1. Load Stats and Charts Data
        queries_to_run = {
            'total_revenue': QUERIES['total_revenue'],
            'platform_count': QUERIES['platform_count'],
            'organization_by_platform': QUERIES['organization_by_platform'],
            'user_by_platform': QUERIES['user_by_platform'],
            'ecosystem_adoption_rate': QUERIES['ecosystem_adoption_rate'],
            'platform_organization_user_count': QUERIES['platform_organization_user_count'],
            'platform_rate_metrics': QUERIES['platform_rate_metrics']
        }
        
        results = loader.execute_batch_queries(queries_to_run, start_date, end_date)
        
            
        multi_org_count = 0
        if not results['multiplatform_organization'].empty:
            multi_org_count = results['multiplatform_organization'].iloc[0, 0]
            
        total_orgs = 0
        if not results['organization_by_platform'].empty:
             total_orgs = results['organization_by_platform'].iloc[:, 0].sum()

        stats_data = {
            'multi_orgs': str(multi_org_count),
            'total_orgs': str(total_orgs)
        }
        
        # --- Filter Chart Data ---
        # Remove 'Unknown' platforms from all chart data
        if not results['platform_organization_user_count'].empty:
            results['platform_organization_user_count'] = results['platform_organization_user_count'][
                results['platform_organization_user_count']['platform'].str.lower() != 'unknown'
            ]
        
        if not results['platform_rate_metrics'].empty:
            # Filter out 'Unknown' platforms
            results['platform_rate_metrics'] = results['platform_rate_metrics'][
                results['platform_rate_metrics']['platform'].str.lower() != 'unknown'
            ]
            # Filter out rows where all rate metrics are null
            #rate_cols = ['growth_rate_pct', 'churn_rate_pct', 'engagement_rate_pct']
            #results['platform_rate_metrics'] = results['platform_rate_metrics'].dropna(
                #subset=rate_cols, 
                #how='all'
            #)
            
            # Clip negative rates to zero
            #for col in rate_cols:
                #if col in results['platform_rate_metrics'].columns:
                    #results['platform_rate_metrics'][col] = results['platform_rate_metrics'][col].clip(lower=0)
        
        return stats_data, results

    async def content():
        with ui.column().classes('w-full gap-8'):
            # Header Section
            with ui.column().classes('w-full gap-2'):
                #ui.label('Ecosystem Performance Overview').classes(ThemeManager.TYPOGRAPHY['h1'])
                ui.label('Driving adoption, engagement, and cross-platform growth across our full suite of solutions.').classes(f'text-lg {ThemeManager.COLORS["text"]["secondary"]} max-w-xl')
            
            # Container that will be refreshed
            content_container = ui.column().classes('w-full gap-8')

            async def refresh_content():
                content_container.clear()
                
                with content_container:
                    ui.spinner(size='lg').classes('mx-auto my-20')
                
                # Hardcode date range for "All Data" as requested
                start_date = '2020-01-01'
                end_date = '2026-12-31'
                
                queries_to_run = {
                    'organization_by_platform': QUERIES['organization_by_platform'],
                    'user_by_platform': QUERIES['user_by_platform'],
                    'ecosystem_adoption_rate': QUERIES['ecosystem_adoption_rate'],
                    'platform_organization_user_count': QUERIES['platform_organization_user_count'],
                    'platform_rate_metrics': QUERIES['platform_rate_metrics'],
                    'top_org_per_platform': QUERIES['top_org_per_platform']
                }
                
                # Execute queries within a thread to keep UI responsive if needed, 
                # though execute_batch_queries is already synchronous here.
                results = loader.execute_batch_queries(queries_to_run, start_date, end_date)
                
                # --- Process Stats (Row 1) ---
                total_ecosystem_orgs = results['organization_by_platform'].iloc[:, 0].sum() if not results['organization_by_platform'].empty else 0
                total_ecosystem_users = results['user_by_platform'].iloc[:, 0].sum() if not results['user_by_platform'].empty else 0
                total_platforms = results['user_by_platform'].shape[0] if not results['user_by_platform'].empty else 0

                multi_platform_rate = 0
                full_ecosystem_rate = 0
                if not results['ecosystem_adoption_rate'].empty:
                    multi_platform_rate = results['ecosystem_adoption_rate'].iloc[0].get('multi_platform_adoption_rate', 0)
                    full_ecosystem_rate = results['ecosystem_adoption_rate'].iloc[0].get('full_ecosystem_adoption_rate', 0)
                 
                stats_data = {
                    'total_orgs': f"{total_ecosystem_orgs:,}",
                    'total_users': f"{total_ecosystem_users:,}",
                    'total_platforms': str(total_platforms),
                    'multi_rate': f"{multi_platform_rate * 100:.1f}%",
                    'full_rate': f"{full_ecosystem_rate * 100:.1f}%"
                }
                
                # Populate METRIC_INFO for AI insights
                METRIC_INFO['ecosystem_orgs']['chart_data'] = {'total_orgs': total_ecosystem_orgs}
                METRIC_INFO['ecosystem_users']['chart_data'] = {'total_users': total_ecosystem_users}
                METRIC_INFO['ecosystem_platforms']['chart_data'] = {'total_platforms': total_platforms}
                METRIC_INFO['multi_platform_rate']['chart_data'] = {'rate': multi_platform_rate}
                METRIC_INFO['full_ecosystem_rate']['chart_data'] = {'rate': full_ecosystem_rate}

                content_container.clear()
                with content_container:
                    # 1. Stats Row (KPIs) - Responsive Grid
                    with ui.grid(columns=5).classes('w-full gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 items-stretch'):
                        stats_config = [
                            {'id': 'ecosystem_orgs', 'title': 'Total Ecosystem Organizations', 'value': stats_data['total_orgs'], 'icon': 'domain', 'color': 'purple'},
                            {'id': 'ecosystem_users', 'title': 'Total Ecosystem Users', 'value': stats_data['total_users'], 'icon': 'groups', 'color': 'blue'},
                            {'id': 'ecosystem_platforms', 'title': 'Total Platforms', 'value': stats_data['total_platforms'], 'icon': 'layers', 'color': 'green'},
                            {'id': 'multi_platform_rate', 'title': 'Multi-platform Adoption Rate', 'value': stats_data['multi_rate'], 'icon': 'hub', 'color': 'orange'},
                            {'id': 'full_ecosystem_rate', 'title': 'Full Ecosystem Adoption Rate', 'value': stats_data['full_rate'], 'icon': 'verified', 'color': 'indigo'}
                        ]
                        
                        for stat in stats_config:
                            with ui.card().classes(f'h-full p-6 pt-4 {ThemeManager.get_card_style()} hover:shadow-md transition-shadow flex flex-col'): # Reduced top padding
                                with ui.row().classes('w-full justify-between items-start mb-1 no-wrap shrink-0'): # Reduced mb
                                    ui.label(stat['title']).classes(ThemeManager.TYPOGRAPHY['small'] + ' font-bold tracking-wider')
                                    
                                    with ui.row().classes('items-center gap-2'):
                                        # Info Icon with Popover
                                        if 'id' in stat:
                                            desc_data = METRIC_INFO.get(stat['id'])
                                            if desc_data:
                                                with ui.button(icon='info_outline', color='slate-100').props('flat round size=sm').classes('opacity-60 hover:opacity-100 p-0'):
                                                    with ui.menu().classes('p-4 max-w-xs shadow-2xl rounded-xl border border-slate-100'):
                                                        ui.label(desc_data['title']).classes('font-bold text-slate-900 mb-1')
                                                        ui.label(desc_data['description']).classes('text-sm text-slate-600 leading-normal')
                                                
                                                # AI Insight Icon
                                                if desc_data.get('show_ai_icon'):
                                                    from components.chart_components import show_ai_insight_dialog
                                                    ui.button(icon='auto_awesome', color='amber').props('flat round size=sm').classes('p-0').on('click', lambda s=stat['id']: show_ai_insight_dialog(s))
                                
                                ui.label(stat['value']).classes(ThemeManager.TYPOGRAPHY['h1'].replace('text-4xl', 'text-2xl') + ' mt-auto leading-none pt-2')

                    # 2. Charts Row (Organizations & Users) - Side by Side Responsive Grid
                    with ui.grid(columns=2).classes('w-full gap-6 grid-cols-1 lg:grid-cols-2 items-stretch mt-4'):
                        # Chart 1: Organizations by Platform (Horizontal Bar)
                        if not results['organization_by_platform'].empty:
                            org_data = results['organization_by_platform']
                            org_data = org_data[org_data['platform'].str.lower() != 'unknown']
                            
                            # Data for AI
                            METRIC_INFO['org_breakdown']['chart_data'] = org_data.to_dict('records')

                            create_bar_chart(
                                org_data, 
                                'Platform Organization Breakdown',  
                                'platform', 
                                ['total_orgs'],
                                height='h-72',
                                labels = ['Total Organizations'],
                                id='org_breakdown'
                            )

                        # Chart 2: Signed-In Users (Vertical Column)
                        if not results['user_by_platform'].empty:
                            user_data = results['user_by_platform']
                            user_data = user_data[user_data['platform'].str.lower() != 'unknown']

                            # Data for AI
                            METRIC_INFO['user_breakdown']['chart_data'] = user_data.to_dict('records')

                            create_column_chart(
                                user_data,
                                'Platform User Breakdown', 
                                'platform',
                                ['total_users'],
                                height='h-72',
                                id='user_breakdown'
                            )

                    # --- NEW LINE CHARTS SECTION (COMMENTED OUT) ---
                    # ui.label('Platform Growth & Churn Trends').classes(ThemeManager.TYPOGRAPHY['h2'] + ' mt-8 mb-2 px-1')
                    # 
                    # years_df = loader.execute_query(QUERIES['product_available_years'])
                    # available_years = years_df['year'].astype(int).tolist() if not years_df.empty else [2026]
                    # if not available_years: available_years = [2026]
                    # selected_year = available_years[0]
                    # 
                    # with ui.row().classes('w-full items-center justify-end mb-4 px-1'):
                    #     year_select = ui.select(
                    #         options=available_years,
                    #         value=selected_year,
                    #         label='Select Year'
                    #     ).classes('w-48')
                    # 
                    # charts_container = ui.row().classes('w-full items-stretch')
                    # 
                    # def update_line_charts(e=None):
                    #     year_to_use = e.value if e else selected_year
                    #     charts_container.clear()
                    #     
                    #     growth_df = loader.execute_query(QUERIES['product_growth_rate'], [year_to_use])
                    #     churn_df = loader.execute_query(QUERIES['product_churn_rate'], [year_to_use, year_to_use])
                    #     
                    #     with charts_container:
                    #         with ui.grid(columns=2).classes('w-full gap-6 grid-cols-1 lg:grid-cols-2'):
                    #             # --- Growth Rate Chart ---
                    #             if not growth_df.empty:
                    #                 growth_df['month_date'] = pd.to_datetime(growth_df['month'])
                    #                 growth_pivot = growth_df.pivot(index='month_date', columns='platform', values='mom_growth_rate_pct').reset_index()
                    #                 growth_pivot = growth_pivot.sort_values('month_date')
                    #                 growth_pivot['month_str'] = growth_pivot['month_date'].dt.strftime('%b')
                    # 
                    #                 cols_dict = {c: str(c).replace('_', ' ').title() for c in growth_pivot.columns if c not in ['month_date', 'month_str'] and pd.notna(c) and str(c).lower() != 'unknown'}
                    #                 create_line_chart(
                    #                     growth_pivot,
                    #                     'Month-on-Month Growth Rate',
                    #                     'month_str',
                    #                     cols_dict,
                    #                     height='h-72',
                    #                     y_axis_name='Growth %'
                    #                 )
                    #             else:
                    #                 with ui.card().classes(f'w-full p-6 {ThemeManager.get_card_style()} flex items-center justify-center h-72'):
                    #                     ui.label('No growth data available for this year').classes('text-slate-400 italic')
                    #                     
                    #             # --- Churn Rate Chart ---
                    #             if not churn_df.empty:
                    #                 churn_df['month_date'] = pd.to_datetime(churn_df['month'])
                    #                 churn_pivot = churn_df.pivot(index='month_date', columns='platform', values='churn_rate_pct').reset_index()
                    #                 churn_pivot = churn_pivot.sort_values('month_date')
                    #                 churn_pivot['month_str'] = churn_pivot['month_date'].dt.strftime('%b')
                    #                 cols_dict = {c: str(c).replace('_', ' ').title() for c in churn_pivot.columns if c not in ['month_date', 'month_str'] and pd.notna(c) and str(c).lower() != 'unknown'}
                    #                 create_line_chart(
                    #                     churn_pivot,
                    #                     'Month-on-Month Churn Rate',
                    #                     'month_str',
                    #                     cols_dict,
                    #                     height='h-72',
                    #                     y_axis_name='Churn %'
                    #                 )
                    #             else:
                    #                 with ui.card().classes(f'w-full p-6 {ThemeManager.get_card_style()} flex items-center justify-center h-72'):
                    #                     ui.label('No churn data available for this year').classes('text-slate-400 italic')
                    # 
                    # year_select.on_value_change(update_line_charts)
                    # update_line_charts()
                                
                    # 3. Top Organization per Platform (Row 3) - Responsive Grid
                    ui.label('Top Organization by Engagement').classes(ThemeManager.TYPOGRAPHY['h2'] + ' mt-8 mb-2 px-1')
                    
                    with ui.grid(columns=3).classes('w-full gap-6 grid-cols-1 md:grid-cols-2 xl:grid-cols-3 items-stretch'):
                        top_orgs_data = results.get('top_org_per_platform', pd.DataFrame())
                        
                        if not top_orgs_data.empty:
                            for idx, row in top_orgs_data.iterrows():
                                platform_name = row['platform']
                                org_name = row['organizationName']
                                email = row['email_domain']
                                # Handle nullable or weird date formats
                                try:
                                    raw_date = row['organization_start_date']
                                    if pd.notna(raw_date):
                                        start_date_val = pd.to_datetime(raw_date).strftime('%b %d, %Y')
                                    else:
                                        start_date_val = 'N/A'
                                except:
                                    start_date_val = 'N/A'
                                
                                with ui.card().classes(f'h-full p-6 {ThemeManager.get_card_style()} hover:shadow-md transition-shadow flex flex-col'):
                                    # Platform Header
                                    ui.label(platform_name).classes('text-xs font-bold text-slate-500 tracking-wider uppercase mb-3')
                                    
                                    # Organization Name & Email
                                    with ui.column().classes('gap-1 mb-4 flex-grow'):
                                        ui.label(org_name).classes(ThemeManager.TYPOGRAPHY['h3'] + ' break-words')
                                        ui.label(email).classes(ThemeManager.TYPOGRAPHY['small'])
                                    
                                    # Metrics Row
                                    with ui.row().classes('w-full items-center justify-between mb-4 mt-auto'):
                                        # Engagement
                                        with ui.column().classes('gap-0'):
                                            if pd.notna(row['engagement_rate_pct']):
                                                engagement_rate = float(row['engagement_rate_pct'])
                                                eng_label = f"{engagement_rate:.1f}%"
                                            else:
                                                eng_label = "N/A"
                                            ui.label(eng_label).classes(f'text-2xl font-black {ThemeManager.COLORS["accent"]["success"]} leading-none')
                                            ui.label('Engagement Rate').classes('text-[10px] text-slate-400 font-medium uppercase mt-1')
                                        
                                        # Total Sessions
                                        with ui.column().classes('gap-0 items-end'):
                                            sessions = int(row['total_sessions']) if pd.notna(row['total_sessions']) else 0
                                            ui.label(f"{sessions}").classes(f'text-xl font-bold {ThemeManager.COLORS["text"]["primary"]} leading-none')
                                            ui.label('Total Sessions').classes('text-[10px] text-slate-400 font-medium uppercase mt-1')
                                    
                                    # Footer Info
                                    ui.separator().classes('my-2 opacity-50')
                                    with ui.row().classes('w-full items-center gap-2'):
                                        ui.icon('calendar_month', size='xs').classes('text-slate-300')
                                        ui.label(f"Client since {start_date_val}").classes('text-xs text-slate-500 font-medium')
                        else:
                            ui.label('No organization data available.').classes(f'{ThemeManager.COLORS["text"]["muted"]} italic px-1')

            # Initial Load
            await refresh_content()
            
            # Section Label
            with ui.column().classes('w-full mt-8 mb-4'):
                ui.label('Product Dashboards').classes(ThemeManager.TYPOGRAPHY['h2'])
                ui.label('Deep dive into specific product performance and metrics.').classes(ThemeManager.TYPOGRAPHY['body'])

            # Product Cards Grid
            with ui.grid(columns=3).classes('w-full gap-6 items-stretch grid-cols-1 md:grid-cols-2 lg:grid-cols-3'):
                # RegComply Card
                with ui.card().classes(f'h-full p-8 {ThemeManager.get_card_style()} hover:shadow-xl transition-all group overflow-hidden relative cursor-pointer') \
                    .on('click', lambda: ui.navigate.to('/product/regcomply')):
                    # Background Accent
                    ui.element('div').classes('absolute -right-12 -top-12 w-48 h-48 bg-blue-50 rounded-full opacity-50 group-hover:scale-110 transition-transform duration-500')
                    
                    with ui.column().classes('w-full h-full relative z-10'):
                        ui.icon('verified_user', size='3rem').classes('text-blue-600 mb-6 bg-blue-50 p-4 rounded-xl')
                        ui.label('RegComply').classes(ThemeManager.TYPOGRAPHY['h2'] + ' mb-2')
                        ui.label('Comprehensive compliance management and audit tracking. Monitor regulatory adherence in real-time.').classes(ThemeManager.TYPOGRAPHY['body'] + ' mb-8 flex-grow')
                        
                        with ui.row().classes('w-full justify-between items-center mt-auto'):
                            ui.label('View Dashboard').classes(f'font-bold group-hover:translate-x-1 transition-transform text-{ThemeManager.get_primary_color()}')
                            ui.icon('arrow_forward').classes(f'text-{ThemeManager.get_primary_color()}')

                # RegPort Card
                with ui.card().classes(f'h-full p-8 {ThemeManager.get_card_style()} hover:shadow-xl transition-all group overflow-hidden relative cursor-pointer') \
                    .on('click', lambda: ui.navigate.to('/product/regport')):
                    # Background Accent
                    ui.element('div').classes('absolute -right-12 -top-12 w-48 h-48 bg-green-50 rounded-full opacity-50 group-hover:scale-110 transition-transform duration-500')
                    
                    with ui.column().classes('w-full h-full relative z-10'):
                        ui.icon('account_balance_wallet', size='3rem').classes('text-green-600 mb-6 bg-green-50 p-4 rounded-xl')
                        ui.label('RegPort').classes(ThemeManager.TYPOGRAPHY['h2'] + ' mb-2')
                        ui.label('Regulatory reporting and portfolio analysis tool. Visualise performance with advanced analytics.').classes(ThemeManager.TYPOGRAPHY['body'] + ' mb-8 flex-grow')
                        
                        with ui.row().classes('w-full justify-between items-center mt-auto'):
                            ui.label('View Dashboard').classes('text-green-600 font-bold group-hover:translate-x-1 transition-transform')
                            ui.icon('arrow_forward').classes('text-green-600')

                # RegWatch Card
                with ui.card().classes(f'h-full p-8 {ThemeManager.get_card_style()} hover:shadow-xl transition-all group overflow-hidden relative cursor-pointer') \
                    .on('click', lambda: ui.navigate.to('/product/regwatch')):
                    # Background Accent
                    ui.element('div').classes('absolute -right-12 -top-12 w-48 h-48 bg-purple-50 rounded-full opacity-50 group-hover:scale-110 transition-transform duration-500')
                    
                    with ui.column().classes('w-full h-full relative z-10'):
                        ui.icon('troubleshoot', size='3rem').classes('text-purple-600 mb-6 bg-purple-50 p-4 rounded-xl')
                        ui.label('RegWatch').classes(ThemeManager.TYPOGRAPHY['h2'] + ' mb-2')
                        ui.label('Active monitoring and automated alerts for regulatory changes and risk assessments.').classes(ThemeManager.TYPOGRAPHY['body'] + ' mb-8 flex-grow')
                        
                        with ui.row().classes('w-full justify-between items-center mt-auto'):
                            ui.label('View Dashboard').classes('text-purple-600 font-bold group-hover:translate-x-1 transition-transform')
                            ui.icon('arrow_forward').classes('text-purple-600')

            # Features Section
            ui.label('Common Features').classes(ThemeManager.TYPOGRAPHY['h2'] + ' mt-12 mb-4')
            with ui.row().classes('w-full gap-4'):
                features = [
                    {'title': 'Real-time Analytics', 'icon': 'data_exploration', 'desc': 'Instant insights into your regulatory data.'},
                    {'title': 'AI-Powered Platform', 'icon': 'auto_awesome', 'desc': 'Anomaly detection and Conversational AI'},
                    {'title': 'Secure & Private', 'icon': 'lock', 'desc': 'Enterprise-grade security and data encryption.'}
                ]
                for f in features:
                    with ui.card().classes('flex-1 p-6 border border-slate-100 bg-slate-50 shadow-none rounded-xl'):
                        with ui.row().classes('items-center gap-3 mb-2'):
                            ui.icon(f['icon']).classes('text-slate-600')
                            ui.label(f['title']).classes('font-bold text-slate-800')
                        ui.label(f['desc']).classes('text-sm text-slate-500')

    await dashboard_layout(content, page_title="Ecosystem Performance Overview", active_page="product/home")
