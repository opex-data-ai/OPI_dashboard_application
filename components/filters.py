from nicegui import ui, app
from datetime import datetime, timedelta
import asyncio
import inspect
from typing import Callable, Optional, List
from components.theme_manager import ThemeManager

def get_date_range_from_period(period: str):
    today = datetime.now()
    if period == 'Last 7 days':
        start = today - timedelta(days=7)
    elif period == 'Last 30 days':
        start = today - timedelta(days=30)
    elif period == 'Last 90 days':
        start = today - timedelta(days=90)
    elif period == 'Last 12 months':
        start = today - timedelta(days=365)
    else:  # Custom
        return None
    return {
        'from': start.strftime('%Y-%m-%d'),
        'to': today.strftime('%Y-%m-%d')
    }

def detect_period_from_dates(date_range):
    if not date_range or 'from' not in date_range or 'to' not in date_range:
        return 'Custom'
    
    try:
        start = datetime.strptime(date_range['from'], '%Y-%m-%d')
        end = datetime.strptime(date_range['to'], '%Y-%m-%d')
        days_diff = (end - start).days
        
        # Check if end date is today (or very close)
        today = datetime.now()
        is_today = abs((end - today).days) <= 1
        
        if is_today:
            if abs(days_diff - 7) <= 1:
                return 'Last 7 days'
            elif abs(days_diff - 30) <= 1:
                return 'Last 30 days'
            elif abs(days_diff - 90) <= 1:
                return 'Last 90 days'
            elif abs(days_diff - 365) <= 1:
                return 'Last 12 months'
        
        return 'Custom'
    except:
        return 'Custom'

def create_filter_bar(
    on_filter_change: Optional[Callable] = None,
    org_options: List[str] = None,
    current_org_val: str = None,
    on_org_change: Optional[Callable] = None
):
    """
    Creates a standardized filter bar that syncs with app.storage.user
    Returns a dictionary of created elements for external visibility control.
    """
    
    # Initialize storage with default values if not present
    today = datetime.now()
    thirty_days_ago = today - timedelta(days=30)
    
    if 'date_range' not in app.storage.user:
        app.storage.user['date_range'] = {
            'from': thirty_days_ago.strftime('%Y-%m-%d'),
            'to': today.strftime('%Y-%m-%d')
        }
    
    if 'time_period' not in app.storage.user:
        app.storage.user['time_period'] = 'Last 30 days'
    
    
    with ui.row().classes(f'w-full items-center justify-between p-2 {ThemeManager.get_card_style()}'):
        # Left side: Filter icon, label, and filter controls
        with ui.row().classes('items-center gap-4'):
            # Filter icon and label
            with ui.row().classes('items-center gap-2'):
                ui.icon('filter_alt').classes('text-slate-600')
                ui.label('Filters').classes('text-sm font-semibold text-slate-700')

            # Defined update handlers first so they can be referenced
            def notify_and_callback():
                # Show notification
                stored_period = app.storage.user.get('time_period')
                stored_range = app.storage.user.get('date_range')
                # Optional: Concise notification or skip to reduce noise
                # ui.notify(f"Filter: {stored_period}", type='positive', position='top', timeout=1000)
                
                if on_filter_change:
                    if inspect.iscoroutinefunction(on_filter_change):
                        asyncio.create_task(on_filter_change())
                    else:
                        on_filter_change()

            # Time period filter
            def on_period_change(e):
                period = e.value
                app.storage.user['time_period'] = period
                
                # Update date range based on period
                date_range = get_date_range_from_period(period)
                if date_range:
                    app.storage.user['date_range'] = date_range
                    # Update UI elements
                    date_label.set_text(f"{date_range['from']} - {date_range['to']}")
                    date_picker.set_value(date_range)
                
                notify_and_callback()

            time_select = ui.select(
                ['Last 7 days', 'Last 30 days', 'Last 90 days', 'Last 12 months', 'Custom'],
                value=app.storage.user.get('time_period', 'Last 30 days'),
                on_change=on_period_change
            ).props('outlined dense rounded').classes('w-48')

            # Organization Filter (Optional)
            org_select = None
            if org_options is not None:
                org_select = ui.select(
                    options=org_options,
                    value=current_org_val,
                    on_change=on_org_change,
                    with_input=True,
                    label='Organization'
                ).props('outlined dense rounded').classes('w-64 ml-4')
            
        
        # Right side: Date range section
        current = app.storage.user['date_range']
        
        with ui.row().classes('items-center gap-3 px-4 py-2 border border-slate-200 rounded-xl hover:bg-indigo-50 cursor-pointer transition-colors group') as date_button:
            ui.icon('calendar_today').classes('text-slate-700 text-sm group-hover:text-indigo-600')
            date_label = ui.label(f"{current['from']} - {current['to']}").classes('text-sm font-medium text-slate-700 group-hover:text-indigo-600')

            with ui.menu().props('no-parent-event') as date_menu:
                with ui.column().classes('p-2 items-center'):
                    date_picker = ui.date(value=app.storage.user['date_range']).props('range minimal color="indigo"')
                    
                    def apply_date():
                        val = date_picker.value
                        if not val: return
                        
                        new_range = {'from': val, 'to': val} if isinstance(val, str) else val
                        app.storage.user['date_range'] = new_range
                        
                        # Update UI
                        date_label.set_text(f"{new_range['from']} - {new_range['to']}")
                        
                        # Detect period
                        detected = detect_period_from_dates(new_range)
                        app.storage.user['time_period'] = detected
                        time_select.set_value(detected)
                        
                        date_menu.close()
                        notify_and_callback()

                    ui.button('Apply', on_click=apply_date).props('unelevated').classes('btn-primary w-full mt-2')

            date_button.on('click', date_menu.open)
        
    return {
        'time_select': time_select,
        'org_select': org_select,
        'date_container': date_button
    }
