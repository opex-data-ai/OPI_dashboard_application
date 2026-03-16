from nicegui import ui, app, run
from typing import Optional

def create_header(page_title: Optional[str] = None,
                  page_subtitle: Optional[str] = None):
    """
    Creates the top header bar with logo, page title, search, notifications, and user menu.
    Fixed position, starts after sidebar (adjusts based on collapse state).
    """
    
    # Get user info from session
    first_name = app.storage.user.get('first_name', 'User')
    last_name = app.storage.user.get('last_name', '')
    role = app.storage.user.get('role', 'Viewer')
    
    # Check sidebar collapse state
    is_collapsed = app.storage.user.get('sidebar_collapsed', False)
    sidebar_width = '80px' if is_collapsed else '260px'
    
    # Create initials for avatar
    initials = f"{first_name[0]}{last_name[0] if last_name else ''}".upper()

    
    
    with ui.header().classes('bg-white border-b border-slate-200').style(f'height: 60px; padding: 0; position: fixed; top: 0; z-index: 999; transition: left 0.3s ease, width 0.3s ease;'): #left: {sidebar_width}; width: calc(100% - {sidebar_width})
        with ui.row().classes('w-full h-full items-center justify-between px-6'):
            
                    
            # Left: Page Title
            with ui.row().classes('items-center gap-3'):
                if page_title or page_subtitle:
                    with ui.column().classes('w-full mb-1'):
                        if page_title:
                            ui.label(page_title).classes('text-3xl font-bold text-slate-900 mb-2')
                        if page_subtitle:
                            ui.label(page_subtitle).classes('text-slate-600')
                #ui.image('/assets/img/epi_logo.png').classes('h-12 w-20 object-contain')
            
            # Right: Search, Notifications, User
            with ui.row().classes('items-center gap-4'):
                
                # Search button and functionality
                def open_search():
                    from config import FEATURES
                    # Searchable items (pages and features)
                    all_search_items = [
                        {'title': 'Overview', 'path': '/dashboard/overview', 'category': 'Pages', 'feature': 'overview'},
                        {'title': 'RegComply', 'path': '/dashboard/product/regcomply', 'category': 'Product Intelligence', 'feature': 'product'},
                        {'title': 'RegPort', 'path': '/dashboard/product/regport', 'category': 'Product Intelligence', 'feature': 'product'},
                        {'title': 'RegWatch', 'path': '/dashboard/product/regwatch', 'category': 'Product Intelligence', 'feature': 'product'},
                        {'title': 'Projects', 'path': '/dashboard/workforce/projects', 'category': 'Workforce Intelligence', 'feature': 'project'},
                        {'title': 'Tasks', 'path': '/dashboard/workforce/tasks', 'category': 'Workforce Intelligence', 'feature': 'project'},
                        {'title': 'Utilization', 'path': '/dashboard/workforce/utilization', 'category': 'Workforce Intelligence', 'feature': 'people'},
                        {'title': 'Staff Performance', 'path': '/dashboard/workforce/staff-performance', 'category': 'Workforce Intelligence', 'feature': 'people'},
                        {'title': 'AI Insights', 'path': '/dashboard/ai-insights', 'category': 'Pages', 'feature': 'ai_insights'},
                        {'title': 'Reports', 'path': '/dashboard/reports', 'category': 'Pages', 'feature': 'reports'},
                        {'title': 'Settings', 'path': '/dashboard/settings', 'category': 'Pages', 'feature': 'settings'},
                    ]
                    
                    # Filter items based on FEATURES config
                    search_items = [item for item in all_search_items if FEATURES.get(item['feature'], True)]
                    
                    with ui.dialog() as search_dialog, ui.card().classes('w-full max-w-2xl p-4'):
                        ui.label('Search').classes('text-xl font-bold text-slate-900 mb-4')
                        
                        search_input = ui.input(placeholder='Type to search pages...').props('autofocus outlined').classes('w-full mb-4')
                        
                        results_container = ui.column().classes('w-full gap-2 max-h-96 overflow-y-auto')
                        
                        def update_results():
                            query = search_input.value.lower().strip()
                            results_container.clear()
                            
                            if not query:
                                with results_container:
                                    ui.label('Type to search...').classes('text-slate-400 text-center py-4')
                                return
                            
                            # Filter items based on search query
                            filtered = [item for item in search_items if query in item['title'].lower() or query in item['category'].lower()]
                            
                            if not filtered:
                                with results_container:
                                    ui.label('No results found').classes('text-slate-400 text-center py-4')
                                return
                            
                            # Display results
                            with results_container:
                                for item in filtered:
                                    with ui.card().classes('w-full p-3 cursor-pointer hover:bg-blue-50 border border-slate-200').on('click', lambda p=item['path'], d=search_dialog: [ui.navigate.to(p), d.close()]):
                                        with ui.row().classes('w-full items-center justify-between'):
                                            with ui.column().classes('gap-0'):
                                                ui.label(item['title']).classes('text-base font-semibold text-slate-900')
                                                ui.label(item['category']).classes('text-xs text-slate-500')
                                            ui.icon('arrow_forward').classes('text-slate-400')
                        
                        # Update results on input change
                        search_input.on('input', update_results)
                        
                        # Initial empty state
                        with results_container:
                            ui.label('Type to search...').classes('text-slate-400 text-center py-4')
                        
                        ui.label('Press Ctrl+K to open search anytime').classes('text-xs text-slate-400 mt-2 text-center')
                    
                    search_dialog.open()
                
                # Refresh Data Button
                async def handle_refresh_data():
                    async def perform_refresh():
                        confirm_dialog.close()
                        from data_engine.data_service import get_data_service
                        with ui.dialog() as loading_dialog, ui.card().classes('p-6 items-center'):
                            ui.spinner(size='lg').classes('mb-4')
                            ui.label('Refreshing data from Data Source...').classes('text-slate-600')
                            ui.label('This may take 2-3 minutes.').classes('text-xs text-slate-400')
                        
                        loading_dialog.open()
                        try:
                            service = get_data_service()
                            # Run in thread to not block UI
                            await run.io_bound(service.reload_all_data)
                            ui.notify('Data refreshed successfully!', type='positive', position='top')
                            # Refresh current page to show new data
                            ui.navigate.to(app.storage.user.get('current_page', '/dashboard/overview'))
                        except Exception as e:
                            ui.notify(f'Failed to refresh data: {str(e)}', type='negative', position='top')
                        finally:
                            loading_dialog.close()

                    with ui.dialog() as confirm_dialog, ui.card().classes('p-6 max-w-sm'):
                        with ui.column().classes('items-center gap-4'):
                            with ui.avatar().classes('bg-amber-100 text-amber-600').props('size=lg'):
                                ui.icon('warning', size='md')
                            
                            with ui.column().classes('items-center gap-1'):
                                ui.label('Refresh Data Source?').classes('text-lg font-bold text-slate-900')
                                ui.label('This will download the latest metrics. The process takes 2-3 minutes.').classes('text-sm text-slate-500 text-center')
                            
                            with ui.row().classes('w-full gap-3 mt-4'):
                                ui.button('Cancel', on_click=confirm_dialog.close).props('outline').classes('flex-1 text-slate-600')
                                ui.button('Proceed', on_click=perform_refresh).props('flat').classes('flex-1 bg-blue-600 text-white font-bold')
                    
                    confirm_dialog.open()

                ui.button(icon='refresh', on_click=handle_refresh_data).props('flat round').classes('text-slate-600').tooltip('Refresh Data from Source')
                

                ui.button(icon='search', on_click=open_search).props('flat round').classes('text-slate-600')
                
                # Keyboard shortcut for search (Ctrl+K)
                ui.keyboard(on_key=lambda e: open_search() if e.action.keydown and e.key == 'k' and e.modifiers.ctrl else None)
                
                # Notifications dropdown
                with ui.button(icon='notifications', on_click=lambda: None).props('flat round').classes('text-slate-600 relative'):
                    # Badge
                    ui.badge('3').props('color=red floating').classes('text-xs')
                    
                    # Dropdown menu
                    with ui.menu().classes('w-80'):
                        with ui.card().classes('w-full p-4 shadow-xl'):
                            ui.label('Notifications').classes('text-lg font-bold text-slate-900 mb-3')
                            
                            with ui.column().classes('w-full gap-2 max-h-96 overflow-y-auto'):
                                # Sample notifications
                                for i in range(3):
                                    with ui.card().classes('w-full p-3 bg-blue-50 border-l-4 border-blue-600'):
                                        ui.label(f'New report available').classes('font-semibold text-slate-900 text-sm')
                                        ui.label(f'Report #{i+1} has been generated').classes('text-xs text-slate-600')
                                        ui.label('2 hours ago').classes('text-xs text-slate-400 mt-1')
                            
                            ui.button('View All Notifications').props('flat').classes('w-full mt-2 text-blue-600')
                
                # User dropdown menu
                with ui.button().props('flat').classes('gap-2'):
                    # Avatar with initials
                    with ui.avatar().classes('bg-blue-600 text-white').props('size=sm'):
                        ui.label(initials).classes('text-sm font-bold')
                    
                    # User info (hidden on mobile)
                    with ui.column().classes('items-start gap-0 hidden md:flex'):
                        ui.label(f'{first_name} {last_name}').classes('text-sm font-semibold text-slate-900 leading-tight')
                        ui.label(role).classes('text-xs text-slate-500 leading-tight')
                    
                    ui.icon('arrow_drop_down').classes('text-slate-600')
                    
                    # Dropdown menu
                    with ui.menu():
                        with ui.column().classes('w-56 p-2'):
                            # User info section
                            with ui.row().classes('w-full p-3 border-b border-slate-200 gap-3'):
                                with ui.avatar().classes('bg-blue-600 text-white'):
                                    ui.label(initials).classes('text-sm font-bold')
                                with ui.column().classes('gap-0'):
                                    ui.label(f'{first_name} {last_name}').classes('text-sm font-semibold text-slate-900')
                                    ui.label(role).classes('text-xs text-slate-500')
                            
                            # Menu items
                            #ui.menu_item('Profile', on_click=lambda: ui.notify('Profile clicked')).classes('px-4 py-2')
                            #ui.menu_item('Account Settings', on_click=lambda: ui.notify('Settings clicked')).classes('px-4 py-2')
                            #ui.separator()
                            
                            def logout():
                                app.storage.user.clear()
                                ui.navigate.to('/login')
                            
                            ui.menu_item('Logout', on_click=logout).classes('px-4 py-2 text-red-600')