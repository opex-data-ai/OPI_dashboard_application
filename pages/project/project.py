import asyncio
# pages/projects.py
from nicegui import ui, app
from components.dashboard_layout import dashboard_layout
from components.page_template import create_page_template
import inspect

async def show_projects_page():
    async def content():
        # Keep track of functions to refresh data
        refresh_callbacks = []
        
        def get_current_dates():
            date_range = app.storage.user.get('date_range', {})
            start = date_range.get('from', '2026-01-01').replace('/', '-')
            end = date_range.get('to', '2026-01-14').replace('/', '-')
            return start, end

        async def active_projects_content():
            container = ui.column().classes('w-full')
            async def load_data():
                start_date, end_date = get_current_dates()
                container.clear()
                with container:
                    ui.label('Active projects list').classes('text-slate-600')
                    ui.label(f'Filter: {start_date} - {end_date}').classes('text-xs text-slate-400')
            
            refresh_callbacks.append(load_data)
            asyncio.create_task(load_data())
        
        async def completed_content():
            container = ui.column().classes('w-full')
            async def load_data():
                start_date, end_date = get_current_dates()
                container.clear()
                with container:
                    ui.label('Completed projects').classes('text-slate-600')
                    ui.label(f'Filter: {start_date} - {end_date}').classes('text-xs text-slate-400')
            
            refresh_callbacks.append(load_data)
            asyncio.create_task(load_data())
        
        async def analytics_content():
            container = ui.column().classes('w-full')
            async def load_data():
                start_date, end_date = get_current_dates()
                container.clear()
                with container:
                    ui.label('Project analytics').classes('text-slate-600')
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
            page_title='Projects',
            page_subtitle='Project management and tracking',
            tabs=[
                {'name': 'Active', 'content_func': active_projects_content},
                {'name': 'Completed', 'content_func': completed_content},
                {'name': 'Analytics', 'content_func': analytics_content}
            ],
            show_filters=True,
            on_filter_change=handle_refresh
        )
    
    await dashboard_layout(content, page_title="Projects", active_page="project/project")
