from components.sidebar import sidebar

def product_sidebar(active_tab: str):
    menu_items = [
        ('RegComply', 'regcomply', 'grid_view'),
        ('RegWatch', 'regwatch', 'category'),
        ('RegPort', 'regport', 'folder'),
        ('AI Analytics', 'ai', 'analytics'),
    ]
    sidebar(menu_items=menu_items, active_tab=active_tab, title="Products")
