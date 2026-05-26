from nicegui import ui, app
import asyncio
import inspect
from components.sidebar import create_sidebar
from components.header import create_header
from components.theme_manager import ThemeManager




async def dashboard_layout(content_func, page_title: str = "Dashboard", page_subtitle: str = None, active_page: str = ''):
    """
    Main dashboard layout wrapper that combines header, sidebar, and content area.
    
    Args:
        content_func: Function that renders the page content
        page_title: Title to display in header
        page_subtitle: Subtitle to display in header
        active_page: Current page path for sidebar highlighting
    """
    
    # Check if user is logged in
    is_logged_in = app.storage.user.get('logged_in', False)
    if not is_logged_in:
        app.storage.user['email'] = 'admin@opex.ai'
        app.storage.user['first_name'] = 'Demo'
        app.storage.user['last_name'] = 'Admin'
        app.storage.user['role'] = 'admin'
        app.storage.user['logged_in'] = True
        app.storage.user['auth_method'] = 'password'
        is_logged_in = True
    
    # Check sidebar collapse state
    is_collapsed = app.storage.user.get('sidebar_collapsed', False)
    sidebar_width = '80px' if is_collapsed else '260px'
    
    # Create sidebar (full height, fixed)
    create_sidebar(active_page)
    
    # Create header (fixed, full width)
    create_header(page_title, page_subtitle)
    
    # Main content area (scrollable, positioned after header and sidebar)
    # Adjust left margin based on sidebar width
    with ui.column().classes('w-full overflow-y-auto').style(
        f'padding: 28px 32px; padding-top: 88px; min-height: 100vh; '
        f'margin-left: {sidebar_width}; width: calc(100% - {sidebar_width}); '
        f'{ThemeManager.get_bg_gradient()} '
        f'transition: margin-left 0.3s ease, width 0.3s ease;'
    ):
        # Call the content function to render page-specific content
        if inspect.iscoroutinefunction(content_func):
            await content_func()
        else:
            content_func()