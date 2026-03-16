# pages/tasks.py
from nicegui import ui, app
from components.dashboard_layout import dashboard_layout
from components.page_template import create_page_template
import inspect

async def show_tasks_page():
    async def content():
        # Keep track of functions to refresh data
        refresh_callbacks = []
        
        def get_current_dates():
            date_range = app.storage.user.get('date_range', {})
            start = date_range.get('from', '2026-01-01').replace('/', '-')
            end = date_range.get('to', '2026-01-14').replace('/', '-')
            return start, end

        async def my_tasks_content():
            container = ui.column().classes('w-full')
            async def load_data():
                start_date, end_date = get_current_dates()
                container.clear()
                with container:
                    ui.label('My tasks list').classes('text-slate-600')
                    ui.label(f'Active range: {start_date} to {end_date}').classes('text-xs text-slate-400')
            
            refresh_callbacks.append(load_data)
            ui.timer(0, load_data, once=True)
        
        async def team_tasks_content():
            container = ui.column().classes('w-full')
            async def load_data():
                start_date, end_date = get_current_dates()
                container.clear()
                with container:
                    ui.label('Team tasks overview').classes('text-slate-600')
                    ui.label(f'Active range: {start_date} to {end_date}').classes('text-xs text-slate-400')
            
            refresh_callbacks.append(load_data)
            ui.timer(0, load_data, once=True)
        
        async def handle_refresh():
            for callback in refresh_callbacks:
                if inspect.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()

        await create_page_template(
            page_title='Tasks',
            page_subtitle='Task management and assignment',
            tabs=[
                {'name': 'My Tasks', 'content_func': my_tasks_content},
                {'name': 'Team Tasks', 'content_func': team_tasks_content}
            ],
            show_filters=True,
            on_filter_change=handle_refresh
        )
    
    await dashboard_layout(content, page_title="Tasks", active_page="project/task")
