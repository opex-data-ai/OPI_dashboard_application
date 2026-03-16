# pages/utilization.py
from nicegui import ui, app
from components.dashboard_layout import dashboard_layout
from components.page_template import create_page_template
import inspect

async def show_utilization_page():
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
                    ui.label('Utilization overview').classes('text-slate-600')
                    ui.label(f'Filter: {start_date} - {end_date}').classes('text-xs text-slate-400')
            
            refresh_callbacks.append(load_data)
            ui.timer(0, load_data, once=True)
        
        async def by_team_content():
            container = ui.column().classes('w-full')
            async def load_data():
                start_date, end_date = get_current_dates()
                container.clear()
                with container:
                    ui.label('Utilization by team').classes('text-slate-600')
                    ui.label(f'Filter: {start_date} - {end_date}').classes('text-xs text-slate-400')
            
            refresh_callbacks.append(load_data)
            ui.timer(0, load_data, once=True)
        
        async def trends_content():
            container = ui.column().classes('w-full')
            async def load_data():
                start_date, end_date = get_current_dates()
                container.clear()
                with container:
                    ui.label('Utilization trends').classes('text-slate-600')
                    ui.label(f'Filter: {start_date} - {end_date}').classes('text-xs text-slate-400')
            
            refresh_callbacks.append(load_data)
            ui.timer(0, load_data, once=True)
        
        async def handle_refresh():
            for callback in refresh_callbacks:
                if inspect.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()

        await create_page_template(
            page_title='Utilization',
            page_subtitle='Team and resource utilization metrics',
            tabs=[
                {'name': 'Overview', 'content_func': overview_content},
                {'name': 'By Team', 'content_func': by_team_content},
                {'name': 'Trends', 'content_func': trends_content}
            ],
            show_filters=True,
            on_filter_change=handle_refresh
        )
    
    await dashboard_layout(content, page_title="Utilization", active_page="people/utilization")
