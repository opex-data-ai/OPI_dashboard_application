from nicegui import ui, app
from components.dashboard_layout import dashboard_layout
from components.theme_manager import ThemeManager
from config import FEATURES


async def show_overview_page():
    """Overview/Dashboard home page"""
    first_name = app.storage.user.get('first_name', '')

    async def content():
        # Page header
        ui.label(f'Welcome back, {first_name}').classes(ThemeManager.TYPOGRAPHY['h1'].replace('text-4xl', 'text-3xl') + ' mb-2')
        ui.label("Here's what's happening across your organization today.").classes(ThemeManager.TYPOGRAPHY['body'] + ' mb-6')
        
        # Stats cards
        with ui.row().classes('w-full gap-4 mb-6'):
            stats = [
                {'title': 'Total Revenue', 'value': '$2.4M', 'change': '+12.5%', 'icon': 'attach_money', 'color': 'orange'},
                {'title': 'Active Projects', 'value': '24', 'change': '+4.2%', 'icon': 'work', 'color': 'red'},
                {'title': 'Team Utilization', 'value': '87%', 'change': '-2.1%', 'icon': 'groups', 'color': 'blue'},
                {'title': 'Performance Score', 'value': '92', 'change': '+5.8%', 'icon': 'trending_up', 'color': 'pink'}
            ]
            
            for stat in stats:
                with ui.card().classes(f'flex-1 p-6 {ThemeManager.get_card_style()}'):
                    with ui.row().classes('w-full justify-between items-start mb-3'):
                        ui.label(stat['title']).classes(ThemeManager.TYPOGRAPHY['small'])
                        ui.icon(stat['icon']).classes(f'text-2xl text-{stat["color"]}-500')
                    ui.label(stat['value']).classes('text-3xl font-bold text-slate-900 mb-1')
                    ui.label(f"{stat['change']} vs last month").classes(
                        f'text-sm {ThemeManager.COLORS["accent"]["success"]}' if '+' in stat['change'] else f'text-sm {ThemeManager.COLORS["accent"]["danger"]}'
                    )
        
        # Quick Access Section
            
        # Quick Access Section
        ui.label('Quick Access').classes(ThemeManager.TYPOGRAPHY['h2'] + ' mb-4')
        
        with ui.row().classes('w-full gap-4'):
            quick_access = [
                {
                    'title': 'Product Performance', 
                    'desc': 'Track product metrics, sales analytics, and market performance', 
                    'icon': 'inventory_2', 
                    'path': '/dashboard/product/regcomply',
                    'feature': 'product'
                },
                {
                    'title': 'Staff Performance', 
                    'desc': 'Monitor team productivity, project assignments, and individual KPIs', 
                    'icon': 'groups', 
                    'path': '/dashboard/workforce/staff-performance',
                    'feature': 'people'
                }
            ]
            
            # Filter quick access items based on FEATURES config
            quick_access = [item for item in quick_access if FEATURES.get(item['feature'], True)]
            
            for item in quick_access:
                with ui.card().classes(f'flex-1 p-6 {ThemeManager.get_card_style()} hover:shadow-lg transition-shadow cursor-pointer').on('click', lambda p=item['path']: ui.navigate.to(p)):
                    with ui.row().classes('items-center gap-4 mb-3'):
                        with ui.avatar().classes(f'bg-orange-100'):
                            ui.icon(item['icon']).classes('text-orange-600')
                        ui.label(item['title']).classes(ThemeManager.TYPOGRAPHY['h3'])
                    ui.label(item['desc']).classes(ThemeManager.TYPOGRAPHY['small'])
        
        with ui.page_scroller(position='bottom-right', x_offset=20, y_offset=20):
            ui.button('Scroll to Top')
    
    await dashboard_layout(content, page_title="Overview", active_page="overview")