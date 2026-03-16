from nicegui import ui, app


from config import FEATURES

def create_sidebar(active_page: str = ''):
    """
    Creates the navigation sidebar with menu items, dropdowns, and collapse functionality.
    Full height, independently scrollable.
    
    Args:
        active_page: Current page path (e.g., '/overview' or 'overview')
    """
    
    # Normalize active page (remove /dashboard/ prefix if present)
    # Normalize active page (remove leading slash if present)
    if active_page.startswith('/'):
        active_page = active_page[1:]
    
    # Standard widths
    EXPANDED_WIDTH = 260
    COLLAPSED_WIDTH = 80

    # Get current state from storage
    is_collapsed = app.storage.user.get('sidebar_collapsed', False)
    current_width = COLLAPSED_WIDTH if is_collapsed else EXPANDED_WIDTH

    # Use a local state or check storage initially
    with ui.left_drawer(value=True, fixed=True, top_corner=True, bottom_corner=True, elevated=False) \
        .props(f'bordered width={current_width} breakpoint=0') \
        .classes('border-r border-slate-300 p-0') \
        .style('''
            position: fixed; top: 0; left: 0; height: 100vh; overflow: hidden;
            background: linear-gradient(180deg, #171d26 0%, #171d26 100%);
            box-shadow: 4px 0 12px rgba(0, 0, 0, 0.1);
        ''') as drawer:
        
        # Internal state to track toggle locally for UI changes
        state = {'collapsed': is_collapsed}

        def toggle_sidebar():
            # Toggle state and save to storage
            new_state = not state['collapsed']
            app.storage.user['sidebar_collapsed'] = new_state
            
            # Reload page to apply new layout
            ui.navigate.reload()

        with ui.column().classes('w-full h-full').style('height: 100vh; display: flex; flex-direction: column;'):
            
            # Header Section
            header_classes = 'p-1 justify-center' if state['collapsed'] else 'p-4 gap-3 no-wrap'
            with ui.row().classes(f'items-center w-full overflow-hidden {header_classes}'):
                if state['collapsed']:
                    ui.image('/assets/img/epi_logo_white.png').classes('w-full h-6 object-contain m-2')
                else:
                    ui.image('/assets/img/epi_logo_white.png').classes('h-8 w-18 object-contain flex-shrink-0')
                    with ui.column().classes('gap-0'):
                        ui.label('Enterprise Performance').classes('text-blue-400 font-bold tracking-wider uppercase text-[8px] leading-tight')
                        ui.label('Intelligence').classes('text-xs font-black text-slate-200 leading-tight')
            # Menu Section (scrollable, takes remaining space)
            with ui.scroll_area().classes('w-full p-0').style('flex: 1; overflow-y: auto; overflow-x: hidden;'):
                
                # Menu items with icons
                menu_items = [
                    {
                        'title': 'Overview',
                        'icon': 'dashboard',
                        'path': 'overview',
                        'feature': 'overview',
                        'children': None
                    },
                    {
                        'title': 'Product',
                        'icon': 'inventory_2',
                        'path': 'product/home',
                        'base_path': 'product',
                        'feature': 'product',
                        'children': [
                            {'title': 'RegComply', 'path': 'product/regcomply'},
                            {'title': 'RegPort', 'path': 'product/regport'},
                            {'title': 'RegWatch', 'path': 'product/regwatch'}
                        ]
                    },
                    {
                        'title': 'People',
                        'icon': 'groups',
                        'path': 'people',
                        'feature': 'people',
                        'children': [
                            {'title': 'Utilization', 'path': 'people/utilization'},
                            {'title': 'Staff Performance', 'path': 'people/performance'}
                        ]
                    },
                     {
                        'title': 'Projects',
                        'icon': 'bookmarks',
                        'path': 'project',
                        'feature': 'project',
                        'children': [
                            {'title': 'Projects', 'path': 'project/project'},
                            {'title': 'Tasks', 'path': 'project/task'},
                        ]
                    },
                    {
                        'title': 'AI Insights',
                        'icon': 'psychology',
                        'path': 'ai_insights',
                        'feature': 'ai_insights',
                        'children': None
                    },
                    {
                        'title': 'Reports',
                        'icon': 'assessment',
                        'path': 'reports',
                        'feature': 'reports',
                        'children': None
                    },
                    {
                        'title': 'Settings',
                        'icon': 'settings',
                        'path': 'settings',
                        'feature': 'settings',
                        'children': None
                    }
                ]
                
                # Filter menu items based on FEATURES config
                menu_items = [item for item in menu_items if FEATURES.get(item['feature'], True)]
                
                # Render menu items
                for item in menu_items:
                    # Check if this item or any of its children is active
                    base_path = item.get('base_path', item['path'])
                    is_parent_active = active_page.startswith(base_path)
                    
                    if state['collapsed']:
                        # Show only icons when collapsed
                        is_active = active_page == item['path'] or (active_page.startswith(base_path) and base_path != active_page)
                        
                        with ui.button(icon=item['icon'], on_click=lambda p=item['path']: ui.navigate.to(f'/{p}')).props('flat').classes(
                            'w-full py-3 rounded-none bg-white text-[#171d26] shadow-lg' if is_active else
                            'w-full py-3 rounded-none text-white hover:bg-white/10 transition-all duration-200'
                        ):
                            ui.tooltip(item['title'])
                    
                    elif item['children']:
                        # Item with dropdown (expanded mode)
                        # Keep dropdown open if we're on any of its child pages
                        is_expanded = is_parent_active
                        
                        with ui.expansion(item['title'], icon=item['icon'], value=is_expanded).classes(
                            'w-full text-white' if is_parent_active else 'w-full text-slate-300'
                        ).props('dense dark').style(
                            'background: rgba(23, 29, 38, 0.2); border-left: 3px solid #f0f2f5; backdrop-filter: blur(10px);' if is_parent_active else
                            'background: transparent;'
                        ) as exp:
                            # CLICK HANDLER FOR NAVIGATION ON THE EXPANSION HEADER
                            exp.on('click', lambda p=item['path']: ui.navigate.to(f'/{p}'))
                            
                            for child in item['children']:
                                is_child_active = active_page == child['path']
                                
                                with ui.item(on_click=lambda p=child['path']: ui.navigate.to(f'/{p}')).classes(
                                    'w-full pl-12 py-2 rounded-lg transition-all duration-200'
                                ).style(
                                    'background: white; color: #171d26; transform: translateX(4px); box-shadow: 0 4px 6px rgba(0,0,0,0.1); font-weight: 600;' if is_child_active else 
                                    'background: rgba(255, 255, 255, 0.05); color: #cbd5e1;' if is_parent_active else
                                    'background: transparent; color: #94a3b8;'
                                ):
                                    with ui.row().classes('items-center gap-2'):
                                        #if is_child_active:
                                        #    ui.icon('arrow_right').classes('text-sm')
                                        ui.item_label(child['title']).classes('text-sm font-medium')
                    else:
                        # Simple item (expanded mode)
                        is_active = active_page == item['path']
                        
                        with ui.item(on_click=lambda p=item['path']: ui.navigate.to(f'/{p}')).classes(
                            'w-full py-3 px-4 rounded-lg transition-all duration-200'
                        ).style(
                            'background: white; color: #171d26; transform: translateX(4px); box-shadow: 0 4px 6px rgba(0,0,0,0.1); font-weight: 600;' if is_active else
                            'background: transparent; color: #cbd5e1;'
                        ):
                            with ui.row().classes('items-center gap-3'):
                                ui.icon(item['icon']).classes('text-xl' + (' drop-shadow-lg' if is_active else ''))
                                ui.item_label(item['title']).classes('text-sm font-medium')

            # Footer Section (fixed at bottom)
            ui.separator().classes('bg-slate-600/30')
            with ui.row().classes('w-full p-4 items-center cursor-pointer transition-all duration-200 text-slate-300').style(
                'min-height: 60px; background: rgba(255, 255, 255, 0.05);'
            ).on('click', toggle_sidebar):
                if state['collapsed']:
                    # Icon only when collapsed
                    ui.icon('chevron_right').classes('w-full text-center text-white hover:text-blue-400')
                else:
                    # Text + Icon when expanded
                    ui.icon('chevron_left').classes('text-sm')
                    ui.label('Collapse').classes('text-sm font-medium')