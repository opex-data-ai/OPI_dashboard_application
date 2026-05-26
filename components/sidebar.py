from nicegui import ui, app


from config import FEATURES

def get_abbreviation(title: str) -> str:
    # If it's CamelCase or has spaces, take uppercase letters
    upper_chars = [c for c in title if c.isupper()]
    if len(upper_chars) >= 2:
        return "".join(upper_chars[:2])
    # Otherwise take first two letters uppercase
    return title[:2].upper()

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
            background: #0f172a;
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
                    ui.image('/assets/img/logo_dark.png').classes('w-full h-8 object-contain m-2')
                else:
                    ui.image('/assets/img/logo_dark.png').classes('h-10 w-10 object-contain flex-shrink-0')
                    with ui.column().classes('gap-0'):
                        ui.label('Product').classes('text-indigo-400 font-extrabold tracking-wider uppercase text-[10px] leading-tight')
                        ui.label('Intelligence').classes('text-sm font-black text-slate-100 leading-tight')
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
                        'title': 'AI Analyst',
                        'icon': 'psychology',
                        'path': 'ai_insights',
                        'feature': 'ai_insights',
                        'children': None,
                        'beta': True
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
                        is_active = active_page == item['path'] or (active_page.startswith(base_path) and base_path != active_page)
                        
                        with ui.column().classes('w-full items-center gap-1.5 py-2'):
                            # Render parent icon (styled consistently)
                            with ui.button(icon=item['icon'], on_click=lambda p=item['path']: ui.navigate.to(f'/{p}')).props('flat').classes(
                                'w-12 h-12 rounded-xl bg-indigo-500/20 text-indigo-400 border-l-[3px] border-indigo-500 shadow-md' if is_active else
                                'w-12 h-12 rounded-xl text-white hover:bg-white/10 transition-all duration-200'
                            ):
                                ui.tooltip(item['title'])
                            
                            # Render sub-items if present
                            if item['children']:
                                with ui.column().classes('w-full items-center gap-2 mt-1'):
                                    for child in item['children']:
                                        is_child_active = active_page == child['path']
                                        abbrev = get_abbreviation(child['title'])
                                        
                                        with ui.button(on_click=lambda p=child['path']: ui.navigate.to(f'/{p}')).props('flat').classes(
                                            'w-8 h-8 rounded-full bg-indigo-500/20 text-indigo-400 border border-indigo-500/50 shadow-sm font-bold text-[9px] p-0' if is_child_active else
                                            'w-8 h-8 rounded-full bg-white/10 text-slate-300 hover:bg-white/20 hover:text-white transition-all duration-200 text-[9px] font-bold p-0 border border-slate-700/30'
                                        ):
                                            ui.label(abbrev).classes('font-bold tracking-tight')
                                            ui.tooltip(child['title'])
                    
                    elif item['children']:
                        # Item with dropdown (expanded mode)
                        # Keep dropdown open if we're on any of its child pages
                        is_expanded = is_parent_active
                        
                        with ui.expansion(item['title'], icon=item['icon'], value=is_expanded).classes(
                            'w-full text-white' if is_parent_active else 'w-full text-slate-300'
                        ).props('dense dark').style(
                            'background: rgba(99, 102, 241, 0.1); border-left: 3px solid #6366f1;' if is_parent_active else
                            'background: transparent;'
                        ) as exp:
                            # CLICK HANDLER FOR NAVIGATION ON THE EXPANSION HEADER
                            exp.on('click', lambda p=item['path']: ui.navigate.to(f'/{p}'))
                            
                            for child in item['children']:
                                is_child_active = active_page == child['path']
                                
                                with ui.item(on_click=lambda p=child['path']: ui.navigate.to(f'/{p}')).classes(
                                    'w-full pl-12 py-2 rounded-lg transition-all duration-200'
                                ).style(
                                    'background: rgba(99, 102, 241, 0.15); color: #818cf8; font-weight: 600;' if is_child_active else 
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
                            'background: rgba(99, 102, 241, 0.1); border-left: 3px solid #6366f1; color: #ffffff; font-weight: 600;' if is_active else
                            'background: transparent; color: #cbd5e1;'
                        ):
                            with ui.row().classes('w-full items-center justify-between'):
                                with ui.row().classes('items-center gap-3'):
                                    ui.icon(item['icon']).classes('text-xl' + (' drop-shadow-lg' if is_active else ''))
                                    ui.item_label(item['title']).classes('text-sm font-medium')
                                
                                if item.get('beta'):
                                    with ui.element('div').classes(
                                        'px-1.5 py-0.5 rounded text-[8px] font-bold uppercase tracking-wider'
                                    ).style(
                                        'background: #fef3c7; color: #d97706; border: 0.5px solid #fcd34d;' if is_active else
                                        'background: rgba(254, 243, 199, 0.15); color: #fcd34d; border: 0.5px solid rgba(252, 211, 77, 0.3);'
                                    ):
                                        ui.label('Beta')

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