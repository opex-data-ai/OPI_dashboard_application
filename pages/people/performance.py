import asyncio
# pages/staff_performance.py
from nicegui import ui, app
from components.dashboard_layout import dashboard_layout
from components.page_template import create_page_template
import inspect

async def show_performance_page():
    async def content():
        # Keep track of functions to refresh data
        refresh_callbacks = []
        
        def get_current_dates():
            date_range = app.storage.user.get('date_range', {})
            start = date_range.get('from', '2026-01-01').replace('/', '-')
            end = date_range.get('to', '2026-01-14').replace('/', '-')
            return start, end

        async def overview_content():
            container = ui.column().classes('w-full')
            async def load_data():
                start_date, end_date = get_current_dates()
                container.clear()
                with container:
                    ui.label('Staff performance overview').classes('text-slate-600')
                    ui.label(f'Filter: {start_date} - {end_date}').classes('text-xs text-slate-400')
            
            refresh_callbacks.append(load_data)
            asyncio.create_task(load_data())
        
        async def individual_content():
            container = ui.column().classes('w-full')
            async def load_data():
                start_date, end_date = get_current_dates()
                container.clear()
                with container:
                    ui.label('Individual performance metrics').classes('text-slate-600')
                    ui.label(f'Filter: {start_date} - {end_date}').classes('text-xs text-slate-400')
            
            refresh_callbacks.append(load_data)
            asyncio.create_task(load_data())
        
        async def reviews_content():
            container = ui.column().classes('w-full')
            async def load_data():
                start_date, end_date = get_current_dates()
                container.clear()
                with container:
                    ui.label('Performance reviews').classes('text-slate-600')
                    ui.label(f'Filter: {start_date} - {end_date}').classes('text-xs text-slate-400')
            
            refresh_callbacks.append(load_data)
            asyncio.create_task(load_data())
        
        async def handle_refresh():
            for callback in refresh_callbacks:
                if inspect.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()

        await create_page_template(
            page_title='Staff Performance',
            page_subtitle='Individual and team performance tracking',
            tabs=[
                {'name': 'Overview', 'content_func': overview_content},
                {'name': 'Individual', 'content_func': individual_content},
                {'name': 'Reviews', 'content_func': reviews_content}
            ],
            show_filters=True,
            on_filter_change=handle_refresh
        )
    
    await dashboard_layout(content, page_title="Staff Performance", active_page="people/performance")
