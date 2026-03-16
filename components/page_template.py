from nicegui import ui, app
from typing import List, Callable, Optional
from datetime import datetime, timedelta
import asyncio
import inspect
from components.theme_manager import ThemeManager


async def create_page_template(
    page_title: Optional[str] = None,
    page_subtitle: Optional[str] = None,
    tabs: List[dict] = None,
    active_tab: str = None,
    show_filters: bool = True,
    on_filter_change: Optional[Callable] = None
):
    """
    Creates a universal page template with title, filters, and tabs.
    """
    
    # Filters section (if enabled)
    if show_filters:

        # Initialize storage with default values
        today = datetime.now()
        thirty_days_ago = today - timedelta(days=30)
        
        if 'date_range' not in app.storage.user:
            app.storage.user['date_range'] = {
                'from': thirty_days_ago.strftime('%Y/%m/%d'),
                'to': today.strftime('%Y/%m/%d')
            }
        
        if 'time_period' not in app.storage.user:
            app.storage.user['time_period'] = 'Last 30 days'
        
            
        # Use shared filter component
        from components.filters import create_filter_bar
        create_filter_bar(on_filter_change)


    # Tabs section
    if tabs and len(tabs) > 0:
        # Set default active tab if not provided
        if not active_tab:
            active_tab = tabs[0]['name']
        
        with ui.element('div').classes('bg-slate-300/60 p-1 rounded-xl inline-flex mb-0'):
            with ui.tabs().props('dense no-caps align="left" breakpoint=0 indicator-color="transparent" active-bg-color="white" active-text-color="dark"') \
                .classes('bg-transparent') as tab_panel:
                
                for tab in tabs:
                    is_active = tab['name'] == active_tab
                    # Use standard text colors from ThemeManager
                    text_class = ThemeManager.COLORS['text']['primary'] if is_active else ThemeManager.COLORS['text']['secondary']
                    font_weight = 'font-bold' if is_active else 'font-medium'
                    
                    ui.tab(tab['name']).classes(
                        f'rounded-lg px-6 min-h-[32px] transition-all {text_class} {font_weight} ' + 
                        ('shadow-sm' if is_active else '')
                    )

        # Tab content panels
        with ui.tab_panels(tab_panel, value=active_tab).classes('w-full bg-transparent'):
            for tab in tabs:
                with ui.tab_panel(tab['name']).classes('p-0 pt-4'):
                    if 'content_func' in tab and callable(tab['content_func']):
                        if inspect.iscoroutinefunction(tab['content_func']):
                            await tab['content_func']()
                        else:
                            tab['content_func']()
                    else:
                        ui.label(f'{tab["name"]} content goes here').classes(ThemeManager.TYPOGRAPHY['body'])


def create_stats_row(stats: List[dict]):
    """
    Helper function to create a row of stat cards.
    """
    with ui.row().classes('w-full gap-4 mb-6'):
        for stat in stats:
            with ui.card().classes(f'flex-1 p-6 {ThemeManager.get_card_style()}'):
                with ui.row().classes('w-full justify-between items-start mb-3'):
                    ui.label(stat['title']).classes(ThemeManager.TYPOGRAPHY['small'])
                    ui.icon(stat['icon']).classes(f'text-2xl text-{stat["color"]}-500')
                ui.label(stat['value']).classes(ThemeManager.TYPOGRAPHY['h1'].replace('text-4xl', 'text-3xl')) # Reuse H1 style but smaller
                change_color = ThemeManager.COLORS['accent']['success'] if '+' in stat['change'] else ThemeManager.COLORS['accent']['danger']
                ui.label(stat['change']).classes(f'text-sm {change_color}')
