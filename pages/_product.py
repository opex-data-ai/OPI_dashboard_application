'''from nicegui import ui
from fastapi import Request
from config import THEME


# Map sidebar tabs to friendly titles 
# 
DOMAIN_TITLES = { 'regcomply': 'RegComply Performance', 
                 'regwatch': 'RegWatch Performance', ''
                 'regport': 'RegPort Performance', 
                 'ai': 'AI Analytics' }
def show_product_page(request: Request):
    active_domain = request.query_params.get('tab', 'regcomply')

    page_title = DOMAIN_TITLES.get(active_domain, 'Product Performance')
    ui.label(page_title).classes(f'{THEME["font_heading"]} mb-4')


    # Define horizontal tabs for this domain
    if active_domain == 'regcomply':
        tabs_list = ['Tab 1', 'Tab 2', 'Tab 3']
        panels_content = [
            'RegComply Tab 1 Content',
            'RegComply Tab 2 Content',
            'RegComply Tab 3 Content',
        ]
    elif active_domain == 'regport':
        tabs_list = ['Tab A', 'Tab B', 'Tab C']
        panels_content = [
            'RegPort Tab A Content',
            'RegPort Tab B Content',
            'RegPort Tab C Content',
        ]
    else:
        tabs_list = ['Tab 1', 'Tab 2', 'Tab 3']
        panels_content = [f'{active_domain} {t} content' for t in tabs_list]

    # Create horizontal tabs
    with ui.tabs().classes('mb-4') as tabs:
        tab_objects = [ui.tab(name) for name in tabs_list]

    # Tab panels
    with ui.tab_panels(tabs, value=tabs_list[0]):
        for tab_obj, content in zip(tab_objects, panels_content):
            with ui.tab_panel(tab_obj):
                ui.label(content).classes(THEME["font_body"])
'''